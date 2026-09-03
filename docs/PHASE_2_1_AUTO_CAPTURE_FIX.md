# Phase 2.1 - Auto-Capture Regression Fix

## Scope

This change fixes only the frontend auto-capture delivery path. The Phase 2
image decoder, preprocessing pipeline, OCR, classifiers, parsers, validators,
and backend API are unchanged.

## Root cause

`VideoPreview` submitted a new frame on every 8 FPS tick, then accepted a
Worker result only when its ID matched the newest submitted frame ID. On a
real device, Worker analysis can complete after the next preview tick. The
valid result was then treated as stale and discarded before `ScannerContainer`
could observe the Worker-authoritative `quality.ready` value. Manual capture
does not depend on this bridge, explaining why it continued to work.

The asynchronous `createImageBitmap()` continuation also read the mutable
latest frame ID instead of retaining the ID for the bitmap it created.

## Fix

- Document-region quality: detection still uses the full downscaled preview,
  while brightness, contrast, glare, and blur are now measured within the
  detected document bounds. A dark background can no longer make a clear,
  well-lit card fail those document-specific gates. The thresholds themselves
  are unchanged.
- Rejection guidance now prioritizes actual exposure, glare, contrast, and
  blur failures before an edge-visibility failure. This does not bypass the
  edge gate; it gives users the actionable reason when low light also weakens
  edges.
- The preview permits one analysis request at a time. It keeps the exact frame
  ID with that request and forwards its completed result to the UI.
- The preview waits for non-zero intrinsic video dimensions before drawing a
  frame, which avoids an iOS Safari stream-start timing failure. Browsers
  without `createImageBitmap()` continue through the existing `ImageData`
  fallback.
- The next downscaled frame is submitted only after the active result, Worker
  error, bitmap failure, or component cleanup releases that request. Analysis
  remains capped at 8 FPS and stays in the Worker; preview frames are never
  uploaded.
- The Worker hook restarts a failed Worker and reapplies the existing quality
  configuration. Unmount terminates the active Worker and cancels restart work.
- `CaptureQuality.ready` remains the single readiness decision. Its existing
  configurable five-frame stability window and quality thresholds are not
  lowered or duplicated in the UI.
- The capture/upload lock now releases in all terminal paths: successful and
  failed upload, missing video/canvas, JPEG generation failure, and file-reader
  failure. A Worker-reported processing error also clears it. It still prevents
  duplicate captures while work is in progress.
- `ScannerContainer` accepts an `autoCaptureEnabled` prop, enabled by default.
  The scanner HUD is auto-capture-only; when deliberately disabled, it states
  that status and does not offer a camera capture button. Image upload remains
  the explicit fallback.

## Automated regression coverage

- delayed Worker result is delivered rather than discarded by a newer preview
  tick;
- a clear document within a dark preview is scored using its document region,
  rather than being rejected as a dark full-frame image;
- not-ready and unstable results do not capture;
- ready/stable results capture exactly once, including repeated ready results;
- an in-progress upload prevents a second capture;
- success and failure recovery permit the next scan;
- the manual camera capture control is absent, while auto-capture opt-out is
  respected and image upload remains available;
- Worker restart continues to accept analysis and unmount terminates the Worker.

## Verification (2026-09-02)

| Check | Result |
| --- | --- |
| Frontend tests | PASS - 36/36 |
| Lint | PASS with one pre-existing `ScannerContainer` exhaustive-deps warning |
| Typecheck | PASS (`tsc -b`, as part of production build) |
| Frontend production build | PASS |
| SDK build | PASS |
| Local Vite startup / HTTP smoke | PASS - HTTP 200 on `127.0.0.1:3233` |
| Interactive browser camera test | NOT TESTED - no interactive browser/camera available to this environment |
| Mobile browser test | NOT TESTED - no mobile hardware available |
| Backend / Phase 2 runtime regression | NOT VERIFIED - Python/Docker runtime is unavailable here; Phase 2 files were not modified |

## Limitations

The Worker restart mechanism is covered by a deterministic lifecycle test, but
browser-specific camera permissions, actual device frame timing, and mobile
hardware still require a manual device check. No document images or identity
data are used in the automated tests or logged by this change.
