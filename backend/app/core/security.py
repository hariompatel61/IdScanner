from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.core.config import settings

security = HTTPBearer(auto_error=False)

def verify_api_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> bool:
    if not settings.api_token:
        return True
    if not credentials or credentials.credentials != settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Bearer API token."
        )
    return True
