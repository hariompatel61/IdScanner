# ID Scanner SDK

The ID Scanner SDK provides a typed, promise-based client for interacting with the Mobile Identity Document Scanner API. It handles multipart uploads, timeouts, error parsing, and rate-limiting gracefully.

## Installation

\\\ash
npm install @idscanner/sdk
\\\

## Initialization

\\\	ypescript
import { IdScanner } from '@id-scanner/sdk';

const scanner = new IdScanner({
    apiHost: 'https://api.yourdomain.com',
    apiToken: process.env.API_TOKEN,
    timeoutMs: 30000 // 30 seconds
});
\\\

## Scanning a Document

Pass a standard Web API \File\ or \Blob\ object.

\\\	ypescript
try {
    const result = await scanner.scanDocument(fileBlob, {
        documentType: 'pan_card', // optional hint
        requestId: 'req_12345'    // optional correlation ID
    });

    if (result.success) {
        console.log("Document detected:", result.document_type);
        console.log("Extracted Fields:", result.fields);
    }
} catch (error) {
    if (error instanceof ScanError) {
        console.error(\Scan failed (\): \\);
    }
}
\\\

## Error Handling

The SDK throws a \ScanError\ with structured codes mapping to the API:

- \RATE_LIMITED\: Exceeded concurrency or rate limits.
- \AUTHENTICATION_REQUIRED\: Missing token.
- \AUTHENTICATION_FAILED\: Invalid token.
- \IMAGE_TOO_LARGE\: Exceeded upload size.
- \UNSUPPORTED_FORMAT\: Image must be JPEG, PNG, or WEBP.
- \REQUEST_TIMEOUT\: The request took longer than \	imeoutMs\.
- \INTERNAL_ERROR\: Network failure or unhandled exception.

## Types

The SDK exports full typings for the response (\IdScannerResult\) and fields. 
Refer to the TypeScript definitions for exhaustive interfaces mapping to the API confidence and validation scores.
