"""Inventory Sonar baseline issues and map to current file state."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
data = json.loads(
    (ROOT / "reports/quality/sonar_baseline_report.json").read_text(encoding="utf-8")
)
issues = data.get("live_issues", {}).get("issues", [])
print(f"baseline generated_at={data.get('generated_at')}")
print(f"total_open={len(issues)}")
print(f"in_scope={sum(1 for i in issues if i.get('in_supported_scope'))}")
print("--- by rule ---")
for rule, n in Counter(i["rule"] for i in issues).most_common():
    print(f"  {rule}: {n}")
print("--- by path ---")
by_path: dict[str, list] = defaultdict(list)
for i in issues:
    by_path[i["path"]].append(i)
for path, rows in sorted(by_path.items(), key=lambda x: -len(x[1])):
    exists = (ROOT / path).exists()
    lines = 0
    if exists:
        lines = len((ROOT / path).read_text(encoding="utf-8", errors="replace").splitlines())
    print(f"  {len(rows):2d}  exists={exists}  lines={lines:5d}  {path}")
    for i in rows:
        print(
            f"      {i['rule']} L{i.get('line')} "
            f"scope={i.get('in_supported_scope')} :: {i['message'][:90]}"
        )
