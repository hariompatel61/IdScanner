# Node.js Example

This example uses standard `fetch` (available natively in Node 18+) and `FormData`.

## Scan Document

```javascript
// scan.js
const fs = require('fs');

async function scanDocument(filePath, apiToken) {
    const url = "http://localhost:4500/api/v1/scan";
    
    // Create form data
    const formData = new FormData();
    const fileBuffer = fs.readFileSync(filePath);
    const blob = new Blob([fileBuffer], { type: "image/jpeg" });
    formData.append("file", blob, "document.jpg");

    // Configure timeout using AbortController
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${apiToken}`,
                "X-Request-ID": "req_node_1"
            },
            body: formData,
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);

        if (response.status === 429) {
            console.error("Error: Rate Limit Exceeded");
            return;
        }

        const data = await response.json();
        
        if (data.success) {
            console.log(`Success! Document: ${data.document_type}`);
            console.log(`Status: ${data.status}`);
            console.log("Fields:", data.fields);
        } else {
            console.error(`Scan Failed: ${data.error?.message}`);
        }
        
    } catch (err) {
        if (err.name === "AbortError") {
            console.error("Error: Request timed out.");
        } else {
            console.error("Unexpected error:", err);
        }
    }
}

// Run
scanDocument("document.jpg", "test_token");
```
