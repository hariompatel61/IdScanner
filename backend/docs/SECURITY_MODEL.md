# Security Model & Operational Guardrails (Phase 6)

## 1. Request and Payload Defenses
The API applies rigid boundaries to all incoming scan requests before any expensive parsing or OCR can begin:
- **Maximum Payload:** Hard capped at 10MB (configurable via \MAX_UPLOAD_SIZE_BYTES\). Requests exceeding this are rejected at the stream boundary without buffering fully into memory.
- **Decompression Bombs:** We inspect image headers safely. Any image exceeding \max_image_dimension\ or \max_image_pixels\ (configurable) is rejected immediately with an HTTP 400.
- **MIME Spoo?ng:** Relying on the Content-Type header is unsafe. We validate the actual binary signatures of standard image formats (JPEG, PNG, WEBP). Non-image and potentially executable content will be blocked at the decode layer.

## 2. Resource & Concurrency Control
- **OCR Concurrency:** Because RapidOCR is heavily CPU bound, the application guards the inference block using an \syncio.Semaphore\ matching the CPU cores available (configurable via \MAX_CONCURRENT_OCR\). Excess requests queue safely up to the timeout.
- **Timeouts:** A strict timeout (\API_TIMEOUT_SECONDS\) is placed over the OCR inference pipeline to prevent stalled requests from hanging the worker threads.
- **Rate Limiting:** A sliding window rate limiter prevents abuse of the API by blocking IPs exceeding the threshold (\RATE_LIMIT_REQUESTS\ / \RATE_LIMIT_WINDOW\).

## 3. Privacy & Ephemeral Data Handling
- **Zero Persistence:** Uploaded files are streamed directly into memory. They are *never* persisted to disk on the server during the standard scan lifecycle.
- **Sensitive Data Masking:** The application Logger masks Personally Identifiable Information (PII) before logging it. Full identifiers like Aadhaar, PAN, and Passports are partially redacted (\XXXXXXXX3916\). Raw OCR blocks and full document contents are never logged.

## 4. Authentication & Authorization
- **API Key Bound:** All endpoints (except \/health\ and \/ready\) enforce authorization headers if \AUTH_REQUIRED\ is true.
- **Environment Management:** Keys and credentials are read strictly from environment variables and never hard-coded in the repository.

## 5. Security Headers & CORS
- **CORS:** Cross-Origin Resource Sharing is restrictively configured via \CORS_ORIGINS\.
- **Headers:** Middlewares inject strict security headers including \X-Content-Type-Options: nosniff\, \X-Frame-Options: DENY\, and \Content-Security-Policy\.

## 6. Threat Model Mitigation
- **Denial of Service (DoS):** Mitigated by payload caps, image dimension limits, API rate limiting, and inference timeouts.
- **Remote Code Execution (RCE):** Mitigated by safe binary structure decoding rather than relying on underlying system libraries to magically resolve file types.
- **Data Exfiltration:** Mitigated by zero disk caching, logging redaction, and strict outbound policy limits.
