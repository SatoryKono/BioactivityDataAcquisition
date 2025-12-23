import time

import requests
from prometheus_client import Counter, start_http_server

# Define a metric
c = Counter('bioetl_records_processed_total', 'Description of counter')
c.inc()

def test_server() -> None:
    print("Starting server...")
    try:
        start_http_server(8001)
        print("Server started.")
    except Exception as e:
        print(f"Server start failed (expected if already running): {e}")

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
    test_server()
