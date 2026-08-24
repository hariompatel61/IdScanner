from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class FieldResult(BaseModel):
    """Result of extracting a single document field."""
    value: Optional[str] = Field(None, description="Extracted field value")
    confidence: float = Field(0.0, description="OCR confidence score for this field (0.0-1.0)")
    status: str = Field("not_found", description="Field status: ok, low_confidence, or not_found")

class ScanMetrics(BaseModel):
    processing_time_ms: int = Field(..., description="Time taken for OCR and extraction in milliseconds")
    request_id: str = Field(..., description="Unique request identifier")

class ScanResponse(BaseModel):
    success: bool = Field(..., description="True if document was successfully scanned & extracted with high confidence")
    document_type: str = Field(..., description="Document type: aadhaar_card, pan_card, voter_id, abha_number, or unknown")
    identifier: Optional[str] = Field(None, description="Extracted primary ID number (for backward compatibility)")
    fields: Dict[str, Any] = Field(default_factory=dict, description="Dictionary of extracted document fields")
    confidence: float = Field(0.0, description="Extraction confidence score between 0.0 and 1.0")
    requires_rescan: bool = Field(False, description="True if rescan is required due to low confidence or invalid document")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    request_id: str = Field(..., description="Unique request identifier")
    message: Optional[str] = Field(None, description="Human-readable status or error message")
    error_code: Optional[str] = Field(None, description="Error code if scan failed (e.g. LOW_CONFIDENCE, INVALID_PAYLOAD)")
    
    # Backward compatibility metrics sub-object
    metrics: Optional[ScanMetrics] = None

    # ── NEW: Structured field extraction results ──
    details: Optional[Dict[str, FieldResult]] = Field(None, description="Per-field extraction results with value, confidence, and status")
    overall_status: Optional[str] = Field(None, description="Overall extraction status: ok or rescan_required")
    failed_fields: Optional[List[str]] = Field(None, description="List of mandatory field names that failed extraction")
