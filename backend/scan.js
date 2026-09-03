const fs = require('fs');

async function scanDocument(filePath, apiToken) {
    const url = "http://localhost:4500/api/v1/scan";
    const formData = new FormData();
    const fileBuffer = fs.readFileSync(filePath);
    const blob = new Blob([fileBuffer], { type: "image/jpeg" });
    formData.append("file", blob, "document.jpg");
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
        const data = await response.json();
        console.log(`Success: ${data.success}, DocType: ${data.document_type}`);
    } catch (err) {
        console.error("Error:", err);
    }
}
scanDocument("document.jpg", "test_token");
