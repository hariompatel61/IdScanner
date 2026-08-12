# RIMS Hospital ID Scanner API Integration Documentation

## 1. Overview
The Mobile Identity Document Scanner API provides standalone, high-throughput OCR and extraction for Indian identity documents (**Aadhaar Card, PAN Card, Voter ID / EPIC, and ABHA Card**). It accepts an uploaded image payload and returns validated JSON data containing extracted document numbers and field details.

---

## 2. Server Base URLs & Health Status

| Environment | Base URL |
|---|---|
| **Production Server** | `https://your-production-domain.com` |
| **Development / Ngrok Tunnel** | `https://maybell-basifixed-nonsubversively.ngrok-free.dev` |

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

## 5. RIMS Integration Code Examples

### 5.1 Laravel HTTP Client Implementation (PHP)
Place this code directly inside your Laravel Controller (e.g. `PatientRegistrationController.php`):

```php
<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class PatientRegistrationController extends Controller
{
    /**
     * Scans uploaded patient ID document and auto-fills registration form.
     */
    public function scanPatientDocument(Request $request)
    {
        $request->validate([
            'document_image' => 'required|image|mimes:jpeg,png,jpg,webp|max:5120',
            'doc_type' => 'nullable|string|in:aadhaar,pan,voter,abha'
        ]);

        $uploadedFile = $request->file('document_image');
        $scannerUrl = config('services.id_scanner.url', 'https://maybell-basifixed-nonsubversively.ngrok-free.dev');
        $apiToken   = config('services.id_scanner.token', null);

        $httpClient = Http::timeout(15);
        if ($apiToken) {
            $httpClient->withToken($apiToken);
        }

        try {
            $response = $httpClient->attach(
                'image',
                file_get_contents($uploadedFile->getRealPath()),
                $uploadedFile->getClientOriginalName()
            )->post($scannerUrl . '/api/v1/scan', [
                'document_type' => $request->input('doc_type')
            ]);

            if ($response->successful()) {
                $data = $response->json();

                if ($data['success'] && !$data['requires_rescan']) {
                    return response()->json([
                        'status' => 'success',
                        'document_type' => $data['document_type'],
                        'identifier' => $data['identifier'],
                        'fields' => $data['fields'],
                        'processing_time_ms' => $data['processing_time_ms']
                    ]);
                } else {
                    return response()->json([
                        'status' => 'rescan_required',
                        'message' => $data['message'] ?? 'Document text is unreadable or blurry.',
                        'error_code' => $data['error_code'] ?? 'LOW_CONFIDENCE'
                    ], 422);
                }
            }

            Log::error("ID Scanner API returned status: " . $response->status());
            return response()->json(['status' => 'error', 'message' => 'Scan service error'], $response->status());

        } catch (\Exception $e) {
            Log::error("ID Scanner Connection Error: " . $e->getMessage());
            return response()->json(['status' => 'error', 'message' => 'Unable to connect to scanner service'], 500);
        }
    }
}
```

---

### 5.2 Core PHP cURL Implementation
```php
<?php

$imagePath = '/path/to/patient_id.jpg';
$apiUrl = 'https://maybell-basifixed-nonsubversively.ngrok-free.dev/api/v1/scan';

$ch = curl_init();
$cfile = new CURLFile($imagePath, 'image/jpeg', basename($imagePath));

curl_setopt_array($ch, [
    CURLOPT_URL => $apiUrl,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => true,
    CURLOPT_TIMEOUT => 15,
    CURLOPT_POSTFIELDS => [
        'image' => $cfile,
        'document_type' => 'pan'
    ]
]);

$responseJson = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode === 200) {
    $result = json_decode($responseJson, true);
    print_r($result);
} else {
    echo "Scan Error: HTTP " . $httpCode;
}
```

---

### 5.3 Command Line cURL Test
```bash
curl -X POST "https://maybell-basifixed-nonsubversively.ngrok-free.dev/api/v1/scan" \
  -F "image=@/path/to/patient_card.jpg" \
  -F "document_type=aadhaar"
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
