#!/usr/bin/env python3
"""Emit static panel audit matrix for shipped Grafana dashboards."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = ROOT / "grafana" / "dashboards"
INVENTORY_CONTRACT = (
    ROOT
    / "docs"
    / "03-guides"
    / "dashboards"
    / "contracts"
    / "dashboard-inventory.yaml"
)
CONTENT_CONTRACT = (
    ROOT
    / "docs"
    / "03-guides"
    / "dashboards"
    / "contracts"
    / "panel-content-contract.yaml"
)
HTTP_DATASOURCE_HINTS = (
    "quarantine explorer",
    "bioetl ops http",
    "bioetl-ops-http",
    "infinity",
)


def expected_panel_count_from_inventory(
    inventory_path: Path = INVENTORY_CONTRACT,
) -> int:
    """Sum `panel_count` for every shipped UID in the inventory contract."""
    payload = yaml.safe_load(inventory_path.read_text(encoding="utf-8"))
    dashboards = payload.get("dashboards", []) if isinstance(payload, dict) else []
    total = 0
    for entry in dashboards:
        if isinstance(entry, dict) and isinstance(entry.get("panel_count"), int):
            total += int(entry["panel_count"])
    return total


# Derived from dashboard-inventory.yaml. Do not hardcode a stale baseline.
EXPECTED_PANEL_COUNT = expected_panel_count_from_inventory()


def _content_contract_by_panel(
    content_contract_path: Path = CONTENT_CONTRACT,
) -> dict[tuple[str, str], dict[str, object]]:
    """Вернуть content contract records, индексированные по UID и panel ID."""
    payload = yaml.safe_load(content_contract_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{content_contract_path}: expected YAML mapping")
    dashboards = payload.get("dashboards", {})
    if not isinstance(dashboards, dict):
        raise ValueError(f"{content_contract_path}: dashboards must be a mapping")
    records: dict[tuple[str, str], dict[str, object]] = {}
    for uid, dashboard in dashboards.items():
        if not isinstance(uid, str) or not isinstance(dashboard, dict):
            continue
        panels = dashboard.get("panels", {})
        if not isinstance(panels, dict):
            continue
        for panel_id, record in panels.items():
            if isinstance(panel_id, str) and isinstance(record, dict):
                records[(uid, panel_id)] = record
    return records


def _contract_string_list(value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return []
    return list(value)


def _joined_contract_list(value: object) -> str:
    return ",".join(_contract_string_list(value))


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


def _contract_field(record: dict[str, object] | None, field: str) -> object:
    return record.get(field) if record is not None else None


def _panel_audit_row(
    *,
    dashboard_path: Path,
    uid: str,
    panel: dict[str, object],
    content_record: dict[str, object] | None,
) -> dict[str, str]:
    panel_id = str(panel.get("id", ""))
    title = str(panel.get("title", ""))
    normalized_title = title.strip().lower()
    expr_blob = " | ".join(_panel_exprs(panel))
    covered = content_record is not None
    return {
        "dashboard_uid": uid,
        "dashboard_file": dashboard_path.name,
        "panel_id": panel_id,
        "panel_title": title,
        "panel_type": str(panel.get("type", "")),
        "content_contract_status": "covered" if covered else "missing",
        "eligible": "true",
        "enrolled": "true" if covered else "false",
        "coverage_reason": "all_shipped_panels" if covered else "missing_shipped_panel",
        "content_role": str(_contract_field(content_record, "role") or ""),
        "content_tier": str(_contract_field(content_record, "tier") or ""),
        "content_scope": str(_contract_field(content_record, "scope") or ""),
        "content_state_model": _joined_contract_list(
            _contract_field(content_record, "state_model")
        ),
        "fixture_case_count": str(
            len(_contract_string_list(_contract_field(content_record, "fixture_cases")))
        ),
        "render_profile_count": str(
            len(
                _contract_string_list(
                    _contract_field(content_record, "render_profiles")
                )
            )
        ),
        "datasource_kind": _datasource_kind(panel),
        "uses_run_id_in_promql": str("run_id=" in expr_blob),
        "uses_run_type_in_promql": str(
            "run_type=~" in expr_blob or 'run_type="' in expr_blob
        ),
        "is_identity_panel": str(normalized_title == "id"),
        "is_processed_records_panel": str(normalized_title == "processed records"),
        "is_provider_status_panel": str(
            normalized_title == "status" and uid == "bioetl-provider-health-v2"
        ),
        "query_preview": expr_blob[:500],
        "live_audit_status": "not_run",
        "live_classification": "",
        "render_status": "not_run",
    }


def _collect_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    content_contract = _content_contract_by_panel()
    for dashboard_path in sorted(DASHBOARD_DIR.glob("*.json")):
        if dashboard_path.name.endswith(".backup"):
            continue
        payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
        uid = str(payload.get("uid", dashboard_path.stem))
        for panel in _iter_panels(payload):
            panel_id = str(panel.get("id", ""))
            content_record = content_contract.get((uid, panel_id))
            rows.append(
                _panel_audit_row(
                    dashboard_path=dashboard_path,
                    uid=uid,
                    panel=panel,
                    content_record=content_record,
                )
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

    try:
        rows = _collect_rows()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"panel audit matrix error: {exc}", file=sys.stderr)
        return 1
    # Includes collapsed row headers. Expected count is the YAML inventory sum.
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
