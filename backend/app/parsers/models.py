from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ValidationResult:
    status: str  # "VALID", "INVALID", "UNKNOWN", "NOT_APPLICABLE"
    rule: str = ""
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConsistencyResult:
    status: str  # "CONSISTENT", "INCONSISTENT", "UNKNOWN"
    conflicts: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FieldConfidence:
    ocr_confidence: float = 0.0
    extraction_confidence: float = 0.0
    validation_confidence: float = 0.0
    score: float = 0.0

@dataclass
class DocumentConfidence:
    overall_confidence: float = 0.0
    decision: str = "REVIEW"  # "ACCEPT", "REVIEW", "RECAPTURE", "INVALID"
    reasons: List[str] = field(default_factory=list)

@dataclass
class FieldResult:
    value: Optional[Any] = None
    raw_value: Optional[str] = None
    normalized_value: Optional[Any] = None
    
    # Keeping old confidence/status for backward compatibility during transition
    confidence: float = 0.0
    status: str = "not_found"  # "ok" | "low_confidence" | "not_found"
    
    # New Phase 5 models
    field_confidence: FieldConfidence = field(default_factory=FieldConfidence)
    validation: ValidationResult = field(default_factory=lambda: ValidationResult(status="UNKNOWN"))
    
    source: str = ""
    polygon: Optional[List[List[float]]] = None
    bbox: Optional[List[float]] = None
    candidates: List[Any] = field(default_factory=list)
