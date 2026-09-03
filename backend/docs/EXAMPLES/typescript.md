# TypeScript / SDK Example

The easiest way to use the API in TypeScript or JavaScript environments is via the official SDK.

## Scan Document Using SDK

```typescript
import { IdScanner, ScanError } from '@id-scanner/sdk';

async function performScan(file: File) {
    const scanner = new IdScanner({
        apiHost: 'http://localhost:4500',
        apiToken: 'test_token',
        timeoutMs: 15000
    });

    try {
        const result = await scanner.scanDocument(file, {
            requestId: 'req_ts_1',
            documentType: 'pan_card' // Optional hint
        });

        if (result.success) {
            console.log(`Success! Document: ${result.document_type}`);
            console.log(`Status: ${result.status}`);
            console.log(`Extracted Name: ${result.fields.name}`);
        } else {
            console.log(`Failed! Status: ${result.status}, Message: ${result.error?.message}`);
        }

    } catch (err) {
        if (err instanceof ScanError) {
            console.error(`API Error: ${err.code} - ${err.message}`);
        } else {
            console.error("Unexpected error:", err);
        }
    }
}
```
