import os
from locust import HttpUser, task, between
import io
import cv2
import numpy as np

# Create a dummy image for testing
img = np.zeros((800, 600, 3), dtype=np.uint8)
cv2.putText(img, "INCOME TAX DEPARTMENT", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
cv2.putText(img, "ABCDE1234F", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
_, encoded_img = cv2.imencode('.jpg', img)
dummy_image_bytes = encoded_img.tobytes()

class DocumentScannerUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(3)
    def scan_valid_document(self):
        files = {'file': ('dummy.jpg', dummy_image_bytes, 'image/jpeg')}
        data = {'document_type': 'pan_card'}
        self.client.post("/api/v1/scan", files=files, data=data)
        
    @task(1)
    def scan_no_doc_type(self):
        files = {'file': ('dummy.jpg', dummy_image_bytes, 'image/jpeg')}
        self.client.post("/api/v1/scan", files=files)

    @task(1)
    def health_check(self):
        self.client.get("/health")
