# Phase 2: Advanced Image Preprocessing & Document Rectification

**Status:** In progress — implementation and frontend regression are complete; backend execution, OCR regression, and device testing are blocked by the current environment.  
**Scope:** Server-side image safety and OCR input preparation only. RapidOCR, extractors, parsers, validators, response schema, and supported document types are unchanged.

## Architecture

```text
multipart upload
  -> MIME + magic/header + byte/dimension/pixel validation
  -> cv2.imdecode in memory
  -> isolated decoded original
  -> optional boundary estimation / validated quadrilateral
  -> optional perspective rectification
  -> resolution normalization (downscale only)
  -> adaptive enhancement when image metrics justify it
  -> fail-safe OCR-ready image (or original copy)
  -> existing RapidOCR -> classifier -> parser -> validator
```

`backend/app/preprocessing/pipeline.py` is the sole new processing boundary. `scan.py` calls `decode_image_bytes()` and `preprocess_document_image()` before the existing first OCR pass. Public `POST /api/v1/scan` request and response contracts remain unchanged.

## Safe decoding and privacy

- Only JPEG, PNG, and WebP MIME types and file signatures are accepted.
- JPEG SOF, PNG IHDR, and WebP dimensions are inspected before `cv2.imdecode`; byte, width, height, and pixel-count limits are enforced before full pixel allocation.
- Decoding remains entirely in memory. No original, rectified, or enhanced document image is written to disk.
- Corrupt/empty/unsupported inputs raise a generic `400 Invalid image payload`; request bytes and image data are never logged.
- The preprocessing log includes only request ID, step names, booleans, and duration. It contains no OCR text or document fields.
- `PreprocessingResult` keeps the original and processed images logically separate. Any unexpected preprocessing error returns a copy of the decoded original to OCR with `fallback_used=true` and a non-sensitive exception class reason.

## Rectification and crop behavior

The server does not receive usable Phase 1 geometry metadata, so it does not trust or consume client geometry. It estimates a document only when a Canny-contour candidate is a convex four-corner polygon with plausible area and aspect ratio. Corner values are finite, in bounds, convex, non-degenerate, and have safe side lengths before a perspective transform is allowed.

Perspective output dimensions are derived from opposing side lengths and limited by `PREPROCESS_MAX_DIMENSION`; no transform is forced when the candidate is invalid, partial, too small, or implausible. The result falls back to the original image rather than risking field clipping. `smart_crop()` is available as a bounded, padded utility for future trusted crop bounds; current successful perspective rectification is already the document crop.

Rotation utilities support 0°, 90°, 180°, and 270° and record `rotation`, `original_orientation`, and `final_orientation` in the internal result. The API supplies no reliable orientation hint today, so the pipeline intentionally applies 0° and retains the existing OCR fallback rotations.

## Adaptive preprocessing

Image quality uses brightness, grayscale contrast, Laplacian variance, and median-residual noise. A good image receives no enhancement. Conditional operations are:

- dark, bright, or low-contrast: LAB/CLAHE local contrast normalization;
- noisy: controlled low-strength color denoise;
- soft text: controlled unsharp masking.

The post-enhancement quality utility must be at least as good as the unenhanced candidate; otherwise enhancement is reverted. The pipeline is deliberately prepared for multiple internal candidates, but Phase 2 sends exactly one image to RapidOCR and does not add OCR passes without measured evidence. The pre-existing RapidOCR adaptive-threshold fallback remains unchanged.

## Configuration

| Setting | Default | Purpose |
|---|---:|---|
| `MAX_IMAGE_SIZE_MB` | 5 code default | Request byte limit. |
| `MAX_IMAGE_WIDTH` / `MAX_IMAGE_HEIGHT` | 4096 / 4096 | Header/decode dimension protection. |
| `MAX_IMAGE_PIXELS` | 12,000,000 | Decompression/pixel allocation ceiling. |
| `PREPROCESS_MAX_DIMENSION` | 960 | Downscale-only OCR processing bound; matches existing OCR size behavior. |
| `PREPROCESS_MIN_OCR_DIMENSION` | 600 | Documents the minimum useful target; images are not blindly upscaled. |
| crop padding / minimum | 2% / 160 px | Safe crop utility bounds. |
| document area range | 20%..95% | Server boundary-estimation acceptance. |
| enhancement enabled | true | Allows only conditional, quality-checked enhancement. |

The template includes these variables in `.env.example`. Default values remain conservative and require fixture/device calibration before production tuning.

## Test coverage added

`backend/tests/test_preprocessing.py` covers in-memory safe decode, MIME/magic validation, byte/dimension/pixel limits, malformed payloads, normal/mild/strong perspective quadrilaterals, crossed/degenerate corners, boundary detection, 0/90/180/270 rotation, safe crop bounds, downscale-only resize, dark/noisy/soft/low-contrast safety, and forced fallback behavior. It uses synthetic images only.

## Verification record

### Passed

- Phase 1 frontend regression: 6 test files / 30 tests passed.
- Frontend lint completed (one pre-existing `ScannerContainer` React hook dependency warning).
- Frontend TypeScript/Vite production build passed.
- SDK build passed.

### Blocked — do not treat as passed

- Backend unit/API/preprocessing tests: the machine exposes only an inaccessible Windows Store Python stub; no project virtual environment or Docker CLI is installed.
- OCR before/after regression for Aadhaar, PAN, Voter ID, ABHA, Farmer ID, and Passport: cannot run without the backend runtime and approved fixture set. The private `assets/` documents are not committed as fixtures.
- Decode/detection/rectification/pipeline latency average, p50, p95, and memory measurements: cannot be produced without the Python/OpenCV runtime. `PreprocessingResult.processing_time_ms` is implemented for future measurement; no values are claimed here.
- Real browser/mobile camera and backend round-trip tests: no mobile hardware/browser-camera environment is available.

## Known limitations

- Server boundary estimation is intentionally conservative and may use the original image rather than rectifying difficult, partial, low-edge, or non-card-shaped documents.
- Client geometry is not currently transmitted with the final crop; future metadata must be scaled to the submitted image and validated server-side before use.
- No automatic 180° orientation classifier is added in this phase. Existing OCR rotation fallback remains responsible for OCR-driven orientation recovery.
- The broader scan logger PII persistence identified in Phase 0 is outside Phase 2 scope; this new preprocessing module itself does not log PII or write images.

No Phase 3 OCR/layout work has been started.
