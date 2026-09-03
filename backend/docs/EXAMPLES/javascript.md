# Browser JavaScript Example

This example demonstrates calling the API from a browser frontend. Note that because of CORS, your backend must have the origin properly configured in `CORS_ORIGINS`.

## Scan Document

```javascript
async function scanDocument(fileInputId, apiToken) {
    const fileInput = document.getElementById(fileInputId);
    if (!fileInput.files.length) {
        console.error("Please select a file.");
        return;
    }
    
    const file = fileInput.files[0];
    const url = "http://localhost:4500/api/v1/scan";
    
    const formData = new FormData();
    formData.append("file", file);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${apiToken}`,
                "X-Request-ID": "req_browser_1"
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
            console.error(`Scan Failed: ${data.error?.message || data.message}`);
        }
        
    } catch (err) {
        if (err.name === "AbortError") {
            console.error("Error: Request timed out.");
        } else {
            console.error("Unexpected error:", err);
        }
    }
}
```
