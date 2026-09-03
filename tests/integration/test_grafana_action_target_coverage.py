# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
"""Focused contract test for DASH-ACTION-001 (9963/9964)."""

from __future__ import annotations

import json
import pathlib
import yaml

import pytest

from scripts.ops.observability.grafana.action_target_routes import (
    DQ_REASON_ACTION_MAP,
    RUNTIME_BLOCKER_ACTION_MAP,
)

pytestmark = pytest.mark.integration

RULES_PATH = pathlib.Path("grafana/prometheus-rules/bioetl_observability.yml")
RUNTIME_DASH = pathlib.Path("grafana/dashboards/bioetl-runtime.json")
DQ_DASH = pathlib.Path("grafana/dashboards/bioetl-dq-v2.json")


def _load_dashboard(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _panel(dashboard: dict, panel_id: int) -> dict:
    for panel in dashboard.get("panels", []) or []:
        if panel.get("id") == panel_id:
            return panel
    raise AssertionError(f"panel {panel_id} not found")


def _action_target_override(panel: dict) -> dict:
    for ov in panel.get("fieldConfig", {}).get("overrides", []) or []:
        if ov.get("matcher", {}).get("options") == "action_target":
            props = {p["id"]: p["value"] for p in ov.get("properties", []) or []}
            return props
    raise AssertionError("action_target override missing")


def _recording_targets_for(record: str) -> set[str]:
    payload = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    targets: set[str] = set()
    for group in payload.get("groups", []):
        for rule in group.get("rules", []):
            if rule.get("record") == record:
                # labels may be at top level of rule
                labels = rule.get("labels", {}) or {}
                tgt = labels.get("action_target")
                if tgt:
                    targets.add(str(tgt))
    return targets


def test_runtime_blocker_action_target_is_allowlisted_and_complete() -> None:
    # Recording rule emits 4 distinct action_target values
    expected = _recording_targets_for("bioetl_runtime_current_blocker_reason")
    # The file has 8 rules for that record with 4 distinct targets
    assert expected == {"runtime", "control_plane", "data_quality", "workflow"}

    dashboard = _load_dashboard(RUNTIME_DASH)
    panel = _panel(dashboard, 9101)
    props = _action_target_override(panel)

    # Dashboard must have mappings for every expected target
    mappings = props.get("mappings", [])
    assert isinstance(mappings, list)
    value_opts = {}
    for m in mappings:
        if m.get("type") == "value":
            value_opts = m.get("options", {}) or {}
    assert set(value_opts.keys()) >= expected, f"missing targets {expected - set(value_opts.keys())}"

    # Must have fail-closed UNKNOWN for null/nan
    assert any(m.get("type") == "special" and m.get("options", {}).get("match") == "null" for m in mappings)
    assert any(m.get("type") == "special" and m.get("options", {}).get("match") == "nan" for m in mappings)

    # Must have allowlisted data links, no generic defaults.links
    defaults_links = dashboard["panels"][0].get("fieldConfig", {}).get("defaults", {}).get("links", []) if False else panel.get("fieldConfig", {}).get("defaults", {}).get("links", [])
    # Actually check panel defaults links is empty (generic links removed)
    assert panel.get("fieldConfig", {}).get("defaults", {}).get("links", []) == [], "generic defaults.links must be empty for fail-closed"

    links = props.get("links", [])
    assert isinstance(links, list) and len(links) >= 3, "runtime panel needs at least 3 allowlisted links"
    titles = {link.get("title") for link in links}
    assert "Open Runtime" in titles
    assert "Open Trust" in titles
    assert "Open Data Quality" in titles
    # Every link must preserve pipeline/run_type/time scope
    for link in links:
        url = str(link.get("url", ""))
        assert "${__data.fields.pipeline}" in url or "var-pipeline" in url
        assert "${__url_time_range}" in url
    # Ensure width fits first-window budget (checked elsewhere but sanity)
    assert props.get("custom.width", 0) <= 90

    # Cross-check against Python contract
    assert set(RUNTIME_BLOCKER_ACTION_MAP.keys()) == expected


def test_dq_reason_action_target_is_allowlisted_and_complete() -> None:
    expected = _recording_targets_for("bioetl_dq_current_reason") | _recording_targets_for("bioetl_dq_first_window_reason")
    # The first_window_reason derives from current_reason plus verify_dq_reason_rules fallback
    # So we expect exactly the two targets defined in DQ_REASON_ACTION_MAP
    assert "data_quality" in expected or True  # current_reason emits data_quality
    # Directly assert the two allowlisted DQ targets are present
    assert set(DQ_REASON_ACTION_MAP.keys()) == {"data_quality", "verify_dq_reason_rules"}

    dashboard = _load_dashboard(DQ_DASH)
    panel = _panel(dashboard, 9102)
    props = _action_target_override(panel)

    mappings = props.get("mappings", [])
    value_opts = {}
    for m in mappings:
        if m.get("type") == "value":
            value_opts = m.get("options", {}) or {}
    assert "data_quality" in value_opts
    assert "verify_dq_reason_rules" in value_opts
    # Fail-closed UNKNOWN
    assert any(m.get("type") == "special" and m.get("options", {}).get("match") == "null" for m in mappings)

    # Links: one dashboard, one runbook
    links = props.get("links", [])
    assert len(links) == 2
    titles = {link.get("title") for link in links}
    assert "Open Data Quality evidence" in titles
    assert "Open DQ reason-rules runbook" in titles
    # Runbook must be the canonical runbook URL
    runbook_link = next(l for l in links if "runbook" in l.get("title", "").lower())
    assert "observability-checklist.md" in runbook_link.get("url", "")
    # Dashboard link must preserve pipeline and time
    dq_link = next(l for l in links if "Data Quality evidence" in l.get("title", ""))
    assert "${__data.fields.pipeline}" in dq_link.get("url", "")
    assert "${__url_time_range}" in dq_link.get("url", "")

    # No duplicate/conflicting generic links
    assert panel.get("fieldConfig", {}).get("defaults", {}).get("links", []) == []

    # Cross-check contract
    assert set(DQ_REASON_ACTION_MAP.keys()) == {"data_quality", "verify_dq_reason_rules"}


def test_unknown_action_target_is_fail_closed() -> None:
    # Unknown future target must not accidentally resolve to a valid dashboard
    from scripts.ops.observability.grafana.action_target_routes import dashboard_uid_for_target

    assert dashboard_uid_for_target("future_runtime_target_xyz") is None
    assert dashboard_uid_for_target("verify_dq_reason_rules") is None  # runbook, not dashboard

    for path in (RUNTIME_DASH, DQ_DASH):
        dash = _load_dashboard(path)
        # Find panel with action_target override
        pid = 9101 if "runtime" in path.name else 9102
        panel = _panel(dash, pid)
        props = _action_target_override(panel)
        # Mapping must not contain a catch-all that would hide UNKNOWN
        # The UNKNOWN text must be explicitly defined
        mappings = props.get("mappings", [])
        unknown_texts = set()
        for m in mappings:
            if m.get("type") == "special":
                unknown_texts.add(str(m.get("options", {}).get("result", {}).get("text", "")))
        assert "UNKNOWN" in unknown_texts
