import time
import uuid
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends, Header
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import logging

from app.core.config import settings
from app.ocr.engine import ocr_engine
from app.extractors.regex import AadhaarExtractor, PANExtractor, VoterIDExtractor, ABHAExtractor
from app.schemas.scan import ScanResponse, ScanMetrics

router = APIRouter()
logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE_BYTES = settings.max_image_size_mb * 1024 * 1024

# Instantiated Extractor Registry
EXTRACTOR_MAP = {
    "aadhaar": AadhaarExtractor(),
    "pan": PANExtractor(),
    "voter": VoterIDExtractor(),
    "abha": ABHAExtractor()
}

def verify_api_token(authorization: Optional[str] = Header(None)):
    """
    Validates Authorization: Bearer <API_TOKEN> if settings.api_token is configured.
    """
    if settings.api_token:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized. Missing Bearer token.")
        token = authorization.split("Bearer ")[1].strip()
        if token != settings.api_token:
            raise HTTPException(status_code=401, detail="Unauthorized. Invalid Bearer token.")

@router.post("/scan", response_model=ScanResponse, dependencies=[Depends(verify_api_token)])
async def scan_document(
    request: Request,
    file: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    document_type: Optional[str] = Form(None)
):
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    start_time = time.time()
    
    # Handle either 'file' or 'image' form field name
    upload_file = file or image
    if not upload_file:
        raise HTTPException(status_code=400, detail="Missing image upload. Supply 'image' or 'file' field.")

    if not ocr_engine.is_ready():
        raise HTTPException(status_code=503, detail="OCR Engine is not ready or warming up.")

    # 1. Validate file payload limits
    content = await upload_file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Max size is {settings.max_image_size_mb}MB.")
    
    if upload_file.content_type and upload_file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=415, detail="Unsupported media type. Use JPEG, PNG, or WEBP.")

    # 2. In-Memory Image Decoding (Zero disk I/O)
    try:
        np_arr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image buffer.")
    except Exception as e:
        logger.error(f"Image decode error [{request_id}]: {e}")
        raise HTTPException(status_code=400, detail="Invalid image payload.")

    # 3. Determine Extractor Strategy
    target_doc_type = (document_type or "").strip().lower()
    if target_doc_type and target_doc_type in EXTRACTOR_MAP:
        selected_extractors = [EXTRACTOR_MAP[target_doc_type]]
    else:
        selected_extractors = list(EXTRACTOR_MAP.values())

    # 4. OCR Processing (Pass 1)
    raw_results = ocr_engine.process_image(img, apply_adaptive_threshold=False)
    
    best_doc_result = None
    best_doc_conf = 0.0

    for ext in selected_extractors:
        res = ext.extract(raw_results)
        if res and res["confidence"] > best_doc_conf:
            best_doc_conf = res["confidence"]
            best_doc_result = res

    # 5. OCR Processing (Pass 2 - Adaptive Threshold Fallback if confidence < threshold)
    if not best_doc_result or best_doc_conf < settings.high_confidence_threshold:
        logger.info(f"[{request_id}] Pass 1 confidence low ({best_doc_conf:.2f}). Running Pass 2 (adaptive thresholding).")
        raw_results_pass2 = ocr_engine.process_image(img, apply_adaptive_threshold=True)
        
        for ext in selected_extractors:
            res = ext.extract(raw_results_pass2)
            if res and res["confidence"] > best_doc_conf:
                best_doc_conf = res["confidence"]
                best_doc_result = res

    processing_time_ms = int((time.time() - start_time) * 1000)

    metrics = ScanMetrics(
        processing_time_ms=processing_time_ms,
        request_id=request_id
    )

    # 6. Evaluation & Response Generation (Safe Logging: NO PII logged!)
    if best_doc_result and best_doc_conf >= settings.high_confidence_threshold:
        raw_doc_type = best_doc_result["document_type"].lower()
        doc_type = "voter" if raw_doc_type == "voter_id" else raw_doc_type
        identifier = best_doc_result["identifier"]

        # Build RIMS fields dictionary
        fields: Dict[str, Any] = {}
        if doc_type == "aadhaar":
            fields["aadhaar_number"] = identifier
        elif doc_type == "pan":
            fields["pan_number"] = identifier
        elif doc_type == "voter":
            fields["voter_id"] = identifier
        elif doc_type == "abha":
            if best_doc_result.get("abha_number"):
                fields["abha_number"] = best_doc_result.get("abha_number")
            if best_doc_result.get("abha_address"):
                fields["abha_address"] = best_doc_result.get("abha_address")

        logger.info(f"[{request_id}] Success | doc_type={doc_type} | confidence={best_doc_conf:.2f} | processing_time={processing_time_ms}ms")

        return ScanResponse(
            success=True,
            document_type=doc_type,
            identifier=identifier,
            fields=fields,
            confidence=round(best_doc_conf, 4),
            requires_rescan=False,
            processing_time_ms=processing_time_ms,
            request_id=request_id,
            metrics=metrics
        )
    else:
        logger.warning(f"[{request_id}] Scan Low Confidence / Unrecognized | processing_time={processing_time_ms}ms")
        return ScanResponse(
            success=False,
            document_type="unknown",
            identifier=None,
            fields={},
            confidence=round(best_doc_conf, 4),
            requires_rescan=True,
            processing_time_ms=processing_time_ms,
            request_id=request_id,
            error_code="LOW_CONFIDENCE",
            message="Unable to confidently extract the document identifier.",
            metrics=metrics
        )
