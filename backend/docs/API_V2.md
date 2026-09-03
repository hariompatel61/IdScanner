# ID Scanner API V2 Documentation

## Current Production Endpoint (/api/v1/scan)

The existing /api/v1/scan endpoint remains the primary integration point. Phase 6 enforces robust security, rate limiting, and size restrictions while completely preserving the backward-compatible response shape.

### Backward Compatibility
Existing integrations relying on the old ScanResponse will continue to receive:
\\\json
{
  "success": true,
  "document_type": "aadhaar_card",
  "identifier": "123412341234",
  "fields": {...}
}
\\\

If an error occurs, it continues to return:
\\\json
{
  "success": false,
  "document_type": "unknown",
  "error_code": "LOW_CONFIDENCE",
  "message": "Unable to confidently extract..."
}
\\\

### Versioning Strategy
There is currently no forced migration to a /api/v2/scan. The Phase 6 changes augment the existing V1 response with new standard structures (equest_id, status, alidation, confidence, error). Clients are encouraged to migrate their reading logic to the new structures at their own pace. A future V2 may eventually drop the legacy fields (error_code, message, identifier at root).

## New Request/Response Schema

**Request:** POST /api/v1/scan (multipart/form-data)
- ile: The image file (JPEG, PNG, WEBP).
- document_type: (Optional) Hint to force a specific parser.

**Response:**
\\\json
{
  "success": true,
  "request_id": "req_8a7b6c5d4e3f",
  "document_type": "pan_card",
  "status": "ACCEPT", // ACCEPT, REVIEW, RECAPTURE, INVALID
  "fields": {
    "name": "Jane Doe",
    "pan_number": "ABCDE1234F"
  },
  "validation": { ... },
  "confidence": { ... },
  "processing_time_ms": 1250,
  
  // Legacy fields
  "identifier": "ABCDE1234F"
}
\\\

## Error Format
If validation, payload size, rate limits, or processing fail, a standard Error structure is returned:
\\\json
{
  "success": false,
  "request_id": "req_8a7b6c5d4e3f",
  "error": {
    "code": "IMAGE_TOO_LARGE",
    "message": "File too large. Max size is 10485760 bytes."
  }
}
\\\

### Common Error Codes
- INVALID_IMAGE: Decompression or parsing failed.
- IMAGE_TOO_LARGE: Exceeds MAX_UPLOAD_SIZE_BYTES.
- UNSUPPORTED_FORMAT: Not JPEG, PNG, or WEBP.
- EMPTY_UPLOAD: File size is 0.
- RATE_LIMITED: Too many requests.
- REQUEST_TIMEOUT: OCR process stalled.
- AUTHENTICATION_REQUIRED / AUTHENTICATION_FAILED.
- INTERNAL_ERROR: Unhandled exception.

## Utility Endpoints
- GET /health: Liveness probe.
- GET /ready: Readiness probe (confirms OCR is loaded).
- GET /metadata: Exposes version, supported documents, and limits.
