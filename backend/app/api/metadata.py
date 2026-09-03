from fastapi import APIRouter
from app.parsers.registry import document_registry
from app.core.config import settings

router = APIRouter()

@router.get("/metadata")
async def get_metadata():
    """
    Exposes API capabilities, versions, and limits.
    """
    return {
        "api_version": "1.0.0",
        "supported_documents": list(document_registry.list_supported().keys()),
        "limits": {
            "max_upload_size_bytes": settings.max_upload_size_bytes,
            "max_image_dimension": settings.max_image_dimension,
            "rate_limit_requests": settings.rate_limit_requests,
            "rate_limit_window_seconds": settings.rate_limit_window
        }
    }
