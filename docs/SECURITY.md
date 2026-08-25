# Security & Privacy Specification

## 1. Core Principles: Privacy by Design

IDScanner is built with strict privacy and security principles:

1. **Zero-Disk Data Storage**:
   - The API is completely stateless.
   - Raw document images and extracted text buffers are processed in volatile memory only and discarded immediately after HTTP response delivery.
2. **PII Masking & Sanitization**:
   - Application logs never contain raw sensitive identifiers or plaintext identity images.
3. **Strict Input Sanitization**:
   - Image payload validation prevents decompression bombs and malicious buffers (`max_image_dimension = 1920`, max upload size = 10MB).
4. **CORS & Access Control**:
   - Configurable CORS origins via `.env`. No wildcard `*` allowed in production configurations.
5. **Secure Transport**:
   - Strict HTTPS enforcement via TLS 1.3 / SSL reverse proxy.
