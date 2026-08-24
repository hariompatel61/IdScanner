"""
Voter ID (EPIC) Parser — Extracts structured fields from Voter ID card OCR output.

Fields extracted:
    - Name (mandatory)
    - Relation Name / Father Name / Mother Name (mandatory)
    - Gender (optional — on back of some voter IDs)
    - DOB or Age (optional — on back of some voter IDs)
"""

import re
from typing import List
from app.extractors.line_reconstructor import OCRLine
from app.parsers.base import BaseDocParser, FieldResult, ParsedDocument
from app.core.config import settings
from app.validators.field_validators import validate_name, clean_name_text


class VoterIDParser(BaseDocParser):
    MANDATORY_FIELDS = ["name", "relation_name"]
    OPTIONAL_FIELDS = ["gender", "dob"]

    def extract_fields(self, ocr_lines: List[OCRLine]) -> ParsedDocument:
        fields = {}

        # 1. Extract Relation Name (Mother/Father/Husband/Other) first
        relation_res = self._extract_relation_name(ocr_lines)
        fields["relation_name"] = relation_res

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
        # 1. English line with Elector's Name
        for line in ocr_lines:
            if re.search(r'elector(?:\'s)?\s*name', line.text, re.I):
                cleaned = clean_name_text(line.text)
                if cleaned and validate_name(cleaned):
                    status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                    return FieldResult(value=cleaned, confidence=round(line.confidence, 4), status=status)

        # 2. Explicit "Name:" line (that is NOT a relation line)
        for line in ocr_lines:
            if re.search(r'\bname\b', line.text, re.I) and not re.search(r'(father|mother|husband|relation|आईचे|वडिलांचे|पतीचे|माता|पिता|other|s/o|w/o|d/o|m/o)', line.text, re.I):
                cleaned = clean_name_text(line.text)
                if cleaned and validate_name(cleaned):
                    status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                    return FieldResult(value=cleaned, confidence=round(line.confidence, 4), status=status)

        # 3. Devanagari मतदाराचे नाव or नाव (that is NOT a relation line)
        for line in ocr_lines:
            if re.search(r'मतदाराचे\s*नाव', line.text, re.I) or (re.search(r'नाव', line.text) and not re.search(r'(आईचे|वडिलांचे|पतीचे|माता|पिता)', line.text)):
                cleaned = clean_name_text(line.text)
                if cleaned and validate_name(cleaned):
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

    def _extract_relation_name(self, ocr_lines: List[OCRLine]) -> FieldResult:
        # 1. English line with Mother's / Father's / Husband's Name
        for line in ocr_lines:
            if re.search(r'(?:mother(?:\'s)?\s*name|father(?:\'s)?\s*name|husband(?:\'s)?\s*name)', line.text, re.I):
                cleaned = clean_name_text(line.text)
                if cleaned and validate_name(cleaned):
                    status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                    return FieldResult(value=cleaned, confidence=round(line.confidence, 4), status=status)

        # 2. Devanagari आईचे / वडिलांचे / पतीचे / माता / पिता का नाम
        for line in ocr_lines:
            if re.search(r'(?:आईचे\s*नाव|वडिलांचे\s*नाव|पतीचे\s*नाव|माता\s*का\s*नाम|पिता\s*का\s*नाम)', line.text, re.I):
                cleaned = clean_name_text(line.text)
                if cleaned and validate_name(cleaned):
                    status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                    return FieldResult(value=cleaned, confidence=round(line.confidence, 4), status=status)

        for label_key in ["mother_name", "relation_name", "father_name", "husband_name", "daughter_of"]:
            result = self._extract_name_near_anchor(ocr_lines, label_key)
            if result.status != "not_found" and validate_name(result.value):
                return result

        for line in ocr_lines:
            if re.search(r'^(other|father|mother|husband|relation|आईचे|वडिलांचे|पतीचे|s/o|w/o|d/o|m/o)\s*[:\-\/\.\s]', line.text, re.I):
                cleaned = clean_name_text(line.text)
                if validate_name(cleaned):
                    status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                    return FieldResult(value=cleaned, confidence=round(line.confidence, 4), status=status)

        return FieldResult(value=None, confidence=0.0, status="not_found")

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
