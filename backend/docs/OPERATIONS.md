# Phase 9: Operations & Observability

## Overview
This document outlines how to observe, monitor, and manage the lifecycle of the Document Scanner API.

## 1. Lifecycle Probes
* **Readiness Check (`/ready`)**: Validates that the OCR ONNX model is loaded, warmed up, and capable of processing traffic. Kubernetes should use this for traffic routing.
* **Health Check (`/health`)**: Validates the web server is responsive. Should be used for liveness probes.
* **Graceful Shutdown**: Handled via FastAPI's `@asynccontextmanager` lifespan. Container receives SIGTERM, stops accepting new traffic, finishes in-flight requests, unloads the OCR model, and exits.

## 2. Prometheus Metrics
The API exposes an endpoint at `/metrics` for Prometheus scraping.
Key metrics exported:
* `api_request_latency_seconds`: Histogram of total request latency by endpoint.
* `ocr_processing_latency_seconds`: Histogram of raw OCR (ONNX) engine latency.
* `preprocessing_latency_seconds`: Histogram of OpenCV image normalization latency.
* `parser_latency_seconds`: Histogram of schema parsing latency by document type.
* `api_errors_total`: Counter for errors, segmented by `error_code`.
* `document_type_total`: Counter showing distribution of processed documents (`status=ok`, `status=low_confidence`, `status=incomplete_fields`), categorized by `document_type`.

**Note:** No PII is exposed in Prometheus metrics.

## 3. Structured Logging
* Logs are emitted in JSON format (via standard python formatters) or strict structured text depending on `APP_ENV`.
* Logs contain a `request_id` allowing you to trace a scan through preprocessing, OCR passes, schema matching, and validation.
* **PII Redaction**: Explicit fields containing sensitive strings (like `voter_id`, `name`) are excluded from logs. You will only see metadata such as `confidence`, `document_type`, and `processing_time_ms`.

## 4. Error Handling & Edge Cases
* **Failed OCR**: Handled by falling back to 90-degree rotations and adaptive thresholding passes.
* **Malformed Requests**: Triggers standard HTTP 422 with `VALIDATION_FAILED` metrics.
* **Container Restarts**: The stateless nature of the container ensures no data corruption upon restart. The startup penalty is ~2-3 seconds for model warm-up.
