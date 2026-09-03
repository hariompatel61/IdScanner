# Python Example

The following example uses the `httpx` library to handle asynchronous requests, file uploads, and timeouts.

## Dependencies

```bash
pip install httpx pydantic
```

## Scan Document

```python
import httpx
import asyncio
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

# Define typed models
class ScanResponse(BaseModel):
    success: bool
    request_id: str
    document_type: str
    status: Optional[str] = None
    fields: Dict[str, Any] = {}
    validation: Dict[str, Any] = {}
    confidence: Dict[str, Any] = {}
    processing_time_ms: int
    identifier: Optional[str] = None
    error: Optional[Dict[str, Any]] = None

async def scan_document(file_path: str, api_token: str):
    url = "http://localhost:4500/api/v1/scan"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "X-Request-ID": "req_py_client_1"
    }
    
    timeout = httpx.Timeout(15.0) # Configure request timeout
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path, f, "image/jpeg")}
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, headers=headers, files=files)
                
                # Handle Rate Limiting
                if response.status_code == 429:
                    print("Error: Rate Limit Exceeded")
                    return None
                    
                data = response.json()
                scan_res = ScanResponse(**data)
                
                if scan_res.success:
                    print(f"Success! Document: {scan_res.document_type}")
                    print(f"Status: {scan_res.status}")
                    print(f"Extracted Fields: {scan_res.fields}")
                else:
                    err = scan_res.error
                    print(f"Scan Failed. Code: {err['code'] if err else 'UNKNOWN'}")
                    
                return scan_res
                
    except httpx.TimeoutException:
        print("Error: Request timed out.")
    except Exception as e:
        print(f"Unexpected error: {e}")

# Run
if __name__ == "__main__":
    asyncio.run(scan_document("document.jpg", "test_token"))
```
