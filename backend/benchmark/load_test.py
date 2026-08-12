import time
import numpy as np
import cv2
import psutil
import os
import json
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

API_URL = "http://127.0.0.1:4500/api/v1/scan"

def generate_sample_id_image() -> bytes:
    """Generates a synthetic PAN card image in memory for benchmark testing."""
    img = np.ones((600, 950, 3), dtype=np.uint8) * 240
    cv2.rectangle(img, (20, 20), (930, 580), (200, 220, 240), -1)
    cv2.rectangle(img, (20, 20), (930, 580), (100, 100, 100), 3)
    cv2.putText(img, "INCOME TAX DEPARTMENT", (250, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 120), 2)
    cv2.putText(img, "GOVT. OF INDIA", (330, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 120), 2)
    cv2.putText(img, "Permanent Account Number", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
    cv2.putText(img, "ABCDE1234F", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
    cv2.putText(img, "Name: TEST USER", (50, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
    cv2.putText(img, "Father's Name: TEST FATHER", (50, 380), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
    cv2.putText(img, "Date of Birth: 01/01/1990", (50, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
    
    success, buffer = cv2.imencode(".jpg", img)
    if not success:
        raise RuntimeError("Failed to encode synthetic test image")
    return buffer.tobytes()

def send_single_scan_request(client: httpx.Client, image_bytes: bytes) -> Dict[str, Any]:
    start_t = time.time()
    files = {'image': ('test_pan.jpg', image_bytes, 'image/jpeg')}
    data = {'document_type': 'pan'}

    try:
        resp = client.post(API_URL, files=files, data=data, timeout=30.0)
        elapsed_ms = (time.time() - start_t) * 1000.0
        if resp.status_code == 200:
            return {"success": True, "latency_ms": elapsed_ms, "status": resp.status_code, "resp": resp.json()}
        else:
            return {"success": False, "latency_ms": elapsed_ms, "status": resp.status_code, "resp": None}
    except Exception as e:
        elapsed_ms = (time.time() - start_t) * 1000.0
        return {"success": False, "latency_ms": elapsed_ms, "status": 500, "error": str(e)}

def run_load_scenario(scenario_name: str, target_rps: float, duration_seconds: int, image_bytes: bytes) -> Dict[str, Any]:
    print(f"\n=======================================================")
    print(f" Running Load Scenario: {scenario_name}")
    print(f" Target Rate: {target_rps} req/sec | Duration: {duration_seconds}s")
    print(f" Target Scans/Minute: {target_rps * 60:.0f}")
    print(f"=======================================================")

    results: List[Dict[str, Any]] = []
    process = psutil.Process(os.getpid())
    cpu_samples = []
    ram_samples = []

    client = httpx.Client()
    max_workers = max(10, int(target_rps * 2))
    
    start_time = time.time()
    end_time = start_time + duration_seconds
    interval = 1.0 / target_rps

    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        while time.time() < end_time:
            t0 = time.time()
            futures.append(executor.submit(send_single_scan_request, client, image_bytes))
            
            # Sample CPU and RAM
            cpu_samples.append(psutil.cpu_percent(interval=None))
            ram_samples.append(process.memory_info().rss / (1024 * 1024))
            
            elapsed = time.time() - t0
            sleep_t = interval - elapsed
            if sleep_t > 0:
                time.sleep(sleep_t)

        for future in as_completed(futures):
            results.append(future.result())

    client.close()

    total_time = time.time() - start_time
    total_requests = len(results)
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    latencies = sorted([r["latency_ms"] for r in results])
    
    p50 = float(np.percentile(latencies, 50)) if latencies else 0.0
    p95 = float(np.percentile(latencies, 95)) if latencies else 0.0
    p99 = float(np.percentile(latencies, 99)) if latencies else 0.0

    rps = total_requests / total_time
    scans_per_minute = rps * 60.0
    error_rate = (len(failed) / total_requests * 100.0) if total_requests > 0 else 0.0
    avg_cpu = float(np.mean(cpu_samples)) if cpu_samples else 0.0
    avg_ram_mb = float(np.mean(ram_samples)) if ram_samples else 0.0

    print(f"\n--- SCENARIO RESULTS: {scenario_name} ---")
    print(f"  Total Requests Executed : {total_requests}")
    print(f"  Successful Scans        : {len(successful)}")
    print(f"  Failed Scans            : {len(failed)}")
    print(f"  Sustained Rate (RPS)    : {rps:.2f} req/sec")
    print(f"  Sustained Throughput    : {scans_per_minute:.1f} scans/minute")
    print(f"  Latency P50             : {p50:.2f} ms")
    print(f"  Latency P95             : {p95:.2f} ms")
    print(f"  Latency P99             : {p99:.2f} ms")
    print(f"  Error Rate              : {error_rate:.2f}%")
    print(f"  Average CPU Load        : {avg_cpu:.1f}%")
    print(f"  Average RAM Usage       : {avg_ram_mb:.1f} MB")

    return {
        "scenario": scenario_name,
        "target_rps": target_rps,
        "total_requests": total_requests,
        "successful_requests": len(successful),
        "failed_requests": len(failed),
        "actual_rps": rps,
        "scans_per_minute": scans_per_minute,
        "p50_ms": p50,
        "p95_ms": p95,
        "p99_ms": p99,
        "error_rate_pct": error_rate,
        "avg_cpu_pct": avg_cpu,
        "avg_ram_mb": avg_ram_mb
    }

def main():
    print("Generating sample ID image...")
    image_bytes = generate_sample_id_image()
    print(f"Sample image generated ({len(image_bytes)} bytes).")

    scenarios = [
        ("Scenario A: Baseline (1 req/sec)", 1.0, 5),
        ("Scenario B: Medium (5 req/sec)", 5.0, 5),
        ("Scenario C: Target 500+/min (10 req/sec)", 10.0, 10),
        ("Scenario D: Burst (15 req/sec)", 15.0, 5),
        ("Scenario E: Peak Burst (20 req/sec)", 20.0, 5),
    ]

    summary = []
    for name, rps, dur in scenarios:
        res = run_load_scenario(name, rps, dur, image_bytes)
        summary.append(res)
        time.sleep(1)

    print("\n=======================================================")
    print("        FINAL PERFORMANCE & ACCEPTANCE REPORT")
    print("=======================================================")
    print(f"{'Scenario':<40} | {'Scans/Min':<10} | {'P50 (ms)':<10} | {'P95 (ms)':<10} | {'Error Rate':<10}")
    print("-" * 82)
    for s in summary:
        print(f"{s['scenario']:<40} | {s['scans_per_minute']:<10.1f} | {s['p50_ms']:<10.1f} | {s['p95_ms']:<10.1f} | {s['error_rate_pct']:<10.2f}%")

if __name__ == "__main__":
    main()
