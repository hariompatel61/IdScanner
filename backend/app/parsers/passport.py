"""
Passport Parser — Extracts structured fields from Indian and International Passport OCR output.

Supports both:
    1. MRZ (Machine Readable Zone — ICAO Doc 9303 Type 3)
    2. VIZ (Visual Inspection Zone — Given Names, Surname, DOB, Gender, Expiry Date, Nationality)

Fields extracted:
    - Name (mandatory)
    - DOB (mandatory)
    - Gender (mandatory)
    - Surname (optional)
    - Given Name (optional)
    - Expiry Date (optional)
    - Nationality (optional)
"""

import re
from typing import List, Optional, Tuple
from app.extractors.line_reconstructor import OCRLine
from app.parsers.base import BaseDocParser, FieldResult, ParsedDocument
from app.core.config import settings
from app.extractors.labels import LABELS, GENDER_MAP
from app.validators.field_validators import (
    validate_name,
    clean_name_text,
    validate_dob,
    normalize_dob,
    validate_expiry_date,
    normalize_expiry_date,
)


class PassportParser(BaseDocParser):
    MANDATORY_FIELDS = ["name", "gender", "dob"]
    OPTIONAL_FIELDS = ["surname", "given_name", "expiry_date", "nationality"]

    def extract_fields(self, ocr_lines: List[OCRLine]) -> ParsedDocument:
        fields = {}

        # First, attempt to parse from MRZ if 2 MRZ lines are detected
        mrz_data = self._parse_mrz(ocr_lines)

        # 1. Extract Surname & Given Name & Name
        surname_res, given_res, name_res = self._extract_names(ocr_lines, mrz_data)
        fields["name"] = name_res
        if surname_res and surname_res.value:
            fields["surname"] = surname_res
        if given_res and given_res.value:
            fields["given_name"] = given_res

        # 2. Extract DOB
        if mrz_data.get("dob"):
            fields["dob"] = mrz_data["dob"]
        else:
            fields["dob"] = self._extract_date_near_anchor(ocr_lines, "dob")

        # 3. Extract Gender
        if mrz_data.get("gender"):
            fields["gender"] = mrz_data["gender"]
        else:
            fields["gender"] = self._extract_gender_near_anchor(ocr_lines)

        # 4. Extract Expiry Date
        if mrz_data.get("expiry_date"):
            fields["expiry_date"] = mrz_data["expiry_date"]
        else:
            fields["expiry_date"] = self._extract_expiry_date(ocr_lines)

        # 5. Extract Nationality
        if mrz_data.get("nationality"):
            fields["nationality"] = mrz_data["nationality"]
        else:
            fields["nationality"] = self._extract_nationality(ocr_lines)

        return self._build_result(fields)

    def _parse_mrz(self, ocr_lines: List[OCRLine]) -> dict:
        """
        Parse ICAO Doc 9303 standard 2-line MRZ (Type 3) if present.
        Line 1: P<IND<SURNAME<<GIVEN<NAMES<<<<<<<<<<<<<<<<<<
        Line 2: Z1234567<0IND9106105M3408151<<<<<<<<<<<<<<02
        """
        mrz_results = {}
        line1, line2 = None, None
        conf1, conf2 = 0.95, 0.95

        for line in ocr_lines:
            text = line.text.replace(' ', '').upper()
            if text.startswith('P<') or text.startswith('P<<'):
                line1 = text
                conf1 = line.confidence
            elif re.search(r'^[A-Z0-9<]{9}[0-9][A-Z]{3}[0-9]{6}', text):
                line2 = text
                conf2 = line.confidence

        if line1:
            # Parse names from line 1: P<CTY<SURNAME<<GIVEN<NAMES<<<<
            body = re.sub(r'^P<[A-Z]{3}', '', line1).strip('<')
            if '<<' in body:
                parts = body.split('<<', 1)
                surname = clean_name_text(parts[0].replace('<', ' '))
                given_name = clean_name_text(parts[1].replace('<', ' '))
            else:
                surname = ""
                given_name = clean_name_text(body.replace('<', ' '))

            full_name = f"{given_name} {surname}".strip() if surname else given_name
            status1 = "ok" if conf1 >= settings.field_confidence_threshold else "low_confidence"

            if full_name:
                mrz_results["name"] = FieldResult(value=full_name, confidence=round(conf1, 4), status=status1)
            if surname:
                mrz_results["surname"] = FieldResult(value=surname, confidence=round(conf1, 4), status=status1)
            if given_name:
                mrz_results["given_name"] = FieldResult(value=given_name, confidence=round(conf1, 4), status=status1)

        if line2:
            # Line 2: [PassNo:9][Chk:1][Nat:3][DOB:6 YYMMDD][Chk:1][Sex:1][Exp:6 YYMMDD][Chk:1]
            status2 = "ok" if conf2 >= settings.field_confidence_threshold else "low_confidence"
            match = re.search(r'([A-Z]{3})([0-9]{6})[0-9]([MF<])([0-9]{6})', line2)
            if match:
                nat_code, raw_dob, sex_char, raw_exp = match.groups()
                
                # DOB
                dob_fmt = self._mrz_date_to_dmy(raw_dob, is_dob=True)
                if dob_fmt:
                    mrz_results["dob"] = FieldResult(value=dob_fmt, confidence=round(conf2, 4), status=status2)

                # Gender
                gender = "Male" if sex_char == 'M' else "Female" if sex_char == 'F' else "Transgender"
                mrz_results["gender"] = FieldResult(value=gender, confidence=round(conf2, 4), status=status2)

                # Expiry
                exp_fmt = self._mrz_date_to_dmy(raw_exp, is_dob=False)
                if exp_fmt:
                    mrz_results["expiry_date"] = FieldResult(value=exp_fmt, confidence=round(conf2, 4), status=status2)

                # Nationality
                nat_name = "INDIAN" if nat_code == "IND" else nat_code
                mrz_results["nationality"] = FieldResult(value=nat_name, confidence=round(conf2, 4), status=status2)

        return mrz_results

    def _mrz_date_to_dmy(self, yymmdd: str, is_dob: bool = True) -> Optional[str]:
        if len(yymmdd) != 6 or not yymmdd.isdigit():
            return None
        yy = int(yymmdd[0:2])
        mm = yymmdd[2:4]
        dd = yymmdd[4:6]

        if is_dob:
            # Assume 1900s for yy > 25, 2000s for yy <= 25
            century = 2000 if yy <= 26 else 1900
            full_year = century + yy
            formatted = f"{dd}/{mm}/{full_year}"
            if validate_dob(formatted):
                return formatted
        else:
            # Expiry date is usually future (2000s)
            century = 2000
            full_year = century + yy
            formatted = f"{dd}/{mm}/{full_year}"
            if validate_expiry_date(formatted):
                return formatted
        return None

    def _extract_names(
        self,
        ocr_lines: List[OCRLine],
        mrz_data: dict
    ) -> Tuple[Optional[FieldResult], Optional[FieldResult], FieldResult]:
        """Extract Surname, Given Name, and full Name from VIZ or fallback to MRZ."""
        surname_res = mrz_data.get("surname")
        given_res = mrz_data.get("given_name")

        # 1. Search VIZ for explicit Surname anchor
        viz_surname, sur_conf = self._find_value_near_labels(ocr_lines, LABELS["surname"])
        if viz_surname:
            cleaned_sur = clean_name_text(viz_surname)
            if validate_name(cleaned_sur):
                status = "ok" if sur_conf >= settings.field_confidence_threshold else "low_confidence"
                surname_res = FieldResult(value=cleaned_sur, confidence=round(sur_conf, 4), status=status)

        # 2. Search VIZ for explicit Given Name anchor
        viz_given, giv_conf = self._find_value_near_labels(ocr_lines, LABELS["given_name"])
        if viz_given:
            cleaned_giv = clean_name_text(viz_given)
            if validate_name(cleaned_giv):
                status = "ok" if giv_conf >= settings.field_confidence_threshold else "low_confidence"
                given_res = FieldResult(value=cleaned_giv, confidence=round(giv_conf, 4), status=status)

        # 3. Construct Full Name
        if given_res and surname_res and given_res.value and surname_res.value:
            full_name = f"{given_res.value} {surname_res.value}".strip()
            avg_conf = round((given_res.confidence + surname_res.confidence) / 2, 4)
            status = "ok" if avg_conf >= settings.field_confidence_threshold else "low_confidence"
            name_res = FieldResult(value=full_name, confidence=avg_conf, status=status)
            return surname_res, given_res, name_res

        if mrz_data.get("name"):
            return surname_res, given_res, mrz_data["name"]

        # 4. Fallback search for general "Name" anchor
        viz_name, name_conf = self._find_value_near_labels(ocr_lines, LABELS["name"])
        if viz_name:
            cleaned = clean_name_text(viz_name)
            if validate_name(cleaned):
                status = "ok" if name_conf >= settings.field_confidence_threshold else "low_confidence"
                return surname_res, given_res, FieldResult(value=cleaned, confidence=round(name_conf, 4), status=status)

        return surname_res, given_res, FieldResult(value=None, confidence=0.0, status="not_found")

    def _find_value_near_labels(
        self,
        ocr_lines: List[OCRLine],
        label_list: List[str]
    ) -> Tuple[Optional[str], float]:
        """Find value on the same line or line immediately following a label."""
        for i, line in enumerate(ocr_lines):
            text_lower = line.text.lower().strip()
            for lbl in label_list:
                pattern = rf'^(?:{re.escape(lbl)})[\s:\-]+(.*)$'
                match = re.match(pattern, text_lower, re.I)
                if match:
                    rem = match.group(1).strip()
                    if rem and len(rem) > 1:
                        # Extract exact casing from original text
                        orig_val = line.text[match.start(1):match.end(1)].strip()
                        return orig_val, line.confidence
                    elif i + 1 < len(ocr_lines):
                        next_line = ocr_lines[i + 1]
                        if not re.search(r'(passport|dob|sex|gender|nationality|expiry|place|issue|type|country)', next_line.text, re.I):
                            return next_line.text.strip(), next_line.confidence
        return None, 0.0

    def _extract_expiry_date(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """Extract Expiry Date from VIZ."""
        exp_text, conf = self._find_value_near_labels(ocr_lines, LABELS["expiry_date"])
        if exp_text:
            cleaned = normalize_expiry_date(exp_text)
            if cleaned and validate_expiry_date(cleaned):
                status = "ok" if conf >= settings.field_confidence_threshold else "low_confidence"
                return FieldResult(value=cleaned, confidence=round(conf, 4), status=status)

        # Search any line for expiry date near anchor
        for line in ocr_lines:
            if re.search(r'(expiry|valid\s*until|valid\s*upto|expires)', line.text, re.I):
                date_m = re.search(r'\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b', line.text)
                if date_m:
                    norm = normalize_expiry_date(date_m.group(1))
                    if norm and validate_expiry_date(norm):
                        status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                        return FieldResult(value=norm, confidence=round(line.confidence, 4), status=status)

        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _extract_nationality(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """Extract Nationality from VIZ."""
        nat_text, conf = self._find_value_near_labels(ocr_lines, LABELS["nationality"])
        if nat_text:
            val = nat_text.upper().strip()
            if re.search(r'IND', val):
                val = "INDIAN"
            status = "ok" if conf >= settings.field_confidence_threshold else "low_confidence"
            return FieldResult(value=val, confidence=round(conf, 4), status=status)

        for line in ocr_lines:
            if re.search(r'\b(INDIAN|INDIA)\b', line.text, re.I):
                status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                return FieldResult(value="INDIAN", confidence=round(line.confidence, 4), status=status)

        return FieldResult(value=None, confidence=0.0, status="not_found")
