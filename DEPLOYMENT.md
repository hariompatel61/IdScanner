# Deployment Guide

## Production Environment Setup
1. Clone the repository.
2. Copy `.env.example` to `.env` and fill in production secrets/configs.
3. Start the stack: `docker compose -f docker-compose.yml up --build -d`
4. Configure Nginx reverse proxy to handle HTTPS and route to port 80 (frontend) and 8000 (backend API).

## Local Mobile Development (HTTPS Requirement)
To test the camera on a physical mobile device via your local network (e.g., `192.168.1.100`), the frontend must be served over HTTPS. Browsers block `getUserMedia` on insecure origins.
Options:
1. **mkcert**: Generate a local trusted certificate and mount it into the Nginx container.
2. **Reverse Proxy tunnel**: Use ngrok, Cloudflare Tunnels, or similar tools to securely expose `localhost:80` to an HTTPS endpoint.

## Docker
- `scanner-web`: Multi-stage Dockerfile that builds Vite React app and serves it via Nginx.
- `scanner-api`: Python FastAPI container with PaddleOCR and OpenCV-headless. Pinned dependencies for reproducibility.

*Note: Phase 1 implements the Dockerfiles and basic container setup.*
