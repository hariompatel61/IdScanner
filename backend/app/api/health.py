from fastapi import APIRouter, Response, status
from app.ocr.engine import ocr_engine

router = APIRouter()

@router.get("/health")
def health_check():
    """Verify that the API process is alive."""
    return {"status": "ok"}

@router.get("/ready")
def ready_check(response: Response):
    """Verify that the API is fully configured and the OCR model is loaded."""
    if ocr_engine.is_ready():
        return {"status": "ready"}
    
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "not_ready"}
