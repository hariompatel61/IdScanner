# Phase 9: Performance & Scalability

## Production Benchmarks
Because the OCR extraction pipeline utilizes `rapidocr-onnxruntime` heavily relying on CPU bounds, the throughput scales linearly with available vCPUs.

### Benchmark Setup
* **Hardware Profile**: Local execution (4 logical cores).
* **Container Bounds**: 2 concurrent workers per instance (`max_concurrent_ocr=2`).
* **Test Tool**: Custom asynchronous HTTTP script (`production_benchmark.py`).

### Results Summary
| Concurrency | Throughput (req/s) | Median Latency | P95 Latency | Errors |
|-------------|--------------------|----------------|-------------|--------|
| 1           | 0.25               | 4.06s          | 4.06s       | 0      |
| 5           | 0.28               | 16.5s          | 17.2s       | 0      |
| 10          | 0.28               | 34.2s          | 35.8s       | 0      |

*Note: Since the server only processes a limited number of ONNX passes concurrently, higher concurrency simply increases queueing latency (P95 goes up proportionally). The raw throughput ceiling remains ~0.25 to 0.35 req/s per node on this baseline hardware configuration.*

## Capacity Planning
To claim **500+ scans/minute** (~8.3 requests/second), you would need to scale horizontally:
* Baseline Node: 0.28 requests/second.
* Required Nodes: ~30 nodes behind a load balancer.
* Each node requiring 2-4 vCPUs.

## Hardware Acceleration
For single-node high throughput, switch the `ocr_engine` backend from `rapidocr-onnxruntime` to a GPU-accelerated package (e.g. `onnxruntime-gpu` and CUDA 11.8+ drivers).
