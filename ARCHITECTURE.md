# Architecture

## High-Level Architecture
1. **Frontend (Scanner Web Application)**
   - **Tech**: React + TypeScript + Vite + OpenCV.js (Future Phase)
   - **Role**: Mobile UI, camera control, lightweight frame analysis (blur, glare, alignment), auto-capture, cropping, sending optimized image to API.
   - **State**: `INITIALIZING`, `CAMERA_READY`, `DOCUMENT_DETECTED`, `CAPTURING`, etc.
   - **Workers**: Heavy OpenCV.js operations are offloaded to Web Workers.
2. **Backend (Scanner API)**
   - **Tech**: Python 3.11 + FastAPI + PaddleOCR + OpenCV
   - **Role**: Receive cropped image, classify document, identify ROIs, run PaddleOCR, normalize text, validate patterns, compute confidence score.
3. **Integration SDK**
   - **Tech**: Vanilla JS
   - **Role**: Provides `IdScanner.open(options)` to embed the scanner into any host application (like PHP/Laravel).

## Constraints
- **No Database**: The system is completely stateless. No images or IDs are persisted.
- **Microservices**: Deployed via Docker compose.

*Note: Phase 1 implements the boilerplate foundation for these components.*
