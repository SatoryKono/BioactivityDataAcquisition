"""Script to validate and fix Grafana dashboard variables for BioETL pipelines.

Uses merge strategy: adds missing required variables without removing existing ones.
Fixes run_id to use infrastructure_validated (which actually has run_id label).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DATASOURCE = {"type": "prometheus", "uid": "prometheus"}

REQUIRED_VARS = {
    "pipeline": {
        "allValue": None,
        "current": {},
        "datasource": DATASOURCE,
        "definition": "label_values(bioetl_records_processed_total, pipeline)",
        "hide": 0,
        "includeAll": True,
        "label": "Pipeline",
        "multi": True,
        "name": "pipeline",
        "options": [],
        "query": {
            "query": "label_values(bioetl_records_processed_total, pipeline)",
            "refId": "StandardVariableQuery",
        },
        "refresh": 1,
        "regex": "",
        "skipUrlSync": False,
        "sort": 1,
        "tagValuesQuery": "",
        "tags": [],
        "tagsQuery": "",
        "type": "query",
        "useTags": False,
    },
    "run_id": {
        "allValue": ".*",
        "current": {"selected": True, "text": "All", "value": "$__all"},
        "datasource": DATASOURCE,
        "definition": 'label_values(bioetl_infrastructure_validated{pipeline=~"$pipeline"}, run_id)',
        "hide": 0,
        "includeAll": True,
        "label": "Run ID",
        "multi": False,
        "name": "run_id",
        "options": [],
        "query": {
            "query": 'label_values(bioetl_infrastructure_validated{pipeline=~"$pipeline"}, run_id)',
            "refId": "StandardVariableQuery",
        },
        "refresh": 2,
        "regex": "",
        "skipUrlSync": False,
        "sort": 3,
        "type": "query",
    },
}


def fix_dashboard(path: Path) -> None:
    """Fix dashboard variables using merge strategy."""
    sys.stdout.write(f"Processing {path}...\n")
    try:
        with path.open(encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        sys.stderr.write(f"  Error reading {path}: {e}\n")
        return

    existing_vars = data.get("templating", {}).get("list", [])
    existing_names = {v.get("name") for v in existing_vars}

    # Merge: add missing required variables, fix existing ones
    for req_name, req_var in REQUIRED_VARS.items():
        if req_name in existing_names:
            # Update existing variable
            for i, v in enumerate(existing_vars):
                if v.get("name") == req_name:
                    existing_vars[i] = req_var
                    sys.stdout.write(f"  Updated variable: {req_name}\n")
                    break
        else:
            existing_vars.append(req_var)
            sys.stdout.write(f"  Added variable: {req_name}\n")

    # Remove duplicates (keep first occurrence)
    seen: set[str] = set()
    deduped = []
    for v in existing_vars:
        name = v.get("name")
        if name not in seen:
            seen.add(name)
            deduped.append(v)
    data["templating"]["list"] = deduped

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    sys.stdout.write(f"  Done ({len(deduped)} variables)\n")


if __name__ == "__main__":
    dashboard_dir = Path("grafana/dashboards")
    for file in sorted(dashboard_dir.glob("*.json")):
        fix_dashboard(file)
