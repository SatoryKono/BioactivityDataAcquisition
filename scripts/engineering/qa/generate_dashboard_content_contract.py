#!/usr/bin/env python3
"""Сгенерировать полный semantic content contract для shipped Grafana panels."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = ROOT / "grafana" / "dashboards"
CONTRACT_PATH = (
    ROOT
    / "docs"
    / "03-guides"
    / "dashboards"
    / "contracts"
    / "panel-content-contract.yaml"
)

_ALLOWED_ROLES = [
    "verdict",
    "confidence",
    "next_action",
    "navigation",
    "selected_range_count",
    "selected_range_duration",
    "identity_table",
    "accounting_table",
    "severity_table",
    "causes_table",
    "freshness",
    "forensic_table",
    "alert_timeline",
    "row_group",
    "guidance",
    "indicator",
    "evidence_table",
    "trend",
    "heatmap",
    "state_timeline",
]
_ALLOWED_SCOPES = ["current", "selected_run", "time_range", "global"]
_ALLOWED_EVIDENCE_SOURCES = ["prometheus", "ops_http", "grafana_builtin"]
_ALLOWED_STATES = [
    "OK",
    "WARN",
    "CRIT",
    "UNKNOWN",
    "INCOMPLETE",
    "ERROR",
    "VALID_EMPTY",
    "TELEMETRY_ABSENT",
    "N/A",
]
_RENDER_PROFILES = ["full_dark", "full_light", "zoom_200"]
_ALLOWED_EMPTY_STATE_CLASSES = [
    "event_empty",
    "telemetry_missing",
    "unsupported",
    "select_run",
]
_NON_DATA_ROLES = frozenset({"navigation", "row_group", "guidance"})


def _iter_panels(payload: dict[str, object]) -> Iterable[dict[str, object]]:
    raw_panels = payload.get("panels", [])
    if not isinstance(raw_panels, list):
        return
    stack = [panel for panel in raw_panels if isinstance(panel, dict)]
    while stack:
        panel = stack.pop(0)
        yield panel
        nested = panel.get("panels", [])
        if isinstance(nested, list):
            stack[0:0] = [child for child in nested if isinstance(child, dict)]


def _is_ops_http(panel: dict[str, object]) -> bool:
    targets = panel.get("targets", [])
    if not isinstance(targets, list):
        targets = []
    for target in targets:
        if not isinstance(target, dict):
            continue
        url = target.get("url")
        if isinstance(url, str) and "/ops/" in url:
            return True
        datasource = target.get("datasource")
        if (
            isinstance(datasource, dict)
            and datasource.get("type") == "yesoreyeram-infinity-datasource"
        ):
            return True
    datasource = panel.get("datasource")
    return (
        isinstance(datasource, dict)
        and datasource.get("type") == "yesoreyeram-infinity-datasource"
    )


def _uses_prometheus(panel: dict[str, object]) -> bool:
    datasource = panel.get("datasource")
    if isinstance(datasource, str) and datasource.lower() == "prometheus":
        return True
    if isinstance(datasource, dict) and datasource.get("type") == "prometheus":
        return True
    targets = panel.get("targets", [])
    if not isinstance(targets, list):
        targets = []
    for target in targets:
        if not isinstance(target, dict):
            continue
        if isinstance(target.get("expr"), str) and target["expr"].strip():
            return True
        target_datasource = target.get("datasource")
        if (
            isinstance(target_datasource, dict)
            and target_datasource.get("type") == "prometheus"
        ):
            return True
    return False


def _evidence_source(panel: dict[str, object]) -> str:
    if _is_ops_http(panel):
        return "ops_http"
    if _uses_prometheus(panel):
        return "prometheus"
    return "grafana_builtin"


def _scope(title: str, panel: dict[str, object]) -> str:
    normalized = title.lower()
    if panel.get("type") in {"row", "text"}:
        return "global"
    if _is_ops_http(panel) and (
        "run" in normalized or "manifest" in normalized or "retention" in normalized
    ):
        return "selected_run"
    if _uses_prometheus(panel):
        if "current" in normalized or "fleet" in normalized:
            return "current"
        return "time_range"
    if "run" in normalized or "manifest" in normalized:
        return "selected_run"
    return "time_range"


def _empty_state_class(
    panel: dict[str, object], role: str, evidence_source: str
) -> str:
    if role in _NON_DATA_ROLES:
        return "unsupported"
    if evidence_source == "ops_http":
        return "select_run"
    if evidence_source == "grafana_builtin":
        return "unsupported"
    title = str(panel.get("title") or "").lower()
    if any(token in title for token in ("event", "total", "count", "failure", "alert")):
        return "event_empty"
    return "telemetry_missing"


def _role(title: str, panel: dict[str, object]) -> str:
    panel_type = panel.get("type")
    normalized = title.lower()
    panel_id = panel.get("id")
    if panel_type == "row":
        return "row_group"
    if panel_type == "text":
        return "navigation" if panel_id == 1000 else "guidance"
    if panel_type == "table":
        return "forensic_table" if "inspect" in normalized else "evidence_table"
    if panel_type == "timeseries":
        return "trend"
    if panel_type == "heatmap":
        return "heatmap"
    if panel_type == "state-timeline":
        return "state_timeline"
    if "freshness" in normalized or "age" in normalized:
        return "freshness"
    if "confidence" in normalized:
        return "confidence"
    if "action" in normalized:
        return "next_action"
    return "indicator"


def _state_model(role: str) -> list[str]:
    if role in {"row_group", "guidance", "navigation"}:
        return ["N/A"]
    if role in {"forensic_table", "evidence_table"}:
        return ["VALID_EMPTY", "ERROR", "TELEMETRY_ABSENT"]
    if role in {"trend", "heatmap", "state_timeline", "alert_timeline"}:
        return ["OK", "WARN", "CRIT", "UNKNOWN", "ERROR", "VALID_EMPTY"]
    return [
        "OK",
        "WARN",
        "CRIT",
        "UNKNOWN",
        "INCOMPLETE",
        "ERROR",
        "VALID_EMPTY",
        "TELEMETRY_ABSENT",
    ]


def _fixture_cases(role: str) -> list[str]:
    if role in {"row_group", "guidance", "navigation"}:
        return ["not_applicable"]
    if role in {
        "forensic_table",
        "evidence_table",
        "trend",
        "heatmap",
        "state_timeline",
        "alert_timeline",
    }:
        return ["populated", "valid_empty", "telemetry_absent", "backend_error"]
    return ["ok", "warn", "crit", "telemetry_absent", "backend_error"]


def _required_copy(role: str) -> list[str]:
    if role == "navigation":
        return ["navigation_context"]
    if role in {"row_group", "guidance"}:
        return ["operator_guidance"]
    if role in {"next_action", "confidence", "freshness", "indicator"}:
        return ["evidence_scope", "no_data", "next_action"]
    return ["evidence_scope", "no_data"]


def _record(panel: dict[str, object]) -> dict[str, object]:
    panel_id = panel.get("id")
    title = panel.get("title")
    if not isinstance(panel_id, int) or not isinstance(title, str):
        raise ValueError("contractable panel requires integer id and string title")
    role = _role(title, panel)
    evidence_source = _evidence_source(panel)
    scope = _scope(title, panel)
    return {
        "title": title,
        "role": role,
        "tier": 4 if role in {"row_group", "guidance"} else 3,
        "scope": scope,
        "scope_class": scope,
        "evidence_source": evidence_source,
        "empty_state_class": _empty_state_class(panel, role, evidence_source),
        "state_model": _state_model(role),
        "required_copy": _required_copy(role),
        "fixture_cases": _fixture_cases(role),
        "render_profiles": _RENDER_PROFILES,
    }


def _load_contract(path: Path) -> dict[str, object]:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    safe_path = resolve_output_path(path, root=REPO_ROOT)
    payload = yaml.safe_load(
        safe_path.read_text(encoding="utf-8")  # NOSONAR -- confined above
    )
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected YAML mapping")
    return payload


def _full_contract(existing: dict[str, object]) -> dict[str, object]:
    existing_dashboards = existing.get("dashboards", {})
    if not isinstance(existing_dashboards, dict):
        raise ValueError("panel-content-contract.yaml: dashboards must be a mapping")
    dashboards: dict[str, object] = {}
    for dashboard_path in sorted(DASHBOARD_DIR.glob("*.json")):
        payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{dashboard_path}: expected JSON object")
        uid = payload.get("uid")
        if not isinstance(uid, str) or not uid:
            raise ValueError(f"{dashboard_path}: missing dashboard uid")
        previous_dashboard = existing_dashboards.get(uid, {})
        previous_panels = (
            previous_dashboard.get("panels", {})
            if isinstance(previous_dashboard, dict)
            else {}
        )
        if not isinstance(previous_panels, dict):
            raise ValueError(
                f"panel-content-contract.yaml:{uid}: panels must be a mapping"
            )
        panels: dict[str, object] = {}
        for panel in _iter_panels(payload):
            panel_id = panel.get("id")
            if not isinstance(panel_id, int):
                continue
            generated = _record(panel)
            previous = previous_panels.get(str(panel_id))
            if isinstance(previous, dict):
                merged = {**generated, **previous}
                merged["title"] = generated["title"]
                merged["evidence_source"] = generated["evidence_source"]
                role = str(merged.get("role") or generated["role"])
                if (
                    merged["evidence_source"] == "prometheus"
                    and merged.get("scope") == "selected_run"
                    and role not in _NON_DATA_ROLES
                ):
                    generated_scope = str(generated["scope"])
                    merged["scope"] = (
                        generated_scope
                        if generated_scope != "selected_run"
                        else "time_range"
                    )
                merged["scope_class"] = merged.get("scope", generated["scope"])
                if merged.get("empty_state_class") not in _ALLOWED_EMPTY_STATE_CLASSES:
                    merged["empty_state_class"] = generated["empty_state_class"]
                elif role in _NON_DATA_ROLES:
                    merged["empty_state_class"] = "unsupported"
                panels[str(panel_id)] = merged
            else:
                panels[str(panel_id)] = generated
        dashboards[uid] = {
            "panels": dict(sorted(panels.items(), key=lambda item: int(item[0])))
        }
    return {
        "schema_version": 2,
        "coverage_policy": "all_shipped_panels",
        "allowed_roles": _ALLOWED_ROLES,
        "allowed_scopes": _ALLOWED_SCOPES,
        "allowed_evidence_sources": _ALLOWED_EVIDENCE_SOURCES,
        "allowed_states": _ALLOWED_STATES,
        "allowed_empty_state_classes": _ALLOWED_EMPTY_STATE_CLASSES,
        "dashboards": dashboards,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    existing = _load_contract(args.contract)
    generated = _full_contract(existing)
    rendered = yaml.safe_dump(
        generated, allow_unicode=True, sort_keys=False, width=1000
    )
    if args.check:
        current = args.contract.read_text(encoding="utf-8")
        if current != rendered:
            print(f"dashboard content contract is stale: {args.contract}")
            return 1
        print("dashboard content contract is current")
        return 0
    args.contract.write_text(rendered, encoding="utf-8")
    print(f"wrote full semantic contract -> {args.contract}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
