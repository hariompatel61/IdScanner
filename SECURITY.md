# Security & Privacy By Design

## Core Principles
1. **No Data Storage**: The application must not store raw document images or extracted identity text.
2. **Logging Restrictions**: Logs must NEVER contain sensitive identifier numbers (Aadhaar, PAN, Voter, ABHA). Mask them immediately (e.g. `XXXXXXXX9012`).
3. **Data Minimization**: Only the targeted ID number is extracted and returned. Names, DOBs, etc. are ignored unless strictly required for classification, and are dropped immediately.

## Web Security
- **CORS**: Configurable via `.env`. No wildcard `*` in production.
- **Payload Limits**: Max image size strictly enforced to prevent DoS.
- **Auth**: API expects authenticated requests in production integrations (e.g., Server-to-Server API Keys, or short-lived signed JWTs).

*Note: Phase 1 establishes the environment configuration and payload limit scaffolds.*
