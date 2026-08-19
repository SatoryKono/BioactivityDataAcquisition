# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
"""DASH-SCOPE #9009 contracts: scope_class, coverage CTA, chips, refresh, D6."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from scripts.engineering.qa import validate_dashboard_content_contract as content

from tests.integration._dashboard_layout_budgets import (
    FIRST_WINDOW_Y,
    select_first_window_panels,
)
from tests.integration._grafana_dashboard_links_support import get_dashboard_files

pytestmark = pytest.mark.integration

DASHBOARD_DIR = Path("grafana/dashboards")
CONTRACT_PATH = Path("docs/03-guides/dashboards/contracts/panel-content-contract.yaml")
SCOPE_BADGE = {
    "current": "CURRENT",
    "time_range": "TIME RANGE",
    "selected_run": "SELECTED RUN",
    "global": "GLOBAL",
}
HIDDEN_CHIP_VARS = {
    "bioetl-provider-health-v2.json": ("adapter", "pipeline_context"),
    "bioetl-runtime.json": ("provider_hint",),
}
SUMMARY_PANELS = {
    "bioetl-overview-v2.json": 9603,
    "bioetl-runtime.json": 9998,
    "bioetl-dq-v2.json": 9406,
    "bioetl-incident-v1.json": 2101,
}
QUERY_TYPES = {
    "stat",
    "table",
    "timeseries",
    "gauge",
    "bargauge",
    "heatmap",
    "state-timeline",
}


def _iter_panels(panels: list[object]):
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        yield panel
        nested = panel.get("panels")
        if isinstance(nested, list):
            yield from _iter_panels(nested)


def _root_panels(dashboard: dict[str, object]) -> list[dict[str, object]]:
    raw = dashboard.get("panels") or []
    return [panel for panel in raw if isinstance(panel, dict)]


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _first_window_blob(dashboard: dict[str, object]) -> str:
    parts: list[str] = []
    for panel in select_first_window_panels(_root_panels(dashboard)):
        parts.append(str(panel.get("title") or ""))
        parts.append(str(panel.get("description") or ""))
        options = panel.get("options") or {}
        if isinstance(options, dict):
            parts.append(str(options.get("content") or ""))
        for link in panel.get("links") or []:
            if isinstance(link, dict):
                parts.append(str(link.get("title") or ""))
                parts.append(str(link.get("url") or ""))
    return "\n".join(parts)


def test_overview_selected_run_summary_is_in_first_window() -> None:
    dashboard = _load(DASHBOARD_DIR / "bioetl-overview-v2.json")
    root = _root_panels(dashboard)
    panel = next((item for item in root if item.get("id") == 9603), None)
    assert panel is not None, "9603 must be a root panel"
    assert panel.get("type") != "row"
    y = int((panel.get("gridPos") or {}).get("y") or 99)
    assert y < FIRST_WINDOW_Y, f"9603 must sit in first window, got y={y}"
    fleet_y = int(
        next(item for item in root if item.get("id") == 214)["gridPos"]["y"]
    )
    action_y = int(
        next(item for item in root if item.get("id") == 215)["gridPos"]["y"]
    )
    assert y < fleet_y, "SELECTED RUN summary must sit above Monitor Fleet Health"
    assert y < action_y, "SELECTED RUN summary must sit above Review First Action"
    blob = f"{panel.get('title') or ''}\n{panel.get('description') or ''}"
    assert "SELECTED RUN" in blob
    urls = [
        str(target.get("url") or "")
        for target in (panel.get("targets") or [])
        if isinstance(target, dict)
    ]
    assert any("view=summary" in url for url in urls)


def test_query_panels_declare_scope_class_matching_scope() -> None:
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(contract, dict)
    records, errors = content._contract_panel_records(contract)
    assert errors == []
    missing: list[str] = []
    for (uid, panel_id), record in sorted(records.items()):
        scope = record.get("scope")
        scope_class = record.get("scope_class", scope)
        if scope not in SCOPE_BADGE or scope_class != scope:
            missing.append(
                f"{uid}:{panel_id} scope={scope!r} scope_class={scope_class!r}"
            )
    assert not missing, "scope_class must join existing scope:\n" + "\n".join(
        missing[:20]
    )


def test_query_panel_descriptions_carry_scope_badge() -> None:
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(contract, dict)
    records, _ = content._contract_panel_records(contract)
    missing: list[str] = []
    for path in get_dashboard_files():
        dashboard = _load(path)
        uid = str(dashboard.get("uid"))
        for panel in _iter_panels(_root_panels(dashboard)):
            if panel.get("type") not in QUERY_TYPES:
                continue
            panel_id = str(panel.get("id"))
            record = records.get((uid, panel_id))
            if record is None:
                continue
            if record.get("role") in {"navigation", "row_group", "guidance"}:
                continue
            badge = SCOPE_BADGE.get(
                str(record.get("scope_class") or record.get("scope"))
            )
            if not badge:
                continue
            blob = f"{panel.get('title') or ''}\n{panel.get('description') or ''}"
            if badge not in blob:
                missing.append(f"{path.name}:{panel_id} missing {badge}")
    assert not missing, "query-panel scope badges:\n" + "\n".join(missing[:30])


def test_first_window_coverage_set_range_and_refresh_copy() -> None:
    required = (
        "Set range to run",
        "Effective refresh",
        "60s",
        "timezone",
        "Run coverage",
        "IN RANGE",
        "OUT OF RANGE",
    )
    missing: list[str] = []
    for path in get_dashboard_files():
        dashboard = _load(path)
        blob = _first_window_blob(dashboard)
        for token in required:
            if token not in blob:
                missing.append(f"{path.name} missing {token}")
        assert dashboard.get("refresh") == "60s", path.name
        assert dashboard.get("timezone") == "browser", path.name
    assert not missing, "coverage/refresh header:\n" + "\n".join(missing)


def test_hidden_vars_have_read_only_chips() -> None:
    missing: list[str] = []
    for path in get_dashboard_files():
        dashboard = _load(path)
        blob = _first_window_blob(dashboard)
        if path.name == "bioetl-provider-health-v2.json":
            if "adapter=" not in blob or "pipeline_context=" not in blob:
                missing.append(f"{path.name} missing adapter/pipeline_context chips")
        if path.name == "bioetl-runtime.json" and "provider_hint=" not in blob:
            missing.append(f"{path.name} missing provider_hint chip")
    assert not missing, "hidden-var chips:\n" + "\n".join(missing)


def test_compact_selected_run_summary_uses_shared_projection() -> None:
    missing: list[str] = []
    for name, panel_id in SUMMARY_PANELS.items():
        dashboard = _load(DASHBOARD_DIR / name)
        panel = next(
            (
                item
                for item in _iter_panels(_root_panels(dashboard))
                if item.get("id") == panel_id
            ),
            None,
        )
        if panel is None:
            missing.append(f"{name}:{panel_id} missing")
            continue
        targets = panel.get("targets") or []
        urls = [
            str(target.get("url") or "")
            for target in targets
            if isinstance(target, dict)
        ]
        if not any(
            "view=summary" in url and "pipeline-run-report" in url for url in urls
        ):
            missing.append(f"{name}:{panel_id} missing view=summary")
        blob = json.dumps(panel)
        if "viewPanel=9402" not in blob:
            missing.append(f"{name}:{panel_id} missing D6 viewPanel=9402")
        if "from=${__data.fields.from_ms}" not in blob:
            missing.append(f"{name}:{panel_id} missing Set range from_ms")
        no_value = str(
            ((panel.get("fieldConfig") or {}).get("defaults") or {}).get("noValue")
            or ""
        )
        if "SELECT RUN" not in no_value and "VALID EMPTY" not in no_value:
            missing.append(f"{name}:{panel_id} missing SELECT RUN/VALID EMPTY")
    assert not missing, "selected-run summary:\n" + "\n".join(missing)


def test_provider_reason_and_causes_share_empty_state() -> None:
    dashboard = _load(DASHBOARD_DIR / "bioetl-provider-health-v2.json")
    row = next(item for item in _root_panels(dashboard) if item.get("id") == 9106)
    assert row.get("type") == "row"
    assert row.get("collapsed") is True
    assert int((row.get("gridPos") or {}).get("y", -1)) >= FIRST_WINDOW_Y
    nested_ids = {
        item.get("id") for item in row.get("panels") or [] if isinstance(item, dict)
    }
    assert {9102, 9103} <= nested_ids
    reason = next(
        item for item in _iter_panels(_root_panels(dashboard)) if item.get("id") == 9107
    )
    assert int((reason.get("gridPos") or {}).get("y", 99)) < FIRST_WINDOW_Y
    expr = str((reason.get("targets") or [{}])[0].get("expr") or "")
    assert "bioetl_provider_current_status_info" in expr
    assert "run_id" not in expr


def test_promql_targets_do_not_select_run_id_label() -> None:
    offenders: list[str] = []
    for path in get_dashboard_files():
        dashboard = _load(path)
        for panel in _iter_panels(_root_panels(dashboard)):
            for target in panel.get("targets") or []:
                if not isinstance(target, dict):
                    continue
                expr = target.get("expr")
                if isinstance(expr, str) and "run_id=" in expr.replace(" ", ""):
                    offenders.append(f"{path.name}:{panel.get('id')}")
    assert not offenders, "PromQL run_id label:\n" + "\n".join(offenders)
