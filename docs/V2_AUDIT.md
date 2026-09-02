# V2 Engineering Audit (Phase 0)

**Audit date:** 2026-09-02  
**Audited revision:** `584e46720c440b1d17b5f8558136f1c22cfda01b`  
**Scope:** Current repository only. No production source, runtime configuration, or feature behavior was changed by this audit.

## Executive summary

IDScanner is a React/Vite browser scanner backed by a FastAPI service. The browser captures a camera or uploaded image, uses a Web Worker for pre-capture quality checks, then submits a cropped JPEG to FastAPI. The backend decodes the image in memory, uses a singleton RapidOCR ONNX engine, selects the strongest regex-based document extractor, reconstructs OCR reading order, and runs a document-specific field parser.

The codebase has a useful modular core: separate OCR, extractors, parsers, validators, schemas, and UI scanner components. The main Phase 0 concerns are production integration and data handling rather than a need to rewrite the OCR pipeline. In particular, the current Docker frontend cannot proxy its relative `/api` calls to the backend, the worker expects a missing OpenCV asset, the API writes raw PII to disk, and several published/API/benchmark contracts do not match the source.

## Files inspected

### Repository, deployment, and configuration

- `README.md`, `.gitignore`, `.env.example`, `docker-compose.yml`
- `.github/workflows/ci.yml`
- `backend/Dockerfile`, `backend/requirements.txt`, `backend/benchmark/*`
- `frontend/Dockerfile`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.ts`, `frontend/tsconfig*.json`, `frontend/README.md`
- `sdk/package.json`, `sdk/package-lock.json`, `sdk/tsconfig.json`, `sdk/src/id-scanner.ts`
- Existing `docs/*` deployment, architecture, API, benchmark, and security documents

### Backend

- `backend/app/main.py`
- `backend/app/api/health.py`, `backend/app/api/v1/scan.py`
- `backend/app/core/config.py`, `logging.py`, `security.py`, `scan_logger.py`
- `backend/app/ocr/engine.py`
- `backend/app/extractors/labels.py`, `line_reconstructor.py`, `regex.py`, `verhoeff.py`
- All `backend/app/parsers/*.py`, `backend/app/schemas/scan.py`, and `backend/app/validators/field_validators.py`
- All `backend/tests/*.py`

### Frontend

- `frontend/src/App.tsx` and styles
- All scanner components, hooks, CV modules, worker, types, and tests under `frontend/src/`

## Current architecture and components

```text
Camera / file upload
  -> React scanner container
  -> 320px video frame at up to 8 FPS -> module Web Worker -> quality decision
  -> high-resolution overlay crop -> JPEG Blob -> POST /api/v1/scan
  -> FastAPI validation and cv2.imdecode (memory)
  -> RapidOCR ONNX -> [{text, confidence, bbox}]
  -> extractor competition / classification
  -> spatial line reconstruction -> document parser -> ScanResponse JSON
  -> scan-history logger (memory and backend/logs/scan_history.jsonl)
```

Backend modules have clear responsibilities:

- `main.py` creates the FastAPI application, configures permissive CORS, mounts health and v1 routers, and initializes OCR in its lifespan hook.
- `ocr/engine.py` owns the process-local `RapidOCREngine` singleton.
- `extractors/regex.py` provides type detection and primary identifier extraction; `verhoeff.py` validates Aadhaar candidates.
- `extractors/line_reconstructor.py` provides reading order for parser input.
- `parsers/` turn OCR lines into structured field candidates; `validators/` normalizes and rejects weak values.
- `scan_logger.py` retains the latest 100 scans in memory and appends all scan records to a JSONL file.
- The frontend consists of a camera hook, frame transport component, worker CV pipeline, overlay/HUD, result card, and upload fallback.

## Data flow and request lifecycle

1. `ScannerContainer` starts the environment-facing camera at an ideal 1280x720. It retries with looser constraints and then any camera.
2. `VideoPreview` draws video to a hidden 320px-wide canvas and sends an `ImageBitmap` (or `ImageData`) to a module Worker, limited to 8 FPS.
3. The worker attempts to load `/lib/opencv.js`; when ready it measures exposure, glare, Laplacian variance, a Canny-contour card candidate, and five-frame stability.
4. A `READY_TO_CAPTURE` result calls `captureHighResFrame`. The UI crops the visible video based on the overlay rectangle, JPEG-encodes at quality 0.92, stops the camera, and posts `file=document.jpg` to the relative endpoint `/api/v1/scan`.
5. `scan_document` reads the complete multipart upload, rejects files larger than `MAX_IMAGE_SIZE_MB` (5 MB by code default) or a declared non-JPEG/PNG/WEBP media type, and uses `numpy.frombuffer` plus `cv2.imdecode(..., IMREAD_COLOR)`. It does not write the image itself to disk.
6. The API runs normal-orientation OCR and all supported extractors unless a recognized `document_type` query parameter restricts the selection. It retains the candidate with the greatest extractor confidence.
7. If the best result is absent or below `RETRY_THRESHOLD` (0.75), it OCRs counter-clockwise then clockwise 90-degree rotations. If still low, it runs the original image with adaptive thresholding.
8. If the winning extractor confidence is at least `HIGH_CONFIDENCE_THRESHOLD` (0.80), the API normalizes the type, adds its primary identifier, reconstructs lines from that same winning OCR pass, runs the matching parser, and returns only parser fields whose status is `ok`. Parser `overall_status` is logged but does not change a successful API response.
9. All successful and low-confidence calls are logged with identifier, fields, client IP, confidence, latency, and status. The response schema has `success`, `document_type`, optional `identifier`, `fields`, optional `message`, and optional `error_code`.

## OCR initialization, configuration, and output

`RapidOCREngine` constructs `rapidocr_onnxruntime.RapidOCR()` without custom detector/recognizer/model/session options. It performs one synthetic 300x500 warm-up inference during the FastAPI lifespan startup. `is_ready()` lazily calls `initialize()` if needed, so `/ready` can initialize OCR as a side effect. The singleton is process-local; every Uvicorn worker gets its own model instance.

The configured inputs are `OCR_DEVICE` and `OCR_WORKERS`, but they are not passed to RapidOCR or used to select execution providers/threads. Images above `MAX_IMAGE_DIMENSION` (960 default) are resized just before OCR. The optional retry preprocessing is grayscale adaptive Gaussian thresholding (block size 11, constant 2). No deskew, perspective correction, crop detection, color normalization, orientation classification, or OCR-language/model configuration is currently applied server-side.

OCR output is normalized to a list of dictionaries:

```json
{"text":"ABCDE1234F","confidence":0.98,"bbox":[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]}
```

## Spatial line reconstruction

`reconstruct_lines()` discards empty OCR text, calculates each quadrilateral's mean Y and minimum/maximum X, sorts items by mean Y, and creates a new horizontal band when the next item differs from the *first* item's Y in the current band by more than `LINE_MERGE_Y_TOLERANCE` (15 pixels by default). Items are then emitted in X-start order within each band, one `OCRLine` per OCR box. It does not merge adjacent boxes into a textual line and does not scale tolerance for image resolution, skew, text height, or perspective.

## Classification and supported documents

Classification is a best-confidence competition among regex extractors, not a dedicated layout/model classifier. Supplying a recognized `document_type` query alias narrows that competition to one extractor; unknown aliases silently fall back to all types.

| Canonical API type | Extractor / identifier rule | Parser fields (mandatory; optional) |
|---|---|---|
| `aadhaar_card` | 12 digits with OCR `O` handling and Verhoeff check; rejects farmer context and likely back side | `name`, `dob`, `gender`; none |
| `aadhaar_card_back` | Verhoeff Aadhaar plus address/UIDAI-back markers | `aadhaar_number`, `address`, `state`, `pincode`; `relation_type`, `relation_name` |
| `pan_card` | case-insensitive `AAAAA9999A` pattern | `name`, `father_name`, `dob`; none |
| `voter_id` | `AAA9999999` or legacy slash-separated EPIC pattern | `name`, `relation_name`; `gender`, `dob`, `relation_type` |
| `abha_number` | normalized 14-digit ABHA number, or contextual ABHA handle; excludes common government/support email domains and Aadhaar-back context | `name`, `gender`, `dob`; `mobile` |
| `farmer_id` | 11 digits formatted `999 99 99 99 99`, with farmer context or confidence >0.7 | `name`, `gender`, `dob`; `mobile`, `aadhaar_number` |
| `passport` | passport/machine-readable-zone pattern with passport context or high confidence | `name`, `gender`, `dob`; `surname`, `given_name`, `expiry_date`, `nationality` |

Document aliases include `aadhaar`, `aadhaar_back`/`aadhar_back`, `pan`, `voter`/`epic`, `abha`, `farmer`/`agri`/`agriculture`/`kisan`, and `passports`/`indian_passport`.

## Parsers and validators

Every parser implements `BaseDocParser.extract_fields()` and returns `ParsedDocument`, containing `FieldResult(value, confidence, status)` entries. The base class nulls low-confidence/not-found values and sets `overall_status=rescan_required` when a mandatory parser field is unavailable. It includes bilingual label-anchor lookup, nearby same-line/below-line name extraction, DOB extraction that rejects common helpline values, and gender normalization.

Specialized logic includes Aadhaar-back footer filtering/address assembly, PAN father/name disambiguation, Voter relation/name disambiguation, ABHA name protections against e-mail/address text, Farmer name/masked-mobile/Aadhaar extraction, and Passport VIZ plus partial ICAO type-3 MRZ parsing.

The reusable validators cover Verhoeff, names and label/header rejection, date/DOB and expiry normalization, gender normalization, Indian mobile validation, Indian state detection, pincode normalization, and address quality/footer-leak rejection. There is no cryptographic, government-authoritative, or MRZ check-digit validation beyond these rules.

## API endpoints and response contract

| Method and path | Current behavior |
|---|---|
| `GET /health` | Liveness only; always returns `{"status":"healthy"}` and does not check OCR. |
| `GET /ready` | Returns 200 when the engine is ready; otherwise 503. Calling it may initialize OCR. |
| `POST /api/v1/scan` | Requires multipart field **`file`**. Optional `document_type` is a **query** parameter. Protected only when `API_TOKEN` is configured. |
| `GET /api/v1/logs?limit=1..200` | Returns persisted/in-memory PII scan records. |
| `DELETE /api/v1/logs` | Clears the in-memory buffer and truncates the persisted history. |

The single Pydantic `ScanResponse` omits null optional values. It does not expose OCR lines, field-level confidence/status, parser failure reasons, request ID, processing time, image metadata, API version negotiation, or a typed document-union response.

## Frontend, worker, and auto-capture

The worker reuses OpenCV Mats for grayscale, blur, and edges, explicitly deletes per-frame matrices, and closes transferred bitmaps. Its quality gates are: exposure 40..240, glare <=5%, Laplacian variance >=100, quadrilateral contour area 20..90% of frame, aspect ratio 1.3..1.8, then five samples with max center shift 10px and area variance <=5%. It reports `READY_TO_CAPTURE` only when all gates pass.

The user can also manually capture or upload JPEG/PNG/WebP. The result card displays/copies identifier and fields, retains the captured document image in React state, and offers the raw JSON response. The shipped SDK is not integrated with this UI or API: `IdScanner.open()` waits one second and returns a hard-coded mock result.

## Dependencies and delivery configuration

- Backend: FastAPI 0.111, Uvicorn 0.30, Pydantic 2.12, RapidOCR ONNX Runtime 1.2.3, ONNX Runtime 1.25.1, OpenCV headless 4.10, NumPy 2.4, pytest, and httpx.
- Frontend: React 19, Vite 8, TypeScript 6, Vitest, Testing Library, and oxlint.
- SDK: TypeScript 5 only.
- Backend image: Python 3.11 slim with build tools, OpenCV system libraries, and curl; it starts one Uvicorn process by default.
- Frontend image: Node 20 build stage and stock Nginx static serving stage.
- Compose exposes backend `4500:8000`, frontend `3233:80`, gives the backend a 4 GB memory limit, adds health checks, and bind-mounts `./backend:/app`.
- CI runs selected pure backend tests (not API or real-image tests), frontend build, and Docker image builds. It does not run frontend tests/lint, SDK build, security scans, integration tests, or benchmark/load tests.

## Baseline verification

### Executed successfully

| Check | Result |
|---|---|
| `frontend/npm.cmd ci` | Passed; 109 packages installed; npm reported 0 vulnerabilities. |
| `frontend/npm.cmd test` | **Passed: 3 files, 11 tests.** |
| `frontend/npm.cmd run lint` | Passed with 2 warnings: unused `e` in the ngrok plugin and missing React effect dependencies in `ScannerContainer`. |
| `frontend/npm.cmd run build` | Passed: TypeScript build and Vite production bundle. |
| `sdk/npm.cmd ci && npm.cmd run build` | Passed; SDK TypeScript declaration/JS build completed. |

### Not executable in this audit environment

The workspace has no usable Python interpreter (`python.exe` is the inaccessible Windows Store stub), no repository virtual environment, no Docker CLI, and WSL access is denied. Therefore the following required checks were **blocked by the environment**, not marked passing or failing:

- Backend pytest suite and API tests.
- Local FastAPI launch, `/health` and `/ready` HTTP checks, and an end-to-end scan.
- `backend/benchmark/run_benchmark.py` and `load_test.py`.
- Docker/Compose build and the deployed frontend-to-backend scan path.

No `test_image/` fixture directory exists in this checkout (it is ignored for privacy). The 11 real-image tests would be skipped by their fixture guard, so baseline parser accuracy cannot be measured here. Static inventory finds 135 test functions, with two seven-parser parameterizations, for an expected 147 collected cases before fixture-dependent skips. The real-image suite declares expected values for 11 private fixtures but no aggregate accuracy metric.

The repository's existing `docs/BENCHMARKS.md` reports historical/claimed figures (60, 300, and 585 scans/minute; high-load P95 about 1,450 ms). Those figures were not reproduced and must not be treated as this audit's baseline. The simple benchmark script targets the current `file` multipart name, but the load-test and Locust scripts use `image`, put `document_type` in form data rather than the API query, and expect a removed/nonexistent `details` response key. Additionally, `psutil` and `locust` are not declared in `backend/requirements.txt`.

### Pre-existing failures

No failing test result was observed because backend execution was unavailable. The following are pre-existing, source-level blockers/inconsistencies that require verification/fix in later phases:

1. `frontend/public/lib/opencv.js` is absent, but the worker imports exactly `/lib/opencv.js`; automatic capture will remain in `WORKER_INITIALIZING`/error on a normal static deployment unless that asset is supplied by another untracked deployment mechanism.
2. The Docker frontend is stock Nginx with no `/api` proxy, while the frontend always fetches relative `/api/v1/scan`. Compose's `API_URL` environment variable is unused by built code. The Docker scanner therefore cannot reach `scanner-api` through the documented frontend URL.
3. API docs say `image` (or `file`) and BMP are accepted, while implementation requires `file` and allows only JPEG/PNG/WEBP. Benchmark load clients use the stale contract.
4. API success is based on identifier extractor confidence even when the field parser returns `rescan_required`; that parser result is logged but not communicated to the client.

## Current strengths

- Incremental retry behavior preserves the primary OCR path and only adds rotations/adaptive thresholding when extraction confidence is low.
- OCR output includes geometric data, and spatial ordering is separated from parsing.
- Document support and parser interfaces are modular, with regression tests for extractor outputs and parser no-guessing cases.
- Aadhaar uses Verhoeff; ABHA and Aadhaar-back include explicit cross-document disambiguation safeguards.
- Images are decoded from request bytes without intentionally writing raw images to disk.
- Camera fallbacks, manual capture, and file upload offer a usable recovery path when automatic detection is unavailable.
- The frontend and SDK builds are currently reproducible from their lockfiles.

## Weaknesses, risks, and limitations

### Technical and accuracy risks

- Regex-confidence competition can misclassify a syntactically valid identifier without verifying visual document layout; PAN and EPIC syntax have no authoritative checksum.
- OCR confidence is treated as document confidence. There is no calibrated confidence model, field-confidence response, cross-field agreement, or image-quality evidence returned to clients.
- Rotation only tries +/-90 degrees after a low result; 180 degrees, perspective, skew, crop bounds, multi-side sessions, and device/image EXIF orientation are not handled.
- Fixed 15-pixel banding is resolution- and skew-sensitive. It does not join text fragments, so parser behavior depends heavily on RapidOCR box segmentation.
- Parser success policy is inconsistent with endpoint success policy; fields may be silently omitted from a `success:true` response.
- Passport MRZ parsing does not verify MRZ check digits and its two-digit DOB century heuristic is fixed.
- Private fixtures are absent from the repository and no confusion matrix, field accuracy, false-positive rate, or calibrated acceptance metric exists.

### Performance risks

- `scan_document` is `async` but performs synchronous OpenCV and ONNX work in the event loop. Per-process concurrent scans can block one another.
- OCR initializes once per process, so multi-worker scaling multiplies model memory and startup/model-download risk.
- `OCR_DEVICE` and `OCR_WORKERS` are configuration dead ends today; they do not configure RapidOCR/ONNX.
- Uploaded image dimensions are constrained only by a post-decode resize. Compressed image size does not prevent decompression-pixel/memory abuse before decoding.
- The documented throughput is not reproducible with the checked-in load scripts/dependencies; the Docker default is one Uvicorn process.

### Security and privacy risks

- `scan_logger.py` persists raw identifiers, complete extracted PII, timestamps, and client IPs to `backend/logs/scan_history.jsonl`, and reloads it at startup. This directly contradicts the current README/security claims of zero PII logging and stateless operation.
- `/api/v1/logs` exposes that PII, and `DELETE /api/v1/logs` destroys the audit trail. Both are publicly callable whenever `API_TOKEN` is unset, which is the default.
- Runtime CORS ignores `settings.cors_origins` and permits `allow_origins=["*"]` together with credentials. The `.env` setting is therefore ineffective.
- API token comparison is ordinary string equality, with no rate limit, request body streaming limit, tenant isolation, audit controls, key rotation, or role separation.
- No TLS, security headers, trusted-proxy configuration, malware scanning, content signature checking, or retention/deletion policy exists in application/Compose code. TLS guidance is documentation-only.
- The current worktree has an unrelated modification to `.env.example` containing an altered ngrok token placeholder. It was not created or changed by this audit and should be reviewed before commit; credentials should not be stored in example or tracked files.

### API and frontend UX limitations

- Request/response documentation, SDK types, benchmark expectations, and API implementation have drifted. The SDK result interface is incompatible with `ScanResponse` and is a mock.
- No API version deprecation strategy, idempotency, request IDs, typed per-document schemas, pagination cursor, consistent error envelope, or client-configurable endpoint exists.
- No document-type selector exists in the UI, so every normal scan tests every extractor. The user cannot know why a field was omitted or distinguish parser confidence from OCR success.
- The user-facing result says "Verified" and "100% Validated" despite heuristic OCR/parsing and no authoritative verification.
- Capture uses DOM geometry and `document.querySelector`, which is fragile for responsive layout, browser video transformations, multiple scanner instances, and orientation changes. The crop lacks bounds checks/rounding.
- Auto-capture has no debounce/in-flight guard beyond later state updates; several worker results can arrive while capture begins. `consecutiveStableRef` is declared but unused.
- Worker initialization and actual device CV are not tested. The worker has an unused timeout ref and lacks a robust cancellation/backpressure protocol.
- Captured image and raw PII remain visible/copyable in browser memory/UI until a rescan or page lifecycle cleanup.

### Testing gaps

- CI omits backend API tests, real-image tests, frontend tests, frontend lint, SDK build, Compose integration, and all benchmarks.
- Backend API testing covers only health/readiness state mocks and invalid MIME type; it does not test a successful route, size/empty/decode cases, auth, logs, aliases, fallback OCR, schema variants, or error paths.
- No frontend integration/E2E tests cover camera permission flows, worker loading, quality transitions, auto-capture, crop, upload, API errors, mobile browsers, or Docker networking.
- No security/privacy tests assert CORS, log redaction/retention/access control, image limits, headers, or authorization.
- No pinned/committed private de-identified fixture strategy supports reproducible real-image accuracy measurement.

## Recommended upgrade sequence

1. **Phase 0 exit gate:** provide a supported Python 3.11 runtime and Docker access, then rerun full pytest, API health/readiness/scan, Docker Compose, benchmark, and private-fixture accuracy baselines without changing production behavior. Resolve the two integration blockers only after confirming their intended deployment model.
2. **Phase 1:** make capture-quality telemetry observable and testable; provide the OpenCV worker asset through a deliberate build path; validate camera/crop behavior across target browsers.
3. **Phase 2:** add measured, feature-flagged image preprocessing with fixture-based regression gates.
4. **Phase 3:** replace fixed spatial assumptions incrementally with layout-aware reconstruction and expose diagnostic confidence evidence internally.
5. **Phase 4–5:** strengthen classification and field validation with document evidence, calibrated confidence, field-level results, and no-guessing regression data.
6. **Phase 6:** reconcile privacy claims with implementation, remove/secure PII persistence by product decision, enforce configured CORS/auth/rate limits, and version the API.
7. **Phase 7–9:** replace the mock SDK, formalize contracts and benchmarks, then harden reproducible builds, deployment, observability, and operations.

No Phase 1 implementation was started.
