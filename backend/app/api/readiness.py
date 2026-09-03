from fastapi import APIRouter, Response
from app.ocr.engine import ocr_engine

router = APIRouter()

@router.get("/ready")
async def readiness_probe():
    """
    Checks if application is ready to process requests (e.g., OCR model loaded).
    """
    if ocr_engine.is_ready():
        return {"status": "ready", "ocr_engine": "rapidocr"}
    
    return Response(content='{"status": "not_ready", "ocr_engine": "rapidocr"}', status_code=503, media_type="application/json")
