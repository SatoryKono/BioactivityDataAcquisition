"""Refresh source-tree hash and hotspot summary in module coverage inventory."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.engineering.qa.report_module_coverage_inventory import (
    _build_hotspot_family_coverage,
    compute_source_tree_sha256,
)

ROOT = Path(__file__).resolve().parent
INVENTORY_PATH = ROOT / "reports" / "quality" / "module-coverage-inventory.json"

payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
payload["source_tree_sha256"] = compute_source_tree_sha256(repo_root=ROOT)
payload["summary"]["hotspot_family_coverage"] = _build_hotspot_family_coverage(
    payload["modules"],
    repo_root=ROOT,
)
INVENTORY_PATH.write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(f"updated {INVENTORY_PATH}")
