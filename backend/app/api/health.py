from fastapi import APIRouter, Response, status
from app.ocr.engine import ocr_engine

router = APIRouter()

@router.get("/health")
def health_check():
    """Lightweight liveness check - returns instantly without running OCR."""
    return {"status": "healthy"}


