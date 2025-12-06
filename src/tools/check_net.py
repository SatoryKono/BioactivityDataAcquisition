import time

import requests


def check(url):
    print(f"Fetching {url}...")
    try:
        start = time.time()
        resp = requests.get(url, timeout=10)
        print(f"Status: {resp.status_code} in {time.time()-start:.2f}s")
        print(resp.text[:200])
    except Exception as e:
        print(f"Error: {e}")

# check("https://www.ebi.ac.uk/chembl/api/data/status")
check("https://www.ebi.ac.uk/chembl/api/data/molecule?limit=1")
