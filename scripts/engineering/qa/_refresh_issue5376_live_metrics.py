"""Rebind only live fields of the Codex-authored #5376 historical record.

The canonical coverage inventory supplies adopted values; W44 raw measurements
and historical floors remain distinct. This record has no existing generator.
"""

from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

root = Path(__file__).resolve().parents[3]
proof = root / "reports/quality/proof-or-stop/config-root-11899"
inventory_path = root / "reports/quality/module-coverage-inventory.json"
record_path = root / "reports/quality/issue-5376-coverage-tail-closeout.json"
inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
record = json.loads(record_path.read_text(encoding="utf-8"))
historical = deepcopy(record["historical_coverage_inventory_delta"])
removed = deepcopy(record["removed_low_tail_module"])
assert record["schema_version"] == "issue-5376-coverage-tail-closeout-v1"
assert record["issue"]["number"] == 5376
assert record["closeout"]["status"] == "regressed_after_closeout"
rows = inventory["modules"]
below = [
    row
    for row in rows
    if isinstance(row.get("coverage_percent"), (int, float))
    and row["coverage_percent"] < 85
]
tracked = next(row for row in rows if row["path"] == removed["path"])
record["current_live_metrics"].update(
    below_85_module_count=len(below),
    uncovered_module_count=inventory["summary"]["uncovered_module_count"],
    unmeasured_module_count=inventory["summary"]["unmeasured_module_count"],
    tracked_module_coverage_percent=tracked["coverage_percent"],
    tracked_module_status=tracked["coverage_status"],
)
record["closeout"].update(
    residual_tail_remains=bool(below),
    residual_below_85_module_count=len(below),
    rationale=(
        f"Retained live inventory has {len(below)} measured modules below the default floor; "
        f"uncovered={inventory['summary']['uncovered_module_count']}, "
        f"unmeasured={inventory['summary']['unmeasured_module_count']}. "
        "Historical floors are retained; these values do not assert fresh raw coverage. "
        "Historical shard delta and regressed_after_closeout status remain unchanged."
    ),
)
record["current_live_metrics_provenance"] = {
    "source_inventory_sha256": hashlib.sha256(
        inventory_path.read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest(),
    "source_tree_sha256": inventory["source_tree_sha256"],
    "derived_by": "scripts/engineering/qa/_refresh_issue5376_live_metrics.py",
    "semantics": "Live retained-inventory binding; raw W44 regression ledger is separate.",
}
assert record["historical_coverage_inventory_delta"] == historical
assert record["removed_low_tail_module"] == removed
record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
sys.stdout.write(
    f"Updated #5376 live metrics; historical record preserved; below85={len(below)}\n"
)
