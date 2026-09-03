from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ScanResponse(BaseModel):
    success: bool = Field(..., description="True if document was successfully scanned & extracted")
    request_id: Optional[str] = Field(None, description="Unique request identifier for tracing")
    document_type: str = Field(..., description="Document type: aadhaar_card, aadhaar_card_back, pan_card, voter_id, abha_number, farmer_id, passport, or unknown")
    status: Optional[str] = Field(None, description="Decision status (ACCEPT, REVIEW, RECAPTURE, INVALID)")
    
    # Backward Compatibility fields
    identifier: Optional[str] = Field(None, description="Extracted primary ID number")
    message: Optional[str] = Field(None, description="Human-readable error message if scan failed")
    error_code: Optional[str] = Field(None, description="Error code if scan failed")
    
    # New Phase 6 Fields
    fields: Dict[str, Any] = Field(default_factory=dict, description="Dictionary of extracted document fields")
    validation: Dict[str, Any] = Field(default_factory=dict, description="Format and checksum validation results per field")
    confidence: Dict[str, Any] = Field(default_factory=dict, description="Overall document confidence score and reasons")
    processing_time_ms: int = Field(0, description="Time taken to process the scan")
    error: Optional[ErrorDetail] = Field(None, description="Structured error details if success is false")
