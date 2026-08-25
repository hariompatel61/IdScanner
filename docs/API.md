# Universal Mobile ID Scanner API Specification

## 1. Overview
The IDScanner API provides standalone, high-throughput OCR and structured data extraction for identity documents (**Aadhaar, PAN, Voter ID, ABHA, Farmer ID, and Passport**).

It accepts an uploaded image payload and returns a clean, validated JSON object.

---

## 2. Server Base URLs & Health Status

| Environment | Base URL |
|---|---|
| **Production Server** | `https://your-domain.com` |
| **Local / Docker Development** | `http://localhost:4500` (or `http://localhost:8000`) |

### Health Check Endpoints
- **Liveness Check**: `GET /health` $\rightarrow$ Returns `HTTP 200 OK` `{"status": "healthy"}`
- **Readiness Check**: `GET /ready` $\rightarrow$ Returns `HTTP 200 OK` `{"status": "ready", "ocr_engine": "rapidocr"}`

---

## 3. Main Scanning Endpoint

### `POST /api/v1/scan`

Uploads an image file to be decoded, OCR-processed, and parsed.

#### Request Parameters
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `image` (or `file`) **[Required]**: Image file (JPEG, PNG, WEBP, BMP). Max size: **10MB**.

---

### Response Format (Clean Standardized JSON)

#### 3.1 Aadhaar Card (Front)
```json
{
  "success": true,
  "document_type": "aadhaar_card",
  "identifier": "825395633085",
  "fields": {
    "aadhaar_number": "825395633085",
    "dob": "28/12/2004",
    "gender": "Male",
    "name": "Aarav Sharma"
  }
}
```

#### 3.2 Aadhaar Card (Back Side)
```json
{
  "success": true,
  "document_type": "aadhaar_card_back",
  "identifier": "925474400335",
  "fields": {
    "aadhaar_number": "925474400335",
    "relation_type": "S/O",
    "relation_name": "Sanjay Kumar",
    "address": "1013, jamalpur shekhan, Jamalpur Shekhan(99), Fatehabad, Haryana - 125120",
    "state": "Haryana",
    "pincode": "125120"
  }
}
```

#### 3.3 PAN Card
```json
{
  "success": true,
  "document_type": "pan_card",
  "identifier": "LGSPK7071C",
  "fields": {
    "pan_number": "LGSPK7071C",
    "dob": "24/10/2003",
    "name": "SHASHI RANJAN KUMAR",
    "father_name": "NAVEEN KUMAR JHA"
  }
}
```

#### 3.3 Voter ID (EPIC)
```json
{
  "success": true,
  "document_type": "voter_id",
  "identifier": "RIW7626286",
  "fields": {
    "voter_id": "RIW7626286",
    "relation_name": "Nandini Darekar",
    "relation_type": "Mother",
    "name": "Shubham Darekar"
  }
}
```

#### 3.4 ABHA Card
```json
{
  "success": true,
  "document_type": "abha_number",
  "identifier": "91-2748-8665-1315",
  "fields": {
    "abha_number": "91-2748-8665-1315",
    "abha_address": "aarav282004@sbx",
    "name": "Aarav Sharma",
    "gender": "Male",
    "dob": "28/12/2004",
    "mobile": "9876543210"
  }
}
```

#### 3.5 Agriculture Card (Farmer ID)
```json
{
  "success": true,
  "document_type": "farmer_id",
  "identifier": "195 36 94 77 21",
  "fields": {
    "farmer_id": "195 36 94 77 21",
    "name": "Pramod Kumar",
    "dob": "10/06/1991",
    "gender": "Male",
    "mobile": "9027956097",
    "aadhaar_number": "527613815535"
  }
}
```

#### 3.6 Passport
```json
{
  "success": true,
  "document_type": "passport",
  "identifier": "Z1234567",
  "fields": {
    "passport_number": "Z1234567",
    "name": "AARAV SHARMA",
    "surname": "SHARMA",
    "given_name": "AARAV",
    "dob": "28/12/2004",
    "gender": "Male",
    "expiry_date": "15/08/2034",
    "nationality": "INDIAN"
  }
}
```

---

## 4. Client Code Integration Examples

### cURL
```bash
curl -X POST "http://localhost:4500/api/v1/scan" \
  -F "image=@/path/to/document.jpg"
```

### Python
```python
import requests

url = "http://localhost:4500/api/v1/scan"
files = {"image": open("document.jpg", "rb")}
response = requests.post(url, files=files)
data = response.json()
print(data)
```

### Node.js / TypeScript
```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

const form = new FormData();
form.append('image', fs.createReadStream('document.jpg'));

axios.post('http://localhost:4500/api/v1/scan', form, {
  headers: form.getHeaders(),
}).then(res => {
  console.log(res.data);
});
```

### PHP / Laravel
```php
<?php
$client = new \GuzzleHttp\Client();
$response = $client->request('POST', 'http://localhost:4500/api/v1/scan', [
    'multipart' => [
        [
            'name'     => 'image',
            'contents' => fopen('/path/to/document.jpg', 'r')
        ]
    ]
]);

$result = json_decode($response->getBody(), true);
print_r($result);
```
