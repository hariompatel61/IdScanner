from pydantic import BaseModel, Field
from typing import Optional, Dict

class ScanMetrics(BaseModel):
    processing_time_ms: int = Field(..., description="Time taken for OCR and extraction in milliseconds")
    request_id: str = Field(..., description="Unique request identifier")

class ScanResponse(BaseModel):
    document_type: Optional[str] = Field(None, description="Identified document type (e.g. PAN, AADHAAR)")
    identifier: Optional[str] = Field(None, description="Primary identifier extracted")
    confidence: float = Field(0.0, description="Overall confidence score (0.0 to 1.0)")
    requires_rescan: bool = Field(False, description="True if no valid high-confidence identifier was found")
    
    # Optional fields for ABHA which has two
    abha_number: Optional[str] = None
    abha_address: Optional[str] = None
    
    metrics: ScanMetrics
