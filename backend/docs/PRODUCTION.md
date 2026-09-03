# Phase 9: Production Deployment Guide

## Overview
This document outlines the architecture and deployment strategy for the Mobile Identity Document Scanner API in a production environment.

## 1. Docker Production Image
We provide a multi-stage `Dockerfile` based on `python:3.11-slim`. 
* **Minimal Base**: Keeps the image lightweight and reduces the security attack surface.
* **Non-root Execution**: (Recommended) Run the container under a non-root user for enhanced security.
* **Pre-installed System Libs**: Required libraries (`libgl1`, `libglib2.0-0`) are bundled for OpenCV and ONNX CPU processing.

## 2. Resource Limits
The API is CPU-bound due to the `rapidocr-onnxruntime` engine.
* **CPU Limits**: We strongly recommend assigning at least 2 vCPUs per container. The ONNX engine utilizes multithreading (configured via `OMP_NUM_THREADS`).
* **Memory Limits**: The model footprint requires ~500MB at baseline. Set memory limits to at least `1Gi` per container to accommodate request bursts.
* **Concurrency Configuration**: We utilize `uvicorn` and restrict concurrency to protect CPU boundaries (`max_concurrent_ocr=2` is default in settings). Adjust workers based on hardware.

## 3. Reverse Proxy & HTTPS
* **Reverse Proxy**: Place the Docker container behind a mature reverse proxy such as Nginx, Traefik, or an AWS ALB/API Gateway.
* **HTTPS**: TLS termination should occur at the reverse proxy layer. The backend assumes safe HTTP traffic within the local cluster but explicitly provides `SecurityHeadersMiddleware` (HSTS, etc.).
* **Timeouts**: Ensure your reverse proxy timeout is strictly greater than `api_timeout_seconds` (default 30s) to allow deep adaptive-thresholding OCR passes.

## 4. Secret & Environment Variable Validation
* The API uses `pydantic-settings` to strictly type-check and validate environment variables at startup.
* The API will refuse to start if critical types are incorrect.
* Pass sensitive variables (e.g., `API_TOKEN`) using Docker Secrets or Kubernetes Secrets injected as environment variables.

## 5. Security & Privacy Features
* **Non-Root Execution**: Configure Kubernetes `securityContext: runAsUser: 1000`.
* **PII-Safe Logging**: Logging explicitly omits `identifier` and any sensitive OCR texts (filtered in Phase 6 logger implementation).
* **No Persistence**: The Docker container writes zero raw image data to disk after the request lifecycle. Temporary buffers are held entirely in memory or immediately unlinked.
