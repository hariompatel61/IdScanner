import numpy as np
import cv2
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class RapidOCREngine:
    """
    Production-grade RapidOCR Engine (ONNX CPU Runtime).
    Loaded ONCE at application startup and reused across requests for maximum throughput.
    """
    def __init__(self):
        self._engine: Optional[Any] = None
        self._initialized: bool = False

    def initialize(self) -> bool:
        """
        Instantiates RapidOCR model ONCE and executes a warm-up inference pass.
        """
        if self._initialized and self._engine is not None:
            return True

        try:
            logger.info("Initializing RapidOCR ONNX model...")
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()

            # Execute Warm-Up Inference Pass
            dummy_img = np.zeros((300, 500, 3), dtype=np.uint8)
            cv2.putText(dummy_img, "WARMUP TEST 123", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            _ = self._engine(dummy_img)

            self._initialized = True
            logger.info("RapidOCR model initialized and warmed up successfully!")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize RapidOCR model: {e}")
            self._initialized = False
            return False

    def is_ready(self) -> bool:
        if not self._initialized or self._engine is None:
            return self.initialize()
        return self._initialized

    def optimize_image_dimensions(self, img: np.ndarray) -> np.ndarray:
        """
        Resizes unnecessarily huge high-resolution mobile camera uploads 
        to max_image_dimension while preserving exact aspect ratio.
        """
        h, w = img.shape[:2]
        max_dim = settings.max_image_dimension
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            new_w = int(w * scale)
            new_h = int(h * scale)
            return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return img

    def process_image(self, img_array: np.ndarray, apply_adaptive_threshold: bool = False) -> List[Dict[str, Any]]:
        """
        Executes OCR inference on input numpy image.
        """
        if not self.is_ready() or self._engine is None:
            raise RuntimeError("RapidOCR Engine is not initialized or ready")

        # 1. Optimize dimensions if huge image
        img = self.optimize_image_dimensions(img_array)

        # 2. Apply preprocessing if second pass requested
        if apply_adaptive_threshold:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            img = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

        # 3. RapidOCR Inference
        result, _ = self._engine(img)
        
        parsed_results: List[Dict[str, Any]] = []
        if result:
            for item in result:
                # item format: [bbox, text, confidence]
                bbox, text, confidence = item
                parsed_results.append({
                    "text": str(text).strip(),
                    "confidence": float(confidence),
                    "bbox": [[float(p[0]), float(p[1])] for p in bbox]
                })

        return parsed_results

    async def process_image_async(self, img_array: np.ndarray, apply_adaptive_threshold: bool = False) -> List[Dict[str, Any]]:
        """
        Asynchronously executes OCR inference with concurrency protection and timeout.
        """
        import asyncio
        if not hasattr(self, '_semaphore'):
            self._semaphore = asyncio.Semaphore(settings.max_concurrent_ocr)
            
        try:
            async with self._semaphore:
                return await asyncio.wait_for(
                    asyncio.to_thread(self.process_image, img_array, apply_adaptive_threshold),
                    timeout=settings.api_timeout_seconds
                )
        except asyncio.TimeoutError:
            raise TimeoutError("OCR Processing Timeout")

# Singleton Instance initialized once across application lifecycle
ocr_engine = RapidOCREngine()
