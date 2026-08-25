"""
Aadhaar Card Back Side Parser.

Extracts:
- aadhaar_number (12 digits, validated via Verhoeff algorithm)
- relation_type (S/O, D/O, W/O, C/O, M/O, etc.)
- relation_name (Name of father/husband/mother/guardian)
- address (Clean formatted full address string)
- state (Standardized Indian State / UT)
- pincode (6-digit Indian PIN code)
"""

import re
from typing import List, Optional, Tuple, Dict
from app.extractors.line_reconstructor import OCRLine
from app.parsers.base import BaseDocParser, FieldResult, ParsedDocument
from app.extractors.verhoeff import validate_verhoeff
from app.validators.field_validators import (
    clean_name_text,
    validate_name,
    extract_state_from_text,
    extract_pincode_from_text,
    validate_pincode,
    normalize_pincode
)


class AadhaarBackParser(BaseDocParser):
    MANDATORY_FIELDS = ["aadhaar_number", "address", "state", "pincode"]
    OPTIONAL_FIELDS = ["relation_type", "relation_name"]

    RELATION_PATTERNS = [
        (r'(?:^|[\s,;])(?:S/O|S/0|SO|S\\O|SON\s*OF|आत्मज|सुपुत्र|पुत्र)\s*[:\-\.]?\s*([A-Za-z\u0900-\u097F\s\.]+?)(?:,|$|\n|\d)', "S/O"),
        (r'(?:^|[\s,;])(?:D/O|D/0|DO|D\\O|DAUGHTER\s*OF|सुपुत्री|पुत्री|आत्मजा)\s*[:\-\.]?\s*([A-Za-z\u0900-\u097F\s\.]+?)(?:,|$|\n|\d)', "D/O"),
        (r'(?:^|[\s,;])(?:W/O|W/0|WO|W\\O|WIFE\s*OF|पत्नी)\s*[:\-\.]?\s*([A-Za-z\u0900-\u097F\s\.]+?)(?:,|$|\n|\d)', "W/O"),
        (r'(?:^|[\s,;])(?:C/O|C/0|CO|C\\O|CARE\s*OF)\s*[:\-\.]?\s*([A-Za-z\u0900-\u097F\s\.]+?)(?:,|$|\n|\d)', "C/O"),
        (r'(?:^|[\s,;])(?:F/O|F/0|FO|FATHER\s*OF|पिता)\s*[:\-\.]?\s*([A-Za-z\u0900-\u097F\s\.]+?)(?:,|$|\n|\d)', "S/O"),
        (r'(?:^|[\s,;])(?:M/O|M/0|MO|MOTHER\s*OF|माता)\s*[:\-\.]?\s*([A-Za-z\u0900-\u097F\s\.]+?)(?:,|$|\n|\d)', "M/O"),
    ]

    FOOTER_PATTERNS = re.compile(
        r'(?:VID|\b\d{4}\s?\d{4}\s?\d{4}\b|1947|uidai|help@|www\.|p\.o\.\s*box|bengaluru|unique\s*identification)',
        re.I
    )

    def extract_fields(self, ocr_lines: List[OCRLine]) -> ParsedDocument:
        if not ocr_lines:
            return self._build_result({})

        fields: Dict[str, FieldResult] = {}
        all_text = " ".join([l.text for l in ocr_lines])

        # 1. Extract Aadhaar Number
        fields["aadhaar_number"] = self._extract_aadhaar_number(ocr_lines)

        # 2. Extract Relation Type and Relation Name
        r_type_res, r_name_res = self._extract_relation(ocr_lines, all_text)
        fields["relation_type"] = r_type_res
        fields["relation_name"] = r_name_res

        # 3. Extract State
        fields["state"] = self._extract_state(ocr_lines, all_text)

        # 4. Extract PIN Code
        fields["pincode"] = self._extract_pincode(ocr_lines, all_text)

        # 5. Extract Address String
        fields["address"] = self._extract_address(ocr_lines)

        return self._build_result(fields)

    def _extract_aadhaar_number(self, ocr_lines: List[OCRLine]) -> FieldResult:
        pattern = re.compile(r'\b(\d{4})[\s\-]?[Oo0]?[\s\-]?(\d{4})[\s\-]?[Oo0]?[\s\-]?(\d{4})\b')
        best_num = None
        best_conf = 0.0

        for line in ocr_lines:
            text = line.text
            matches = pattern.finditer(text)
            for m in matches:
                raw_str = m.group(0)
                clean_str = re.sub(r'[Oo]', '0', raw_str)
                clean_str = re.sub(r'[^\d]', '', clean_str)
                if len(clean_str) == 12 and validate_verhoeff(clean_str):
                    if line.confidence > best_conf:
                        best_conf = line.confidence
                        best_num = clean_str

            # Check unspaced digits in line
            digits = re.sub(r'[^\d]', '', text)
            if len(digits) == 12 and validate_verhoeff(digits):
                if line.confidence > best_conf:
                    best_conf = line.confidence
                    best_num = digits

        if best_num:
            return FieldResult(
                value=best_num,
                confidence=best_conf,
                status="ok" if best_conf >= 0.70 else "low_confidence"
            )
        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _extract_relation(self, ocr_lines: List[OCRLine], all_text: str) -> Tuple[FieldResult, FieldResult]:
        for line in ocr_lines:
            for pattern, r_type in self.RELATION_PATTERNS:
                match = re.search(pattern, line.text, re.I)
                if match:
                    raw_name = match.group(1).strip()
                    cleaned_name = clean_name_text(raw_name)
                    if len(cleaned_name) >= 3 and validate_name(cleaned_name):
                        return (
                            FieldResult(value=r_type, confidence=line.confidence, status="ok"),
                            FieldResult(value=cleaned_name, confidence=line.confidence, status="ok")
                        )

        # Fallback search across concatenated text
        for pattern, r_type in self.RELATION_PATTERNS:
            match = re.search(pattern, all_text, re.I)
            if match:
                raw_name = match.group(1).strip()
                cleaned_name = clean_name_text(raw_name)
                if len(cleaned_name) >= 3 and validate_name(cleaned_name):
                    return (
                        FieldResult(value=r_type, confidence=0.85, status="ok"),
                        FieldResult(value=cleaned_name, confidence=0.85, status="ok")
                    )

        return (
            FieldResult(value=None, confidence=0.0, status="not_found"),
            FieldResult(value=None, confidence=0.0, status="not_found")
        )

    def _extract_state(self, ocr_lines: List[OCRLine], all_text: str) -> FieldResult:
        for line in ocr_lines:
            state = extract_state_from_text(line.text)
            if state:
                return FieldResult(value=state, confidence=line.confidence, status="ok")

        state = extract_state_from_text(all_text)
        if state:
            return FieldResult(value=state, confidence=0.85, status="ok")

        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _extract_pincode(self, ocr_lines: List[OCRLine], all_text: str) -> FieldResult:
        for line in ocr_lines:
            pin = extract_pincode_from_text(line.text)
            if pin:
                return FieldResult(value=pin, confidence=line.confidence, status="ok")

        pin = extract_pincode_from_text(all_text)
        if pin:
            return FieldResult(value=pin, confidence=0.85, status="ok")

        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _extract_address(self, ocr_lines: List[OCRLine]) -> FieldResult:
        address_segments: List[str] = []
        confidences: List[float] = []
        is_collecting = False

        for line in ocr_lines:
            text = line.text.strip()
            # Match Address header line
            if re.search(r'^(?:Address|पता|पत्ता|निवासाचा\s*पत्ता)\s*[:\-]?', text, re.I):
                is_collecting = True
                after = re.sub(r'^(?:Address|पता|पत्ता|निवासाचा\s*पत्ता)\s*[:\-]?\s*', '', text, flags=re.I).strip()
                if after:
                    address_segments.append(after)
                    confidences.append(line.confidence)
                continue

            if is_collecting:
                # Stop if reached bottom section / footer / aadhaar number / VID / uidai
                if self.FOOTER_PATTERNS.search(text):
                    break
                if text:
                    address_segments.append(text)
                    confidences.append(line.confidence)

        if not address_segments:
            # Fallback: find lines containing S/O, state, or pincode before the footer
            for line in ocr_lines:
                text = line.text.strip()
                if self.FOOTER_PATTERNS.search(text):
                    continue
                if re.search(r'(?:S/O|D/O|W/O|C/O|Haryana|Uttar\s*Pradesh|Maharashtra|Delhi|\b\d{6}\b)', text, re.I):
                    address_segments.append(text)
                    confidences.append(line.confidence)

        if not address_segments:
            return FieldResult(value=None, confidence=0.0, status="not_found")

        # Combine segments cleanly
        raw_combined = ", ".join(address_segments)
        
        # Clean delimiters and double commas
        cleaned = re.sub(r'\s*,\s*', ', ', raw_combined)
        cleaned = re.sub(r',\s*,+', ', ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ,.-')

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.85
        return FieldResult(value=cleaned, confidence=avg_conf, status="ok")
