import time
import uuid
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
import logging

from app.ocr.engine import ocr_engine
from app.extractors.regex import AadhaarExtractor, PANExtractor, VoterIDExtractor, ABHAExtractor
from app.schemas.scan import ScanResponse, ScanMetrics

router = APIRouter()
logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

extractors = [
    AadhaarExtractor(),
    PANExtractor(),
    VoterIDExtractor(),
    ABHAExtractor()
]

@router.post("/scan", response_model=ScanResponse)
async def scan_document(request: Request, file: UploadFile = File(...)):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    if not ocr_engine.is_ready():
        raise HTTPException(status_code=503, detail="OCR Engine is not ready.")

    # 1. Validate file payload limits
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Max size is {MAX_FILE_SIZE_MB}MB.")
    
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=415, detail="Unsupported media type. Use JPEG, PNG, or WEBP.")

    # 2. In-Memory Image Decoding (Zero disk I/O)
    try:
        np_arr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image.")
    except Exception as e:
        logger.error(f"Image decode error [{request_id}]: {e}")
        raise HTTPException(status_code=400, detail="Invalid image payload.")

    # 3. OCR Processing (First Pass)
    raw_results = ocr_engine.process_image(img, apply_adaptive_threshold=False)
    
    best_doc_result = None
    best_doc_conf = 0.0

    # Execute all extractors to find the best match
    for ext in extractors:
        res = ext.extract(raw_results)
        if res and res["confidence"] > best_doc_conf:
            best_doc_conf = res["confidence"]
            best_doc_result = res

    # 4. OCR Processing (Second Pass / Fallback)
    # If confidence is low or nothing was found, try with adaptive thresholding
    if not best_doc_result or best_doc_conf < 0.85:
        logger.info(f"[{request_id}] Low confidence ({best_doc_conf}). Attempting second pass.")
        raw_results_pass2 = ocr_engine.process_image(img, apply_adaptive_threshold=True)
        
        for ext in extractors:
            res = ext.extract(raw_results_pass2)
            if res and res["confidence"] > best_doc_conf:
                best_doc_conf = res["confidence"]
                best_doc_result = res

    processing_time_ms = int((time.time() - start_time) * 1000)

    metrics = ScanMetrics(
        processing_time_ms=processing_time_ms,
        request_id=request_id
    )

    # 5. Final Evaluation
    # We NEVER return silently uncertain identifiers as per strict requirements.
    if best_doc_result and best_doc_conf >= 0.85:
        logger.info(f"[{request_id}] Success: {best_doc_result['document_type']} identified.")
        
        return ScanResponse(
            document_type=best_doc_result["document_type"],
            identifier=best_doc_result["identifier"],
            confidence=best_doc_result["confidence"],
            requires_rescan=False,
            abha_number=best_doc_result.get("abha_number"),
            abha_address=best_doc_result.get("abha_address"),
            metrics=metrics
        )
    else:
        logger.warning(f"[{request_id}] Failed to extract high-confidence identifier. Requires rescan.")
        return ScanResponse(
            document_type=None,
            identifier=None,
            confidence=best_doc_conf,
            requires_rescan=True,
            metrics=metrics
        )
