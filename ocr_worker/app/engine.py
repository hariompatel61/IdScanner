import os
import cv2
import numpy as np
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    RapidOCR = None

class OCREngine:
    def __init__(self):
        self.model = None

    def load_model(self):
        if RapidOCR is None:
            raise ImportError("rapidocr_onnxruntime library is not installed.")
        
        logger.info("Initializing RapidOCR (ONNX)...")
        # RapidOCR is lightweight and very fast.
        self.model = RapidOCR()
        self.warmup()

    def warmup(self):
        if self.model:
            logger.info("Warming up RapidOCR...")
            # Create a dummy 100x100 white image
            dummy_img = np.ones((100, 100, 3), dtype=np.uint8) * 255
            self.model(dummy_img)
            logger.info("RapidOCR warmup complete.")

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
            # Convert back to 3 channels for RapidOCR
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)

        # Optimization 1: Resize image if it's too large to speed up processing
        max_dim = 1024
        h, w = img_array.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            new_w, new_h = int(w * scale), int(h * scale)
            img_array = cv2.resize(img_array, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Optimization 2: Avoid double execution of text detection
        result = []
        if self.model.use_text_det:
            img_loaded = self.model.load_img(img_array)
            dt_boxes, _ = self.model.text_detector(img_loaded)
            
            # FAST VALIDATION: A valid ID usually has at least 4-5 text boxes
            if dt_boxes is None or len(dt_boxes) < 4:
                raise ValueError("Invalid Document: Please rescan with a correct document (Aadhaar, PAN, Voter ID, or ABHA).")
                
            dt_boxes = self.model.sorted_boxes(dt_boxes)
            img_crop_list = self.model.get_crop_img_list(img_loaded, dt_boxes)
            
            if self.model.use_angle_cls:
                img_crop_list, _, _ = self.model.text_cls(img_crop_list)
                
            rec_res, _ = self.model.text_recognizer(img_crop_list)
            filter_boxes, filter_rec_res = self.model.filter_boxes_rec_by_score(dt_boxes, rec_res)
            
            result = [[dt.tolist(), rec[0], str(rec[1])] for dt, rec in zip(filter_boxes, filter_rec_res)]
        else:
            result, _ = self.model(img_array)
        
        parsed_results = []
        if not result:
            return parsed_results

        for line in result:
            if line:
                box = line[0]
                text = line[1]
                conf = line[2]
                parsed_results.append({
                    "box": box,
                    "text": text,
                    "confidence": conf
                })
                
        return parsed_results

# Singleton instance
ocr_engine = OCREngine()
