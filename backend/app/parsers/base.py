import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from app.parsers.models import FieldResult

from app.ocr.models import OCRLine
from app.extractors.labels import LABELS
from app.validators.field_validators import validate_name, clean_name_text, validate_date, extract_date_from_text, normalize_gender
from app.core.config import settings
from app.parsers.candidate import FieldCandidate, CandidateResolver

@dataclass
class ParsedDocument:
    """Aggregated result of parsing all fields from a document."""
    fields: Dict[str, FieldResult] = field(default_factory=dict)
    overall_status: str = "ok"  # "ok" | "rescan_required"
    failed_fields: List[str] = field(default_factory=list)

@dataclass
class DocumentSchema:
    expected_fields: List[str]
    mandatory_fields: List[str]

class BaseDocParser:
    document_id: str = ""
    extractor = None
    display_name: str = ""
    aliases: List[str] = []
    supported_sides: List[str] = ["front"]
    schema: DocumentSchema = DocumentSchema([], [])
    version: str = "1.0.0"

    MANDATORY_FIELDS: List[str] = []
    OPTIONAL_FIELDS: List[str] = []

    def __init__(self):
        if not self.MANDATORY_FIELDS:
            self.MANDATORY_FIELDS = self.schema.mandatory_fields
        if not self.OPTIONAL_FIELDS:
            self.OPTIONAL_FIELDS = [f for f in self.schema.expected_fields if f not in self.schema.mandatory_fields]

    def extract_fields(self, ocr_lines: List[OCRLine]) -> ParsedDocument:
        """To be implemented by subclasses"""
        raise NotImplementedError

    def _find_anchor(self, ocr_lines: List[OCRLine], label_key: str) -> Optional[int]:
        label_variants = LABELS.get(label_key, [])
        if not label_variants: return None
        for idx, line in enumerate(ocr_lines):
            cleaned_line = re.sub(r'[^\w\s]', ' ', line.text).lower()
            line_words = set(cleaned_line.split())
            if label_key == "name":
                if any(rel in cleaned_line for rel in ["father", "mother", "husband", "other", "s o", "w o", "d o", "m o"]):
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

    def _get_value_same_line(self, ocr_lines: List[OCRLine], anchor_idx: int, label_key: str) -> Tuple[Optional[str], float]:
        line = ocr_lines[anchor_idx]
        cleaned = clean_name_text(line.text)
        if cleaned: return cleaned, line.confidence
        return None, 0.0

    def _get_value_below_anchor(self, ocr_lines: List[OCRLine], anchor_idx: int) -> Tuple[Optional[str], float]:
        anchor_line = ocr_lines[anchor_idx]
        anchor_x = anchor_line.x_start
        cands = []
        for idx in range(anchor_idx + 1, min(anchor_idx + 4, len(ocr_lines))):
            line = ocr_lines[idx]
            text = line.text.strip()
            if not text or self._is_label_line(text): continue
            cleaned = clean_name_text(text)
            if cleaned and validate_name(cleaned):
                dist = abs(line.x_start - anchor_x)
                cands.append((dist, cleaned, line.confidence))
        if cands:
            cands.sort(key=lambda c: c[0])
            return cands[0][1], cands[0][2]
        return None, 0.0

    def _is_label_line(self, text: str) -> bool:
        from app.validators.field_validators import is_pure_label_line
        if is_pure_label_line(text): return True
        cleaned = re.sub(r'[^\w\s]', '', text).lower().strip()
        for label_key, variants in LABELS.items():
            for variant in variants:
                var_clean = re.sub(r'[^\w\s]', '', variant).lower().strip()
                if cleaned == var_clean: return True
        return False

    def _extract_date_candidates(self, ocr_lines: List[OCRLine], label_key: str = "dob") -> List[FieldCandidate]:
        _HELPLINE_PATTERN = re.compile(r'\b(1947|1800[-\s]?\d{3}[-\s]?\d{3,4}|14477)\b')
        def _is_helpline_only_line(text: str) -> bool:
            if re.search(r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b', text): return False
            stripped = re.sub(r'[\s\-\(\):]', '', text)
            return bool(re.fullmatch(r'(1947|18003001947|18001801947|1800114477|14477)', stripped))

        candidates = []
        for line in ocr_lines:
            if _is_helpline_only_line(line.text): continue
            if re.search(r'(dob|birth|age)', line.text, re.I) and not re.search(r'(download|issue)', line.text, re.I):
                d = extract_date_from_text(line.text)
                if d:
                    status = "valid" if validate_date(d) else "invalid"
                    candidates.append(FieldCandidate(value=d, raw_value=line.text, confidence=line.confidence, source="label_match_inline", polygon=line.bbox, validation_status=status))

        anchor_idx = self._find_anchor(ocr_lines, label_key)
        if anchor_idx is not None:
            anchor_line = ocr_lines[anchor_idx]
            if not _is_helpline_only_line(anchor_line.text):
                d = extract_date_from_text(anchor_line.text)
                if d:
                    status = "valid" if validate_date(d) else "invalid"
                    candidates.append(FieldCandidate(value=d, raw_value=anchor_line.text, confidence=anchor_line.confidence, source="label_match_anchor", polygon=anchor_line.bbox, validation_status=status))
            for idx in range(anchor_idx + 1, min(anchor_idx + 3, len(ocr_lines))):
                sub_line = ocr_lines[idx]
                if _is_helpline_only_line(sub_line.text): continue
                d = extract_date_from_text(sub_line.text)
                if d:
                    status = "valid" if validate_date(d) else "invalid"
                    candidates.append(FieldCandidate(value=d, raw_value=sub_line.text, confidence=sub_line.confidence, source="label_match_below", polygon=sub_line.bbox, validation_status=status))

        _FULL_DATE_PATTERN = re.compile(r'\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b')
        for line in ocr_lines:
            if re.search(r'(download|issue|valid|print|expiry)', line.text, re.I): continue
            if _is_helpline_only_line(line.text) or _HELPLINE_PATTERN.search(line.text): continue
            if _FULL_DATE_PATTERN.search(line.text):
                d = extract_date_from_text(line.text)
                if d:
                    status = "valid" if validate_date(d) else "invalid"
                    candidates.append(FieldCandidate(value=d, raw_value=line.text, confidence=line.confidence, source="pattern_match", polygon=line.bbox, validation_status=status))
        return candidates

    def _extract_date_near_anchor(self, ocr_lines: List[OCRLine], label_key: str = "dob") -> FieldResult:
        candidates = self._extract_date_candidates(ocr_lines, label_key)
        return CandidateResolver.resolve(candidates, FieldResult)

    def _extract_gender_candidates(self, ocr_lines: List[OCRLine]) -> List[FieldCandidate]:
        candidates = []
        for line in ocr_lines:
            g = normalize_gender(line.text)
            if g:
                candidates.append(FieldCandidate(value=g, raw_value=line.text, confidence=line.confidence, source="pattern_match", polygon=line.bbox, validation_status="valid"))
        return candidates

    def _extract_gender_near_anchor(self, ocr_lines: List[OCRLine]) -> FieldResult:
        candidates = self._extract_gender_candidates(ocr_lines)
        return CandidateResolver.resolve(candidates, FieldResult)

    def _extract_name_candidates(self, ocr_lines: List[OCRLine], label_key: str = "name") -> List[FieldCandidate]:
        candidates = []
        anchor_idx = self._find_anchor(ocr_lines, label_key)
        if anchor_idx is None: return candidates

        value, conf = self._get_value_same_line(ocr_lines, anchor_idx, label_key)
        if value:
            status = "valid" if validate_name(value) else "invalid"
            candidates.append(FieldCandidate(value=value, raw_value=value, confidence=conf, source="label_match_same_line", validation_status=status))

        value, conf = self._get_value_below_anchor(ocr_lines, anchor_idx)
        if value:
            status = "valid" if validate_name(value) else "invalid"
            candidates.append(FieldCandidate(value=value, raw_value=value, confidence=conf, source="label_match_below", validation_status=status))
            
        return candidates

    def _extract_name_near_anchor(self, ocr_lines: List[OCRLine], label_key: str = "name") -> FieldResult:
        candidates = self._extract_name_candidates(ocr_lines, label_key)
        return CandidateResolver.resolve(candidates, FieldResult)

    def _build_result(self, fields: Dict[str, FieldResult]) -> ParsedDocument:
        failed = []
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
        return ParsedDocument(fields=fields, overall_status=overall_status, failed_fields=failed)

DocumentPlugin = BaseDocParser
