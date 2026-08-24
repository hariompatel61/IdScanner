"""
Base document parser with shared helpers for anchor-based field extraction.

All document parsers inherit from BaseDocParser and implement extract_fields().
Each parser locates label anchors in OCR output, then extracts the value from
the nearest line below/right of the anchor or directly from the line itself.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from app.extractors.line_reconstructor import OCRLine
from app.extractors.labels import LABELS
from app.core.config import settings
from app.validators.field_validators import (
    validate_date,
    normalize_date,
    extract_date_from_text,
    normalize_gender,
    validate_mobile,
    normalize_mobile,
    clean_name_text,
    validate_name,
)


@dataclass
class FieldResult:
    """Result of extracting a single field from OCR output."""
    value: Optional[str] = None
    confidence: float = 0.0
    status: str = "not_found"  # "ok" | "low_confidence" | "not_found"


@dataclass
class ParsedDocument:
    """Aggregated result of parsing all fields from a document."""
    fields: Dict[str, FieldResult] = field(default_factory=dict)
    overall_status: str = "ok"  # "ok" | "rescan_required"
    failed_fields: List[str] = field(default_factory=list)


class BaseDocParser:
    """
    Base class for document-specific parsers.

    Subclasses must define:
        MANDATORY_FIELDS: List[str] — fields that must be extracted for a successful scan.
        OPTIONAL_FIELDS: List[str] — fields that are extracted if present, but don't block.

    And implement:
        extract_fields(ocr_lines: List[OCRLine]) -> ParsedDocument
    """

    MANDATORY_FIELDS: List[str] = []
    OPTIONAL_FIELDS: List[str] = []

    def extract_fields(self, ocr_lines: List[OCRLine]) -> ParsedDocument:
        raise NotImplementedError

    # ── Shared Helpers ──────────────────────────────────────────────

    def _find_anchor(
        self,
        ocr_lines: List[OCRLine],
        label_key: str,
    ) -> Optional[int]:
        """
        Searches OCR lines for a label anchor matching any variant in LABELS[label_key].
        """
        label_variants = LABELS.get(label_key, [])
        if not label_variants:
            return None

        for idx, line in enumerate(ocr_lines):
            cleaned_line = re.sub(r'[^\w\s]', ' ', line.text).lower()
            line_words = set(cleaned_line.split())
            
            # When searching for cardholder name, never match a relation line (father, mother, husband, etc.)
            if label_key == "name":
                if any(rel in cleaned_line for rel in ["father", "mother", "husband", "आईचे", "वडिलांचे", "पतीचे", "माता", "पिता", "other", "s o", "w o", "d o", "m o"]):
                    continue
            
            for variant in label_variants:
                variant_cleaned = re.sub(r'[^\w\s]', ' ', variant).lower().strip()
                variant_words = variant_cleaned.split()
                
                if len(variant_words) == 1:
                    if variant_words[0] in line_words or variant_cleaned in cleaned_line:
                        return idx
                else:
                    if variant_cleaned in cleaned_line or all(w in line_words for w in variant_words):
                        return idx

        return None

    def _get_value_same_line(
        self,
        ocr_lines: List[OCRLine],
        anchor_idx: int,
        label_key: str,
    ) -> Tuple[Optional[str], float]:
        """
        Extracts the value portion from the same line as the anchor.
        E.g. 'Name:Hari.OmPatel' -> 'Hari Om Patel'
             'Father\'s Name: Ramesh Patel' -> 'Ramesh Patel'
        """
        line = ocr_lines[anchor_idx]
        text = line.text.strip()

        # If the line is purely the label itself (e.g. "Name", "Name/"), skip same-line extraction
        if self._is_label_line(text):
            return None, 0.0

        cleaned = clean_name_text(text)
        if cleaned and validate_name(cleaned):
            return cleaned, line.confidence

        for delimiter in [":", "-", "=", "/", "."]:
            if delimiter in text:
                parts = text.split(delimiter, 1)
                if len(parts) == 2:
                    val = clean_name_text(parts[1])
                    if val and validate_name(val):
                        return val, line.confidence

        return None, 0.0

    def _get_value_below_anchor(
        self,
        ocr_lines: List[OCRLine],
        anchor_idx: int,
    ) -> Tuple[Optional[str], float]:
        """
        Returns text from the nearest line below the anchor that is a valid name.
        """
        anchor_line = ocr_lines[anchor_idx]
        anchor_x = anchor_line.x_start

        candidates = []
        for idx in range(anchor_idx + 1, min(anchor_idx + 4, len(ocr_lines))):
            line = ocr_lines[idx]
            text = line.text.strip()

            if not text or self._is_label_line(text):
                continue

            cleaned = clean_name_text(text)
            if cleaned and validate_name(cleaned):
                dist = abs(line.x_start - anchor_x)
                candidates.append((dist, cleaned, line.confidence))

        if candidates:
            candidates.sort(key=lambda c: c[0])
            return candidates[0][1], candidates[0][2]

        return None, 0.0

    def _is_label_line(self, text: str) -> bool:
        """Check if a text line is purely a known label (not a value)."""
        from app.validators.field_validators import is_pure_label_line
        if is_pure_label_line(text):
            return True
        cleaned = re.sub(r'[^\w\s]', '', text).lower().strip()
        for label_key, variants in LABELS.items():
            for variant in variants:
                var_clean = re.sub(r'[^\w\s]', '', variant).lower().strip()
                if cleaned == var_clean:
                    return True
        return False

    def _extract_date_near_anchor(
        self,
        ocr_lines: List[OCRLine],
        label_key: str = "dob",
    ) -> FieldResult:
        """Extract and validate a date field, ignoring download/issue dates."""
        # 1. First priority: look for line containing DOB/birth/जन्म keywords
        for line in ocr_lines:
            if re.search(r'(dob|birth|जन्म|तारीख|age)', line.text, re.I) and not re.search(r'(download|issue)', line.text, re.I):
                d = extract_date_from_text(line.text)
                if d and validate_date(d):
                    status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                    return FieldResult(value=d, confidence=round(line.confidence, 4), status=status)

        # 2. Second priority: anchor index line and line below it
        anchor_idx = self._find_anchor(ocr_lines, label_key)
        if anchor_idx is not None:
            anchor_line = ocr_lines[anchor_idx]
            d = extract_date_from_text(anchor_line.text)
            if d and validate_date(d):
                status = "ok" if anchor_line.confidence >= settings.field_confidence_threshold else "low_confidence"
                return FieldResult(value=d, confidence=round(anchor_line.confidence, 4), status=status)

            for idx in range(anchor_idx + 1, min(anchor_idx + 3, len(ocr_lines))):
                sub_line = ocr_lines[idx]
                d = extract_date_from_text(sub_line.text)
                if d and validate_date(d):
                    status = "ok" if sub_line.confidence >= settings.field_confidence_threshold else "low_confidence"
                    return FieldResult(value=d, confidence=round(sub_line.confidence, 4), status=status)

        # 3. Third priority: search all lines, explicitly excluding download/issue/valid/print
        for line in ocr_lines:
            if re.search(r'(download|issue|valid|print|expiry)', line.text, re.I):
                continue
            d = extract_date_from_text(line.text)
            if d and validate_date(d):
                status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                return FieldResult(value=d, confidence=round(line.confidence, 4), status=status)

        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _extract_gender_near_anchor(
        self,
        ocr_lines: List[OCRLine],
    ) -> FieldResult:
        """Extract and validate a gender field."""
        for line in ocr_lines:
            g = normalize_gender(line.text)
            if g:
                status = "ok" if line.confidence >= settings.field_confidence_threshold else "low_confidence"
                return FieldResult(value=g, confidence=round(line.confidence, 4), status=status)

        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _extract_name_near_anchor(
        self,
        ocr_lines: List[OCRLine],
        label_key: str = "name",
    ) -> FieldResult:
        """Extract and validate a name field near a label anchor."""
        anchor_idx = self._find_anchor(ocr_lines, label_key)
        if anchor_idx is None:
            return FieldResult(value=None, confidence=0.0, status="not_found")

        # Try same-line first
        value, conf = self._get_value_same_line(ocr_lines, anchor_idx, label_key)
        if value and validate_name(value):
            status = "ok" if conf >= settings.field_confidence_threshold else "low_confidence"
            return FieldResult(value=value, confidence=round(conf, 4), status=status)

        # Fall back to next line below
        value, conf = self._get_value_below_anchor(ocr_lines, anchor_idx)
        if value and validate_name(value):
            status = "ok" if conf >= settings.field_confidence_threshold else "low_confidence"
            return FieldResult(value=value, confidence=round(conf, 4), status=status)

        return FieldResult(value=None, confidence=0.0, status="not_found")

    def _build_result(
        self,
        fields: Dict[str, FieldResult],
    ) -> ParsedDocument:
        """
        Build final ParsedDocument with confidence aggregation and rescan decision.
        """
        failed: List[str] = []

        for field_name, result in fields.items():
            if result.status == "ok":
                if result.confidence < settings.field_confidence_threshold:
                    result.status = "low_confidence"
                    result.value = None
            elif result.status in ("low_confidence", "not_found"):
                result.value = None

        for field_name in self.MANDATORY_FIELDS:
            field_result = fields.get(field_name)
            if not field_result or field_result.status in ("low_confidence", "not_found"):
                failed.append(field_name)

        overall_status = "rescan_required" if failed else "ok"

        return ParsedDocument(
            fields=fields,
            overall_status=overall_status,
            failed_fields=failed,
        )
