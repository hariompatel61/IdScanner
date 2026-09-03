from fastapi import Request, Security
from fastapi.security import APIKeyHeader
from app.core.config import settings
from app.api.errors import APIError

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

def verify_api_key(request: Request, api_key_header: str = Security(api_key_header)):
    if not settings.auth_required:
        return True
        
    if not api_key_header:
        raise APIError(code="AUTHENTICATION_REQUIRED", message="Missing Authorization header", status_code=401)
        
    token = api_key_header.replace("Bearer ", "") if "Bearer " in api_key_header else api_key_header
    
    if token != settings.api_token:
        raise APIError(code="AUTHENTICATION_FAILED", message="Invalid API Key", status_code=403)
        
    return True
