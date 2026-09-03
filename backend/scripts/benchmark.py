import os
import json
import time
import argparse
import numpy as np
from pathlib import Path
from collections import defaultdict
import psutil

from fastapi.testclient import TestClient
from app.main import app
from app.ocr.engine import ocr_engine

DATASET_DIR = Path("tests/fixtures/benchmarks/dataset")

def calculate_exact_match(expected, actual):
    if expected is None and actual is None: return True
    if expected is None or actual is None: return False
    return str(expected).strip() == str(actual).strip()

def calculate_normalized_match(expected, actual):
    if expected is None and actual is None: return True
    if expected is None or actual is None: return False
    return str(expected).strip().lower() == str(actual).strip().lower()

def run_benchmark():
    # Warm up engine explicitly so the first request doesn't skew latencies
    ocr_engine.initialize()
    
    # We must disable dependency overrides or pass valid auth
    # For benchmark we will use test_token
    client = TestClient(app)
    headers = {"Authorization": "Bearer test_token"}

    metrics = {
        "samples": 0,
        "classification": {"correct": 0, "false": 0, "ambiguous": 0},
        "fields": defaultdict(lambda: {"exact": 0, "normalized": 0, "total": 0, "missing": 0, "incorrect": 0}),
        "validation": {"false_accept": 0, "false_reject": 0, "correct": 0},
        "decisions": {"ACCEPT": 0, "REVIEW": 0, "RECAPTURE": 0, "INVALID": 0},
        "latencies": {"total": [], "api": []},
        "failures": []
    }
    
    if not DATASET_DIR.exists():
        print("Dataset directory not found!")
        return

    for doc_type_dir in DATASET_DIR.iterdir():
        if not doc_type_dir.is_dir(): continue
        
        doc_type = doc_type_dir.name
        for cond_dir in doc_type_dir.iterdir():
            if not cond_dir.is_dir(): continue
            
            condition = cond_dir.name
            for sample_dir in cond_dir.iterdir():
                if not sample_dir.is_dir(): continue
                
                gt_path = sample_dir / "ground_truth.json"
                img_path = sample_dir / "image.jpg"
                
                if not gt_path.exists() or not img_path.exists(): continue
                
                with open(gt_path, "r") as f:
                    gt = json.load(f)
                
                metrics["samples"] += 1
                
                t0 = time.perf_counter()
                
                try:
                    with open(img_path, "rb") as f:
                        response = client.post("/api/v1/scan", headers=headers, files={"file": ("document.jpg", f, "image/jpeg")})
                    t_total = time.perf_counter() - t0
                    
                    if response.status_code == 429:
                        metrics["failures"].append({"sample": str(sample_dir), "error": "RATE_LIMITED", "category": "API"})
                        continue
                        
                    data = response.json()
                    metrics["latencies"]["total"].append(t_total * 1000)
                    metrics["latencies"]["api"].append(data.get("processing_time_ms", 0))
                    
                except Exception as e:
                    metrics["failures"].append({
                        "sample": str(sample_dir),
                        "error": str(e),
                        "category": "CRASH"
                    })
                    continue

                actual_doc_type = data.get("document_type", "unknown")
                status = data.get("status", "INVALID")
                actual_fields = data.get("fields", {})
                
                if status in metrics["decisions"]:
                    metrics["decisions"][status] += 1
                
                # Classification
                if actual_doc_type == gt["document_type"]:
                    metrics["classification"]["correct"] += 1
                elif actual_doc_type == "unknown":
                    metrics["classification"]["ambiguous"] += 1
                else:
                    metrics["classification"]["false"] += 1
                    
                # Field Extraction
                for k, v_expected in gt["expected_fields"].items():
                    metrics["fields"][k]["total"] += 1
                    v_actual = actual_fields.get(k)
                    
                    if v_actual is None or v_actual == "":
                        metrics["fields"][k]["missing"] += 1
                    elif calculate_exact_match(v_expected, v_actual):
                        metrics["fields"][k]["exact"] += 1
                        metrics["fields"][k]["normalized"] += 1
                    elif calculate_normalized_match(v_expected, v_actual):
                        metrics["fields"][k]["normalized"] += 1
                        metrics["fields"][k]["incorrect"] += 1
                    else:
                        metrics["fields"][k]["incorrect"] += 1
                        
                # Validation Logic
                if gt["expected_status"] == "ACCEPT" and status != "ACCEPT":
                    metrics["validation"]["false_reject"] += 1
                elif gt["expected_status"] != "ACCEPT" and status == "ACCEPT":
                    metrics["validation"]["false_accept"] += 1
                else:
                    metrics["validation"]["correct"] += 1

    # Generate Report
    print("="*50)
    print(" PHASE 8 BENCHMARK REPORT ")
    print("="*50)
    print(f"Total Samples: {metrics['samples']}")
    
    print("\n--- CLASSIFICATION ---")
    print(f"Correct: {metrics['classification']['correct']}")
    print(f"False: {metrics['classification']['false']}")
    print(f"Ambiguous: {metrics['classification']['ambiguous']}")
    if metrics['samples'] > 0:
        print(f"Accuracy: {metrics['classification']['correct'] / metrics['samples'] * 100:.2f}%")
        
    print("\n--- FIELD EXTRACTION ---")
    for k, v in metrics["fields"].items():
        acc = v["exact"] / v["total"] * 100 if v["total"] > 0 else 0
        norm_acc = v["normalized"] / v["total"] * 100 if v["total"] > 0 else 0
        print(f"Field '{k}': Exact {acc:.1f}% | Norm {norm_acc:.1f}% | Missing {v['missing']}")

    print("\n--- VALIDATION ---")
    print(f"Correct: {metrics['validation']['correct']}")
    print(f"False Accept: {metrics['validation']['false_accept']}")
    print(f"False Reject: {metrics['validation']['false_reject']}")
    print(f"Decision Spread: {dict(metrics['decisions'])}")
    
    print("\n--- PERFORMANCE ---")
    if metrics["latencies"]["total"]:
        totals = np.array(metrics["latencies"]["total"])
        apis = np.array(metrics["latencies"]["api"])
        print(f"Total Client Latency: Avg {np.mean(totals):.1f}ms | p50 {np.percentile(totals, 50):.1f}ms | p95 {np.percentile(totals, 95):.1f}ms")
        print(f"API Processing Latency: Avg {np.mean(apis):.1f}ms")
        print(f"Throughput: {1000.0 / np.mean(totals):.1f} docs/sec")
    
    process = psutil.Process(os.getpid())
    print(f"\nPeak Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB")
    
    print("\n--- FAILURES ---")
    for f in metrics["failures"]:
        print(f"Sample: {f['sample']}, Error: {f['error']}")

    with open("benchmark_results.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print("\nSaved benchmark_results.json")
    
if __name__ == "__main__":
    run_benchmark()
