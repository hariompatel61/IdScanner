# Performance Targets & Architecture

## Pipeline Overview
1. **Camera Frame**: ~30 FPS on frontend.
2. **Frame Analysis**: Lightweight OpenCV.js in Web Worker checks blur, glare, and stability. Fast enough to run continuously.
3. **Auto Capture**: Triggers only when conditions are optimal.
4. **API Request**: Compressed crop sent to backend.
5. **Backend Processing**: ROI extraction + PaddleOCR extraction + Validation.

## Targets (Backend API)
- **P50 Latency**: 100 - 250ms
- **P95 Latency**: <500ms
*Measurements to be validated in future phases using the `benchmark/` test suite.*

## Optimizations
- Keep OCR model loaded in memory (FastAPI lifespan context).
- Use `opencv-python-headless` for smaller Docker footprint.
- Pin dependencies for predictable performance.

*Note: Phase 1 establishes the benchmark scaffolding and environment placeholders.*
