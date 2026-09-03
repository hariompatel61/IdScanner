import subprocess
import time
import json
import os

concurrencies = [1, 10, 25, 50]
duration = "10s"

results = {}

for c in concurrencies:
    print(f"Running load test for {c} concurrent users...")
    cmd = [
        "locust",
        "-f", "locustfile.py",
        "--headless",
        "-u", str(c),
        "-r", str(c), # spawn rate
        "--run-time", duration,
        "--host", "http://127.0.0.1:4500",
        "--csv", f"locust_results_{c}"
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Done with {c} concurrent users.")

print("Load tests complete. Check CSV files for detailed metrics.")
