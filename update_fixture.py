"""Script to update the run_manifest_inspection golden fixture."""

import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tests.unit.application.services.test_reproducibility_golden_fixtures import (
    _make_run_manifest_inspection_payload,
    FIXTURE_DIR,
)

def main():
    payload = _make_run_manifest_inspection_payload()
    fixture_path = FIXTURE_DIR / "run_manifest_inspection_v1.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Updated fixture: {fixture_path}")

if __name__ == "__main__":
    main()
