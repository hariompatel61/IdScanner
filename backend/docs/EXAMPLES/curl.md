# cURL Example

The simplest way to integrate with the ID Scanner API is via cURL.

## Scan Document

```bash
curl -X POST "http://localhost:4500/api/v1/scan" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "X-Request-ID: req_custom_123" \
  -F "file=@document.jpg;type=image/jpeg"
```

## Expected Success Response

```json
{
  "success": true,
  "request_id": "req_custom_123",
  "document_type": "pan_card",
  "status": "ACCEPT",
  "fields": {
    "name": "Jane Doe",
    "pan_number": "ABCDE1234F"
  },
  "validation": {},
  "confidence": {
    "overall_confidence": 0.98,
    "decision": "ACCEPT",
    "reasons": []
  },
  "processing_time_ms": 1200,
  "identifier": "ABCDE1234F"
}
```
