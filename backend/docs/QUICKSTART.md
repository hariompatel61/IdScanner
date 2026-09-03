# ID Scanner Quickstart

Follow these steps to deploy and integrate the ID Scanner API.

## 1. Start the API

The backend requires Python 3.10+ and OpenCV.

\\\ash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the server (runs on port 4500 by default)
uvicorn app.main:app --host 0.0.0.0 --port 4500
\\\

## 2. Test Readiness

The RapidOCR engine takes a few seconds to warm up into memory on boot.

\\\ash
curl http://localhost:4500/ready
# Wait until it returns: {"status":"ready","ocr_engine":"rapidocr"}
\\\

## 3. Run Your First Scan

By default, the API token is configured via environment variables. If testing locally, you can pass \	est_token\ or configure \API_TOKEN\.

\\\ash
curl -X POST "http://localhost:4500/api/v1/scan" \
  -H "Authorization: Bearer test_token" \
  -F "file=@sample_aadhaar.jpg;type=image/jpeg"
\\\

## 4. Launch the Demo UI

The repository includes a modern React Vite frontend for testing.

\\\ash
cd frontend
npm install
npm run dev
\\\

Navigate to \http://localhost:5173\ to use the Camera scanner or test file uploads with the API Developer View.

## Next Steps
- See [API_V2.md](./API_V2.md) for full endpoint schemas.
- See [SECURITY_MODEL.md](./SECURITY_MODEL.md) for privacy and operational guardrails.
- See [SDK.md](./SDK.md) for TypeScript integration.
