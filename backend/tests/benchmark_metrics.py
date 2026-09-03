import time
import numpy as np
import cv2
from app.ocr.engine import ocr_engine
from app.extractors.line_reconstructor import reconstruct_document
import psutil
import os

def run_benchmark():
    ocr_engine.initialize()
    
    latencies = []
    
    img = np.zeros((800, 1200, 3), dtype=np.uint8)
    img.fill(255)
    for i in range(10):
        cv2.putText(img, f"Line {i} text here", (50, 100 + i*50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    
    # Warmup
    for _ in range(3):
        ocr_engine.process_image(img)
        
    for _ in range(50):
        start = time.perf_counter()
        raw = ocr_engine.process_image(img)
        doc = reconstruct_document(raw)
        latencies.append((time.perf_counter() - start) * 1000)
        
    latencies = np.array(latencies)
    avg_latency = np.mean(latencies)
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    throughput = 1000.0 / avg_latency
    
    process = psutil.Process(os.getpid())
    mem_usage = process.memory_info().rss / 1024 / 1024
    
    print("--- OCR Benchmark Metrics ---")
    print(f"Average Latency: {avg_latency:.2f} ms")
    print(f"p50 Latency: {p50:.2f} ms")
    print(f"p95 Latency: {p95:.2f} ms")
    print(f"Throughput: {throughput:.2f} images/sec")
    print(f"Memory Usage: {mem_usage:.2f} MB")

if __name__ == '__main__':
    run_benchmark()
