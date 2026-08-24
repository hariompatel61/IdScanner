from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: List[str] = ["*"]
    api_token: Optional[str] = None  # Server-to-server Bearer Token (e.g., "secure_api_token_99812")
    max_image_size_mb: int = 5
    max_image_dimension: int = 960  # Optimized resolution bound for 150ms OCR latency
    ocr_device: str = "cpu"
    ocr_workers: int = 4
    high_confidence_threshold: float = 0.80
    retry_threshold: float = 0.75
    api_timeout_seconds: int = 30
    field_confidence_threshold: float = 0.70  # Per-field low-confidence cutoff for structured extraction
    line_merge_y_tolerance: int = 15  # Pixel tolerance for grouping OCR boxes into horizontal bands
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
