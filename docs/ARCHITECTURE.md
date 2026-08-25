# IDScanner Architecture & System Design

## 1. System Overview

IDScanner is an enterprise-grade, high-throughput, edge-assisted identity document extraction pipeline designed for real-time mobile and API environments. The system pairs client-side Computer Vision pre-checks (blur, glare, frame stability) with server-side high-accuracy OCR (RapidOCR ONNX CPU runtime) and modular regex/spatial document parsers.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CLIENT (Browser / Mobile)                        │
│                                                                             │
│  Camera Stream  ──>  Web Worker (Frame Analysis)  ──>  HUD / Auto-Capture    │
│                                                               │ (Image/Blob)│
└───────────────────────────────────────────────────────────────┼─────────────┘
                                                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND API (FastAPI)                             │
│                                                                             │
│  FastAPI Gateway (Port 8000 / 4500)                                         │
│    │                                                                        │
│    ├──> Request Validation & In-Memory Decode (cv2.imdecode, no disk I/O)   │
│    │                                                                        │
│    ├──> RapidOCR ONNX Inference (Loaded once at startup, zero cold starts) │
│    │                                                                        │
│    ├──> Spatial Line Reconstructor (Top-to-bottom, left-to-right banding)  │
│    │                                                                        │
│    ├──> Document Classifier (Aadhaar, PAN, Voter, ABHA, Farmer, Passport)   │
│    │                                                                        │
│    └──> Dedicated Field Parser & Sanitizer (Checksums, Name cleaning, DOB) │
│                                                               │             │
│                                                       JSON Response         │
└───────────────────────────────────────────────────────────────┼─────────────┘
                                                                ▼
                                              Clean Standardized JSON Payload
```

---

## 2. Component Breakdown

### 2.1 Client-Side Mobile Scanner (`frontend/`)
- **React 18 + TypeScript + Vite**: Ultra-responsive UI layer with zero heavy dependencies on the main thread.
- **Dedicated Web Worker**: Performs real-time Laplacian blur variance, brightness histograms, and bounding box guidance at 30 FPS without dropping frames.
- **Auto-Capture Engine**: Triggers snapshot capture automatically when frame stability and document alignment reach 100%.
- **Live Preview Card**: Renders document-specific badges (colors, icons, primary ID highlights, and field breakdown).

### 2.2 Server-Side Engine (`backend/`)
- **FastAPI Core**: Asynchronous ASGI server managing request pipelines, input sanitization, rate limiting, and CORS.
- **RapidOCR ONNX Engine**: Model loaded into memory on application bootstrap and pre-warmed with a synthetic inference pass before healthcheck returns `200 OK`.
- **Line Reconstructor**: Reconstructs unstructured OCR bounding boxes into structured logical reading lines using vertical clustering and horizontal ordering.
- **Parser Registry**: Dedicated modular parsers for each document type:
  - `AadhaarParser`: Verhoeff checksum validation, DOB, Gender, Name.
  - `PANParser`: 10-character PAN syntax validation, Name, Father's Name, DOB.
  - `VoterIDParser`: EPIC identifier validation, multilingual label stripping, relation extraction (Father/Mother/Husband/Other).
  - `ABHAParser`: 14-digit ABHA number, ABHA address (@abdm/@sbx), Name, Gender, DOB, Mobile.
  - `FarmerIDParser`: 11-digit formatted farmer identifier, Aadhaar link, Mobile, Name, DOB.
  - `PassportParser`: Dual VIZ and ICAO Doc 9303 Type 3 MRZ parsing (Surname, Given Name, Passport No., DOB, Expiry, Nationality).

---

## 3. Supported Document Types

| Document | Primary ID Key | Standard Format | Validator / Checksum |
|---|---|---|---|
| **Aadhaar Card** | `aadhaar_number` | 12 digits (`XXXX XXXX XXXX`) | Verhoeff Algorithm |
| **PAN Card** | `pan_number` | 10 alphanumeric (`ABCDE1234F`) | Income Tax 5-4-1 Pattern |
| **Voter ID (EPIC)** | `voter_id` | 3 letters + 7 digits (`UBV2991586` / `RIW7626286`) | ECI EPIC Pattern |
| **ABHA Card** | `abha_number` | 14 digits (`91-2748-8665-1315`) | NDHM Syntax & Hyphenation |
| **Agriculture Card (Farmer ID)** | `farmer_id` | 11 digits (`195 36 94 77 21`) | 11-digit Scheme Standard |
| **Passport** | `passport_number` | 1 letter + 7 digits (`Z1234567`) | ICAO Doc 9303 / MRZ Line 2 |

---

## 4. Design Principles
1. **Stateless Processing**: Zero raw document images or PII are written to disk or stored in databases.
2. **Deterministic Outputs**: Strict JSON schemas with uniform error handling and clean field structures.
3. **High Concurrency**: Thread-safe ONNX CPU runtime supporting 500+ scans/minute via horizontal container replicas.
