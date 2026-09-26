import os
import traceback
from pathlib import Path


def check_writable(dir_path):
    path = Path(dir_path)
    print("Testing:", path.absolute())
    try:
        path.mkdir(parents=True, exist_ok=True)
        temp_file = path / ".health_check_probe"
        print("  Attempting touch:", temp_file)
        temp_file.touch()
        print("  Touch OK. Attempting unlink...")
        temp_file.unlink()
        print("  Unlink OK.")
        return True
    except Exception as e:
        print("  FAILED:", type(e).__name__ + ":", e)
        return False


paths = [
    "data/output/bronze/chembl/molecule",
    "data/output/silver/chembl/molecule",
    "data/output/gold/chembl/molecule",
]

print("Starting BioETL Storage Health Debug...")
results = []
for p in paths:
    results.append(check_writable(p))

print(f"\nSummary: {sum(results)}/3 passed")
