#!/usr/bin/env python3
"""Report PromQL scope coverage (run_type / deprecated metrics) for shipped dashboards."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = ROOT / "grafana" / "dashboards"
ALLOWLIST_PATH = ROOT / "configs" / "quality" / "dashboard_promql_scope_allowlist.yaml"
DEPRECATED_METRIC_TOKENS = ("checkpoint_saved_at_epoch_seconds",)


def _load_allowlist() -> tuple[frozenset[str], frozenset[str]]:
    payload = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    metrics = frozenset(
        str(item) for item in payload.get("metrics_without_run_type_label", [])
    )
    dashboards = frozenset(
        str(item) for item in payload.get("pipeline_summary_dashboards", [])
    )
    return metrics, dashboards


def _panel_queries(panel: dict[str, object]) -> list[tuple[str, str]]:
    title = str(panel.get("title", ""))
    rows: list[tuple[str, str]] = []
    for target in panel.get("targets", []):
        if not isinstance(target, dict):
            continue
        expr = target.get("expr", "")
        if isinstance(expr, str) and expr.strip():
            rows.append((title, expr))
    if panel.get("type") == "row":
        for nested in panel.get("panels", []):
            if isinstance(nested, dict):
                rows.extend(_panel_queries(nested))
    return rows


def _collect_rows() -> list[dict[str, str]]:
    _, pipeline_summary = _load_allowlist()
    rows: list[dict[str, str]] = []
    for dashboard_path in sorted(DASHBOARD_DIR.glob("*.json")):
        if dashboard_path.name.endswith(".backup"):
            continue
        dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
        for panel in dashboard.get("panels", []):
            if not isinstance(panel, dict):
                continue
            for title, expr in _panel_queries(panel):
                uses_run_type = "run_type=~" in expr or 'run_type="' in expr
                uses_run_id = "run_id=" in expr
                deprecated = any(token in expr for token in DEPRECATED_METRIC_TOKENS)
                rows.append(
                    {
                        "dashboard": dashboard_path.name,
                        "panel_title": title,
                        "uses_run_type_in_promql": str(uses_run_type),
                        "uses_run_id_in_promql": str(uses_run_id),
                        "deprecated_metric_token": str(deprecated),
                        "pipeline_summary_family": str(
                            dashboard_path.name in pipeline_summary
                        ),
                    }
                )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "reports"
        / "observability"
        / "dashboard-promql-scope-matrix.csv",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    rows = _collect_rows()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "dashboard",
                "panel_title",
                "uses_run_type_in_promql",
                "uses_run_id_in_promql",
                "deprecated_metric_token",
                "pipeline_summary_family",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    if args.check and not _check_promql_scope_rows(rows):
        return 1
    print(f"Wrote {len(rows)} rows to {args.output}")
    return 0


def _print_hit_sample(label: str, hits: list[dict[str, str]]) -> None:
    print(label, file=sys.stderr)
    for row in hits[:10]:
        print(f"  {row['dashboard']} :: {row['panel_title']}", file=sys.stderr)


def _check_promql_scope_rows(rows: list[dict[str, str]]) -> bool:
    deprecated_hits = [row for row in rows if row["deprecated_metric_token"] == "True"]
    run_id_hits = [row for row in rows if row["uses_run_id_in_promql"] == "True"]
    if not deprecated_hits and not run_id_hits:
        return True
    if deprecated_hits:
        _print_hit_sample(
            "Deprecated metric tokens found in dashboard PromQL:", deprecated_hits
        )
    if run_id_hits:
        _print_hit_sample("run_id used in PromQL (forbidden):", run_id_hits)
    return False


if __name__ == "__main__":
    raise SystemExit(main())
