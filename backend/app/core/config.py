from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: List[str] = ["http://localhost", "http://localhost:80"]
    max_image_size_mb: int = 5
    ocr_model: str = "ch_PP-OCRv4"
    ocr_device: str = "cpu"
    ocr_workers: int = 1
    high_confidence_threshold: float = 0.90
    retry_threshold: float = 0.75
    api_timeout_seconds: int = 30
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
