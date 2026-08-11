# API Contracts

## POST `/api/v1/scan` (Future Phase)
Accepts a cropped image and returns the extracted ID.

**Request:** `multipart/form-data`
- `image`: File (JPEG/PNG)
- `document_type`: (Optional) String (aadhaar, pan, voter, abha)

**Response:**
```json
{
  "success": true,
  "document_type": "aadhaar",
  "fields": {
    "aadhaar_number": "123456789012"
  },
  "confidence": 0.997,
  "requires_rescan": false,
  "processing_ms": 142,
  "request_id": "req-12345"
}
```

## GET `/health`
Verifies API process is alive. Returns 200 OK.

## GET `/ready`
Verifies API is fully configured and OCR model is loaded. Returns 200 OK only when ready.

*Note: `/health` and `/ready` are implemented in Phase 1.*
