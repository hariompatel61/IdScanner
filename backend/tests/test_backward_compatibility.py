import pytest
from fastapi.testclient import TestClient
from app.main import app
import numpy as np
import cv2

client = TestClient(app)

def test_backward_compatibility_success_response():
    # We will upload a tiny dummy image that parses to 'unknown' due to LOW_CONFIDENCE,
    # but we can verify the shape of the response matches the old API contract (identifier, message, error_code).
    
    # Create a small valid image in memory
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    success, encoded = cv2.imencode('.jpg', img)
    assert success
    
    response = client.post("/api/v1/scan", files={"file": ("test.jpg", encoded.tobytes(), "image/jpeg")})
    assert response.status_code == 200
    
    data = response.json()
    assert "success" in data
    assert "document_type" in data
    assert "error_code" in data
    assert "message" in data
    assert "request_id" in data
    assert "status" in data
