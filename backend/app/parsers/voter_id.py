"""
Voter ID (EPIC) Parser — Extracts structured fields from Voter ID card OCR output.

Fields extracted:
    - Name (mandatory)
    - Relation Name / Relation Type (Mother/Father/Husband/Other) (mandatory)
    - Specific relation field: mother_name / father_name / husband_name / other_name
    - Gender (optional — on back of some voter IDs)
    - DOB or Age (optional — on back of some voter IDs)
"""

import re
from typing import List, Tuple, Optional
from app.extractors.line_reconstructor import OCRLine
from app.parsers.base import BaseDocParser, FieldResult, ParsedDocument
from app.core.config import settings
from app.validators.field_validators import validate_name, clean_name_text


class VoterIDParser(BaseDocParser):
    MANDATORY_FIELDS = ["name", "relation_name"]
    OPTIONAL_FIELDS = ["gender", "dob", "relation_type"]

    def extract_fields(self, ocr_lines: List[OCRLine]) -> ParsedDocument:
        fields = {}

        # 1. Extract Relation Name and Exact Relation Type (Mother/Father/Husband/Other)
        relation_res, rel_type = self._extract_relation_name_and_type(ocr_lines)
        fields["relation_name"] = relation_res

        if relation_res.status == "ok" and rel_type != "Unknown":
            fields["relation_type"] = FieldResult(value=rel_type, confidence=relation_res.confidence, status="ok")

        # 2. Extract Elector Name (making sure it doesn't collide with relation name)
        fields["name"] = self._extract_elector_name(ocr_lines, relation_val=relation_res.value)

        # 3. Disambiguate if name and relation_name collided
        if (
            fields["name"].status == "ok"
            and fields["relation_name"].status == "ok"
            and fields["name"].value == fields["relation_name"].value
        ):
            fields["name"] = self._disambiguate_elector_name(ocr_lines, fields["relation_name"].value)

        # 4. Extract Gender (if present)
        fields["gender"] = self._extract_gender_near_anchor(ocr_lines)

        # 5. Extract DOB or Age (if present)
        fields["dob"] = self._extract_dob_or_age(ocr_lines)

        return self._build_result(fields)

    def _extract_elector_name(self, ocr_lines: List[OCRLine], relation_val: str = None) -> FieldResult:
        # 1. English line with Elector's Name (excluding Header 'ELECTOR PHOTO IDENTITY CARD')
        for idx, line in enumerate(ocr_lines):
            if re.search(r'elector(?:\'s)?\s*name', line.text, re.I) and not re.search(r'(photo|ident|card|आयोग)', line.text, re.I):
                cleaned = clean_name_text(line.text)
                if cleaned and validate_name(cleaned):
                    if not relation_val or cleaned != relation_val:
                        status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                        return FieldResult(value=cleaned, confidence=round(line.confidence, 4), status=status)
                # If name is below the label
                for next_idx in range(idx + 1, min(idx + 4, len(ocr_lines))):
                    sub_cleaned = clean_name_text(ocr_lines[next_idx].text)
                    if sub_cleaned and validate_name(sub_cleaned):
                        if not relation_val or sub_cleaned != relation_val:
                            status = "ok" if ocr_lines[next_idx].confidence >= settings.field_confidence_threshold else "low_confidence"
                            return FieldResult(value=sub_cleaned, confidence=round(ocr_lines[next_idx].confidence, 4), status=status)

        # 2. Explicit "Name:" line (that is NOT a relation line)
        for idx, line in enumerate(ocr_lines):
            if re.search(r'\bname\b', line.text, re.I) and not re.search(r'(father|mother|husband|relation|आईचे|वडिलांचे|पतीचे|माता|पिता|other|s/o|w/o|d/o|m/o)', line.text, re.I):
                cleaned = clean_name_text(line.text)
                if cleaned and validate_name(cleaned):
                    if not relation_val or cleaned != relation_val:
                        status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                        return FieldResult(value=cleaned, confidence=round(line.confidence, 4), status=status)

        # 3. Devanagari मतदाराचे नाव or नाव (that is NOT a relation line)
        for idx, line in enumerate(ocr_lines):
            if re.search(r'मतदाराचे\s*नाव', line.text, re.I) or (re.search(r'नाव', line.text) and not re.search(r'(आईचे|वडिलांचे|पतीचे|माता|पिता)', line.text)):
                cleaned = clean_name_text(line.text)
                if cleaned and validate_name(cleaned):
                    if not relation_val or cleaned != relation_val:
                        status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                        return FieldResult(value=cleaned, confidence=round(line.confidence, 4), status=status)

        # 4. Anchor search for "name"
        name_res = self._extract_name_near_anchor(ocr_lines, "name")
        if name_res.status != "not_found" and validate_name(name_res.value):
            if not relation_val or name_res.value != relation_val:
                return name_res

        # 5. Positional fallback: find first valid name line above relation line that is not header
        for line in ocr_lines:
            text = line.text.strip()
            if len(text) < 4:
                continue
            if re.search(r'(election|commission|elector|photo|identity|card|epic|भारत|आयोग|ओळख|पत्र|government|india|father|mother|husband|आईचे|वडिलांचे|पतीचे|माता|पिता|\b[A-Z]{3}\d{7}\b|\d{4})', text, re.I):
                continue
            cleaned = clean_name_text(text)
            if cleaned and validate_name(cleaned) and len(cleaned.split()) >= 2:
                if not relation_val or cleaned != relation_val:
                    status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                    return FieldResult(value=cleaned, confidence=round(line.confidence, 4), status=status)

        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _disambiguate_elector_name(self, ocr_lines: List[OCRLine], relation_val: str) -> FieldResult:
        """Finds true elector name if it was erroneously assigned the relation name."""
        relation_clean = clean_name_text(relation_val)
        for line in ocr_lines:
            text = line.text.strip()
            if re.search(r'(father|mother|husband|आईचे|वडिलांचे|पतीचे|माता|पिता|other|s/o|w/o|d/o|m/o)', text, re.I):
                continue
            if re.search(r'(election|commission|elector|photo|identity|card|epic|भारत|आयोग|ओळख|पत्र|government|india|\b[A-Z]{3}\d{7}\b|\d{4})', text, re.I):
                continue
            cleaned = clean_name_text(text)
            if cleaned and cleaned != relation_clean and validate_name(cleaned):
                status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                return FieldResult(value=cleaned, confidence=round(line.confidence, 4), status=status)
        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _find_relation_value(self, ocr_lines: List[OCRLine], idx: int, rel_type: str) -> Optional[FieldResult]:
        line = ocr_lines[idx]
        # 1. Try extracting value on same line
        cleaned = clean_name_text(line.text)
        if cleaned and validate_name(cleaned):
            status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
            return FieldResult(value=cleaned, confidence=round(line.confidence, 4), status=status)

        # 2. If same line is purely label (e.g. "MotherName", "Mother's Name"), check lines below it
        for next_idx in range(idx + 1, min(idx + 4, len(ocr_lines))):
            next_line = ocr_lines[next_idx]
            sub_cleaned = clean_name_text(next_line.text)
            if sub_cleaned and validate_name(sub_cleaned):
                status = "ok" if next_line.confidence >= settings.field_confidence_threshold else "low_confidence"
                return FieldResult(value=sub_cleaned, confidence=round(next_line.confidence, 4), status=status)

        return None

    def _extract_relation_name_and_type(self, ocr_lines: List[OCRLine]) -> Tuple[FieldResult, str]:
        # 1. Mother's Name / आईचे नाव / माता
        for idx, line in enumerate(ocr_lines):
            if re.search(r'(?:mother(?:\'s)?(?:\s*name|\w{0,3})?|आईचे(?:\s*नाव)?|माता(?:\s*का\s*नाम)?|\bm/o\b|mother\s*of)', line.text, re.I):
                res = self._find_relation_value(ocr_lines, idx, "Mother")
                if res:
                    return res, "Mother"

        for label_key in ["mother_name"]:
            result = self._extract_name_near_anchor(ocr_lines, label_key)
            if result.status != "not_found" and validate_name(result.value):
                return result, "Mother"

        # 2. Husband's Name / पतीचे नाव / पति
        for idx, line in enumerate(ocr_lines):
            if re.search(r'(?:husband(?:\'s)?(?:\s*name|\w{0,3})?|पतीचे(?:\s*नाव)?|पति(?:\s*का\s*नाम)?|\bw/o\b|wife\s*of)', line.text, re.I):
                res = self._find_relation_value(ocr_lines, idx, "Husband")
                if res:
                    return res, "Husband"

        for label_key in ["husband_name"]:
            result = self._extract_name_near_anchor(ocr_lines, label_key)
            if result.status != "not_found" and validate_name(result.value):
                return result, "Husband"

        # 3. Father's Name / वडिलांचे नाव / पिता
        for idx, line in enumerate(ocr_lines):
            if re.search(r'(?:father(?:\'s)?(?:\s*name|\w{0,3})?|वडिलांचे(?:\s*नाव)?|पिता(?:\s*का\s*नाम)?|\bs/o\b|son\s*of|\bd/o\b|daughter\s*of)', line.text, re.I):
                res = self._find_relation_value(ocr_lines, idx, "Father")
                if res:
                    return res, "Father"

        for label_key in ["father_name", "daughter_of"]:
            result = self._extract_name_near_anchor(ocr_lines, label_key)
            if result.status != "not_found" and validate_name(result.value):
                return result, "Father"

        # 4. Other / Generic Relation
        for idx, line in enumerate(ocr_lines):
            if re.search(r'^(?:other|relation(?:\s*name)?|नातेदाराचे(?:\s*नाव)?|संबंधी(?:\s*का\s*नाम)?|\bc/o\b)', line.text, re.I):
                res = self._find_relation_value(ocr_lines, idx, "Other")
                if res:
                    return res, "Other"

        for label_key in ["relation_name"]:
            result = self._extract_name_near_anchor(ocr_lines, label_key)
            if result.status != "not_found" and validate_name(result.value):
                return result, "Other"

        return FieldResult(value=None, confidence=0.0, status="not_found"), "Unknown"

    def _extract_dob_or_age(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """
        Extract DOB or Age, whichever is present.
        """
        dob_result = self._extract_date_near_anchor(ocr_lines, "dob")
        if dob_result.status == "ok":
            return dob_result

        age_result = self._extract_age(ocr_lines)
        if age_result.status != "not_found":
            return age_result

        if dob_result.status == "low_confidence":
            return dob_result

        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _extract_age(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """Extract age from Voter ID cards that show age instead of DOB."""
        for line in ocr_lines:
            match = re.search(r'(?:age|आयु|उम्र|वय)\s*[:\-]?\s*(\d{1,3})', line.text, re.I)
            if match:
                age = int(match.group(1))
                if 1 <= age <= 150:
                    age_str = f"Age: {age}"
                    status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                    return FieldResult(value=age_str, confidence=round(line.confidence, 4), status=status)

        return FieldResult(value=None, confidence=0.0, status="not_found")
