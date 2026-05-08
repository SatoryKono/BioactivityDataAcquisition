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
from typing import Any

import yaml

DASHBOARDS_DIR = Path("grafana/dashboards")
VARIABLES_GUIDE = Path("docs/03-guides/dashboards/variables-guide.md")
MONITORING_INDEX = Path("docs/03-guides/dashboards/monitoring-index.md")
SELECTOR_CONTRACT = Path("docs/03-guides/dashboards/contracts/selector-contracts.yaml")
PROVISIONING_CONFIG = Path("grafana/provisioning/dashboards/bioetl.yaml")
VOLATILE_ROOT_KEYS = frozenset({"id", "version"})
VOLATILE_PANEL_KEYS = frozenset({"pluginVersion"})

MANDATORY_LINK_UIDS: dict[str, set[str]] = {
    "bioetl-overview-v2": {
        "bioetl-runtime",
        "bioetl-provider-health-v2",
        "bioetl-dq-v2",
        "bioetl-control-plane-v1",
        "bioetl-workflow-overview",
    },
    "bioetl-runtime": {"bioetl-overview-v2", "bioetl-dq-v2", "bioetl-control-plane-v1"},
    "bioetl-provider-health-v2": {"bioetl-overview-v2", "bioetl-runtime"},
    "bioetl-dq-v2": {"bioetl-overview-v2", "bioetl-silver-reject-explorer"},
    "bioetl-workflow-overview": {"bioetl-overview-v2", "bioetl-runtime", "bioetl-control-plane-v1"},
}


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


def _extract_variables(payload: dict) -> list[str]:
    templating = payload.get("templating", {}).get("list", [])
    names = [f"${item.get('name')}" for item in templating if item.get("name")]
    return sorted(names)


def _extract_link_uids(payload: dict) -> list[str]:
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


def _root_dashboard_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("dashboard"), dict):
        dashboard = payload["dashboard"]
        return dashboard
    return payload


def _normalize_dashboard_payload(payload: dict[str, Any]) -> dict[str, Any]:
    dashboard = _root_dashboard_payload(payload)

    def _normalize(node: Any, *, is_root: bool = False) -> Any:
        if isinstance(node, dict):
            normalized: dict[str, Any] = {}
            for key, value in node.items():
                if is_root and key in VOLATILE_ROOT_KEYS:
                    continue
                if key in VOLATILE_PANEL_KEYS:
                    continue
                normalized[key] = _normalize(value)
            return normalized
        if isinstance(node, list):
            return [_normalize(item) for item in node]
        return node

    return _normalize(dashboard, is_root=True)


def _load_inventory() -> list[dict[str, object]]:
    inventory: list[dict[str, object]] = []
    for path in sorted(DASHBOARDS_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
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


def _check_parity(
    inventory: list[dict[str, object]],
) -> tuple[list[str], dict[str, list[str]]]:
    errors: list[str] = []
    per_dashboard: dict[str, list[str]] = {}
    vars_text = VARIABLES_GUIDE.read_text(encoding="utf-8")
    idx_text = MONITORING_INDEX.read_text(encoding="utf-8")
    vars_map = _parse_variables_guide(vars_text)
    selector_contract = yaml.safe_load(SELECTOR_CONTRACT.read_text(encoding="utf-8"))
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

        registry_entry = shipped_registry.get(uid)
        if registry_entry is None:
            _register_issue(
                errors=errors,
                per_dashboard=per_dashboard,
                uid=uid,
                message=(
                    "selector-contracts: missing shipped_selector_registry entry "
                    f"for {uid}"
                ),
            )
        elif isinstance(registry_entry, dict):
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
            else:
                registry_vars = sorted(
                    f"${name}" for name in [*visible, *hidden, *detail]
                )
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

    return errors, per_dashboard


def _check_provisioning_contract() -> tuple[list[str], dict[str, object]]:
    errors: list[str] = []
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
    path_basename = Path(str(path)).name if path else None

    if folder_uid != "bioetl":
        errors.append(f"provisioning: BioETL folderUid must be 'bioetl', got {folder_uid!r}")
    if allow_ui_updates is not False:
        errors.append("provisioning: BioETL allowUiUpdates must be false")
    if provider_type != "file":
        errors.append(f"provisioning: BioETL provider type must be 'file', got {provider_type!r}")
    if not isinstance(update_interval, int) or update_interval <= 0:
        errors.append(
            "provisioning: BioETL updateIntervalSeconds must be a positive integer"
        )
    if path_basename != "dashboards":
        errors.append(
            "provisioning: BioETL provider path must target a dashboards directory, "
            f"got {path!r}"
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
    return json.loads(path.read_text(encoding="utf-8"))


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
            errors.append(
                f"deployed-dir: duplicate dashboard uid {uid!r} in {path}"
            )
            continue
        by_uid[uid] = _normalize_dashboard_payload(payload)
    return by_uid, errors


def _compare_deployed_dashboards(
    inventory: list[dict[str, object]],
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


def _build_health_summary(
    inventory: list[dict[str, object]],
    *,
    parity_issues: dict[str, list[str]],
    provisioning_issues: list[str],
    provisioning_metadata: dict[str, object],
    deployed_issues: dict[str, list[str]] | None = None,
    deployed_dir: Path | None = None,
) -> dict[str, object]:
    dashboards: list[dict[str, object]] = []
    healthy = 0
    degraded = 0
    deployed_issues = deployed_issues or {}

    for item in inventory:
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
            issues.append(
                f"graphTooltip must be 1, got {item.get('graphTooltip')!r}"
            )
        hide_controls = item.get("hideControls")
        if hide_controls != "<missing>" and hide_controls is not False:
            issues.append(
                "hideControls, when exported, must be false, got "
                f"{hide_controls!r}"
            )
        issues.extend(parity_issues.get(uid, []))
        issues.extend(deployed_issues.get(uid, []))
        status = "healthy" if not issues else "degraded"
        if status == "healthy":
            healthy += 1
        else:
            degraded += 1
        dashboards.append(
            {
                **item,
                "status": status,
                "issues": issues,
            }
        )

    overall_status = "healthy" if not provisioning_issues and degraded == 0 else "degraded"
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


def _render_health_summary(summary: dict[str, object]) -> str:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--check", action="store_true", help="Fail on canonical parity mismatches")
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
    args = parser.parse_args()

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
