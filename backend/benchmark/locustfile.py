import cv2
import numpy as np
from locust import HttpUser, task, between

def generate_sample_id_image() -> bytes:
    """Generates a synthetic PAN card image with full field data for load testing."""
    img = np.ones((600, 950, 3), dtype=np.uint8) * 240
    cv2.rectangle(img, (20, 20), (930, 580), (200, 220, 240), -1)
    cv2.rectangle(img, (20, 20), (930, 580), (100, 100, 100), 3)
    cv2.putText(img, "INCOME TAX DEPARTMENT", (250, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 120), 2)
    cv2.putText(img, "GOVT. OF INDIA", (330, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 120), 2)
    cv2.putText(img, "Permanent Account Number", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
    cv2.putText(img, "ABCDE1234F", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
    cv2.putText(img, "Name", (50, 290), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
    cv2.putText(img, "TEST USER", (50, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, "Father's Name", (50, 370), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
    cv2.putText(img, "TEST FATHER", (50, 410), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, "Date of Birth", (50, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
    cv2.putText(img, "01/01/1990", (50, 490), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    success, buffer = cv2.imencode(".jpg", img)
    return buffer.tobytes()

class IDScannerUser(HttpUser):
    # Simulate a user waiting between 1 to 3 seconds between scans
    wait_time = between(1.0, 3.0)

    def on_start(self):
        # Generate the test image once when the user spawns
        self.image_bytes = generate_sample_id_image()
        
        # If your API has an API token configured in settings:
        # self.headers = {"Authorization": "Bearer YOUR_API_TOKEN"}
        self.headers = {}

    @task
    def test_scan_endpoint(self):
        files = {
            'image': ('test_pan.jpg', self.image_bytes, 'image/jpeg')
        }
        data = {
            'document_type': 'pan_card'
        }
        with self.client.post("/api/v1/scan", files=files, data=data, headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                body = response.json()
                # Validate that new details key is present in successful responses
                if body.get("success") and body.get("details") is None:
                    response.failure("Missing 'details' key in successful response")
                else:
                    response.success()
            else:
                response.failure(f"Status {response.status_code}")
