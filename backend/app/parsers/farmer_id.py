"""
Farmer ID / Agriculture Card Parser — Extracts structured fields from Agri Record / Farmer ID OCR output.

Fields extracted:
    - Name (mandatory)
    - Gender (mandatory)
    - DOB (mandatory)
    - Mobile (optional)
    - Aadhaar Number (optional)
"""

import re
from typing import List
from app.extractors.line_reconstructor import OCRLine
from app.parsers.base import DocumentPlugin, DocumentSchema
from app.parsers.registry import document_registry
from app.parsers.base import FieldResult, ParsedDocument
from app.core.config import settings
from app.validators.field_validators import (
    validate_name,
    clean_name_text,
    validate_mobile,
)
from app.extractors.verhoeff import validate_verhoeff


class FarmerIDPlugin(DocumentPlugin):
    document_id = "farmer_id"
    display_name = "Farmer ID"
    aliases = ["farmer"]
    supported_sides = ["front"]
    schema = DocumentSchema(expected_fields=["name", "dob", "gender", "farmer_id"], mandatory_fields=["name", "dob", "gender"])

    MANDATORY_FIELDS = ["name", "gender", "dob"]
    OPTIONAL_FIELDS = ["mobile", "aadhaar_number"]

    def extract_fields(self, ocr_lines: List[OCRLine]) -> ParsedDocument:
        fields = {}

        # 1. Extract Name
        fields["name"] = self._extract_farmer_name(ocr_lines)

        # 2. Extract DOB
        fields["dob"] = self._extract_date_near_anchor(ocr_lines, "dob")

        # 3. Extract Gender
        fields["gender"] = self._extract_gender_near_anchor(ocr_lines)

        # 4. Extract Mobile
        fields["mobile"] = self._extract_mobile(ocr_lines)

        # 5. Extract Aadhaar
        fields["aadhaar_number"] = self._extract_aadhaar(ocr_lines)

        return self._build_result(fields)

    def _extract_farmer_name(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """
        Extract farmer name from Agri card.
        Handles dual-script names (Hindi/English), preferring English Roman script if available.
        """
        candidates = []

        # 1. Look for explicit Name / नाम anchor line
        name_anchor_idx = None
        for i, l in enumerate(ocr_lines):
            cleaned_text = l.text.lower().strip()
            if re.search(r'^(?:नाम|name)[\s:\-]', cleaned_text, re.I):
                name_anchor_idx = i
                break

        if name_anchor_idx is not None:
            anchor_line = ocr_lines[name_anchor_idx]
            same_line_val = re.sub(r'^(?:नाम|name)[\s:\-]+', '', anchor_line.text, flags=re.I).strip()
            if same_line_val:
                cleaned = clean_name_text(same_line_val)
                if validate_name(cleaned):
                    candidates.append((len(cleaned.split()), anchor_line.confidence, cleaned))

            # Look up to 2 lines below name anchor
            for offset in [1, 2]:
                if name_anchor_idx + offset < len(ocr_lines):
                    next_line = ocr_lines[name_anchor_idx + offset]
                    if not re.search(r'(dob|gender|mobile|aadhaar|farmer|agri)', next_line.text, re.I):
                        cleaned = clean_name_text(next_line.text)
                        if validate_name(cleaned):
                            candidates.append((len(cleaned.split()), next_line.confidence, cleaned))

        # 2. Fallback scan if no anchor candidates
        if not candidates:
            for line in ocr_lines:
                text = line.text.strip()
                if re.search(r'(agri|record|farmer|kisan|dob|gender|mobile|aadhaar|download|id\b)', text, re.I):
                    continue
                if re.search(r'\d', text):
                    continue
                text_sub = re.sub(r'^(?:नाम|name)[\s:\-]+', '', text, flags=re.I).strip()
                cleaned = clean_name_text(text_sub if text_sub else text)
                if validate_name(cleaned):
                    candidates.append((len(cleaned.split()), line.confidence, cleaned))

        if candidates:
            # Sort prioritizing: English (Latin), multi-word, then confidence
            candidates.sort(key=lambda c: (bool(re.search(r'[A-Za-z]', c[2])), c[0] > 1, c[1]), reverse=True)
            best = candidates[0]
            status = "ok" if best[1] >= settings.field_confidence_threshold else "low_confidence"
            return FieldResult(value=best[2], confidence=round(best[1], 4), status=status)

        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _extract_mobile(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """Extract unmasked 10-digit mobile number."""
        for line in ocr_lines:
            if any(c in line.text for c in ['X', 'x', '*']):
                continue
            mobile_match = re.search(r'\b([6-9]\d{9})\b', line.text)
            if mobile_match:
                candidate = mobile_match.group(1)
                if validate_mobile(candidate):
                    status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                    return FieldResult(value=candidate, confidence=round(line.confidence, 4), status=status)
        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _extract_aadhaar(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """Extract 12-digit Aadhaar number from Aadhaar anchor or standalone line."""
        for line in ocr_lines:
            m = re.search(r'(?:aadhaar|uid)[\s:\-]*(\d{12})', line.text, re.I)
            if m:
                uid = m.group(1)
                if validate_verhoeff(uid):
                    status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                    return FieldResult(value=uid, confidence=round(line.confidence, 4), status=status)

            m2 = re.search(r'\b(\d{12})\b', line.text)
            if m2:
                uid = m2.group(1)
                if validate_verhoeff(uid):
                    status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                    return FieldResult(value=uid, confidence=round(line.confidence, 4), status=status)

        return FieldResult(value=None, confidence=0.0, status="not_found")

FarmerIDParser = FarmerIDPlugin
document_registry.register(FarmerIDPlugin())
