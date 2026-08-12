# Universal Mobile ID Scanner API Documentation

## 1. Overview
The Mobile Identity Document Scanner API provides standalone, high-throughput OCR and extraction for Indian identity documents (**Aadhaar Card, PAN Card, Voter ID / EPIC, and ABHA Card**). It accepts an uploaded image payload and returns validated JSON data containing extracted document numbers and field details.

It is designed as a **universal REST API (`multipart/form-data`)** compatible with **Node.js, Python, PHP/Laravel, Java, C#, Flutter, Go, and cURL**.

---

## 2. Server Base URLs & Health Status

| Environment | Base URL |
|---|---|
| **Production Server** | `https://your-production-domain.com` |
| **Development / Local** | `http://localhost:4500` |

### Health Check Endpoints
- **Liveness Check**: `GET /health` $\rightarrow$ Returns `HTTP 200 OK` `{"status": "healthy"}`
- **Readiness Check**: `GET /ready` $\rightarrow$ Returns `HTTP 200 OK` `{"status": "ready", "ocr_engine": "rapidocr"}`

---

## 3. Main Scanning Endpoint Specification

### `POST /api/v1/scan`

#### Request Headers
- **Content-Type**: `multipart/form-data`
- **Authorization** *(Optional/Environment-driven)*: `Bearer <API_TOKEN>`

#### Multipart Form Parameters

| Field Name | Type | Required | Allowed Values / Format | Description |
|---|---|---|---|---|
| `image` *(or `file`)* | File Buffer | **Required** | JPEG, PNG, WEBP (Max 5MB) | The uploaded ID Card image snapshot. |
| `document_type` | String | Optional | `aadhaar`, `pan`, `voter`, `abha` | Optimizes regex extraction for a specific document type. If omitted, auto-detection evaluates all document extractors. |

---

## 4. Response Schemas & Examples

### 4.1 Success Response — PAN Card
```json
{
  "success": true,
  "document_type": "pan",
  "identifier": "ABCDE1234F",
  "fields": {
    "pan_number": "ABCDE1234F"
  },
  "confidence": 0.99,
  "requires_rescan": false,
  "processing_time_ms": 87,
  "request_id": "req_a1b2c3d4e5f6"
}
```

### 4.2 Success Response — Aadhaar Card
```json
{
  "success": true,
  "document_type": "aadhaar",
  "identifier": "123456789012",
  "fields": {
    "aadhaar_number": "123456789012"
  },
  "confidence": 0.99,
  "requires_rescan": false,
  "processing_time_ms": 90,
  "request_id": "req_f6e5d4c3b2a1"
}
```

### 4.3 Success Response — ABHA Card
```json
{
  "success": true,
  "document_type": "abha",
  "identifier": "12-3456-7890-1234",
  "fields": {
    "abha_number": "12-3456-7890-1234",
    "abha_address": "user@abdm"
  },
  "confidence": 0.98,
  "requires_rescan": false,
  "processing_time_ms": 95,
  "request_id": "req_778899aabbcc"
}
```

### 4.4 Success Response — Voter ID (EPIC)
```json
{
  "success": true,
  "document_type": "voter",
  "identifier": "ABC1234567",
  "fields": {
    "voter_id": "ABC1234567"
  },
  "confidence": 0.97,
  "requires_rescan": false,
  "processing_time_ms": 89,
  "request_id": "req_112233445566"
}
```

### 4.5 Rescan Required / Low Confidence Response
```json
{
  "success": false,
  "document_type": "unknown",
  "identifier": null,
  "fields": {},
  "confidence": 0.42,
  "requires_rescan": true,
  "processing_time_ms": 110,
  "request_id": "req_998877665544",
  "error_code": "LOW_CONFIDENCE",
  "message": "Unable to confidently extract the document identifier."
}
```

---

## 5. Multi-Language Client Code Examples

### 5.1 Node.js / Express (Axios)
```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

async function scanCard() {
  const form = new FormData();
  form.append('image', fs.createReadStream('./card.jpg'));
  form.append('document_type', 'pan');

  const response = await axios.post('http://localhost:4500/api/v1/scan', form, {
    headers: form.getHeaders()
  });

  console.log('Result:', response.data);
}
```

### 5.2 Python (Requests)
```python
import requests

files = {'image': open('aadhaar_card.jpg', 'rb')}
data = {'document_type': 'aadhaar'}

response = requests.post('http://localhost:4500/api/v1/scan', files=files, data=data)
result = response.json()
print("Extracted ID:", result['identifier'])
```

### 5.3 PHP / Laravel
```php
use Illuminate\Support\Facades\Http;

$response = Http::attach('image', file_get_contents($imagePath), 'card.jpg')
    ->post('http://localhost:4500/api/v1/scan', [
        'document_type' => 'pan'
    ]);

$result = $response->json();
echo $result['identifier'];
```

### 5.4 Java (OkHttp)
```java
OkHttpClient client = new OkHttpClient();
RequestBody body = new MultipartBody.Builder()
    .setType(MultipartBody.FORM)
    .addFormDataPart("image", "card.jpg", RequestBody.create(new File("card.jpg"), MediaType.parse("image/jpeg")))
    .addFormDataPart("document_type", "pan")
    .build();

Request request = new Request.Builder()
    .url("http://localhost:4500/api/v1/scan")
    .post(body)
    .build();

Response response = client.newCall(request).execute();
System.out.println(response.body().string());
```

---

## 6. HTTP Status & Error Codes Reference

| HTTP Code | Error Code | Description | Action Required |
|---|---|---|---|
| **200 OK** | - | Scan evaluated cleanly. Check `success` and `requires_rescan`. | Parse `identifier` and `fields`. |
| **400 Bad Request** | `INVALID_PAYLOAD` | Missing image file or unreadable buffer. | Check multipart payload field name (`image` or `file`). |
| **401 Unauthorized** | `UNAUTHORIZED` | Missing or invalid Bearer token. | Provide valid `Authorization: Bearer <TOKEN>` header. |
| **413 Payload Too Large**| `FILE_TOO_LARGE` | Image size exceeds 5MB limit. | Compress or downscale image before upload. |
| **415 Unsupported Media**| `UNSUPPORTED_MEDIA` | File format is not JPEG, PNG, or WEBP. | Convert image payload to JPEG or PNG. |
| **503 Service Unavailable**| `SERVICE_UNAVAILABLE` | RapidOCR engine model initializing or offline. | Retry request after 2 seconds. |
