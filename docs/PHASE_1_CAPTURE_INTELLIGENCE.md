# Phase 1: Advanced Capture Intelligence

**Implemented:** 2026-09-02  
**Scope:** Browser capture quality only. OCR, parsers, extractors, API behavior, and server-side preprocessing were not changed.

## Outcome

The scanner now auto-captures only after a configurable set of client-side OCR-usability gates succeeds. Analysis stays in the existing module Web Worker; the main thread still only downsizes the preview and transfers frames at the existing default maximum of 8 FPS. No preview frame is sent to the backend. Only the selected high-resolution JPEG is uploaded.

The OpenCV.js URL used by the prior worker was not present in this checkout's `frontend/public` directory. Rather than make capture depend on that missing static asset, the Phase 1 worker now uses a small, self-contained pixel-analysis path bundled by Vite. This preserves the Worker architecture and makes its behavior testable without a global OpenCV runtime.

## Capture quality contract

`CaptureQuality` is emitted on every worker result as `result.quality`:

```ts
{
  document_detected: boolean,
  document_area_ratio: number,
  blur_score: number,          // normalized 0..1
  glare_score: number,         // 1 is no glare
  brightness_score: number,    // normalized 0..1
  contrast_score: number,      // normalized 0..1
  edge_score: number,          // visibility of all four sides
  stability_score: number,     // temporal score across frames
  perspective_score: number,   // approximate quadrilateral geometry score
  overall_score: number,       // weighted 0..1 readiness score
  ready: boolean,
  rejection_reason: CaptureRejectionReason,
  geometry?: { bounding_box, corners, aspect_ratio },
  processing_time_ms?: number
}
```

The existing top-level worker values (`detected`, `blurScore`, `brightnessScore`, `glareScore`, `stabilityScore`, `overallQuality`, and `reason`) remain populated for compatibility.

## Worker analysis pipeline

1. Convert the transferred `ImageBitmap`/`ImageData` to grayscale in the Worker.
2. Calculate mean brightness, contrast (pixel standard deviation), near-white glare ratio, and Laplacian variance blur metric.
3. Build a Sobel edge map, apply two small worker-side dilation passes, and select the strongest rectangular connected component.
4. Estimate bounding box and four practical corners from extrema of edge points; score side visibility and opposite-side/angle/polygon consistency as an approximate perspective/skew signal.
5. Reject ambiguous similarly sized rectangular candidates and any candidate that touches the analysis-frame boundary (not all document edges are visible).
6. Score temporal position/area stability over five frames. Motion and area change are graded, but a score below the configured gate cannot auto-capture.
7. Combine blur, brightness, glare, contrast, edge visibility, size, stability, and perspective using documented weights. `ready` requires both the overall threshold and every required individual gate.

## Configurable gates

All defaults are exported as `DEFAULT_CAPTURE_QUALITY_CONFIG` from `frontend/src/scanner/cv/captureQuality.ts`. A caller can pass a partial configuration through `VideoPreview`/`useScannerWorker`; it is sent to the Worker with `SET_CAPTURE_CONFIG` and resets temporal history.

| Setting | Default | Rationale / effect |
|---|---:|---|
| `min_brightness` / `max_brightness` | 55 / 220 | Starts from the previous 40..240 worker exposure gate, narrowed for readable text. |
| `max_glare_ratio` | 0.06 | Near-white pixels above 6% reject the frame; prior worker used 5%. |
| `min_blur_variance` | 90 | Laplacian variance floor, near the prior 100 threshold. |
| `min_contrast` | 24 | Pixel standard deviation floor for separable text/background. |
| document area range | 0.20..0.90 | Retains prior size range; enforces move-closer/keep-in-frame guidance. |
| document aspect range | 1.20..2.05 | Broad card/passport-facing range used when selecting candidates. |
| `min_edge_score` | 0.65 | Requires usable evidence for all four perimeter sides. |
| `min_perspective_score` | 0.55 | Rejects weak quadrilateral geometry with tilt guidance. |
| stability window / score | 5 / 0.80 | Retains five-frame intent and prior 10px/5% movement limits. |
| `auto_capture_threshold` | 0.82 | Minimum weighted readiness after individual safety gates pass. |
| edge gradient threshold | 70 | Sobel cutoff at preview resolution; fixture/device calibration is required before changing it. |

These are intentionally configuration values, not universal device claims. Phase 1 includes synthetic regression coverage; target-device fixture calibration remains required before production tuning.

## Guidance presented to the user

The HUD now displays current quality percentage plus the first blocking action:

- Document not detected
- Show one document only
- Move closer
- Keep document inside frame
- Show all edges
- Improve/reduce lighting
- Improve contrast
- Reduce glare
- Hold still / allow focus
- Hold steady
- Reduce tilt

Manual capture and image upload remain available. Automatic capture uses an in-flight guard so repeated worker results cannot create concurrent uploads.

## Tests and verification

### Automated checks passed

| Check | Result |
|---|---|
| Full frontend test suite | **6 files, 30 tests passed** |
| Existing frontend tests | **11/11 passed** |
| New capture-quality unit/edge-case tests | **16 passed** |
| New camera/worker/UI integration tests | **3 passed** |
| Frontend lint | Passed; retains one pre-existing React hook dependency warning in `ScannerContainer`. |
| Frontend typecheck and production build | Passed (`tsc -b && vite build`). |

New test coverage includes brightness, contrast, blur, glare, edge visibility, corner geometry, stability, readiness scoring, dark/overexposed/blank/small/partial/rotated/tilted/multiple-rectangle frames, camera-frame-to-worker transport, worker-to-HUD guidance, ready-to-auto-capture, and not-ready-no-capture.

### Performance

- Worker frames remain capped at the existing 8 FPS and are downscaled to 320px wide before transfer.
- The worker reports `processing_time_ms` with every `CaptureQuality` result.
- The automated synthetic 320x180 analysis test passed the Phase 1 responsiveness ceiling of **less than 100 ms**. This is a CI safety bound, not a claim of mobile-device latency.
- Heavy pixel and geometry computation is executed in the Worker; the main thread does not perform OCR or per-frame image analysis.
- The local Vite application was started successfully and returned **HTTP 200** at `http://127.0.0.1:3233/`. The optional ngrok plugin now warns rather than terminating Vite when no executable is available.

### Environment-limited verification

- The supplied private local images under `assets/` were inspected for local test availability but are not added to test fixtures or source control.
- A real mobile-browser/camera validation (good/poor light, glare, tilt, partial card, movement, and low-end hardware) could not be performed in this Windows execution environment because no mobile device/browser camera session is available.
- Backend regression, OCR checks against the supplied images, API health checks, Docker verification, and benchmark execution remain blocked because this environment still lacks a usable Python runtime and Docker CLI. No backend code was changed in Phase 1.

## Files changed

- `frontend/src/scanner/cv/captureQuality.ts` — configurable pure quality model and algorithms.
- `frontend/src/scanner/worker.ts` — Worker integration and frame timing.
- `frontend/src/scanner/types/index.ts` — quality/config/geometry contracts.
- `frontend/src/scanner/hooks/useScannerWorker.ts` and `components/VideoPreview.tsx` — Worker configuration transport.
- `frontend/src/scanner/components/ScannerContainer.tsx` and `ScannerHUD.tsx` — readiness-gated auto-capture and guidance.
- `frontend/vite.config.ts` — optional ngrok spawn failure no longer stops local scanner development.
- `frontend/src/tests/captureQuality.test.ts`, `cameraWorker.integration.test.tsx`, and `captureUi.integration.test.tsx` — Phase 1 test coverage.

No Phase 2 image preprocessing or later-phase changes were implemented.
