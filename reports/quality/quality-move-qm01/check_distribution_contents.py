import sys
import json
import tarfile
import zipfile
from pathlib import Path

def check_distribution(dist_path, expected_files_path):
    dist_path = Path(dist_path)
    if not dist_path.exists():
        print(f"ERROR: Distribution {dist_path} not found")
        sys.exit(1)

    with open(expected_files_path) as f:
        expected_files = set(json.load(f))

    actual_files = set()
    if dist_path.suffix == '.whl':
        with zipfile.ZipFile(dist_path) as z:
            actual_files = {f for f in z.namelist() if not f.startswith('bioetl-')}
    elif dist_path.suffix == '.gz':
        with tarfile.open(dist_path) as t:
            actual_files = {f.split('/', 1)[1] for f in t.getnames() if '/' in f}

    # Check for forbidden namespaces in wheel ONLY
    if dist_path.suffix == '.whl':
        for f in actual_files:
            if f.startswith('scripts/') or f.startswith('bioetl/infrastructure/quality/'):
                print(f"ERROR: Forbidden namespace found in wheel: {f}")
                sys.exit(1)

    # Check if all expected files are present (sdist ONLY)
    if dist_path.suffix == '.gz':
        missing = expected_files - actual_files
        if missing:
            print(f"ERROR: Missing expected files in sdist: {missing}")
            sys.exit(1)

    print("SUCCESS: Distribution contents verified")
    sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python check_distribution_contents.py <dist_path> <expected_files.json>")
        sys.exit(1)
    check_distribution(sys.argv[1], sys.argv[2])
