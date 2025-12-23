import contextlib
import time

import requests
from prometheus_client import Counter

from bioetl.infrastructure.observability.server import start_metrics_server

# Define a metric if not already defined (registry is global)
with contextlib.suppress(ValueError):
    c = Counter('bioetl_records_processed_total', 'Description of counter')

def test_idempotency() -> None:
    print("Call 1: Starting server...")
    start_metrics_server(8001)

    print("Call 2: Calling again (should be no-op)...")
    start_metrics_server(8001)

    # Give it a moment
    time.sleep(1)

    try:
        resp = requests.get("http://localhost:8001/metrics")
        print(f"Status: {resp.status_code}")
        if "bioetl_records_processed_total" in resp.text:
            print("Metric found!")
        else:
            print("Metric NOT found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_idempotency()
