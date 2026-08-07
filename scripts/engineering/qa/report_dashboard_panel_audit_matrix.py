#!/usr/bin/env python3
"""Emit static panel audit matrix for shipped Grafana dashboards."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = ROOT / "grafana" / "dashboards"
HTTP_DATASOURCE_HINTS = (
    "quarantine explorer",
    "bioetl ops http",
    "bioetl-ops-http",
    "infinity",
)
EXPECTED_PANEL_COUNT = 218


def _iter_panels(payload: dict[str, object]) -> list[dict[str, object]]:
    panels: list[dict[str, object]] = []
    raw_panels = payload.get("panels", [])
    stack = (
        [panel for panel in raw_panels if isinstance(panel, dict)]
        if isinstance(raw_panels, list)
        else []
    )
    while stack:
        panel = stack.pop(0)
        panels.append(panel)
        nested = panel.get("panels", [])
        if isinstance(nested, list):
            stack[0:0] = [item for item in nested if isinstance(item, dict)]
    return panels


def _datasource_kind(panel: dict[str, object]) -> str:
    datasource = panel.get("datasource")
    if isinstance(datasource, dict):
        ds_type = str(datasource.get("type", "")).lower()
        ds_uid = str(datasource.get("uid", "")).lower()
        if ds_type == "prometheus" or "prometheus" in ds_uid:
            return "prometheus"
        if ds_type in {"yesoreyeram-infinity-datasource", "infinity"}:
            return "http"
        name = str(datasource.get("uid", datasource.get("type", ""))).lower()
        if any(hint in name for hint in HTTP_DATASOURCE_HINTS):
            return "http"
        return ds_type or "unknown"
    if isinstance(datasource, str):
        lowered = datasource.lower()
        if "prometheus" in lowered:
            return "prometheus"
        if any(hint in lowered for hint in HTTP_DATASOURCE_HINTS):
            return "http"
    return "unknown"


def _panel_exprs(panel: dict[str, object]) -> list[str]:
    exprs: list[str] = []
    raw_targets = panel.get("targets", [])
    if not isinstance(raw_targets, list):
        return exprs
    for target in raw_targets:
        if not isinstance(target, dict):
            continue
        expr = target.get("expr")
        if isinstance(expr, str) and expr.strip():
            exprs.append(expr.strip())
        url = target.get("url")
        if isinstance(url, str) and url.strip():
            exprs.append(url.strip())
    return exprs


def _collect_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for dashboard_path in sorted(DASHBOARD_DIR.glob("*.json")):
        if dashboard_path.name.endswith(".backup"):
            continue
        payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
        uid = str(payload.get("uid", dashboard_path.stem))
        for panel in _iter_panels(payload):
            panel_type = str(panel.get("type", ""))
            panel_id = str(panel.get("id", ""))
            title = str(panel.get("title", ""))
            exprs = _panel_exprs(panel)
            expr_blob = " | ".join(exprs)
            rows.append(
                {
                    "dashboard_uid": uid,
                    "dashboard_file": dashboard_path.name,
                    "panel_id": panel_id,
                    "panel_title": title,
                    "panel_type": panel_type,
                    "datasource_kind": _datasource_kind(panel),
                    "uses_run_id_in_promql": str("run_id=" in expr_blob),
                    "uses_run_type_in_promql": str(
                        "run_type=~" in expr_blob or 'run_type="' in expr_blob
                    ),
                    "is_identity_panel": str(title.strip().lower() == "id"),
                    "is_processed_records_panel": str(
                        title.strip().lower() == "processed records"
                    ),
                    "is_provider_status_panel": str(
                        title.strip().lower() == "status"
                        and uid == "bioetl-provider-health-v2"
                    ),
                    "query_preview": expr_blob[:500],
                    "live_audit_status": "not_run",
                    "live_classification": "",
                    "render_status": "not_run",
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
        / "grafana"
        / "panel_audit_static.csv",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    rows = _collect_rows()
    # Includes collapsed row headers in shipped JSON. Reconciled against the
    # seven-dashboard inventory and live audit on 2026-08-07 (#8269).
    if args.check and len(rows) != EXPECTED_PANEL_COUNT:
        print(
            f"panel count mismatch: expected {EXPECTED_PANEL_COUNT}, got {len(rows)}",
            file=sys.stderr,
        )
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} panel rows -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
