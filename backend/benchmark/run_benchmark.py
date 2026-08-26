import os
import sys
import time
import numpy as np
import cv2
import httpx

# Synthetic Data Generation
def create_synthetic_image(text: str) -> np.ndarray:
    img = np.ones((200, 600, 3), dtype=np.uint8) * 255
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, text, (50, 100), font, 1.5, (0, 0, 0), 2, cv2.LINE_AA)
    return img

def benchmark_api(base_url: str = "http://localhost:4500", iterations: int = 10):
    print(f"\n--- Benchmarking IDScanner API ({base_url}) ---")
    url = f"{base_url}/api/v1/scan"
    health_url = f"{base_url}/health"

    # Wait for ready
    max_wait = 15
    for attempt in range(max_wait):
        try:
            if httpx.get(health_url, timeout=2.0).status_code == 200:
                print("API Gateway is ready.")
                break
        except Exception:
            pass
        print(f"Waiting for API to be ready ({attempt + 1}/{max_wait})...")
        time.sleep(1)

    img = create_synthetic_image("INCOME TAX DEPT ABCDE1234F")
    _, buffer = cv2.imencode(".jpg", img)
    image_bytes = buffer.tobytes()

    latencies = []
    
    # Cold start (first request)
    start = time.time()
    try:
        res = httpx.post(url, files={"file": ("test.jpg", image_bytes, "image/jpeg")}, timeout=10.0)
        cold_start = (time.time() - start) * 1000
        print(f"Cold Start Latency: {cold_start:.2f} ms (Status: {res.status_code})")
    except Exception as e:
        print(f"Initial request error: {e}")

    # Warm requests
    for i in range(iterations):
        start = time.time()
        try:
            res = httpx.post(url, files={"file": ("test.jpg", image_bytes, "image/jpeg")}, timeout=10.0)
            if res.status_code == 200:
                latencies.append((time.time() - start) * 1000)
            else:
                print(f"API Error [{i}]: {res.status_code}")
        except Exception as e:
            print(f"Request error [{i}]: {e}")

    if latencies:
        print(f"Iterations: {len(latencies)}")
        print(f"P50: {np.percentile(latencies, 50):.2f} ms")
        print(f"P95: {np.percentile(latencies, 95):.2f} ms")
        print(f"P99: {np.percentile(latencies, 99):.2f} ms")

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:4500"
    benchmark_api(target_url)
