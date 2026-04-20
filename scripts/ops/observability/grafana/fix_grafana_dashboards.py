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


def _load_dashboard(path: Path) -> dict[str, object] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(f"Error reading {path}: {exc}")
        return None


def _dashboard_panels(data: dict[str, object]) -> list[dict[str, object]]:
    panels = list(data.get("panels", []))
    for row in data.get("rows", []):
        if isinstance(row, dict):
            panels.extend(row.get("panels", []))
    return [panel for panel in panels if isinstance(panel, dict)]


def _rewrite_promql_expr(expr: str) -> str:
    if not expr or "bioetl_" not in expr or "$pipeline" in expr:
        return expr

    new_expr = expr
    for metric in re.findall(r"bioetl_[a-z0-9_]+", expr):
        if f"{metric}{{" in new_expr:
            new_expr = new_expr.replace(
                f"{metric}{{",
                f'{metric}{{pipeline=~"$pipeline", run_id=~"$run_id", ',
            )
            continue
        new_expr = new_expr.replace(
            metric,
            f'{metric}{{pipeline=~"$pipeline", run_id=~"$run_id"}}',
        )
    return new_expr.replace(", }", "}").replace(",,", ",")


def _rewrite_panel_targets(panel: dict[str, object]) -> None:
    targets = panel.get("targets", [])
    if not isinstance(targets, list):
        return
    for target in targets:
        if not isinstance(target, dict):
            continue
        expr = target.get("expr", "")
        if isinstance(expr, str):
            target["expr"] = _rewrite_promql_expr(expr)


def _write_dashboard(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")


def fix_dashboard(path):
    print(f"Processing {path}...")
    data = _load_dashboard(path)
    if data is None:
        return

    data["templating"]["list"] = [PIPELINE_VAR, RUN_ID_VAR]
    for panel in _dashboard_panels(data):
        _rewrite_panel_targets(panel)
    _write_dashboard(path, data)


if __name__ == "__main__":
    dashboard_dir = Path("grafana/dashboards")
    for file in dashboard_dir.glob("*.json"):
        fix_dashboard(file)
