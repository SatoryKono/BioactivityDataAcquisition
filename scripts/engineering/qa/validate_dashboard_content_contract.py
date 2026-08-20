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
        "indicator",
    }
)
NON_DATA_ROLES = frozenset({"navigation", "row_group", "guidance"})
FULL_SURFACE_COVERAGE_POLICY = "all_shipped_panels"
ALLOWED_EMPTY_STATE_CLASSES = frozenset(
    {"event_empty", "telemetry_missing", "unsupported", "select_run"}
)


def _load_mapping(path: Path) -> dict[str, object]:
    """Загрузить YAML mapping или вернуть понятную ошибку контракта."""
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    safe_path = resolve_output_path(path, root=REPO_ROOT)
    payload = yaml.safe_load(
        safe_path.read_text(encoding="utf-8")  # NOSONAR -- confined above
    )
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
        entry, error = _inventory_dashboard_entry(dashboard)
        if error is not None:
            errors.append(error)
            continue
        assert entry is not None
        uid, key_panels = entry
        errors.extend(_add_inventory_panels(uid, key_panels, records))
    return records, errors


def _inventory_dashboard_entry(
    dashboard: object,
) -> tuple[tuple[str, list[object]] | None, str | None]:
    if not isinstance(dashboard, dict):
        return None, "dashboard-inventory.yaml: dashboard entry must be a mapping"
    uid = dashboard.get("uid")
    if not isinstance(uid, str) or not uid:
        return None, "dashboard-inventory.yaml: dashboard uid must be a string"
    key_panels = dashboard.get("key_panels")
    if not isinstance(key_panels, list):
        return None, f"dashboard-inventory.yaml:{uid}: key_panels must be a list"
    return (uid, key_panels), None


def _add_inventory_panels(
    uid: str,
    key_panels: list[object],
    records: dict[tuple[str, str], dict[str, object]],
) -> list[str]:
    errors: list[str] = []
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
    return errors


def _contract_panel_records(
    contract: dict[str, object],
) -> tuple[dict[tuple[str, str], dict[str, object]], list[str]]:
    records: dict[tuple[str, str], dict[str, object]] = {}
    errors: list[str] = []
    dashboards = contract.get("dashboards")
    if not isinstance(dashboards, dict):
        return records, ["panel-content-contract.yaml: dashboards must be a mapping"]
    for uid, dashboard in dashboards.items():
        panels, error = _contract_dashboard_panels(uid, dashboard)
        if error is not None:
            errors.append(error)
            continue
        assert isinstance(uid, str) and panels is not None
        errors.extend(_add_contract_panels(uid, panels, records))
    return records, errors


def _contract_dashboard_panels(
    uid: object, dashboard: object
) -> tuple[dict[object, object] | None, str | None]:
    if not isinstance(uid, str) or not isinstance(dashboard, dict):
        return None, "panel-content-contract.yaml: dashboard entry must be a mapping"
    panels = dashboard.get("panels")
    if not isinstance(panels, dict):
        return None, f"panel-content-contract.yaml:{uid}: panels must be a mapping"
    return panels, None


def _add_contract_panels(
    uid: str,
    panels: dict[object, object],
    records: dict[tuple[str, str], dict[str, object]],
) -> list[str]:
    errors: list[str] = []
    for panel_id, panel in panels.items():
        if not isinstance(panel_id, str) or not isinstance(panel, dict):
            errors.append(f"panel-content-contract.yaml:{uid}: malformed panel entry")
            continue
        key = (uid, panel_id)
        if key in records:
            errors.append(
                f"panel-content-contract.yaml:{uid}:{panel_id}: duplicate panel"
            )
            continue
        records[key] = panel
    return errors


def _dashboard_panel_records() -> tuple[
    dict[tuple[str, str], dict[str, object]], list[str]
]:
    records: dict[tuple[str, str], dict[str, object]] = {}
    errors: list[str] = []
    for dashboard_path in sorted(DASHBOARD_DIR.glob("*.json")):
        loaded, error = _load_dashboard_payload(dashboard_path)
        if error is not None:
            errors.append(error)
            continue
        assert loaded is not None
        uid, payload = loaded
        errors.extend(_add_dashboard_panels(uid, payload, records))
    return records, errors


def _load_dashboard_payload(
    dashboard_path: Path,
) -> tuple[tuple[str, dict[str, object]] | None, str | None]:
    try:
        payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{dashboard_path}: invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, f"{dashboard_path}: expected JSON object"
    uid = payload.get("uid")
    if not isinstance(uid, str):
        return None, f"{dashboard_path}: missing dashboard uid"
    return (uid, payload), None


def _add_dashboard_panels(
    uid: str,
    payload: dict[str, object],
    records: dict[tuple[str, str], dict[str, object]],
) -> list[str]:
    errors: list[str] = []
    for panel in _iter_panels(payload):
        panel_id = panel.get("id")
        title = panel.get("title")
        if not isinstance(panel_id, int) or not isinstance(title, str):
            continue
        key = (uid, str(panel_id))
        if key in records:
            errors.append(f"duplicate shipped panel id: {uid}:{panel_id}")
            continue
        records[key] = panel
    return errors


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


def _is_navigation_bus_panel(key: tuple[str, str], panel: dict[str, object]) -> bool:
    return (
        key == ("bioetl-overview-v2", "1000")
        and panel.get("type") == "text"
        and panel.get("title") == ""
    )


def _declared_value_errors(
    *,
    prefix: str,
    key: tuple[str, str],
    record: dict[str, object],
    dashboard_panel: dict[str, object],
    expected_title: str,
    allowed_roles: set[str],
    allowed_scopes: set[str],
    allowed_evidence_sources: set[str],
    allowed_states: set[str],
) -> list[str]:
    errors: list[str] = []
    role = record.get("role")
    navigation_bus = _is_navigation_bus_panel(key, dashboard_panel)
    if record.get("title") != expected_title and not navigation_bus:
        errors.append(f"{prefix}: title does not match dashboard JSON")
    if role not in allowed_roles:
        errors.append(f"{prefix}: role must be one of the declared allowed_roles")
    if navigation_bus and role != "navigation":
        errors.append(f"{prefix}: navigation bus must declare navigation role")
    tier = record.get("tier")
    if not isinstance(tier, int) or tier not in {1, 2, 3, 4}:
        errors.append(f"{prefix}: tier must be an integer from 1 to 4")
    scope = record.get("scope")
    if scope not in allowed_scopes:
        errors.append(f"{prefix}: scope must be one of the declared allowed_scopes")
    scope_class = record.get("scope_class", scope)
    if scope_class not in allowed_scopes:
        errors.append(
            f"{prefix}: scope_class must be one of the declared allowed_scopes"
        )
    elif scope_class != scope:
        errors.append(f"{prefix}: scope_class must match scope (scope is the SSOT)")
    if record.get("evidence_source") not in allowed_evidence_sources:
        errors.append(
            f"{prefix}: evidence_source must be one of the declared allowed_evidence_sources"
        )
    state_model = _string_list(record.get("state_model"))
    if not state_model or not set(state_model).issubset(allowed_states):
        errors.append(f"{prefix}: state_model must be a non-empty declared state list")
    return errors


def _fixture_contract_errors(*, prefix: str, record: dict[str, object]) -> list[str]:
    errors: list[str] = []
    role = record.get("role")
    required_copy = _string_list(record.get("required_copy"))
    if not required_copy:
        errors.append(f"{prefix}: required_copy must be a non-empty list")
    elif role not in NON_DATA_ROLES and not REQUIRED_COPY_TOKENS.issubset(
        required_copy
    ):
        errors.append(
            f"{prefix}: required_copy must include evidence_scope and no_data"
        )
    elif role in ACTION_REQUIRED_ROLES and "next_action" not in required_copy:
        errors.append(f"{prefix}: role {role!r} must include next_action copy")
    if not _string_list(record.get("fixture_cases")):
        errors.append(f"{prefix}: fixture_cases must be a non-empty list")
    if not _string_list(record.get("render_profiles")):
        errors.append(f"{prefix}: render_profiles must be a non-empty list")
    if role in {"identity_table", "accounting_table"} and not _string_list(
        record.get("required_columns")
    ):
        errors.append(f"{prefix}: table role requires required_columns")
    return errors


def _empty_state_errors(*, prefix: str, record: dict[str, object]) -> list[str]:
    role = record.get("role")
    evidence_source = record.get("evidence_source")
    empty_state_class = record.get("empty_state_class")
    if role in NON_DATA_ROLES:
        if empty_state_class in {None, "unsupported"}:
            return []
        return [
            f"{prefix}: non-data role empty_state_class must be unsupported or omitted"
        ]
    errors: list[str] = []
    if empty_state_class not in ALLOWED_EMPTY_STATE_CLASSES:
        errors.append(
            f"{prefix}: empty_state_class must be one of "
            f"{sorted(ALLOWED_EMPTY_STATE_CLASSES)}"
        )
    if record.get("scope") == "selected_run" and evidence_source != "ops_http":
        errors.append(
            f"{prefix}: data-bearing selected_run must use evidence_source=ops_http"
        )
    return errors


def _validate_panel_record(
    *,
    key: tuple[str, str],
    record: dict[str, object],
    dashboard_panel: dict[str, object],
    expected_title: str,
    allowed_roles: set[str],
    allowed_scopes: set[str],
    allowed_evidence_sources: set[str],
    allowed_states: set[str],
) -> list[str]:
    uid, panel_id = key
    prefix = f"panel-content-contract.yaml:{uid}:{panel_id}"
    errors = _declared_value_errors(
        prefix=prefix,
        key=key,
        record=record,
        dashboard_panel=dashboard_panel,
        expected_title=expected_title,
        allowed_roles=allowed_roles,
        allowed_scopes=allowed_scopes,
        allowed_evidence_sources=allowed_evidence_sources,
        allowed_states=allowed_states,
    )
    errors.extend(_fixture_contract_errors(prefix=prefix, record=record))
    errors.extend(_empty_state_errors(prefix=prefix, record=record))
    return errors


def _contract_policy_errors(contract: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema_version") != 2:
        errors.append("panel-content-contract.yaml: schema_version must equal 2")
    if contract.get("coverage_policy") != FULL_SURFACE_COVERAGE_POLICY:
        errors.append(
            "panel-content-contract.yaml: coverage_policy must equal all_shipped_panels"
        )
    return errors


def _allowed_value_sets(
    contract: dict[str, object],
) -> tuple[set[str], set[str], set[str], set[str], list[str]]:
    roles = set(_string_list(contract.get("allowed_roles")) or [])
    scopes = set(_string_list(contract.get("allowed_scopes")) or [])
    evidence_sources = set(_string_list(contract.get("allowed_evidence_sources")) or [])
    states = set(_string_list(contract.get("allowed_states")) or [])
    errors: list[str] = []
    if not all((roles, scopes, evidence_sources, states)):
        errors.append(
            "panel-content-contract.yaml: declared allowed value lists must be non-empty"
        )
    return roles, scopes, evidence_sources, states, errors


def _inventory_alignment_errors(
    inventory_records: dict[tuple[str, str], dict[str, object]],
    dashboard_records: dict[tuple[str, str], dict[str, object]],
) -> list[str]:
    errors: list[str] = []
    for key, inventory_panel in sorted(inventory_records.items()):
        dashboard_panel = dashboard_records.get(key)
        if dashboard_panel is None:
            errors.append(
                f"dashboard-inventory.yaml:{key[0]}:{key[1]}: panel is missing"
            )
            continue
        title_matches = dashboard_panel.get("title") == inventory_panel.get("title")
        if not title_matches and not _is_navigation_bus_panel(key, dashboard_panel):
            errors.append(
                f"dashboard-inventory.yaml:{key[0]}:{key[1]}: "
                "title does not match dashboard JSON"
            )
    return errors


def _shipped_panel_contract_errors(
    *,
    dashboard_records: dict[tuple[str, str], dict[str, object]],
    contract_records: dict[tuple[str, str], dict[str, object]],
    allowed_roles: set[str],
    allowed_scopes: set[str],
    allowed_evidence_sources: set[str],
    allowed_states: set[str],
) -> list[str]:
    errors: list[str] = []
    for key, dashboard_panel in sorted(dashboard_records.items()):
        record = contract_records.get(key)
        if record is None:
            errors.append(
                f"panel-content-contract.yaml:{key[0]}:{key[1]}: missing shipped panel"
            )
            continue
        title = dashboard_panel.get("title")
        assert isinstance(title, str)
        errors.extend(
            _validate_panel_record(
                key=key,
                record=record,
                dashboard_panel=dashboard_panel,
                expected_title=title,
                allowed_roles=allowed_roles,
                allowed_scopes=allowed_scopes,
                allowed_evidence_sources=allowed_evidence_sources,
                allowed_states=allowed_states,
            )
        )
    return errors


def _unshipped_contract_errors(
    contract_records: dict[tuple[str, str], dict[str, object]],
    dashboard_records: dict[tuple[str, str], dict[str, object]],
) -> list[str]:
    return [
        f"panel-content-contract.yaml:{key[0]}:{key[1]}: panel is not shipped"
        for key in sorted(set(contract_records) - set(dashboard_records))
    ]


def validate_content_contract(
    inventory_path: Path = INVENTORY_PATH,
    content_contract_path: Path = CONTENT_CONTRACT_PATH,
) -> list[str]:
    """Вернуть полный список детерминированных нарушений content contract."""
    inventory = _load_mapping(inventory_path)
    contract = _load_mapping(content_contract_path)
    errors = _contract_policy_errors(contract)
    (
        allowed_roles,
        allowed_scopes,
        allowed_evidence_sources,
        allowed_states,
        allowed_value_errors,
    ) = _allowed_value_sets(contract)
    errors.extend(allowed_value_errors)
    inventory_records, inventory_errors = _inventory_key_panels(inventory)
    contract_records, contract_errors = _contract_panel_records(contract)
    errors.extend(inventory_errors)
    errors.extend(contract_errors)
    dashboard_records, dashboard_errors = _dashboard_panel_records()
    errors.extend(dashboard_errors)
    errors.extend(_inventory_alignment_errors(inventory_records, dashboard_records))
    errors.extend(
        _shipped_panel_contract_errors(
            dashboard_records=dashboard_records,
            contract_records=contract_records,
            allowed_roles=allowed_roles,
            allowed_scopes=allowed_scopes,
            allowed_evidence_sources=allowed_evidence_sources,
            allowed_states=allowed_states,
        )
    )
    errors.extend(_unshipped_contract_errors(contract_records, dashboard_records))
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
