from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, status
import uvicorn
import logging
import cv2
import numpy as np

from app.engine import ocr_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load and warm up the OCR model on startup
    logger.info("Loading OCR worker model...")
    try:
        ocr_engine.load_model()
        logger.info("OCR worker model loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load OCR worker model: {e}")
        # We don't exit forcefully here, but /ready will fail.
        # Actually if paddle SIGILLs, it will OS-kill the container immediately.
    yield
    logger.info("Shutting down OCR worker...")

app = FastAPI(
    title="OCR Worker API",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
def health_check():
    """Basic health check that the worker process is alive."""
    return {"status": "ok"}

@app.get("/ready")
def ready_check(response: Response):
    """Check if the OCR model is loaded and ready for inference."""
    if ocr_engine.is_ready():
        return {"status": "ready"}
    
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "not_ready"}

@app.post("/scan")
def scan_image(
    file: UploadFile = File(...),
    adaptive_threshold: bool = Form(False)
):
    if not ocr_engine.is_ready():
        raise HTTPException(
            status_code=503, 
            detail="OCR Engine is not ready"
        )
        
    try:
        contents = file.file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            
        nparr = np.frombuffer(contents, np.uint8)
        img_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img_array is None or img_array.size == 0:
            raise HTTPException(status_code=400, detail="Invalid image file or unsupported format.")

        # Process the image with OCR Engine
        results = ocr_engine.process_image(img_array, apply_adaptive_threshold=adaptive_threshold)
        
        # Apply Demographics Regex Extraction locally in the worker
        from app.extractors import extract_demographics
        demographics = extract_demographics(results)
        
        return {
            "demographics": demographics,
            "raw_results": results
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing image in worker: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001)
