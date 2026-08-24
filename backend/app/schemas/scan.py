from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ScanResponse(BaseModel):
    success: bool = Field(..., description="True if document was successfully scanned & extracted")
    document_type: str = Field(..., description="Document type: aadhaar_card, pan_card, voter_id, abha_number, or unknown")
    identifier: Optional[str] = Field(None, description="Extracted primary ID number")
    fields: Dict[str, Any] = Field(default_factory=dict, description="Dictionary of extracted document fields")
    message: Optional[str] = Field(None, description="Human-readable error message if scan failed")
    error_code: Optional[str] = Field(None, description="Error code if scan failed (e.g. LOW_CONFIDENCE, INVALID_PAYLOAD)")
