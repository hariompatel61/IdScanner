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
from app.parsers.base import DocumentPlugin, DocumentSchema
from app.parsers.registry import document_registry
from app.parsers.base import FieldResult, ParsedDocument
from app.core.config import settings
from app.validators.field_validators import validate_name, clean_name_text, validate_mobile, normalize_mobile


class ABHAPlugin(DocumentPlugin):
    document_id = "abha_card"
    display_name = "ABHA Card"
    aliases = ["abha"]
    supported_sides = ["front"]
    schema = DocumentSchema(expected_fields=["name", "abha_number", "dob", "gender", "mobile", "abha_address"], mandatory_fields=["name", "abha_number", "dob", "gender"])

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

        fields["abha_number"] = self._extract_abha_number(ocr_lines)
        return self._build_result(fields)

    # Relation prefix lines to always skip
    _RELATION_PREFIX_RE = re.compile(
        r'^(?:S/O|S/0|D/O|D/0|W/O|W/0|C/O|C/0|F/O|M/O|Son\s*of|Daughter\s*of|Wife\s*of|Care\s*of'
        r'|\u0906\u0924\u094d\u092e\u091c|\u0938\u0941\u092a\u0941\u0924\u094d\u0930|\u092a\u0941\u0924\u094d\u0930'
        r'|\u092a\u0924\u094d\u0928\u0940|\u092e\u093e\u0924\u093e|\u092a\u093f\u0924\u093e)[\s:\-\.]*',
        re.I
    )
    # Authority/header line markers to always skip
    _HEADER_LINE_RE = re.compile(
        r'(unique\s*identification|ayushman\s*bharat|national\s*health|government\s*of\s*india'
        r'|income\s*tax|election\s*commission|\u092d\u093e\u0930\u0924\u0940\u092f\s*\u0935\u093f\u0936\u093f\u0937\u094d\u091f'
        r'|\u092d\u093e\u0930\u0924\s*\u0938\u0930\u0915\u093e\u0930)',
        re.I
    )

    def _extract_abha_name(self, ocr_lines: List[OCRLine]) -> FieldResult:
        """
        Extract name from ABHA card by finding Name anchor and evaluating the best person name candidate.
        Strict 'no guessing' rules:
        - Rejects relation prefix lines (S/O, D/O, W/O, C/O etc.)
        - Rejects UIDAI / government authority header lines
        - Validates every candidate with validate_name() which rejects address/header/relation contamination
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
                    # Skip relation prefix lines (S/O, D/O, W/O etc.)
                    if self._RELATION_PREFIX_RE.match(text):
                        continue
                    # Skip authority header lines
                    if self._HEADER_LINE_RE.search(text):
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
            # Skip relation prefix lines (S/O, D/O, W/O etc.)
            if self._RELATION_PREFIX_RE.match(text):
                continue
            # Skip authority header lines
            if self._HEADER_LINE_RE.search(text):
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

    def _extract_abha_number(self, ocr_lines):
        import re
        _ABHA_NUMBER_PATTERN = re.compile(r"\b(\d{2})[\s\-]?(\d{4})[\s\-]?(\d{4})[\s\-]?(\d{4})\b")
        best_value, best_conf = None, 0.0
        for line in ocr_lines:
            for match in _ABHA_NUMBER_PATTERN.finditer(line.text):
                val = match.group(0)
                if line.confidence > best_conf:
                    best_conf = line.confidence
                    best_value = val
        if best_value:
            status = "ok" if best_conf >= settings.field_confidence_threshold else "low_confidence"
            return FieldResult(value=best_value, confidence=round(best_conf, 4), status=status)
        return FieldResult(value=None, confidence=0.0, status="not_found")

ABHAParser = ABHAPlugin
document_registry.register(ABHAPlugin())
