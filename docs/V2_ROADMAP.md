# V2 Roadmap

This roadmap is intentionally sequenced to preserve working behavior. A phase starts only after the previous phase has recorded its tests, metrics, compatibility impact, and rollback plan.

## Phase 0 - Audit

Document the current implementation, run reproducible baselines, identify contract/deployment/privacy drift, and define exit gates. Deliver `V2_AUDIT.md` and this roadmap. Do not change scanner behavior.

**Exit gate:** full backend/API/Docker/benchmark baselines are rerun in a supported runtime and private-fixture parser accuracy is recorded.

## Phase 1 - Capture Intelligence — Completed

Make the browser capture path dependable before changing OCR: package the worker CV dependency deliberately, instrument quality decisions, validate device/browser behavior, refine capture state handling, and add camera/worker/crop integration tests.

**Exit gate:** automatic and manual capture work in the supported deployment topology with measurable false-capture and capture-readiness metrics.

## Phase 2 - Image Preprocessing — In Progress

Add feature-flagged, benchmarked preprocessing stages such as safe dimension/pixel limits, orientation handling, crop/perspective correction, glare/contrast treatment, and deskew only where fixtures prove an improvement.

**Exit gate:** per-document and per-field accuracy improves or remains unchanged under a fixed latency/memory budget.

## Phase 3 - OCR/Layout Intelligence

Improve OCR observability, layout ordering, multi-box text reconstruction, and confidence evidence. Keep RapidOCR compatibility until a measured alternative is justified.

**Exit gate:** layout regression corpus passes and accuracy/latency dashboards identify results by document type and image condition.

## Phase 4 - Document Intelligence

Strengthen classifier evidence and document-specific parsers incrementally. Add document-side/session handling where required and retain explicit no-guessing safeguards.

**Exit gate:** classifier confusion matrix, parser regression suite, and per-document acceptance thresholds are approved.

## Phase 5 - Validation & Confidence

Introduce field-level confidence/status in a versioned contract, cross-field consistency checks, calibrated rescan decisions, and clear client guidance without overstating verification.

**Exit gate:** confidence calibration, false-accept/false-reject targets, and API backward compatibility are demonstrated.

## Phase 6 - Security & Production API

Reconcile implementation with privacy policy, decide the permitted PII retention model, protect operational endpoints, enforce CORS/auth/rate limits, validate image attack limits, add structured/redacted logging, and version the API.

**Exit gate:** security/privacy review, endpoint authorization tests, retention tests, and deployment threat-model actions are complete.

## Phase 7 - SDK & Developer Platform

Replace the mock SDK with a real, versioned client; publish typed contracts, examples, error semantics, request correlation, and integration guidance.

**Exit gate:** SDK integration tests run against a versioned API contract and sample applications.

## Phase 8 - Testing/Benchmarking

Create a de-identified fixture governance process, end-to-end/browser/device coverage, benchmark dependency lockfiles, reproducible load profiles, accuracy dashboards, and CI quality gates.

**Exit gate:** CI runs unit, integration, E2E, security, accuracy, and performance gates with published thresholds.

## Phase 9 - Deployment & Production Hardening

Harden container topology, frontend-to-backend routing, immutable artifacts, configuration validation, TLS/proxy controls, observability, capacity planning, backup/retention controls, and incident runbooks.

**Exit gate:** staging production-readiness review, load/chaos validation, monitoring/alerting, and documented rollback are complete.

## Cross-phase rules

- Preserve existing supported document types and public behavior unless a versioned migration is approved.
- Make changes behind tests and measurable baselines; do not rely on claimed benchmark values.
- Treat document images and extracted identity data as sensitive data in every phase.
- Do not advance to the next phase while required checks are failing, skipped without an approved reason, or not reproducible.
