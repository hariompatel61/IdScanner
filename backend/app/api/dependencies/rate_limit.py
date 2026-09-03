from fastapi import Request
from app.core.config import settings
from app.api.errors import APIError
import time
from collections import defaultdict
import threading

# Simple in-memory rate limiter using sliding window for a single process architecture.
class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = threading.Lock()
        
    def check_rate_limit(self, client_ip: str):
        now = time.time()
        window_start = now - settings.rate_limit_window
        
        with self.lock:
            # Clean old requests
            self.requests[client_ip] = [req_time for req_time in self.requests[client_ip] if req_time > window_start]
            
            if len(self.requests[client_ip]) >= settings.rate_limit_requests:
                raise APIError(code="RATE_LIMITED", message="Rate limit exceeded", status_code=429)
                
            self.requests[client_ip].append(now)

limiter = RateLimiter()

def verify_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    limiter.check_rate_limit(client_ip)
    return True
