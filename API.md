# Mobile Identity Document Scanner API Specification

## 1. Overview
The Mobile Identity Document Scanner API provides high-throughput, low-latency OCR and identity document extraction for **Aadhaar, PAN, Voter ID (EPIC), and ABHA cards**. The backend is optimized for **500+ scans/minute** using ONNX CPU runtime inference.

---

## 2. Base Configuration & Authentication

### Base URL
`https://your-domain.com` (or local dev: `http://127.0.0.1:4500`)

### Authentication
Server-to-server HTTP Bearer Token authentication (configured via `API_TOKEN` environment variable).

```http
Authorization: Bearer <YOUR_API_TOKEN>
```

---

## 3. Endpoints

### 3.1 POST `/api/v1/scan`
Extracts identity document details from an uploaded image payload.

#### Request Format
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `image` (or `file`) **[Required]**: Image file buffer (JPEG, PNG, WEBP). Max size: **5MB**.
  - `document_type` **[Optional]**: Target document optimization (`aadhaar`, `pan`, `voter`, `abha`).

#### Response Contracts

##### PAN Card Success Response
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

##### Aadhaar Card Success Response
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

##### ABHA Card Success Response
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

##### Low Confidence / Rescan Required Response
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

### 3.2 GET `/health`
Lightweight liveness check. Returns `200 OK` instantly without executing OCR inference.

```json
{
  "status": "healthy"
}
```

---

### 3.3 GET `/ready`
Readiness check. Returns `200 OK` when the RapidOCR engine model is initialized and warmed up.

```json
{
  "status": "ready",
  "ocr_engine": "rapidocr"
}
```

---

## 4. Code Snippets for Developers

### 4.1 Laravel HTTP Client (PHP)
```php
<?php

use Illuminate\Support\Facades\Http;

$imagePath = storage_path('app/scans/id_card.jpg');

$response = Http::timeout(10)
    ->withToken(config('services.id_scanner.token'))
    ->attach(
        'image',
        fopen($imagePath, 'r'),
        basename($imagePath)
    )
    ->post(config('services.id_scanner.url') . '/api/v1/scan', [
        'document_type' => 'pan'
    ]);

if ($response->successful()) {
    $data = $response->json();
    if ($data['success'] && !$data['requires_rescan']) {
        $panNumber = $data['fields']['pan_number'] ?? $data['identifier'];
        Log::info("Extracted PAN: " . $panNumber);
    } else {
        Log::warning("Scan requires rescan: " . $data['message']);
    }
} else {
    Log::error("ID Scanner API error: " . $response->status());
}
```

### 4.2 Standard PHP cURL
```php
<?php

$ch = curl_init();
$imagePath = '/path/to/id_card.jpg';

$cfile = new CURLFile($imagePath, 'image/jpeg', 'id_card.jpg');

curl_setopt_array($ch, [
    CURLOPT_URL => 'http://127.0.0.1:4500/api/v1/scan',
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => true,
    CURLOPT_TIMEOUT => 10,
    CURLOPT_HTTPHEADER => [
        'Authorization: Bearer ' . getenv('API_TOKEN')
    ],
    CURLOPT_POSTFIELDS => [
        'image' => $cfile,
        'document_type' => 'aadhaar'
    ]
]);

$result = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

$response = json_decode($result, true);
print_r($response);
```

### 4.3 cURL Command
```bash
curl -X POST "http://127.0.0.1:4500/api/v1/scan" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -F "image=@/path/to/aadhaar_card.jpg" \
  -F "document_type=aadhaar"
```

---

## 5. HTTP & Error Status Codes

| Status Code | Error Code | Description |
|---|---|---|
| **200 OK** | - | Scan evaluated successfully. Check `success` and `requires_rescan` fields. |
| **401 Unauthorized** | `UNAUTHORIZED` | Missing or invalid `Authorization: Bearer <TOKEN>`. |
| **400 Bad Request** | `INVALID_PAYLOAD` | Missing image payload or corrupted image buffer. |
| **413 Payload Too Large** | `FILE_TOO_LARGE` | Image size exceeds 5MB limit. |
| **415 Unsupported Media** | `UNSUPPORTED_MEDIA` | File is not a valid JPEG, PNG, or WEBP image. |
| **503 Unavailable** | `SERVICE_UNAVAILABLE` | OCR engine model initializing or unavailable. |
