from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.schemas.scan import ScanResponse, ErrorDetail
import logging
from app.api import metrics

logger = logging.getLogger(__name__)

class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

async def api_error_handler(request: Request, exc: APIError):
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"[{request_id}] APIError: {exc.code} - {exc.message}")
    metrics.ERROR_RATE.labels(error_code=exc.code).inc()
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ScanResponse(
            success=False,
            request_id=request_id,
            document_type="unknown",
            error=ErrorDetail(code=exc.code, message=exc.message, details=exc.details),
            error_code=exc.code,  # legacy
            message=exc.message   # legacy
        ).model_dump(exclude_none=True)
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"[{request_id}] Validation Error: {exc.errors()}")
    metrics.ERROR_RATE.labels(error_code="VALIDATION_FAILED").inc()
    
    return JSONResponse(
        status_code=422,
        content=ScanResponse(
            success=False,
            request_id=request_id,
            document_type="unknown",
            error=ErrorDetail(code="VALIDATION_FAILED", message="Request validation failed", details={"errors": exc.errors()}),
            error_code="VALIDATION_FAILED", # legacy
            message="Request validation failed" # legacy
        ).model_dump(exclude_none=True)
    )

async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.error(f"[{request_id}] Unhandled Exception: {str(exc)}", exc_info=True)
    metrics.ERROR_RATE.labels(error_code="INTERNAL_ERROR").inc()
    
    return JSONResponse(
        status_code=500,
        content=ScanResponse(
            success=False,
            request_id=request_id,
            document_type="unknown",
            error=ErrorDetail(code="INTERNAL_ERROR", message="An unexpected error occurred"),
            error_code="INTERNAL_ERROR", # legacy
            message="An unexpected error occurred" # legacy
        ).model_dump(exclude_none=True)
    )
