"""Temporary helper: list out-of-scope S3776 issues sorted by excess complexity."""
from __future__ import annotations

import json
import re
from pathlib import Path

data = json.loads(Path("reports/quality/sonar_baseline_report.json").read_text(encoding="utf-8"))
issues = data.get("live_issues", {}).get("issues", [])
pat = re.compile(r"from (\d+) to the (\d+) allowed")
rows: list[tuple[int, str, int, str]] = []
for i in issues:
    if i.get("rule") != "python:S3776":
        continue
    m = pat.search(i["message"])
    complexity = int(m.group(1)) if m else 0
    allowed = int(m.group(2)) if m else 15
    rows.append((complexity - allowed, i["path"], i.get("line") or 0, i["message"]))
rows.sort(reverse=True)
print(f"S3776 count: {len(rows)}")
for excess, path, line, msg in rows:
    print(f"+{excess:2d}  {path}:{line}")
