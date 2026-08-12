from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: List[str] = ["*"]
    api_token: Optional[str] = None  # Server-to-server Bearer Token for RIMS (e.g., "rims_sec_token_99812")
    max_image_size_mb: int = 5
    max_image_dimension: int = 960  # Optimized resolution bound for 150ms OCR latency
    ocr_device: str = "cpu"
    ocr_workers: int = 4
    high_confidence_threshold: float = 0.85
    retry_threshold: float = 0.70
    api_timeout_seconds: int = 30
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
