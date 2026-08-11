import os
import cv2
import numpy as np
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Lazy loading to avoid immediate crash if paddle is missing
try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

class OCREngine:
    def __init__(self):
        self.model = None

    def load_model(self):
        if PaddleOCR is None:
            raise ImportError("PaddleOCR library is not installed.")
        
        # Explicitly disable angle classification if not needed for ROI to save time.
        # But for generic ID cards, it might be rotated. We will enable use_angle_cls=True.
        # Ensure we only use english/digits to make it faster for PAN/Aadhaar/Voter.
        logger.info("Initializing PaddleOCR...")
        self.model = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        self.warmup()

    def warmup(self):
        if self.model:
            logger.info("Warming up PaddleOCR...")
            # Create a dummy 100x100 white image
            dummy_img = np.ones((100, 100, 3), dtype=np.uint8) * 255
            self.model.ocr(dummy_img, cls=True)
            logger.info("PaddleOCR warmup complete.")

    def is_ready(self) -> bool:
        return self.model is not None

    def process_image(self, img_array: np.ndarray, apply_adaptive_threshold: bool = False) -> List[Dict[str, Any]]:
        """
        Processes a raw numpy array image and returns parsed OCR results.
        If apply_adaptive_threshold is True, it applies a second-pass preprocessing.
        """
        if not self.model:
            raise RuntimeError("OCR Engine not loaded.")

        if apply_adaptive_threshold:
            # Convert to grayscale
            gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
            # Apply adaptive thresholding to highlight text
            img_array = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            # Convert back to 3 channels for PaddleOCR
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)

        result = self.model.ocr(img_array, cls=True)
        
        parsed_results = []
        if not result or not result[0]:
            return parsed_results

        # PaddleOCR returns [ [ [[x,y], [x,y], [x,y], [x,y]], ('text', confidence) ], ... ]
        for line in result[0]:
            if line:
                box = line[0]
                text = line[1][0]
                conf = line[1][1]
                parsed_results.append({
                    "box": box,
                    "text": text,
                    "confidence": conf
                })
                
        return parsed_results

# Singleton instance
ocr_engine = OCREngine()
