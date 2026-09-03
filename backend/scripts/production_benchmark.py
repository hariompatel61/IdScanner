import asyncio
import time
import httpx
import statistics
import psutil
import os
import cv2
import numpy as np

# Generate dummy test image
img = np.zeros((800, 600, 3), dtype=np.uint8)
cv2.putText(img, "INCOME TAX DEPARTMENT", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
cv2.putText(img, "ABCDE1234F", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
_, encoded_img = cv2.imencode('.jpg', img)
DUMMY_IMAGE = encoded_img.tobytes()

async def fetch(client, i):
    files = {'file': ('dummy.jpg', DUMMY_IMAGE, 'image/jpeg')}
    data = {'document_type': 'pan_card'}
    start = time.time()
    try:
        response = await client.post("http://127.0.0.1:4500/api/v1/scan", files=files, data=data, timeout=120.0)
        return time.time() - start, response.status_code
    except Exception:
        return time.time() - start, 500

async def benchmark_concurrency(c):
    print(f"\n--- Running Benchmark: {c} Concurrent Requests ---")
    async with httpx.AsyncClient() as client:
        start_time = time.time()
        tasks = [fetch(client, i) for i in range(c)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
    latencies = [r[0] for r in results if r[1] == 200]
    errors = len([r for r in results if r[1] != 200])
    
    total_time = end_time - start_time
    throughput = len(latencies) / total_time if total_time > 0 else 0
    
    mem = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    cpu = psutil.cpu_percent(interval=None)

    print(f"Total Time: {total_time:.2f}s")
    print(f"Throughput: {throughput:.2f} req/s")
    print(f"Errors: {errors}")
    if latencies:
        print(f"P50: {statistics.median(latencies):.2f}s")
        print(f"P95: {statistics.quantiles(latencies, n=100)[94] if len(latencies) > 1 else latencies[0]:.2f}s")
    print(f"Peak Client Memory: {mem:.2f} MB")
    print(f"Client CPU: {cpu}%")

async def main():
    for c in [1, 5, 10]: # Scale down for local execution limits, prompt allows "higher only if hardware permits"
        await benchmark_concurrency(c)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
