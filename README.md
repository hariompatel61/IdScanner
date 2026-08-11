# Mobile Identity Document Scanner

A production-ready, enterprise-grade Mobile Identity Document Scanner designed for integration into a live PHP/Laravel hospital/RIMS application.

## Overview
This scanner runs primarily on mobile browsers, opening the rear camera, detecting identity documents, auto-capturing the best frame, and securely extracting the ID numbers using server-side PaddleOCR. 

It never silently returns an incorrect ID. If confidence is low, it requires a rescan.

## Architecture
See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system components.
See [SECURITY.md](SECURITY.md) for privacy-by-design guidelines.

## Quick Start (Phase 1 & 2)
```bash
cp .env.example .env
docker compose up --build -d
```
- API Health: `http://localhost:8000/health`
- Frontend: `http://localhost:80` (or configured HTTPS port for mobile testing)

> [!WARNING]
> **Mobile Camera Testing**: Modern browsers require a secure context (HTTPS) or `localhost` to access `getUserMedia`. If testing on a physical mobile device over your local network (e.g., `192.168.x.x`), you must configure HTTPS (e.g., using a local cert like `mkcert`, or an HTTPS tunnel like ngrok), otherwise the camera permission prompt will not appear.
