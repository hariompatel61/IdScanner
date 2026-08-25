# 🎴 High-Performance Mobile ID Document Scanner & OCR API

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg)](https://fastapi.tiangolo.com/)
[![RapidOCR](https://img.shields.io/badge/OCR-RapidOCR%20ONNX-orange.svg)](https://github.com/RapidAI/RapidOCR)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-61dafb.svg)](https://vitejs.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed.svg)](docker-compose.yml)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](.github/workflows/ci.yml)

> ⚡ **Enterprise Real-Time Mobile Identity Scanner & OCR Engine** supporting **Aadhaar, PAN, Voter ID (EPIC), ABHA Card, Agriculture Card (Farmer ID), and International / Indian Passports**. Built for extreme throughput (**500+ scans/minute**) with zero disk image storage and zero PII logging.

---

## 🌟 Key Capabilities

- 📸 **Edge-Side Web Worker CV**: Real-time Laplacian blur variance, brightness histograms, and edge stability computed directly on the client at 30 FPS without UI stutter.
- ⚡ **Ultra-Fast ONNX RapidOCR Runtime**: 100% CPU-compatible inference initialized once on startup with pre-warmed tensors (zero per-request cold start).
- 🆔 **Multi-Document Support**:
  - **Aadhaar Card**: Verhoeff checksum validation, DOB, Gender, Name.
  - **PAN Card**: Income Tax alphanumeric syntax, Name, Father's Name, DOB.
  - **Voter ID (EPIC)**: ECI EPIC alphanumeric extraction, multilingual label stripping, relation extraction (Father, Mother, Husband, Other).
  - **ABHA Card**: 14-digit ABHA Number, ABHA Address (`@abdm`/`@sbx`), Name, Gender, DOB, Mobile.
  - **Agriculture Card (Farmer ID)**: 11-digit farmer identifier, Aadhaar link, Mobile, Name, DOB.
  - **Passport**: Full VIZ and ICAO Doc 9303 Type 3 MRZ parsing (Surname, Given Name, Passport Number, DOB, Gender, Expiry Date, Nationality).
- 🔒 **Privacy by Design**: In-memory image decoding (`cv2.imdecode`) with zero disk persistence.
- 🔌 **Universal REST API**: Single `POST /api/v1/scan` endpoint compatible with Node.js, Python, PHP/Laravel, Go, Java, C#, Flutter, and cURL.

---

## 🏗️ System Architecture

```
┌────────────────────────────┐         ┌────────────────────────────┐
│      Client Browser        │         │        FastAPI Core        │
│  Camera Stream (30 FPS)    │         │   POST /api/v1/scan        │
│             │              │  HTTPS  │             │              │
│  Web Worker CV Analysis    │ ──────> │   In-Memory Image Decode   │
│             │              │  Blob   │             │              │
│  Auto-Capture on 100% Lock │         │   RapidOCR ONNX Engine     │
└────────────────────────────┘         │             │              │
                                       │   Spatial Line Reconstruct │
                                       │             │              │
                                       │   Document Classification  │
                                       │             │              │
                                       │   Parser & Field Sanitizer │
                                       └─────────────┬──────────────┘
                                                     ▼
                                          Clean Standard JSON Payload
```

---

## 🚀 Quick Start (Run Locally in 2 Minutes)

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/hariompatel61/IdScanner.git
cd IdScanner

# 2. Copy environment template
cp .env.example .env

# 3. Build and launch stack
docker-compose up -d --build
```

Access services:
- **Scanner Web App**: `http://localhost:3233`
- **FastAPI Documentation**: `http://localhost:4500/docs`
- **Health Check**: `http://localhost:4500/health`

---

### Option 2: Native Setup

#### Backend (Python 3.11+)
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend (Node.js 20+)
```bash
cd frontend
npm install
npm run dev
```

---

## 📡 API Specification & Sample Response

### `POST /api/v1/scan`
Accepts `multipart/form-data` with an image file (`image` or `file`).

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

## 📚 Documentation Index

| Guide | Description |
|---|---|
| 🏛️ [**Architecture & Design**](docs/ARCHITECTURE.md) | In-depth breakdown of client worker, ONNX inference, line reconstruction, and parsers. |
| 📡 [**API Specification**](docs/API.md) | Complete REST API reference, request/response formats, and client SDK examples. |
| 🚀 [**Production Deployment**](docs/DEPLOYMENT.md) | Docker Compose, Linux VPS hosting, NGINX SSL reverse proxy, and systemd service setup. |
| 🐧 [**Linux NGINX Backend Hosting Guide**](docs/BACKEND_LINUX_NGINX_DEPLOYMENT.md) | Step-by-step Hindi/Hinglish Linux VPS + NGINX + SSL setup guide for the Backend API. |
| ⚡ [**Performance & Benchmarks**](docs/BENCHMARKS.md) | Throughput test analysis, latency percentiles, and 500+ scans/min scaling strategies. |
| 🔒 [**Security & Privacy**](docs/SECURITY.md) | Zero-persistence model, PII sanitization, input validation, and compliance alignment. |

---

## 🧪 Testing

Run the full test suite (100% passing across all extractors and parsers):

```bash
cd backend
venv\Scripts\pytest.exe tests/ -v
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
