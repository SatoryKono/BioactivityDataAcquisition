"""Script to inject Grafana variables and fix PromQL queries for BioETL pipelines."""

import json
import re
from pathlib import Path

PIPELINE_VAR = {
    "allValue": None,
    "current": {},
    "datasource": "Prometheus",
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
}

RUN_ID_VAR = {
    "allValue": None,
    "current": {},
    "datasource": "Prometheus",
    "definition": 'label_values(bioetl_records_processed_total{pipeline=~"$pipeline"}, run_id)',
    "hide": 0,
    "includeAll": True,
    "label": "Run ID",
    "multi": True,
    "name": "run_id",
    "options": [],
    "query": {
        "query": 'label_values(bioetl_records_processed_total{pipeline=~"$pipeline"}, run_id)',
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
}


def fix_dashboard(path):
    print(f"Processing {path}...")
    try:
        # Use utf-8-sig to handle possible BOM
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return

    # 1. Add variables
    data["templating"]["list"] = [PIPELINE_VAR, RUN_ID_VAR]

    # 2. Update PromQL queries
    panels = data.get("panels", [])
    for row in data.get("rows", []):
        panels.extend(row.get("panels", []))

    for panel in panels:
        targets = panel.get("targets", [])
        if not targets:
            continue

        for target in targets:
            expr = target.get("expr", "")
            if not expr or ("bioetl_" not in expr):
                continue

            # Complex replacement:
            metrics_found = re.findall(r"bioetl_[a-z0-9_]+", expr)
            new_expr = expr

            for m in metrics_found:
                # If metric already has $pipeline filter, skip it
                if "$pipeline" in new_expr:
                    continue

                if f"{m}{{" in new_expr:
                    new_expr = new_expr.replace(
                        f"{m}{{", f'{m}{{pipeline=~"$pipeline", run_id=~"$run_id", '
                    )
                else:
                    new_expr = new_expr.replace(
                        m, f'{m}{{pipeline=~"$pipeline", run_id=~"$run_id"}}'
                    )

            new_expr = new_expr.replace(", }", "}").replace(",,", ",")
            target["expr"] = new_expr

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


if __name__ == "__main__":
    dashboard_dir = Path("grafana/dashboards")
    for file in dashboard_dir.glob("*.json"):
        fix_dashboard(file)
