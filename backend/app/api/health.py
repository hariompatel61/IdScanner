from fastapi import APIRouter, Response, status
from app.ocr.engine import ocr_engine

router = APIRouter()

@router.get("/health")
def health_check():
    """Lightweight liveness check - returns instantly without running OCR."""
    return {"status": "healthy"}

@router.get("/ready")
def ready_check(response: Response):
    """Readiness check - returns 200 OK only when RapidOCR model is initialized and warmed up."""
    if ocr_engine.is_ready():
        return {
            "status": "ready",
            "ocr_engine": "rapidocr"
        }
    
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "not_ready",
        "ocr_engine": "rapidocr",
        "message": "RapidOCR engine initializing or unavailable"
    }
