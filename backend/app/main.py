from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from app.core.config import settings
from app.ocr.engine import ocr_engine
from app.api.health import router as health_router
from app.api.v1.scan import router as scan_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Mobile Identity Document Scanner API...")
    # Initialize and warm up RapidOCR model ONCE at startup
    ready = ocr_engine.initialize()
    if ready:
        logger.info("RapidOCR model loaded & warmed up successfully. Ready for scans!")
    else:
        logger.warning("RapidOCR model failed to initialize on startup.")
    yield
    logger.info("Shutting down API Gateway...")

app = FastAPI(
    title="Mobile Identity Document Scanner API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, tags=["Health"])
app.include_router(scan_router, prefix="/api/v1", tags=["Scan"])

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=4500, reload=False)
