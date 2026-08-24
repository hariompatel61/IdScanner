"""
ABHA Card Parser — Extracts structured fields from ABHA card OCR output.

Fields extracted:
    - Name (mandatory)
    - Gender (mandatory)
    - DOB (mandatory)
    - Mobile Number (optional — only fully visible 10-digit numbers, masked numbers are skipped)
"""

import re
from typing import List
from app.extractors.line_reconstructor import OCRLine
from app.parsers.base import BaseDocParser, FieldResult, ParsedDocument
from app.core.config import settings
from app.validators.field_validators import validate_name, clean_name_text, validate_mobile, normalize_mobile


class ABHAParser(BaseDocParser):
    MANDATORY_FIELDS = ["name", "gender", "dob"]
    OPTIONAL_FIELDS = ["mobile"]

    def extract_fields(self, ocr_lines: List[OCRLine]) -> ParsedDocument:
        fields = {}

        # 1. Extract Name
        fields["name"] = self._extract_abha_name(ocr_lines)

        # 2. Extract Gender
        fields["gender"] = self._extract_gender_near_anchor(ocr_lines)

        # 3. Extract DOB
        fields["dob"] = self._extract_date_near_anchor(ocr_lines, "dob")

        # 4. Extract Mobile Number (optional, unmasked only)
        fields["mobile"] = self._extract_mobile(ocr_lines)

        return self._build_result(fields)

    def _extract_abha_name(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """
        Extract name from ABHA card by finding Name anchor and evaluating the best person name candidate.
        """
        # 1. Look for Name anchor line
        name_anchor_idx = None
        for i, l in enumerate(ocr_lines):
            cleaned = re.sub(r'[^\w\s]', '', l.text).lower().strip()
            if cleaned == "name" or re.search(r'^name\s*[/:\-]', l.text, re.I):
                name_anchor_idx = i
                break

        if name_anchor_idx is not None:
            # Check lines following the name anchor
            candidates = []
            for offset in range(1, 5):
                if name_anchor_idx + offset < len(ocr_lines):
                    candidate_line = ocr_lines[name_anchor_idx + offset]
                    text = candidate_line.text.strip()
                    # Skip ABHA number, header, or labels
                    if re.search(r'(abha|account|health|gender|date|birth|mobile|instruction|toll-free|cop|copy|sample)', text, re.I):
                        continue
                    cleaned = clean_name_text(text)
                    if validate_name(cleaned):
                        word_count = len(cleaned.split())
                        candidates.append((word_count, candidate_line.confidence, cleaned))

            if candidates:
                # Prioritize multi-word names (e.g. First + Middle + Last name) and high confidence
                candidates.sort(key=lambda c: (c[0] > 1, c[1]), reverse=True)
                best = candidates[0]
                status = "ok" if best[1] >= settings.field_confidence_threshold else "low_confidence"
                return FieldResult(value=best[2], confidence=round(best[1], 4), status=status)

        # 2. Fallback: Search all lines before ABHA number / Gender
        fallback_candidates = []
        for line in ocr_lines:
            text = line.text.strip()
            if len(text) < 3:
                continue
            if re.search(r'(ayushman|bharat|health|account|national|authority|abha|instructions|toll-free|digital|records|gender|date|birth|mobile|cop|copy|sample)', text, re.I):
                continue
            if re.search(r'\d', text) or '@' in text:
                continue
            cleaned = clean_name_text(text)
            if validate_name(cleaned):
                word_count = len(cleaned.split())
                fallback_candidates.append((word_count, line.confidence, cleaned))

        if fallback_candidates:
            fallback_candidates.sort(key=lambda c: (c[0] > 1, c[1]), reverse=True)
            best = fallback_candidates[0]
            status = "ok" if best[1] >= settings.field_confidence_threshold else "low_confidence"
            return FieldResult(value=best[2], confidence=round(best[1], 4), status=status)

        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _extract_mobile(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """
        Extract mobile number from ABHA card.
        Only extracts fully visible 10-digit Indian mobile numbers.
        Masked numbers (containing X, *, etc.) are skipped.
        """
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
