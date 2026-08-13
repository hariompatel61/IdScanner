from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

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
