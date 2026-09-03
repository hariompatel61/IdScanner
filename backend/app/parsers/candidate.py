from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from app.core.config import settings

@dataclass
class FieldCandidate:
    value: Any
    raw_value: str
    confidence: float
    source: str
    polygon: Optional[List[List[float]]] = None
    bbox: Optional[List[float]] = None
    score: float = 0.0
    validation_status: str = "unknown"

@dataclass
class ResolvedField:
    value: Any
    confidence: float
    source: str
    raw_value: str
    normalized_value: Any
    validation_status: str
    candidates: List[FieldCandidate] = field(default_factory=list)

class CandidateResolver:
    @staticmethod
    def resolve(candidates: List[FieldCandidate], field_result_cls: Any) -> Any:
        if not candidates:
            return field_result_cls(value=None, confidence=0.0, status="not_found")
            
        valid_candidates = []
        for c in candidates:
            score = c.confidence
            if c.validation_status in ("ok", "valid", "valid_format", "checksum_valid"):
                score += 0.5
            elif c.validation_status in ("invalid", "invalid_format", "checksum_invalid"):
                score -= 1.0
                
            if c.source == "label_match_inline":
                score += 2.0
            elif c.source == "label_match_same_line":
                score += 1.5
            elif c.source == "label_match_anchor":
                score += 1.5
            elif c.source == "label_match_below":
                score += 1.0
            elif c.source == "pattern_match":
                score += 0.0
            elif c.source == "document_rule":
                score += 0.5
                
            c.score = score
            valid_candidates.append(c)
            
        valid_candidates.sort(key=lambda x: x.score, reverse=True)
        best = valid_candidates[0]
        
        if best.validation_status in ("invalid", "invalid_format", "checksum_invalid"):
            return field_result_cls(value=None, confidence=0.0, status="not_found")
            
        status = "ok" if best.confidence >= settings.field_confidence_threshold else "low_confidence"
        
        from app.parsers.models import FieldConfidence, ValidationResult
        ext_conf = best.confidence
        if best.source.startswith("label_match"): ext_conf = min(1.0, ext_conf + 0.1)
        if best.source == "document_rule": ext_conf = min(1.0, ext_conf + 0.05)
        
        fc = FieldConfidence(ocr_confidence=best.confidence, extraction_confidence=ext_conf, score=best.score)
        val_status = "VALID" if best.validation_status in ("ok", "valid", "valid_format", "checksum_valid") else "UNKNOWN"
        vr = ValidationResult(status=val_status)
        
        return field_result_cls(
            value=best.value,
            raw_value=best.raw_value,
            normalized_value=best.value,
            confidence=round(best.confidence, 4),
            status=status,
            field_confidence=fc,
            validation=vr,
            source=best.source,
            polygon=best.polygon,
            bbox=best.bbox,
            candidates=valid_candidates
        )
