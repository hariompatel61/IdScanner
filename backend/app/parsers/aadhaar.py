"""
Aadhaar Card Parser — Extracts structured fields from Aadhaar card OCR output.

Fields extracted (ALL mandatory for front-side capture):
    - Name
    - DOB
    - Gender
    - Aadhaar Number (12-digit, Verhoeff-validated)

If any field is missing or low-confidence, overall_status = 'rescan_required'
and the frontend will reject the scan rather than returning partial data.
"""

import re
from typing import List
from app.extractors.line_reconstructor import OCRLine
from app.parsers.base import BaseDocParser, FieldResult, ParsedDocument
from app.core.config import settings
from app.validators.field_validators import validate_name, clean_name_text
from app.extractors.verhoeff import validate_verhoeff

_DIGITS_ONLY_RE = re.compile(r'[^\d]')
_OO_SWAP_RE = re.compile(r'[Oo]')
_AADHAAR_NUM_RE = re.compile(r'\b(\d{4})[\s\-]?[Oo0]?[\s\-]?(\d{4})[\s\-]?[Oo0]?[\s\-]?(\d{4})\b')


class AadhaarParser(BaseDocParser):
    MANDATORY_FIELDS = ["name", "dob", "gender", "aadhaar_number"]
    OPTIONAL_FIELDS = []

    def extract_fields(self, ocr_lines: List[OCRLine]) -> ParsedDocument:
        fields = {}

        # 1. Extract DOB
        fields["dob"] = self._extract_date_near_anchor(ocr_lines, "dob")

        # 2. Extract Gender
        fields["gender"] = self._extract_gender_near_anchor(ocr_lines)

        # 3. Extract Name
        name_res = self._extract_name_near_anchor(ocr_lines, "name")
        if name_res.status != "ok" or not name_res.value:
            heur_res = self._aadhaar_name_heuristic(ocr_lines)
            if heur_res.status == "ok" and heur_res.value:
                name_res = heur_res
            elif name_res.status == "not_found":
                name_res = heur_res
        fields["name"] = name_res

        # 4. Extract Aadhaar Number (12-digit, Verhoeff-validated)
        # This ensures ALL four mandatory fields go through _build_result's
        # confidence gate — a blurry/unreadable number triggers rescan_required.
        fields["aadhaar_number"] = self._extract_aadhaar_number(ocr_lines)

        return self._build_result(fields)

    def _extract_aadhaar_number(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """Extract and Verhoeff-validate the 12-digit Aadhaar number."""
        best_value = None
        best_conf = 0.0
        for line in ocr_lines:
            for match in _AADHAAR_NUM_RE.finditer(line.text):
                raw = _DIGITS_ONLY_RE.sub('', _OO_SWAP_RE.sub('0', match.group(0)))
                if len(raw) == 12 and validate_verhoeff(raw):
                    if line.confidence > best_conf:
                        best_conf = line.confidence
                        best_value = raw
        if best_value:
            status = "ok" if best_conf >= settings.field_confidence_threshold else "low_confidence"
            return FieldResult(value=best_value, confidence=round(best_conf, 4), status=status)
        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _aadhaar_name_heuristic(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """
        Heuristic: On Aadhaar cards, the cardholder's name is usually the first
        valid name line that appears after the government header and before the DOB/gender lines.
        Strict 'no guessing' rules:
        - Never picks up relation prefix lines (S/O, D/O, W/O, C/O).
        - Never picks up UIDAI authority header text or address fragments.
        - Requires validate_name() to pass (which now rejects address stopwords, headers, relation prefixes).
        """
        _RELATION_PREFIX_RE = re.compile(
            r'^(?:S/O|S/0|D/O|D/0|W/O|W/0|C/O|C/0|F/O|M/O|Son\s*of|Daughter\s*of|Wife\s*of|Care\s*of'
            r'|\u0906\u0924\u094d\u092e\u091c|\u0938\u0941\u092a\u0941\u0924\u094d\u0930|\u092a\u0941\u0924\u094d\u0930'
            r'|\u092a\u0924\u094d\u0928\u0940|\u092e\u093e\u0924\u093e|\u092a\u093f\u0924\u093e)[\s:\-\.]*',
            re.I
        )
        _AADHAAR_BACK_MARKER_RE = re.compile(
            r'(address|p\.o\.?\s*box|unique\s*identification\s*authority|help@uidai|www\.uidai'
            r'|village|district|tehsil|post\s*office|pin\s*code|pincode|\bpo\b)',
            re.I
        )

        for line in ocr_lines:
            text = line.text.strip()

            if len(text) < 4:
                continue

            # Skip lines with 4-digit blocks or full digits
            if re.match(r'^\d{4}', text) or re.search(r'\b\d{4}\s+\d{4}\s+\d{4}\b', text):
                continue

            # Skip known header patterns and labels
            if re.search(r'(government|india|\u092d\u093e\u0930\u0924|\u0938\u0930\u0915\u093e\u0930|uidai|aadhaar|download|issue|vid|dob|\u091c\u0928\u094d\u092e|male|female|\u092a\u0941\u0930\u0941\u0937|\u092e\u0939\u093f\u0932\u093e|\bter\b|\bhteit\b)', text, re.I):
                continue

            # Skip relation prefix lines (Aadhaar back-side marker)
            if _RELATION_PREFIX_RE.match(text):
                continue

            # Skip Aadhaar back address / footer markers
            if _AADHAAR_BACK_MARKER_RE.search(text):
                continue

            cleaned = clean_name_text(text)
            if validate_name(cleaned):
                words = cleaned.split()
                if len(words) >= 2 or (len(words) == 1 and len(words[0]) >= 4):
                    status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                    return FieldResult(value=cleaned, confidence=round(line.confidence, 4), status=status)

        return FieldResult(value=None, confidence=0.0, status="not_found")

