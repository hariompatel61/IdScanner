import os
import cv2
import numpy as np
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def create_dummy_image_bytes():
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    img.fill(255)
    cv2.putText(img, "PAN", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    _, buffer = cv2.imencode('.jpg', img)
    return buffer.tobytes()

def test_scan_document_regression():
    # REGRESSION TEST: Ensure document_registry is imported and doesn't throw NameError
    img_bytes = create_dummy_image_bytes()
    headers = {"Authorization": "Bearer test_token"}
    response = client.post(
        "/api/v1/scan", 
        headers=headers,
        files={"file": ("test.jpg", img_bytes, "image/jpeg")}
    )
    # The scan should process successfully (even if it's INVALID or REVIEW due to low confidence)
    # But it MUST NOT return a 500 Internal Server Error (which happens if document_registry is undefined)
    assert response.status_code == 200
    assert "document_type" in response.json()
