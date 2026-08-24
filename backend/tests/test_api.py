import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.ocr.engine import ocr_engine

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_ready_check():
    # Mock OCR engine loaded state
    ocr_engine._initialized = True
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "ocr_engine": "rapidocr"}

def test_not_ready_check(monkeypatch):
    # Mock OCR engine not ready state
    monkeypatch.setattr(ocr_engine, "is_ready", lambda: False)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_scan_invalid_file_type():
    files = {'file': ('test.txt', b'fake data', 'text/plain')}
    response = client.post("/api/v1/scan", files=files)
    assert response.status_code == 415
    assert response.json()["detail"] == "Unsupported media type. Use JPEG, PNG, or WEBP."

