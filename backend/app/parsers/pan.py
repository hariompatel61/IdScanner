"""
PAN Card Parser — Extracts structured fields from PAN card OCR output.

Fields extracted:
    - Name (mandatory)
    - Father's Name (mandatory)
    - DOB (mandatory)
"""

import re
from typing import List
from app.extractors.line_reconstructor import OCRLine
from app.parsers.base import DocumentPlugin, DocumentSchema, FieldResult, ParsedDocument
from app.parsers.registry import document_registry

from app.core.config import settings
from app.validators.field_validators import validate_name, clean_name_text

_PAN_PATTERN = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', re.IGNORECASE)

class PANPlugin(DocumentPlugin):
    document_id = "pan_card"
    display_name = "PAN Card"
    aliases = ["pan"]
    supported_sides = ["front"]
    schema = DocumentSchema(
        expected_fields=["name", "father_name", "dob", "pan_number"],
        mandatory_fields=["name", "father_name", "dob"]
    )
    
    MANDATORY_FIELDS = ["name", "father_name", "dob"]
    OPTIONAL_FIELDS = []

    def extract_fields(self, ocr_lines: List[OCRLine]) -> ParsedDocument:
        fields = {}

        # 1. Extract DOB
        fields["dob"] = self._extract_date_near_anchor(ocr_lines, "dob")

        # 2. Extract Name & Father's Name
        # Check explicit anchor first if both exist and have clear values
        name_res = self._extract_name_near_anchor(ocr_lines, "name")
        father_res = self._extract_name_near_anchor(ocr_lines, "father_name")

        if (
            name_res.status == "ok"
            and father_res.status == "ok"
            and name_res.value != father_res.value
        ):
            fields["name"] = name_res
            fields["father_name"] = father_res
            return self._build_result(fields)

        # PAN Card Layout Extraction:
        # Collect distinct valid candidate person names
        name_candidates = []
        for line in ocr_lines:
            text = line.text.strip()

            if len(text) < 3:
                continue

            # Skip PAN number pattern
            if re.match(r'^[A-Z]{5}\d{4}[A-Z]$', text.upper()):
                continue

            # Skip dates and numbers
            if re.search(r'\b\d{2}[/\-\.]\d{2}[/\-\.]\d{4}\b', text) or re.match(r'^\d+$', text):
                continue

            # Skip header patterns and labels
            if re.search(r'(income|tax|department|permanent|account|card|govt|india|signature|date|birth|dob|father|name)', text, re.I):
                continue

            cleaned = clean_name_text(text)
            if validate_name(cleaned):
                name_candidates.append((cleaned, line.confidence))

        if len(name_candidates) >= 2:
            fields["name"] = FieldResult(
                value=name_candidates[0][0],
                confidence=round(name_candidates[0][1], 4),
                status="ok" if name_candidates[0][1] >= settings.field_confidence_threshold else "low_confidence"
            )
            fields["father_name"] = FieldResult(
                value=name_candidates[1][0],
                confidence=round(name_candidates[1][1], 4),
                status="ok" if name_candidates[1][1] >= settings.field_confidence_threshold else "low_confidence"
            )
        elif len(name_candidates) == 1:
            fields["name"] = FieldResult(
                value=name_candidates[0][0],
                confidence=round(name_candidates[0][1], 4),
                status="ok" if name_candidates[0][1] >= settings.field_confidence_threshold else "low_confidence"
            )
            fields["father_name"] = father_res if father_res.status != "not_found" else FieldResult(value=None, confidence=0.0, status="not_found")
        else:
            fields["name"] = name_res
            fields["father_name"] = father_res

        fields["pan_number"] = self._extract_pan_number(ocr_lines)
        return self._build_result(fields)

    def _extract_pan_number(self, ocr_lines: List[OCRLine]) -> FieldResult:
        best_value, best_conf = None, 0.0
        for line in ocr_lines:
            for match in _PAN_PATTERN.finditer(line.text):
                val = match.group(0).upper()
                if line.confidence > best_conf:
                    best_conf = line.confidence
                    best_value = val
        if best_value:
            status = "ok" if best_conf >= settings.field_confidence_threshold else "low_confidence"
            return FieldResult(value=best_value, confidence=round(best_conf, 4), status=status)
        return FieldResult(value=None, confidence=0.0, status="not_found")

PANParser = PANPlugin
document_registry.register(PANPlugin())
