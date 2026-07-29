#!/usr/bin/env python3
"""Generate dashboard inventory and verify docs/provisioning/deployment parity.

The command has three complementary modes:

- inventory: shipped dashboard metadata (UID/title/variables/links/tags/root config)
- parity / drift: docs parity plus provisioning and optional deployed snapshot drift
- health summary: per-dashboard local health rollup over canonical contracts
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, TypedDict, cast

import yaml

DASHBOARDS_DIR = Path("grafana/dashboards")
VARIABLES_GUIDE = Path("docs/03-guides/dashboards/variables-guide.md")
MONITORING_INDEX = Path("docs/03-guides/dashboards/monitoring-index.md")
SELECTOR_CONTRACT = Path("docs/03-guides/dashboards/contracts/selector-contracts.yaml")
DASHBOARD_INVENTORY_CONTRACT = Path(
    "docs/03-guides/dashboards/contracts/dashboard-inventory.yaml"
)
PROVISIONING_CONFIG = Path("grafana/provisioning/dashboards/bioetl.yaml")
VOLATILE_ROOT_KEYS = frozenset({"id", "version"})
VOLATILE_PANEL_KEYS = frozenset({"pluginVersion"})
QUARANTINE_EXPLORER_DATASOURCE = "Quarantine Explorer"
DATASOURCE_ORDER = {
    "Prometheus": 0,
    "Loki": 1,
    "Tempo": 2,
    QUARANTINE_EXPLORER_DATASOURCE: 3,
    "Grafana": 4,
}

MANDATORY_LINK_UIDS: dict[str, set[str]] = {
    "bioetl-overview-v2": {
        "bioetl-runtime",
        "bioetl-dq-v2",
        "bioetl-control-plane-v1",
    },
    "bioetl-runtime": {"bioetl-overview-v2", "bioetl-dq-v2", "bioetl-control-plane-v1"},
    "bioetl-provider-health-v2": {
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-control-plane-v1",
        "bioetl-dq-v2",
    },
    "bioetl-dq-v2": {
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-control-plane-v1",
    },
    "bioetl-control-plane-v1": {
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-dq-v2",
    },
}


class DashboardInventoryItem(TypedDict):
    """Typed metadata extracted from one shipped dashboard."""

    file: str
    uid: object
    title: object
    variables: list[str]
    link_uids: list[str]
    tags: list[object]
    style: object
    timezone: object
    refresh: object
    editable: object
    graphTooltip: object
    hideControls: object
    data_sources: list[str]
    panel_count: int
    panel_plugin_versions: list[str]


class DashboardHealthItem(DashboardInventoryItem):
    """Inventory item augmented with local health findings."""

    status: str
    issues: list[str]


class DashboardHealthCounts(TypedDict):
    """Aggregate dashboard health counters."""

    total_dashboards: int
    healthy_dashboards: int
    degraded_dashboards: int
    provisioning_ok: bool
    deployed_dir_used: str | None


class ProvisioningHealth(TypedDict):
    """Provisioning health details included in the summary."""

    status: str
    issues: list[str]
    provider: dict[str, object]


class DashboardHealthSummary(TypedDict):
    """Machine-readable dashboard health summary."""

    overall_status: str
    summary: DashboardHealthCounts
    provisioning: ProvisioningHealth
    dashboards: list[DashboardHealthItem]


def _iter_panels(payload: dict[str, Any]) -> list[dict[str, Any]]:
    panels: list[dict[str, Any]] = []
    stack = list(payload.get("panels", []))
    while stack:
        panel = stack.pop(0)
        if not isinstance(panel, dict):
            continue
        panels.append(panel)
        nested = panel.get("panels", [])
        if isinstance(nested, list):
            stack[0:0] = [item for item in nested if isinstance(item, dict)]
    return panels


def _extract_variables(payload: dict[str, Any]) -> list[str]:
    templating = payload.get("templating", {}).get("list", [])
    names = [f"${item.get('name')}" for item in templating if item.get("name")]
    return sorted(names)


def _extract_link_uids(payload: dict[str, Any]) -> list[str]:
    links = list(payload.get("links", []))
    for panel in payload.get("panels", []):
        if panel.get("id") != 1000:
            continue
        panel_links = panel.get("links", [])
        if isinstance(panel_links, list):
            links.extend(link for link in panel_links if isinstance(link, dict))
    discovered: set[str] = set()
    for link in links:
        url = str(link.get("url", ""))
        matches = re.findall(r"/d/(\w+(?:-\w+)*)", url)
        discovered.update(matches)
    return sorted(discovered)


def _extract_panel_plugin_versions(payload: dict[str, Any]) -> list[str]:
    versions = {
        str(panel.get("pluginVersion"))
        for panel in _iter_panels(payload)
        if panel.get("pluginVersion") is not None
    }
    return sorted(versions)


def _sort_data_sources(names: set[str]) -> list[str]:
    return sorted(names, key=lambda name: (DATASOURCE_ORDER.get(name, 99), name))


def _normalize_datasource_string(value: str) -> str | None:
    stripped = value.strip()
    if not stripped:
        return None
    if stripped == QUARANTINE_EXPLORER_DATASOURCE:
        return QUARANTINE_EXPLORER_DATASOURCE
    if stripped == "-- Grafana --":
        return "Grafana"
    return stripped


def _normalize_datasource_dict(ref: dict[str, object]) -> str | None:
    name = str(ref.get("name", "")).strip()
    uid = str(ref.get("uid", "")).strip().lower()
    kind = str(ref.get("type", "")).strip().lower()

    if name == QUARANTINE_EXPLORER_DATASOURCE or uid == "quarantine-explorer":
        return QUARANTINE_EXPLORER_DATASOURCE
    if kind == "prometheus" or uid == "prometheus":
        return "Prometheus"
    if kind == "loki" or uid == "loki":
        return "Loki"
    if kind == "tempo" or uid == "tempo":
        return "Tempo"
    if kind == "grafana" or uid in {"grafana", "-- grafana --"}:
        return "Grafana"
    return name or uid or kind or None


def _normalize_datasource_ref(ref: object) -> str | None:
    if isinstance(ref, str):
        return _normalize_datasource_string(ref)
    if isinstance(ref, dict):
        return _normalize_datasource_dict(ref)
    return None


def _collect_datasource_refs(node: object, discovered: set[str]) -> None:
    """Recursively collect normalized datasource refs into discovered."""
    if isinstance(node, dict):
        if "datasource" in node:
            normalized = _normalize_datasource_ref(node.get("datasource"))
            if normalized:
                discovered.add(normalized)
        for value in node.values():
            _collect_datasource_refs(value, discovered)
        return
    if isinstance(node, list):
        for item in node:
            _collect_datasource_refs(item, discovered)


def _extract_datasources(payload: dict[str, Any]) -> list[str]:
    discovered: set[str] = set()
    _collect_datasource_refs(payload, discovered)
    return _sort_data_sources(discovered)


def _root_dashboard_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("dashboard"), dict):
        return cast(dict[str, Any], payload["dashboard"])
    return payload


def _normalize_dashboard_node(node: Any, *, is_root: bool = False) -> Any:
    """Drop volatile keys and recursively normalize dashboard JSON nodes."""
    if isinstance(node, dict):
        normalized: dict[str, Any] = {}
        for key, value in node.items():
            if is_root and key in VOLATILE_ROOT_KEYS:
                continue
            if key in VOLATILE_PANEL_KEYS:
                continue
            normalized[key] = _normalize_dashboard_node(value)
        return normalized
    if isinstance(node, list):
        return [_normalize_dashboard_node(item) for item in node]
    return node


def _normalize_dashboard_payload(payload: dict[str, Any]) -> dict[str, Any]:
    dashboard = _root_dashboard_payload(payload)
    return cast(dict[str, Any], _normalize_dashboard_node(dashboard, is_root=True))


def _load_inventory() -> list[DashboardInventoryItem]:
    inventory: list[DashboardInventoryItem] = []
    for path in sorted(DASHBOARDS_DIR.glob("*.json")):
        payload = cast(
            dict[str, Any],
            json.loads(path.read_text(encoding="utf-8")),
        )
        inventory.append(
            {
                "file": str(path),
                "uid": payload.get("uid"),
                "title": payload.get("title"),
                "variables": _extract_variables(payload),
                "link_uids": _extract_link_uids(payload),
                "tags": sorted(payload.get("tags", [])),
                "style": payload.get("style"),
                "timezone": payload.get("timezone"),
                "refresh": payload.get("refresh"),
                "editable": payload.get("editable"),
                "graphTooltip": payload.get("graphTooltip"),
                "hideControls": payload.get("hideControls", "<missing>"),
                "data_sources": _extract_datasources(payload),
                "panel_count": len(_iter_panels(payload)),
                "panel_plugin_versions": _extract_panel_plugin_versions(payload),
            }
        )
    return inventory


def _parse_variables_guide(text: str) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not line.startswith("| `bioetl-"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) < 2:
            continue
        uid = parts[0].strip("`")
        variables = sorted(re.findall(r"\$\w+", parts[1]))
        mapping[uid] = variables
    return mapping


def _normalize_contract_variables(raw_variables: object) -> list[str]:
    if not isinstance(raw_variables, list):
        return []
    variables: list[str] = []
    for name in raw_variables:
        variable = str(name)
        variables.append(variable if variable.startswith("$") else f"${variable}")
    return sorted(variables)


def _normalize_contract_datasources(raw_sources: object) -> list[str]:
    if not isinstance(raw_sources, list):
        return []
    sources = {
        normalized
        for item in raw_sources
        if (normalized := _normalize_datasource_ref(item)) is not None
    }
    return _sort_data_sources(sources)


def _dashboard_inventory_contract_entries() -> tuple[
    dict[str, dict[str, Any]], list[str]
]:
    errors: list[str] = []
    payload = yaml.safe_load(DASHBOARD_INVENTORY_CONTRACT.read_text(encoding="utf-8"))
    dashboards = payload.get("dashboards", []) if isinstance(payload, dict) else []
    if not isinstance(dashboards, list):
        return {}, ["dashboard-inventory: dashboards must be a list"]

    entries: dict[str, dict[str, Any]] = {}
    for entry in dashboards:
        if not isinstance(entry, dict):
            errors.append("dashboard-inventory: dashboard entry must be a mapping")
            continue
        uid = entry.get("uid")
        if not isinstance(uid, str) or not uid:
            errors.append("dashboard-inventory: dashboard entry missing uid")
            continue
        if uid in entries:
            errors.append(f"dashboard-inventory: duplicate dashboard uid {uid}")
            continue
        entries[uid] = entry
    return entries, errors


def _dashboard_panels_by_id(
    item: DashboardInventoryItem,
) -> dict[int, dict[str, Any]]:
    payload = _load_dashboard_file(Path(str(item["file"])))
    panels_by_id: dict[int, dict[str, Any]] = {}
    for panel in _iter_panels(payload):
        panel_id = panel.get("id")
        if isinstance(panel_id, int):
            panels_by_id[panel_id] = panel
    return panels_by_id


def _key_panel_field_mismatches(
    *,
    uid: str,
    panel_id: int,
    panel_contract: dict[str, Any],
    actual_panel: dict[str, Any],
) -> list[str]:
    messages: list[str] = []
    expected_title = panel_contract.get("title")
    actual_title = actual_panel.get("title")
    if expected_title != actual_title:
        messages.append(
            f"dashboard-inventory: {uid} key_panel id={panel_id} "
            f"title mismatch: contract={expected_title!r} "
            f"actual={actual_title!r}"
        )
    expected_type = panel_contract.get("type")
    actual_type = actual_panel.get("type")
    if expected_type != actual_type:
        messages.append(
            f"dashboard-inventory: {uid} key_panel id={panel_id} "
            f"type mismatch: contract={expected_type!r} "
            f"actual={actual_type!r}"
        )
    return messages


def _check_key_panel_contract(
    *,
    uid: str,
    panel_contract: object,
    panels_by_id: dict[int, dict[str, Any]],
    errors: list[str],
    per_dashboard: dict[str, list[str]],
) -> None:
    if not isinstance(panel_contract, dict):
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=f"dashboard-inventory: {uid} key_panel must be a mapping",
        )
        return
    panel_id = panel_contract.get("id")
    if not isinstance(panel_id, int):
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=f"dashboard-inventory: {uid} key_panel missing integer id",
        )
        return
    actual_panel = panels_by_id.get(panel_id)
    if actual_panel is None:
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=(
                f"dashboard-inventory: {uid} key_panel id={panel_id} "
                "missing from dashboard JSON"
            ),
        )
        return
    for message in _key_panel_field_mismatches(
        uid=uid,
        panel_id=panel_id,
        panel_contract=panel_contract,
        actual_panel=actual_panel,
    ):
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=message,
        )


def _check_dashboard_item_contract(
    item: DashboardInventoryItem,
    contract_entry: dict[str, Any],
    *,
    errors: list[str],
    per_dashboard: dict[str, list[str]],
) -> None:
    uid = str(item["uid"])
    if contract_entry.get("panel_count") != item.get("panel_count"):
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=(
                "dashboard-inventory: panel_count mismatch for "
                f"{uid}: contract={contract_entry.get('panel_count')} "
                f"actual={item.get('panel_count')}"
            ),
        )

    contract_sources = _normalize_contract_datasources(
        contract_entry.get("data_sources")
    )
    if contract_sources != list(item["data_sources"]):
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=(
                "dashboard-inventory: data_sources mismatch for "
                f"{uid}: contract={contract_sources} "
                f"actual={item['data_sources']}"
            ),
        )

    contract_variables = _normalize_contract_variables(
        contract_entry.get("selector_variables")
    )
    if contract_variables != list(item["variables"]):
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=(
                "dashboard-inventory: selector variables mismatch for "
                f"{uid}: contract={contract_variables} actual={item['variables']}"
            ),
        )

    panels_by_id = _dashboard_panels_by_id(item)
    key_panels = contract_entry.get("key_panels", [])
    if not isinstance(key_panels, list):
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=f"dashboard-inventory: {uid} key_panels must be a list",
        )
        return
    for panel_contract in key_panels:
        _check_key_panel_contract(
            uid=uid,
            panel_contract=panel_contract,
            panels_by_id=panels_by_id,
            errors=errors,
            per_dashboard=per_dashboard,
        )


def _check_dashboard_inventory_contract(
    inventory: list[DashboardInventoryItem],
) -> tuple[list[str], dict[str, list[str]]]:
    errors: list[str] = []
    per_dashboard: dict[str, list[str]] = {}
    contract_entries, load_errors = _dashboard_inventory_contract_entries()
    for message in load_errors:
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=None,
            message=message,
        )

    shipped_uids = {str(item["uid"]) for item in inventory}
    contract_uids = set(contract_entries)
    for uid in sorted(shipped_uids - contract_uids):
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=f"dashboard-inventory: missing dashboard entry for {uid}",
        )
    for uid in sorted(contract_uids - shipped_uids):
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=f"dashboard-inventory: unexpected dashboard entry for {uid}",
        )

    for item in inventory:
        uid = str(item["uid"])
        contract_entry = contract_entries.get(uid)
        if contract_entry is None:
            continue
        _check_dashboard_item_contract(
            item,
            contract_entry,
            errors=errors,
            per_dashboard=per_dashboard,
        )
    return errors, per_dashboard


def _register_issue(
    *,
    errors: list[str],
    per_dashboard: dict[str, list[str]],
    uid: str | None,
    message: str,
) -> None:
    errors.append(message)
    if uid:
        per_dashboard.setdefault(uid, []).append(message)


def _check_selector_registry_entry(
    *,
    uid: str,
    registry_entry: object,
    vars_actual: list[str],
    errors: list[str],
    per_dashboard: dict[str, list[str]],
) -> None:
    if registry_entry is None:
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=(
                f"selector-contracts: missing shipped_selector_registry entry for {uid}"
            ),
        )
        return
    if not isinstance(registry_entry, dict):
        return
    visible = registry_entry.get("visible_selectors", [])
    hidden = registry_entry.get("hidden_context_selectors", [])
    detail = registry_entry.get("hidden_detail_selectors", [])
    if not all(isinstance(section, list) for section in (visible, hidden, detail)):
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=f"selector-contracts: {uid} selector lists must be arrays",
        )
        return
    registry_vars = sorted(f"${name}" for name in [*visible, *hidden, *detail])
    if registry_vars != vars_actual:
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=(
                "selector-contracts: variables mismatch for "
                f"{uid}: contract={registry_vars} actual={vars_actual}"
            ),
        )


def _check_item_parity(
    item: DashboardInventoryItem,
    *,
    vars_map: dict[str, list[str]],
    idx_text: str,
    shipped_registry: dict[str, object],
    errors: list[str],
    per_dashboard: dict[str, list[str]],
) -> None:
    uid = str(item["uid"])
    vars_actual = list(item["variables"])
    doc_vars = vars_map.get(uid)
    if doc_vars is None:
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=f"variables-guide: missing UID row for {uid}",
        )
    elif doc_vars != vars_actual:
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=(
                "variables-guide: variables mismatch for "
                f"{uid}: doc={doc_vars} actual={vars_actual}"
            ),
        )

    if uid not in idx_text:
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=f"monitoring-index: missing UID mention for {uid}",
        )

    _check_selector_registry_entry(
        uid=uid,
        registry_entry=shipped_registry.get(uid),
        vars_actual=vars_actual,
        errors=errors,
        per_dashboard=per_dashboard,
    )

    expected_links = MANDATORY_LINK_UIDS.get(uid)
    if expected_links:
        actual_links = set(item["link_uids"])
        missing = sorted(expected_links - actual_links)
        if missing:
            _register_issue(
                errors=errors,
                per_dashboard=per_dashboard,
                uid=uid,
                message=f"mandatory links: {uid} missing links to {missing}",
            )


def _check_parity(
    inventory: list[DashboardInventoryItem],
) -> tuple[list[str], dict[str, list[str]]]:
    errors: list[str] = []
    per_dashboard: dict[str, list[str]] = {}
    vars_text = VARIABLES_GUIDE.read_text(encoding="utf-8")
    idx_text = MONITORING_INDEX.read_text(encoding="utf-8")
    vars_map = _parse_variables_guide(vars_text)
    selector_contract = yaml.safe_load(SELECTOR_CONTRACT.read_text(encoding="utf-8"))
    dashboard_inventory_errors, dashboard_inventory_by_dashboard = (
        _check_dashboard_inventory_contract(inventory)
    )
    errors.extend(dashboard_inventory_errors)
    for uid, messages in dashboard_inventory_by_dashboard.items():
        per_dashboard.setdefault(uid, []).extend(messages)
    shipped_registry = selector_contract.get("shipped_selector_registry", {})
    if not isinstance(shipped_registry, dict):
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=None,
            message="selector-contracts: shipped_selector_registry must be a mapping",
        )
        shipped_registry = {}

    for item in inventory:
        _check_item_parity(
            item,
            vars_map=vars_map,
            idx_text=idx_text,
            shipped_registry=shipped_registry,
            errors=errors,
            per_dashboard=per_dashboard,
        )

    return errors, per_dashboard


def _provisioning_field_errors(
    *,
    folder_uid: object,
    allow_ui_updates: object,
    provider_type: object,
    update_interval: object,
    path: object,
) -> list[str]:
    errors: list[str] = []
    path_basename = Path(str(path)).name if path else None
    if folder_uid != "bioetl":
        errors.append(
            f"provisioning: BioETL folderUid must be 'bioetl', got {folder_uid!r}"
        )
    if allow_ui_updates is not False:
        errors.append("provisioning: BioETL allowUiUpdates must be false")
    if provider_type != "file":
        errors.append(
            f"provisioning: BioETL provider type must be 'file', got {provider_type!r}"
        )
    if not isinstance(update_interval, int) or update_interval <= 0:
        errors.append(
            "provisioning: BioETL updateIntervalSeconds must be a positive integer"
        )
    if path_basename != "dashboards":
        errors.append(
            "provisioning: BioETL provider path must target a dashboards directory, "
            f"got {path!r}"
        )
    return errors


def _check_provisioning_contract() -> tuple[list[str], dict[str, object]]:
    payload = yaml.safe_load(PROVISIONING_CONFIG.read_text(encoding="utf-8"))
    providers = payload.get("providers", []) if isinstance(payload, dict) else []
    provider = next(
        (
            item
            for item in providers
            if isinstance(item, dict) and item.get("name") == "BioETL"
        ),
        None,
    )
    if provider is None:
        return ["provisioning: missing BioETL dashboard provider"], {}

    folder_uid = provider.get("folderUid")
    allow_ui_updates = provider.get("allowUiUpdates")
    update_interval = provider.get("updateIntervalSeconds")
    provider_type = provider.get("type")
    options = provider.get("options", {}) if isinstance(provider, dict) else {}
    path = options.get("path") if isinstance(options, dict) else None
    errors = _provisioning_field_errors(
        folder_uid=folder_uid,
        allow_ui_updates=allow_ui_updates,
        provider_type=provider_type,
        update_interval=update_interval,
        path=path,
    )

    return errors, {
        "name": provider.get("name"),
        "folderUid": folder_uid,
        "allowUiUpdates": allow_ui_updates,
        "type": provider_type,
        "updateIntervalSeconds": update_interval,
        "path": path,
    }


def _load_dashboard_file(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _load_deployed_dashboards(
    deployed_dir: Path,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    by_uid: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for path in sorted(deployed_dir.rglob("*.json")):
        payload = _load_dashboard_file(path)
        dashboard = _root_dashboard_payload(payload)
        uid = dashboard.get("uid")
        if not isinstance(uid, str) or not uid:
            errors.append(f"deployed-dir: {path} missing dashboard uid")
            continue
        if uid in by_uid:
            errors.append(f"deployed-dir: duplicate dashboard uid {uid!r} in {path}")
            continue
        by_uid[uid] = _normalize_dashboard_payload(payload)
    return by_uid, errors


def _compare_deployed_dashboards(
    inventory: list[DashboardInventoryItem],
    *,
    deployed_dir: Path,
) -> tuple[list[str], dict[str, list[str]]]:
    errors: list[str] = []
    per_dashboard: dict[str, list[str]] = {}
    deployed, load_errors = _load_deployed_dashboards(deployed_dir)
    for message in load_errors:
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=None,
            message=message,
        )

    shipped_by_uid: dict[str, dict[str, Any]] = {}
    for item in inventory:
        file_path = Path(str(item["file"]))
        payload = _load_dashboard_file(file_path)
        uid = str(item["uid"])
        shipped_by_uid[uid] = _normalize_dashboard_payload(payload)

    for uid in sorted(shipped_by_uid):
        if uid not in deployed:
            _register_issue(
                errors=errors,
                per_dashboard=per_dashboard,
                uid=uid,
                message=f"deployed-dir: missing deployed snapshot for {uid}",
            )
            continue
        if shipped_by_uid[uid] != deployed[uid]:
            _register_issue(
                errors=errors,
                per_dashboard=per_dashboard,
                uid=uid,
                message=f"deployed-dir: dashboard drift detected for {uid}",
            )

    extra = sorted(set(deployed) - set(shipped_by_uid))
    for uid in extra:
        _register_issue(
            errors=errors,
            per_dashboard=per_dashboard,
            uid=uid,
            message=f"deployed-dir: unexpected deployed dashboard {uid}",
        )

    return errors, per_dashboard


def _dashboard_item_health_issues(
    item: DashboardInventoryItem,
    *,
    parity_issues: dict[str, list[str]],
    deployed_issues: dict[str, list[str]],
) -> list[str]:
    """Collect non-canonical / missing-field issues for one dashboard inventory row."""
    uid = str(item["uid"])
    issues: list[str] = []
    if not uid or uid == "None":
        issues.append("missing uid")
    if not item.get("title"):
        issues.append("missing title")
    if item.get("style") != "dark":
        issues.append(f"non-canonical style={item.get('style')!r}")
    if item.get("timezone") != "browser":
        issues.append(f"non-canonical timezone={item.get('timezone')!r}")
    if item.get("editable") is not True:
        issues.append(f"editable must be true, got {item.get('editable')!r}")
    if item.get("graphTooltip") != 1:
        issues.append(f"graphTooltip must be 1, got {item.get('graphTooltip')!r}")
    hide_controls = item.get("hideControls")
    if hide_controls != "<missing>" and hide_controls is not False:
        issues.append(
            f"hideControls, when exported, must be false, got {hide_controls!r}"
        )
    issues.extend(parity_issues.get(uid, []))
    issues.extend(deployed_issues.get(uid, []))
    return issues


def _build_health_summary(
    inventory: list[DashboardInventoryItem],
    *,
    parity_issues: dict[str, list[str]],
    provisioning_issues: list[str],
    provisioning_metadata: dict[str, object],
    deployed_issues: dict[str, list[str]] | None = None,
    deployed_dir: Path | None = None,
) -> DashboardHealthSummary:
    dashboards: list[DashboardHealthItem] = []
    healthy = 0
    degraded = 0
    deployed_issues = deployed_issues or {}

    for item in inventory:
        issues = _dashboard_item_health_issues(
            item,
            parity_issues=parity_issues,
            deployed_issues=deployed_issues,
        )
        status = "healthy" if not issues else "degraded"
        if status == "healthy":
            healthy += 1
        else:
            degraded += 1
        dashboard_health: DashboardHealthItem = {
            **item,
            "status": status,
            "issues": issues,
        }
        dashboards.append(dashboard_health)

    overall_status = (
        "healthy" if not provisioning_issues and degraded == 0 else "degraded"
    )
    return {
        "overall_status": overall_status,
        "summary": {
            "total_dashboards": len(dashboards),
            "healthy_dashboards": healthy,
            "degraded_dashboards": degraded,
            "provisioning_ok": not provisioning_issues,
            "deployed_dir_used": str(deployed_dir) if deployed_dir else None,
        },
        "provisioning": {
            "status": "healthy" if not provisioning_issues else "degraded",
            "issues": provisioning_issues,
            "provider": provisioning_metadata,
        },
        "dashboards": dashboards,
    }


def _render_health_summary(summary: DashboardHealthSummary) -> str:
    lines = [
        "Dashboard health summary:",
        (
            f"- overall={summary['overall_status']} "
            f"total={summary['summary']['total_dashboards']} "
            f"healthy={summary['summary']['healthy_dashboards']} "
            f"degraded={summary['summary']['degraded_dashboards']}"
        ),
    ]
    provisioning = summary["provisioning"]
    lines.append(f"- provisioning={provisioning['status']}")
    for issue in provisioning["issues"]:
        lines.append(f"  - {issue}")
    for item in summary["dashboards"]:
        if item["status"] == "healthy":
            lines.append(f"- {item['uid']}: healthy")
            continue
        lines.append(f"- {item['uid']}: degraded")
        for issue in item["issues"]:
            lines.append(f"  - {issue}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON"
    )
    parser.add_argument(
        "--check", action="store_true", help="Fail on canonical parity mismatches"
    )
    parser.add_argument(
        "--deployed-dir",
        type=Path,
        help=(
            "Optional directory with exported/deployed dashboard JSON snapshots. "
            "When provided, compare shipped dashboards against deployed snapshots "
            "after stripping benign export noise (root id/version, panel pluginVersion)."
        ),
    )
    parser.add_argument(
        "--health-summary",
        action="store_true",
        help="Emit per-dashboard local health rollup over docs/provisioning/deployment contracts",
    )
    args = parser.parse_args(argv)

    inventory = _load_inventory()
    parity_errors, parity_by_dashboard = _check_parity(inventory)
    provisioning_errors, provisioning_metadata = _check_provisioning_contract()
    deployed_errors: list[str] = []
    deployed_by_dashboard: dict[str, list[str]] = {}
    if args.deployed_dir is not None:
        deployed_errors, deployed_by_dashboard = _compare_deployed_dashboards(
            inventory,
            deployed_dir=args.deployed_dir,
        )

    if args.health_summary:
        health_summary = _build_health_summary(
            inventory,
            parity_issues=parity_by_dashboard,
            provisioning_issues=provisioning_errors,
            provisioning_metadata=provisioning_metadata,
            deployed_issues=deployed_by_dashboard,
            deployed_dir=args.deployed_dir,
        )
        if args.json:
            print(json.dumps(health_summary, ensure_ascii=False, indent=2))
        else:
            print(_render_health_summary(health_summary))
    elif args.json:
        print(json.dumps(inventory, ensure_ascii=False, indent=2))
    else:
        for item in inventory:
            print(
                f"{item['uid']}: {item['title']} vars={item['variables']} "
                f"links={item['link_uids']} tags={item['tags']} "
                f"style={item['style']} timezone={item['timezone']} "
                f"refresh={item['refresh']} pluginVersions={item['panel_plugin_versions']}"
            )

    if args.check:
        errors = [*parity_errors, *provisioning_errors, *deployed_errors]
        if errors:
            print("\nDashboard inventory / drift check failed:")
            for error in errors:
                print(f"- {error}")
            return 1
        print("\nDashboard inventory / drift check passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
