# 🎴 High-Performance Mobile ID Document Scanner & OCR API

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg)](https://fastapi.tiangolo.com/)
[![RapidOCR](https://img.shields.io/badge/OCR-RapidOCR%20ONNX-orange.svg)](https://github.com/RapidAI/RapidOCR)
[![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61dafb.svg)](https://vitejs.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed.svg)](docker-compose.yml)

> ⚡ **Real-time Mobile ID Card Scanner & OCR Engine** optimized for **Aadhaar, PAN, Voter ID (EPIC), and ABHA Cards**. Built for extreme throughput (**500+ scans/minute**) with zero disk image storage and zero PII logging.

---

## 🌟 Key Features

- 📸 **Real-Time Mobile Camera HUD**: Responsive scanning UI with automatic blur, glare, and document stability detection running directly in browser Web Workers via OpenCV.js.
- ⚡ **Ultra-Fast ONNX RapidOCR Engine**: 100% CPU-compatible inference initialized once on startup with zero per-request model loading overhead.
- 🆔 **Indian Document Extractors**: Algorithmic regex and checksum verification for **Aadhaar (Verhoeff Checksum), PAN Card, Voter ID, and ABHA Number/Address**.
- 🔒 **Privacy & Zero Image Storage**: In-memory image decoding (`cv2.imdecode`) with immediate memory release. Identity images are never saved to disk.
- 🚀 **High Throughput (500+ Scans/Min)**: Benchmark-verified architecture designed for horizontal container scaling behind NGINX.
- 🔌 **Standalone RIMS Hospital API Integration**: Production-ready `POST /api/v1/scan` REST API endpoint with native PHP/Laravel, cURL, and Python client support.

---

## 🚀 Quick Start (Run Locally in 2 Minutes)

### Option 1: Using Docker Compose (Recommended)

```bash
# 1. Clone Repository
git clone https://github.com/hariompatel61/IdScanner.git
cd IdScanner

# 2. Copy Environment Template
cp .env.example .env

# 3. Launch Stack with Docker
docker-compose up -d --build
```

Access the application:
- **Mobile Scanner UI**: `http://localhost:3233`
- **FastAPI OpenAPI Specs**: `http://localhost:4500/docs`
- **API Health Check**: `http://localhost:4500/health`

---

### Option 2: Run Backend & Frontend Natively

#### Backend Setup (Python)
```bash
cd backend
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 4500 --workers 4
```

#### Frontend Setup (React / Vite)
```bash
cd frontend
npm install
npm run dev
```

---

## 📊 Performance & Load Benchmarks

Tested on standard multi-core CPU hardware using `backend/benchmark/load_test.py`:

| Scenario | Target Rate | Sustained Throughput | Latency P50 | Error Rate |
|---|---|---|---|---|
| **Baseline** | 1 req/sec | 60 scans/min | ~120 ms | 0.00% |
| **Medium Load** | 5 req/sec | 300 scans/min | ~180 ms | 0.00% |
| **Cluster Scaling (4-8 Replicas)** | 10+ req/sec | **500+ to 1,200+ scans/min** | <400 ms | 0.00% |

---

## 🔌 API Integration Reference

### Scan Document (`POST /api/v1/scan`)

#### Request
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `image` *(File, Required)*: JPEG / PNG / WEBP image (Max 5MB)
  - `document_type` *(String, Optional)*: `aadhaar`, `pan`, `voter`, `abha`

#### Response Example (PAN Card)
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

#### Laravel PHP Integration Example
```php
$response = Http::timeout(15)
    ->attach('image', file_get_contents($imagePath), 'card.jpg')
    ->post('https://your-domain.com/api/v1/scan', [
        'document_type' => 'pan'
    ]);

$result = $response->json();
echo $result['identifier']; // Output: ABCDE1234F
```

---

## 🛠️ Tech Stack

- **Frontend**: React, TypeScript, Vite, OpenCV.js Web Worker
- **Backend API**: Python 3.11+, FastAPI, Uvicorn, Pydantic v2
- **OCR Engine**: RapidOCR ONNX CPU Runtime, OpenCV Headless
- **Deployment**: Docker, Docker Compose, NGINX, Certbot (HTTPS)

---

## 📁 Repository Structure

```
IdScanner/
├── backend/                  # FastAPI App, RapidOCR Engine & Extractors
│   ├── app/api/v1/scan.py    # Main /api/v1/scan API Endpoint
│   ├── app/extractors/       # Regex & Verhoeff Checksum Extractor Pipeline
│   └── app/ocr/engine.py     # RapidOCR Singleton Engine & Warm-Up Logic
├── frontend/                 # React + Vite Camera UI & Worker Logic
│   └── src/scanner/          # Camera Overlay, HUD, & OpenCV Web Worker
├── docker-compose.yml        # Production Docker Stack Orchestration
├── RIMS_API_DOCUMENTATION.md # Detailed RIMS Integration Specs
└── LINUX_VPS_DEPLOYMENT.md   # Production Linux VPS Hosting Guide
```

---

## 📜 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

---

## 👨‍💻 Author & Contributions

Created with ❤️ by **[Hari Om Patel](https://github.com/hariompatel61)**.

⭐ **If you find this repository useful, please consider giving it a star!**
