import time
import logging
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, File, UploadFile, Query, HTTPException, Depends, Request
import cv2
import numpy as np

from app.core.config import settings
from app.core.security import verify_api_token
from app.core.scan_logger import scan_logger
from app.ocr.engine import ocr_engine
from app.extractors.regex import (
    AadhaarExtractor,
    PANExtractor,
    VoterIDExtractor,
    ABHAExtractor,
    FarmerIDExtractor,
    PassportExtractor,
)
from app.extractors.line_reconstructor import reconstruct_lines
from app.parsers.aadhaar import AadhaarParser
from app.parsers.pan import PANParser
from app.parsers.voter_id import VoterIDParser
from app.parsers.abha import ABHAParser
from app.parsers.farmer_id import FarmerIDParser
from app.parsers.passport import PassportParser
from app.schemas.scan import ScanResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Max payload bytes calculation: 5MB
MAX_FILE_SIZE_BYTES = settings.max_image_size_mb * 1024 * 1024

# Instantiate Singleton Extractors
_aadhaar_ext = AadhaarExtractor()
_pan_ext = PANExtractor()
_voter_ext = VoterIDExtractor()
_abha_ext = ABHAExtractor()
_farmer_ext = FarmerIDExtractor()
_passport_ext = PassportExtractor()

EXTRACTOR_MAP = {
    "aadhaar_card": _aadhaar_ext,
    "aadhaar": _aadhaar_ext,
    "pan_card": _pan_ext,
    "pan": _pan_ext,
    "voter_id": _voter_ext,
    "voter": _voter_ext,
    "abha_number": _abha_ext,
    "abha": _abha_ext,
    "farmer_id": _farmer_ext,
    "farmer": _farmer_ext,
    "agriculture_card": _farmer_ext,
    "agri": _farmer_ext,
    "kisan_card": _farmer_ext,
    "kisan": _farmer_ext,
    "passport": _passport_ext,
    "passports": _passport_ext,
    "indian_passport": _passport_ext,
}

# Instantiate Singleton Document Parsers
PARSER_MAP = {
    "aadhaar_card": AadhaarParser(),
    "aadhaar": AadhaarParser(),
    "pan_card": PANParser(),
    "pan": PANParser(),
    "voter_id": VoterIDParser(),
    "voter": VoterIDParser(),
    "abha_number": ABHAParser(),
    "abha": ABHAParser(),
    "farmer_id": FarmerIDParser(),
    "farmer": FarmerIDParser(),
    "agriculture_card": FarmerIDParser(),
    "agri": FarmerIDParser(),
    "kisan_card": FarmerIDParser(),
    "kisan": FarmerIDParser(),
    "passport": PassportParser(),
    "passports": PassportParser(),
    "indian_passport": PassportParser(),
}

# Document type canonical map
DOC_TYPE_NORMAL_MAP = {
    "aadhaar": "aadhaar_card",
    "pan": "pan_card",
    "voter": "voter_id",
    "epic": "voter_id",
    "abha": "abha_number",
    "farmer": "farmer_id",
    "agri": "farmer_id",
    "agriculture": "farmer_id",
    "agriculture_card": "farmer_id",
    "kisan": "farmer_id",
    "kisan_card": "farmer_id",
    "passports": "passport",
    "indian_passport": "passport",
}


@router.get("/logs", summary="Get recent scan history logs")
async def get_scan_logs(
    limit: int = Query(default=50, ge=1, le=200, description="Max logs to return"),
    auth: bool = Depends(verify_api_token),
):
    """
    Returns the most recent scan logs (timestamp, document_type, identifier, fields, latency, confidence).
    """
    logs = scan_logger.get_recent_logs(limit=limit)
    return {
        "success": True,
        "total": len(logs),
        "logs": logs,
    }


@router.delete("/logs", summary="Clear scan history logs")
async def clear_scan_logs(auth: bool = Depends(verify_api_token)):
    """
    Clears in-memory and persistent scan history logs.
    """
    scan_logger.clear_logs()
    return {"success": True, "message": "Scan history cleared."}


@router.post("/scan", response_model=ScanResponse, response_model_exclude_none=True, summary="Perform Document OCR and Field Extraction")
async def scan_document(
    request: Request,
    file: UploadFile = File(..., description="Document image file (JPEG, PNG, WEBP)"),
    document_type: Optional[str] = Query(None, description="Optional target document filter: aadhaar_card, pan_card, voter_id, abha_number"),
    auth: bool = Depends(verify_api_token)
):
    start_time = time.time()
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    client_ip = request.client.host if request.client else "127.0.0.1"

    # 1. Validate file payload limits
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Max size is {settings.max_image_size_mb}MB.")
    
    if file.content_type and file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=415, detail="Unsupported media type. Use JPEG, PNG, or WEBP.")

    # 2. In-Memory Image Decoding (Zero disk I/O)
    try:
        if not content:
            raise ValueError("Uploaded file is empty.")
        np_arr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            raise ValueError("Failed to decode image buffer. Unsupported format.")
    except Exception as e:
        logger.error(f"Image decode error [{request_id}]: {e}")
        raise HTTPException(status_code=400, detail="Invalid image payload.")

    # 3. Determine Extractor Strategy
    target_doc_type = (document_type or "").strip().lower()
    if target_doc_type and target_doc_type in EXTRACTOR_MAP:
        selected_extractors = [EXTRACTOR_MAP[target_doc_type]]
    else:
        selected_extractors = [_aadhaar_ext, _pan_ext, _voter_ext, _abha_ext, _farmer_ext, _passport_ext]

    # 4. OCR Processing (Pass 1 - Fast Primary Pass)
    raw_results = ocr_engine.process_image(img, apply_adaptive_threshold=False)
    
    best_doc_result = None
    best_doc_conf = 0.0
    best_raw_results = raw_results

    for ext in selected_extractors:
        res = ext.extract(raw_results)
        if res and res["confidence"] > best_doc_conf:
            best_doc_conf = res["confidence"]
            best_doc_result = res
            best_raw_results = raw_results

    # 5. OCR Processing (Pass 2 - Adaptive Threshold Fallback ONLY if no document found or confidence < retry_threshold)
    if not best_doc_result or best_doc_conf < settings.retry_threshold:
        logger.info(f"[{request_id}] Pass 1 confidence low ({best_doc_conf:.2f}). Running Pass 2 (adaptive thresholding).")
        raw_results_pass2 = ocr_engine.process_image(img, apply_adaptive_threshold=True)
        
        for ext in selected_extractors:
            res = ext.extract(raw_results_pass2)
            if res and res["confidence"] > best_doc_conf:
                best_doc_conf = res["confidence"]
                best_doc_result = res
                best_raw_results = raw_results_pass2

    processing_time_ms = int((time.time() - start_time) * 1000)

    # 6. Evaluation & Response Generation
    if best_doc_result and best_doc_conf >= settings.high_confidence_threshold:
        raw_doc_type = best_doc_result["document_type"].lower()
        doc_type = DOC_TYPE_NORMAL_MAP.get(raw_doc_type, raw_doc_type)
        identifier = best_doc_result["identifier"]

        # Build fields dictionary
        fields: Dict[str, Any] = {}
        if doc_type == "aadhaar_card":
            fields["aadhaar_number"] = identifier
        elif doc_type == "pan_card":
            fields["pan_number"] = identifier
        elif doc_type == "voter_id":
            fields["voter_id"] = identifier
        elif doc_type == "farmer_id":
            fields["farmer_id"] = identifier
        elif doc_type == "passport":
            fields["passport_number"] = identifier
        elif doc_type == "abha_number":
            if best_doc_result.get("abha_number"):
                fields["abha_number"] = best_doc_result.get("abha_number")
            if best_doc_result.get("abha_address"):
                fields["abha_address"] = best_doc_result.get("abha_address")

        # Run structured field parser on the SAME OCR output
        overall_status = "ok"
        parser = PARSER_MAP.get(doc_type)
        if parser:
            try:
                sorted_lines = reconstruct_lines(best_raw_results)
                parsed = parser.extract_fields(sorted_lines)
                for k, v in parsed.fields.items():
                    if v.status == "ok" and v.value and k not in fields:
                        fields[k] = v.value

                overall_status = parsed.overall_status
            except Exception as e:
                logger.warning(f"[{request_id}] Field parser error for {doc_type}: {e}")
                overall_status = "ok"

        logger.info(f"[{request_id}] Success | doc_type={doc_type} | confidence={best_doc_conf:.2f} | overall_status={overall_status} | processing_time={processing_time_ms}ms")

        # Persist Scan Log
        scan_logger.log_scan(
            request_id=request_id,
            document_type=doc_type,
            identifier=identifier,
            fields=fields,
            confidence=best_doc_conf,
            processing_time_ms=processing_time_ms,
            overall_status=overall_status,
            client_ip=client_ip,
        )

        return ScanResponse(
            success=True,
            document_type=doc_type,
            identifier=identifier,
            fields=fields,
        )

    else:
        logger.warning(f"[{request_id}] Scan Low Confidence / Unrecognized | processing_time={processing_time_ms}ms")
        
        # Persist Failed Scan Log
        scan_logger.log_scan(
            request_id=request_id,
            document_type="unknown",
            identifier=None,
            fields={},
            confidence=best_doc_conf,
            processing_time_ms=processing_time_ms,
            overall_status="rescan_required",
            client_ip=client_ip,
            error_code="LOW_CONFIDENCE",
            message="Unable to confidently extract the document identifier.",
        )

        return ScanResponse(
            success=False,
            document_type="unknown",
            identifier=None,
            fields={},
            error_code="LOW_CONFIDENCE",
            message="Unable to confidently extract the document identifier.",
        )
