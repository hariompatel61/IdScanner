import os
import sys
import time
import numpy as np
import cv2
import httpx
import statistics

# Synthetic Data Generation
def create_synthetic_image(text: str) -> np.ndarray:
    img = np.ones((200, 600, 3), dtype=np.uint8) * 255
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, text, (50, 100), font, 1.5, (0, 0, 0), 2, cv2.LINE_AA)
    return img

def benchmark_ocr_worker(iterations: int = 10):
    print("\n--- Benchmarking Isolated OCR Worker ---")
    url = "http://localhost:8001/scan"
    
    # Wait for ready
    while True:
        try:
            if httpx.get("http://localhost:8001/ready").status_code == 200:
                break
        except:
            pass
        print("Waiting for OCR worker to be ready...")
        time.sleep(2)

    img = create_synthetic_image("TEST IMAGE OCR WORKER 12345")
    _, buffer = cv2.imencode(".jpg", img)
    image_bytes = buffer.tobytes()

    latencies = []
    
    # Cold start (first request)
    start = time.time()
    res = httpx.post(url, files={"file": ("test.jpg", image_bytes, "image/jpeg")}, data={"adaptive_threshold": "false"})
    cold_start = (time.time() - start) * 1000
    print(f"Cold Start Latency: {cold_start:.2f} ms")

    # Warm requests
    for i in range(iterations):
        start = time.time()
        httpx.post(url, files={"file": ("test.jpg", image_bytes, "image/jpeg")}, data={"adaptive_threshold": "false"})
        latencies.append((time.time() - start) * 1000)

    print(f"P50: {np.percentile(latencies, 50):.2f} ms")
    print(f"P95: {np.percentile(latencies, 95):.2f} ms")
    print(f"P99: {np.percentile(latencies, 99):.2f} ms")

def benchmark_api_gateway(iterations: int = 10):
    print("\n--- Benchmarking API Gateway (End-to-End) ---")
    url = "http://localhost:4500/api/v1/scan"
    
    img = create_synthetic_image("INCOME TAX DEPT ABCDE1234F")
    _, buffer = cv2.imencode(".jpg", img)
    image_bytes = buffer.tobytes()

    latencies = []
    for i in range(iterations):
        start = time.time()
        res = httpx.post(url, files={"file": ("test.jpg", image_bytes, "image/jpeg")})
        if res.status_code == 200:
            latencies.append((time.time() - start) * 1000)
        else:
            print(f"API Error: {res.status_code}")

    if latencies:
        print(f"P50: {np.percentile(latencies, 50):.2f} ms")
        print(f"P95: {np.percentile(latencies, 95):.2f} ms")
        print(f"P99: {np.percentile(latencies, 99):.2f} ms")
        overhead = np.percentile(latencies, 50) - (latencies[0] if len(latencies) == 1 else 0) # Rough estimate
        print(f"Note: Compare with OCR Worker P50 to see IPC/Network overhead.")

if __name__ == "__main__":
    benchmark_ocr_worker()
    benchmark_api_gateway()
