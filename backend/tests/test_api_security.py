import pytest
from fastapi.testclient import TestClient
from app.main import app
import time
import os
import io
from app.core.config import settings

client = TestClient(app)

def test_api_security_missing_auth():
    settings.auth_required = True
    settings.api_token = "test_token"
    
    response = client.post("/api/v1/scan", files={"file": ("test.jpg", b"123", "image/jpeg")})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    
    settings.auth_required = False

def test_api_security_invalid_auth():
    settings.auth_required = True
    settings.api_token = "test_token"
    
    response = client.post(
        "/api/v1/scan", 
        headers={"Authorization": "Bearer bad_token"},
        files={"file": ("test.jpg", b"123", "image/jpeg")}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"
    
    settings.auth_required = False

def test_api_security_empty_upload():
    response = client.post("/api/v1/scan", files={"file": ("test.jpg", b"", "image/jpeg")})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_UPLOAD"

def test_api_security_unsupported_format():
    response = client.post("/api/v1/scan", files={"file": ("test.txt", b"hello world", "text/plain")})
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FORMAT"

def test_api_security_oversize_payload():
    old_limit = settings.max_upload_size_bytes
    settings.max_upload_size_bytes = 100
    
    huge_data = b"0" * 150
    response = client.post("/api/v1/scan", files={"file": ("test.jpg", huge_data, "image/jpeg")})
    
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "IMAGE_TOO_LARGE"
    
    settings.max_upload_size_bytes = old_limit

def test_api_security_rate_limit():
    old_limit = settings.rate_limit_requests
    settings.rate_limit_requests = 2
    settings.rate_limit_window = 10
    
    # Reset limiter memory if possible
    from app.api.dependencies.rate_limit import limiter
    limiter.requests.clear()
    
    # 1st request
    r1 = client.post("/api/v1/scan", files={"file": ("test.jpg", b"", "image/jpeg")})
    # 2nd request
    r2 = client.post("/api/v1/scan", files={"file": ("test.jpg", b"", "image/jpeg")})
    # 3rd request (should fail)
    r3 = client.post("/api/v1/scan", files={"file": ("test.jpg", b"", "image/jpeg")})
    
    assert r3.status_code == 429
    assert r3.json()["error"]["code"] == "RATE_LIMITED"
    
    settings.rate_limit_requests = old_limit
