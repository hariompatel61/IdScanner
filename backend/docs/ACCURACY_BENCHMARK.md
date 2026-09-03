# Accuracy Benchmark

This document defines the methodology for evaluating the IDScanner system's accuracy, performance, and validation robustness.

## Dataset
The benchmark uses entirely synthetic, safe fixtures to prevent the exposure of PII or actual government identifiers.
All fixtures are stored in `backend/tests/fixtures/benchmarks/dataset/` under the format `{document_type}/{condition}/{sample_id}/`.

## Methodology
The benchmark script (`backend/scripts/benchmark.py`) mimics a true client by generating `multipart/form-data` requests via the `fastapi.testclient.TestClient` against the exact `/api/v1/scan` route.

Metrics tracked:
1. **Classification Accuracy**: Did the document classify correctly?
2. **Field Extraction Accuracy**: Broken down into Exact Match, Normalized Match, and Missing Rates.
3. **Validation / Decision Metrics**: Evaluating False Accepts and False Rejects.
4. **Performance Latency**: `processing_time_ms` distribution and throughput.

## Baseline Guarantee
No Phase 8 fixes were applied to the OCR or extraction engine until the baseline was evaluated. Any regressions or bugs discovered during usage form the Regression Corpus in the test suite.
