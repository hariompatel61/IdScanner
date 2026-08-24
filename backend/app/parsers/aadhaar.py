"""
Aadhaar Card Parser — Extracts structured fields from Aadhaar card OCR output.

Fields extracted:
    - Name (mandatory)
    - DOB (mandatory)
    - Gender (mandatory)

VID is NOT extracted per project requirements.
"""

import re
from typing import List
from app.extractors.line_reconstructor import OCRLine
from app.parsers.base import BaseDocParser, FieldResult, ParsedDocument
from app.core.config import settings
from app.validators.field_validators import validate_name, clean_name_text


class AadhaarParser(BaseDocParser):
    MANDATORY_FIELDS = ["name", "dob", "gender"]
    OPTIONAL_FIELDS = []

    def extract_fields(self, ocr_lines: List[OCRLine]) -> ParsedDocument:
        fields = {}

        # 1. Extract DOB
        fields["dob"] = self._extract_date_near_anchor(ocr_lines, "dob")

        # 2. Extract Gender
        fields["gender"] = self._extract_gender_near_anchor(ocr_lines)

        # 3. Extract Name
        fields["name"] = self._extract_name_near_anchor(ocr_lines, "name")

        if fields["name"].status == "not_found":
            fields["name"] = self._aadhaar_name_heuristic(ocr_lines)

        return self._build_result(fields)

    def _aadhaar_name_heuristic(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """
        Heuristic: On Aadhaar cards, the cardholder's name is usually the first
        valid name line that appears after the government header and before the DOB/gender lines.
        """
        for line in ocr_lines:
            text = line.text.strip()

            if len(text) < 4:
                continue

            # Skip lines with 4-digit blocks or full digits
            if re.match(r'^\d{4}', text) or re.search(r'\b\d{4}\s+\d{4}\s+\d{4}\b', text):
                continue

            # Skip known header patterns and labels
            if re.search(r'(government|india|भारत|सरकार|uidai|aadhaar|download|issue|vid|dob|जन्म|male|female|पुरुष|महिला|\bter\b|\bhteit\b)', text, re.I):
                continue

            cleaned = clean_name_text(text)
            if validate_name(cleaned):
                words = cleaned.split()
                if len(words) >= 2 or (len(words) == 1 and len(words[0]) >= 4):
                    status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                    return FieldResult(value=cleaned, confidence=round(line.confidence, 4), status=status)

        return FieldResult(value=None, confidence=0.0, status="not_found")
