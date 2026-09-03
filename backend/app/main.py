from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from app.core.config import settings
from app.ocr.engine import ocr_engine
from app.api.middlewares.request_id import RequestIDMiddleware
from app.api.middlewares.security import SecurityHeadersMiddleware
from app.api.errors import api_error_handler, validation_exception_handler, global_exception_handler, APIError
from fastapi.exceptions import RequestValidationError
from app.api.readiness import router as readiness_router
from app.api.metadata import router as metadata_router
from app.api.health import router as health_router
from app.api.v1.scan import router as scan_router
from prometheus_client import make_asgi_app
import app.api.metrics as metrics

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

app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)

import time
@app.middleware("http")
async def add_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    metrics.REQUEST_LATENCY.labels(endpoint=request.url.path).observe(duration)
    return response

# Include routers
app.include_router(health_router, tags=["Health"])
app.include_router(readiness_router, tags=["Health"])
app.include_router(metadata_router, tags=["Metadata"])
app.include_router(scan_router, prefix="/api/v1", tags=["Scan"])

# Prometheus Metrics Endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=4500, reload=False)
