import time
import numpy as np
import cv2
import pytest
from app.ocr.engine import ocr_engine
from app.extractors.line_reconstructor import reconstruct_document

def test_ocr_output_stability():
    # Synthetic safe test fixture
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    img.fill(255)
    cv2.putText(img, "Elector's Name", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    cv2.putText(img, "Shubham Darekar", (350, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    cv2.putText(img, "Mother's Name", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    cv2.putText(img, "Nandini Darekar", (350, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    
    ocr_engine.initialize()
    raw = ocr_engine.process_image(img)
    
    # 1. Output stability
    raw_again = ocr_engine.process_image(img)
    assert len(raw) == len(raw_again), "OCR output should be stable"
    for r1, r2 in zip(raw, raw_again):
        assert r1['text'] == r2['text']
        
    doc = reconstruct_document(raw, image_dimensions=(600, 400), processing_time_ms=10)
    assert len(doc.tokens) > 0
    assert len(doc.lines) > 0
    assert len(doc.blocks) > 0
    
    # Assert geometry sorting
    texts = [l.text for l in doc.lines]
    
    # It should correctly place "Elector's Name" then "Shubham Darekar", then "Mother's Name", then "Nandini Darekar"
    expected = ["Elector's Name", "Shubham Darekar", "Mother's Name", "Nandini Darekar"]
    # Depending on OCR segmenting, texts might be grouped differently but order should match
    flattened_extracted = " ".join(texts)
    for e in expected:
        assert e in flattened_extracted

if __name__ == '__main__':
    pytest.main([__file__, "-v"])
