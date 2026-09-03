# Production Integrations

This guide covers integrating the Phase 6 ID Scanner into a production ecosystem.

## Environment Configuration

Set the following environment variables on the backend container:

- \AUTH_REQUIRED\: \	rue\
- \API_TOKEN\: A strong, randomly generated token (e.g., UUIDv4 or SHA256).
- \CORS_ORIGINS\: Comma-separated list of allowed frontend origins (e.g. \https://app.yourdomain.com\).
- \MAX_CONCURRENT_OCR\: Set to the number of physical CPU cores on the host. Do NOT set this higher than core count, as it will cause CPU thrashing.
- \RATE_LIMIT_REQUESTS\: Suggested 5-10 per minute per IP for public endpoints.

## Handling the Response

The extraction returns a Phase 5 normalized JSON block. Production systems should route logic based on the \decision\ status inside \confidence\:

1. **ACCEPT**: Document is high quality and completely parsed. Proceed with automated onboarding.
2. **REVIEW**: Document is parsed but contains consistency issues (e.g., date mismatch) or blurry fields. Flag for human review in your backoffice.
3. **RECAPTURE**: Document is missing mandatory fields. Instruct user to rescan (status code remains 200, but \success\ is false).
4. **INVALID**: Spoofing or completely unrecognized format.

## Privacy Expectations

Do NOT store the raw images returned by the frontend unless absolutely required for legal compliance. The backend streams images directly to the OCR engine and discards them instantly.

Do NOT log the \ields\ object. The backend \ScanLogger\ masks Aadhaar, PAN, and Passport numbers automatically.

## Webhooks / Callbacks

If your application requires asynchronous processing (not natively supported by this real-time API), you should queue the images locally in your own microservice and call this API synchronously from your worker nodes.
