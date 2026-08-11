import httpx
import numpy as np
import cv2
import logging
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class OCREngineClient:
    def __init__(self):
        self.base_url = "http://scanner-ocr:8001"
        self.timeout = settings.api_timeout_seconds
        self.local_engine = None

    def _init_local_engine(self):
        if self.local_engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                logger.info("Initializing local RapidOCR (ONNX engine)...")
                self.local_engine = RapidOCR()
                logger.info("Local RapidOCR engine ready!")
            except Exception as e:
                logger.error(f"Failed to initialize local RapidOCR: {e}")

    def is_ready(self) -> bool:
        # Check HTTP microservice worker first
        try:
            response = httpx.get(f"{self.base_url}/ready", timeout=2.0)
            if response.status_code == 200:
                return True
        except httpx.RequestError:
            pass

        # Fallback to native RapidOCR ONNX engine
        self._init_local_engine()
        return self.local_engine is not None

    def process_image(self, img_array: np.ndarray, apply_adaptive_threshold: bool = False) -> List[Dict[str, Any]]:
        """
        Processes image via HTTP microservice or native RapidOCR engine.
        """
        if apply_adaptive_threshold:
            gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
            img_array = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)

        # 1. Try HTTP microservice if available
        try:
            success, buffer = cv2.imencode(".jpg", img_array)
            if success:
                files = {"file": ("image.jpg", buffer.tobytes(), "image/jpeg")}
                data = {"adaptive_threshold": str(apply_adaptive_threshold).lower()}
                response = httpx.post(f"{self.base_url}/scan", files=files, data=data, timeout=self.timeout)
                if response.status_code == 200:
                    return response.json().get("results", [])
        except Exception:
            pass

        # 2. Fallback to local RapidOCR engine
        self._init_local_engine()
        if not self.local_engine:
            raise RuntimeError("OCR Engine unavailable")

        result, _ = self.local_engine(img_array)
        results = []
        if result:
            for item in result:
                # item format: [bbox, text, confidence]
                bbox, text, confidence = item
                results.append({
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": [[float(p[0]), float(p[1])] for p in bbox]
                })

        return results

# Singleton instance for the API to use
ocr_engine = OCREngineClient()
