from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()

# Metrics
REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint"]
)

OCR_LATENCY = Histogram(
    "ocr_processing_latency_seconds",
    "OCR latency in seconds"
)

PREPROCESSING_LATENCY = Histogram(
    "preprocessing_latency_seconds",
    "Preprocessing latency in seconds"
)

PARSER_LATENCY = Histogram(
    "parser_latency_seconds",
    "Parser latency in seconds",
    ["document_type"]
)

ERROR_RATE = Counter(
    "api_errors_total",
    "Total API errors",
    ["error_code"]
)

DOCUMENT_TYPE_DISTRIBUTION = Counter(
    "document_type_total",
    "Total documents processed by type",
    ["document_type", "status"] # e.g. status="ok", "low_confidence", "invalid"
)

@router.get("/metrics", include_in_schema=False)
def get_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
