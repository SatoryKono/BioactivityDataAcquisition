#!/usr/bin/env python3
"""Проверить content contract ключевых Grafana-панелей fail-closed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = ROOT / "grafana" / "dashboards"
CONTRACT_DIR = ROOT / "docs" / "03-guides" / "dashboards" / "contracts"
INVENTORY_PATH = CONTRACT_DIR / "dashboard-inventory.yaml"
CONTENT_CONTRACT_PATH = CONTRACT_DIR / "panel-content-contract.yaml"
REQUIRED_COPY_TOKENS = frozenset({"evidence_scope", "no_data"})
ACTION_REQUIRED_ROLES = frozenset(
    {
        "verdict",
        "confidence",
        "next_action",
        "severity_table",
        "causes_table",
        "freshness",
    }
)


def _load_mapping(path: Path) -> dict[str, object]:
    """Загрузить YAML mapping или вернуть понятную ошибку контракта."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected YAML mapping")
    return payload


def _string_list(value: object) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return list(value)


def _inventory_key_panels(
    inventory: dict[str, object],
) -> tuple[dict[tuple[str, str], dict[str, object]], list[str]]:
    records: dict[tuple[str, str], dict[str, object]] = {}
    errors: list[str] = []
    dashboards = inventory.get("dashboards")
    if not isinstance(dashboards, list):
        return records, ["dashboard-inventory.yaml: dashboards must be a list"]
    for dashboard in dashboards:
        if not isinstance(dashboard, dict):
            errors.append("dashboard-inventory.yaml: dashboard entry must be a mapping")
            continue
        uid = dashboard.get("uid")
        key_panels = dashboard.get("key_panels")
        if not isinstance(uid, str) or not uid:
            errors.append("dashboard-inventory.yaml: dashboard uid must be a string")
            continue
        if not isinstance(key_panels, list):
            errors.append(f"dashboard-inventory.yaml:{uid}: key_panels must be a list")
            continue
        for panel in key_panels:
            if not isinstance(panel, dict):
                errors.append(
                    f"dashboard-inventory.yaml:{uid}: key panel must be a mapping"
                )
                continue
            panel_id = panel.get("id")
            title = panel.get("title")
            if not isinstance(panel_id, int) or not isinstance(title, str) or not title:
                errors.append(
                    f"dashboard-inventory.yaml:{uid}: key panel needs integer id and title"
                )
                continue
            key = (uid, str(panel_id))
            if key in records:
                errors.append(
                    f"dashboard-inventory.yaml:{uid}:{panel_id}: duplicate key panel"
                )
                continue
            records[key] = panel
    return records, errors


def _contract_panel_records(
    contract: dict[str, object],
) -> tuple[dict[tuple[str, str], dict[str, object]], list[str]]:
    records: dict[tuple[str, str], dict[str, object]] = {}
    errors: list[str] = []
    dashboards = contract.get("dashboards")
    if not isinstance(dashboards, dict):
        return records, ["panel-content-contract.yaml: dashboards must be a mapping"]
    for uid, dashboard in dashboards.items():
        if not isinstance(uid, str) or not isinstance(dashboard, dict):
            errors.append(
                "panel-content-contract.yaml: dashboard entry must be a mapping"
            )
            continue
        panels = dashboard.get("panels")
        if not isinstance(panels, dict):
            errors.append(
                f"panel-content-contract.yaml:{uid}: panels must be a mapping"
            )
            continue
        for panel_id, panel in panels.items():
            if not isinstance(panel_id, str) or not isinstance(panel, dict):
                errors.append(
                    f"panel-content-contract.yaml:{uid}: malformed panel entry"
                )
                continue
            key = (uid, panel_id)
            if key in records:
                errors.append(
                    f"panel-content-contract.yaml:{uid}:{panel_id}: duplicate panel"
                )
                continue
            records[key] = panel
    return records, errors


def _dashboard_panel_titles() -> dict[tuple[str, str], str]:
    titles: dict[tuple[str, str], str] = {}
    for dashboard_path in sorted(DASHBOARD_DIR.glob("*.json")):
        payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        uid = payload.get("uid")
        if not isinstance(uid, str):
            continue
        for panel in _iter_panels(payload):
            panel_id = panel.get("id")
            title = panel.get("title")
            if isinstance(panel_id, int) and isinstance(title, str):
                titles[(uid, str(panel_id))] = title
    return titles


def _iter_panels(payload: dict[str, object]) -> list[dict[str, object]]:
    panels: list[dict[str, object]] = []
    raw_panels = payload.get("panels", [])
    stack = (
        [item for item in raw_panels if isinstance(item, dict)]
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


def _validate_panel_record(
    *,
    key: tuple[str, str],
    record: dict[str, object],
    inventory_panel: dict[str, object],
    dashboard_title: str | None,
    allowed_roles: set[str],
    allowed_scopes: set[str],
    allowed_evidence_sources: set[str],
    allowed_states: set[str],
) -> list[str]:
    uid, panel_id = key
    prefix = f"panel-content-contract.yaml:{uid}:{panel_id}"
    errors: list[str] = []
    expected_title = inventory_panel["title"]
    role = record.get("role")
    if record.get("title") != expected_title:
        errors.append(f"{prefix}: title must match inventory title {expected_title!r}")
    if dashboard_title != expected_title and not (
        role == "navigation" and dashboard_title == ""
    ):
        errors.append(f"{prefix}: title does not match dashboard JSON")
    if role not in allowed_roles:
        errors.append(f"{prefix}: role must be one of the declared allowed_roles")
    tier = record.get("tier")
    if not isinstance(tier, int) or tier not in {1, 2, 3, 4}:
        errors.append(f"{prefix}: tier must be an integer from 1 to 4")
    scope = record.get("scope")
    if scope not in allowed_scopes:
        errors.append(f"{prefix}: scope must be one of the declared allowed_scopes")
    evidence_source = record.get("evidence_source")
    if evidence_source not in allowed_evidence_sources:
        errors.append(
            f"{prefix}: evidence_source must be one of the declared allowed_evidence_sources"
        )
    state_model = _string_list(record.get("state_model"))
    if not state_model or not set(state_model).issubset(allowed_states):
        errors.append(f"{prefix}: state_model must be a non-empty declared state list")
    required_copy = _string_list(record.get("required_copy"))
    if not required_copy:
        errors.append(f"{prefix}: required_copy must be a non-empty list")
    elif role != "navigation" and not REQUIRED_COPY_TOKENS.issubset(required_copy):
        errors.append(
            f"{prefix}: required_copy must include evidence_scope and no_data"
        )
    elif role in ACTION_REQUIRED_ROLES and "next_action" not in required_copy:
        errors.append(f"{prefix}: role {role!r} must include next_action copy")
    fixture_cases = _string_list(record.get("fixture_cases"))
    if not fixture_cases:
        errors.append(f"{prefix}: fixture_cases must be a non-empty list")
    render_profiles = _string_list(record.get("render_profiles"))
    if not render_profiles:
        errors.append(f"{prefix}: render_profiles must be a non-empty list")
    if role in {"identity_table", "accounting_table"}:
        required_columns = _string_list(record.get("required_columns"))
        if not required_columns:
            errors.append(f"{prefix}: table role requires required_columns")
    return errors


def validate_content_contract(
    inventory_path: Path = INVENTORY_PATH,
    content_contract_path: Path = CONTENT_CONTRACT_PATH,
) -> list[str]:
    """Вернуть полный список детерминированных нарушений content contract."""
    inventory = _load_mapping(inventory_path)
    contract = _load_mapping(content_contract_path)
    errors: list[str] = []
    if contract.get("schema_version") != 1:
        errors.append("panel-content-contract.yaml: schema_version must equal 1")
    allowed_roles = set(_string_list(contract.get("allowed_roles")) or [])
    allowed_scopes = set(_string_list(contract.get("allowed_scopes")) or [])
    allowed_evidence_sources = set(
        _string_list(contract.get("allowed_evidence_sources")) or []
    )
    allowed_states = set(_string_list(contract.get("allowed_states")) or [])
    if not all(
        (allowed_roles, allowed_scopes, allowed_evidence_sources, allowed_states)
    ):
        errors.append(
            "panel-content-contract.yaml: declared allowed value lists must be non-empty"
        )
    inventory_records, inventory_errors = _inventory_key_panels(inventory)
    contract_records, contract_errors = _contract_panel_records(contract)
    errors.extend(inventory_errors)
    errors.extend(contract_errors)
    dashboard_titles = _dashboard_panel_titles()
    for key, inventory_panel in sorted(inventory_records.items()):
        record = contract_records.get(key)
        if record is None:
            errors.append(
                f"panel-content-contract.yaml:{key[0]}:{key[1]}: missing inventory key panel"
            )
            continue
        errors.extend(
            _validate_panel_record(
                key=key,
                record=record,
                inventory_panel=inventory_panel,
                dashboard_title=dashboard_titles.get(key),
                allowed_roles=allowed_roles,
                allowed_scopes=allowed_scopes,
                allowed_evidence_sources=allowed_evidence_sources,
                allowed_states=allowed_states,
            )
        )
    for key in sorted(set(contract_records) - set(inventory_records)):
        errors.append(
            f"panel-content-contract.yaml:{key[0]}:{key[1]}: panel is not an inventory key panel"
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    parser.add_argument("--contract", type=Path, default=CONTENT_CONTRACT_PATH)
    args = parser.parse_args(argv)
    errors = validate_content_contract(args.inventory, args.contract)
    if errors:
        print("dashboard content contract violations:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("dashboard content contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
