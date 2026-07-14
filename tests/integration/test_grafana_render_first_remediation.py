"""Regression contracts for the #6246 render-first remediation program."""

from __future__ import annotations

from html import unescape
import json
from pathlib import Path

import pytest
import yaml


pytestmark = pytest.mark.integration

DASHBOARD_DIR = Path("grafana/dashboards")
CONTROL_RULES = Path("grafana/prometheus-rules/bioetl_control_plane_current_status.yml")
OBSERVABILITY_RULES = Path("grafana/prometheus-rules/bioetl_observability.yml")


def _load(name: str) -> dict[str, object]:
    return json.loads((DASHBOARD_DIR / name).read_text(encoding="utf-8"))


def _iter_panels(panels: list[object]):
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        yield panel
        nested = panel.get("panels")
        if isinstance(nested, list):
            yield from _iter_panels(nested)


def _panel(dashboard: dict[str, object], panel_id: int) -> dict[str, object]:
    matches = [
        panel
        for panel in _iter_panels(list(dashboard.get("panels", [])))
        if panel.get("id") == panel_id
    ]
    assert len(matches) == 1, (dashboard.get("uid"), panel_id, len(matches))
    return matches[0]


def _record_expr(path: Path, record: str) -> str:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    matches = [
        str(rule.get("expr", ""))
        for group in payload.get("groups", [])
        for rule in group.get("rules", [])
        if rule.get("record") == record
    ]
    assert len(matches) == 1, (path, record, len(matches))
    return matches[0]


def _mapping_text(panel: dict[str, object], value: str) -> str:
    mappings = panel.get("fieldConfig", {}).get("defaults", {}).get("mappings", [])
    for mapping in mappings:
        if mapping.get("type") == "value" and value in mapping.get("options", {}):
            return str(mapping["options"][value].get("text", ""))
    raise AssertionError((panel.get("title"), value))


def _mapping_result(panel: dict[str, object], value: str) -> dict[str, object]:
    mappings = panel.get("fieldConfig", {}).get("defaults", {}).get("mappings", [])
    for mapping in mappings:
        if mapping.get("type") == "value" and value in mapping.get("options", {}):
            return dict(mapping["options"][value])
    raise AssertionError((panel.get("title"), value))


def _relative_luminance(hex_color: str) -> float:
    value = hex_color.removeprefix("#")
    if len(value) == 3:
        value = "".join(component * 2 for component in value)
    channels = [int(value[offset : offset + 2], 16) / 255 for offset in (0, 2, 4)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(foreground: str, background: str) -> float:
    first, second = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)),
        reverse=True,
    )
    return (first + 0.05) / (second + 0.05)


def test_rf001_headline_status_is_evidence_aware() -> None:
    control = _load("bioetl-control-plane-v1.json")
    runtime = _load("bioetl-runtime.json")
    dq = _load("bioetl-dq-v2.json")
    workflow = _load("bioetl-workflow-overview.json")

    control_expr = _record_expr(
        CONTROL_RULES, "bioetl_control_plane_current_status_trusted"
    )
    for token in (
        "bioetl_replay_safety_blockers_15m",
        "bioetl_control_plane_checkpoint_evidence_status",
        "bioetl_control_plane_telemetry_missing_5m",
        "* 3",
    ):
        assert token in control_expr
    assert "bioetl_control_plane_current_status_trusted" in str(
        _panel(control, 9401).get("targets")
    )
    assert _mapping_text(_panel(control, 9401), "3") == "INCOMPLETE"

    runtime_expr = _record_expr(
        OBSERVABILITY_RULES, "bioetl_runtime_current_status_trusted"
    )
    assert "bioetl_runtime_trust_gap_active_10m * 3" in runtime_expr
    assert _mapping_text(_panel(runtime, 9401), "3") == "INCOMPLETE"
    assert "green OK is impossible" in str(_panel(runtime, 9401).get("description"))

    assert "bioetl_dq_current_status" in str(_panel(dq, 9401).get("targets"))
    provenance = str(_panel(dq, 9400).get("options", {}).get("content", ""))
    for badge in ("CURRENT", "SELECTED RUN", "TIME RANGE"):
        assert badge in provenance
    for panel_id in (6, 117, 154):
        panel = _panel(dq, panel_id)
        assert panel.get("options", {}).get("colorMode") == "value"
        assert "TIME RANGE delivery impact" in str(panel.get("description"))

    assert "bioetl_runtime_current_status" not in str(
        _panel(workflow, 9404).get("targets")
    )
    assert (
        _panel(workflow, 9404).get("fieldConfig", {}).get("defaults", {}).get("noValue")
        == "NOT RESOLVED"
    )
    for panel_id in (2, 3, 6, 7):
        assert _panel(workflow, panel_id).get("options", {}).get("colorMode") != (
            "background"
        )


def test_rf001_shared_headline_vocabulary_is_fail_closed() -> None:
    trusted_headlines = (
        _panel(_load("bioetl-control-plane-v1.json"), 9401),
        _panel(_load("bioetl-runtime.json"), 9401),
    )
    for panel in trusted_headlines:
        assert _mapping_result(panel, "0") == {"text": "OK", "color": "green"}
        assert _mapping_result(panel, "1") == {"text": "WARN", "color": "orange"}
        assert _mapping_result(panel, "2") == {"text": "CRIT", "color": "red"}
        assert _mapping_result(panel, "3") == {
            "text": "INCOMPLETE",
            "color": "gray",
        }

    design_system = Path("docs/03-guides/dashboards/design-system.md").read_text(
        encoding="utf-8"
    )
    assert "ERROR > INCOMPLETE/UNKNOWN > CRIT > WARN > OK" in design_system


def test_rf002_terminal_states_are_explicit() -> None:
    workflow = _load("bioetl-workflow-overview.json")
    outcomes = _panel(workflow, 4)
    expression = str(outcomes.get("targets", [{}])[0].get("expr", ""))
    assert "count(bioetl_workflow_runs_total) > 0" in expression
    assert "absent(bioetl_workflow_runs_total) * -2" in expression
    assert _mapping_text(outcomes, "-2").startswith("TELEMETRY ABSENT")
    assert _mapping_text(outcomes, "-1").startswith("NO MATCHING SCOPE")
    assert _mapping_text(outcomes, "0").startswith("VALID EMPTY")

    silver = _load("bioetl-silver-reject-explorer.json")
    health = _panel(silver, 13)
    health_text = " ".join(
        (
            str(health.get("description", "")),
            str(health.get("fieldConfig", {}).get("defaults", {}).get("noValue", "")),
        )
    )
    for state in ("HEALTHY", "ERROR", "VALID EMPTY"):
        assert state in health_text
    assert "blank" in health_text and "loading" in health_text

    runtime = _load("bioetl-runtime.json")
    for panel_id in (250, 251, 257, 258):
        panel = _panel(runtime, panel_id)
        no_value = str(
            panel.get("fieldConfig", {}).get("defaults", {}).get("noValue", "")
        )
        assert no_value.startswith("VALID EMPTY")
        assert "ERROR" in no_value


def test_rf003_navigation_is_theme_safe_ordered_and_wrapping() -> None:
    canonical_titles = (
        "0. Control Plane",
        "1. Overview",
        "2. Runtime",
        "3. Provider Health",
        "4. Data Quality",
        "5. Workflow",
        "6. Alerts & SLO",
        "Silver Reject Explorer",
        "Explore Logs",
        "Explore Traces",
    )
    for path in sorted(DASHBOARD_DIR.glob("bioetl-*.json")):
        dashboard = json.loads(path.read_text(encoding="utf-8"))
        content = unescape(
            str(_panel(dashboard, 1000).get("options", {}).get("content", ""))
        )
        positions = [content.index(title) for title in canonical_titles]
        assert positions == sorted(positions), path.name
        for token in (
            "flex-wrap:wrap",
            "@media(max-width:1100px)",
            "color:#f8fafc",
            "background:#334155",
            ":hover",
            ":focus-visible",
            "outline:3px solid #38bdf8",
            "background:#1d4ed8",
        ):
            assert token in content, (path.name, token)


def test_rf003_navigation_tokens_meet_wcag_contrast_floors() -> None:
    text_pairs = (
        ("#f8fafc", "#334155"),
        ("#ffffff", "#475569"),
        ("#ffffff", "#1d4ed8"),
    )
    boundary_pairs = (
        ("#94a3b8", "#334155"),
        ("#38bdf8", "#334155"),
        ("#7dd3fc", "#1d4ed8"),
    )
    assert all(_contrast_ratio(*pair) >= 4.5 for pair in text_pairs)
    assert all(_contrast_ratio(*pair) >= 3.0 for pair in boundary_pairs)


def test_rf003_1024_layout_prioritizes_actions_and_readability() -> None:
    overview = _load("bioetl-overview-v2.json")
    first_action = _panel(overview, 215)
    assert first_action["title"] == "First Action"
    assert first_action["gridPos"]["h"] >= 10
    assert first_action["gridPos"]["w"] >= 8
    assert len(str(first_action["title"])) <= 24
    assert len(first_action.get("options", {}).get("dataLinks", [])) >= 5
    assert _panel(overview, 9002)["gridPos"]["w"] == 24

    workflow = _load("bioetl-workflow-overview.json")
    assert _panel(workflow, 9)["gridPos"]["w"] == 24
    provider = _load("bioetl-provider-health-v2.json")
    assert _panel(provider, 9103)["gridPos"]["w"] >= 10
    silver = _load("bioetl-silver-reject-explorer.json")
    for panel_id in (10, 2, 3, 4, 5, 6, 7):
        assert _panel(silver, panel_id)["gridPos"]["w"] == 24


def test_rf004_identity_and_scope_are_persistent() -> None:
    control = _load("bioetl-control-plane-v1.json")
    assert _panel(control, 9404)["gridPos"]["y"] <= 13
    copy_panel = _panel(control, 9407)
    assert copy_panel["gridPos"]["y"] <= 17
    assert "data:text/plain" in str(copy_panel.get("fieldConfig"))

    for name in (
        "bioetl-control-plane-v1.json",
        "bioetl-runtime.json",
        "bioetl-provider-health-v2.json",
        "bioetl-dq-v2.json",
        "bioetl-workflow-overview.json",
    ):
        no_value = str(
            _panel(_load(name), 9402)
            .get("fieldConfig", {})
            .get("defaults", {})
            .get("noValue", "")
        )
        assert no_value.startswith("Not resolved")

    alerts = _load("bioetl-alerts-slo.json")
    alert_table = _panel(alerts, 5)
    expression = str(alert_table.get("targets", [{}])[0].get("expr", ""))
    for scope in ('"Pipeline"', '"Global"'):
        assert scope in expression
    assert "run_id" not in expression
    scope_override = next(
        override
        for override in alert_table.get("fieldConfig", {}).get("overrides", [])
        if override.get("matcher", {}).get("options") == "scope"
    )
    scope_mapping = next(
        prop.get("value", {})
        for prop in scope_override.get("properties", [])
        if prop.get("id") == "mappings"
    )
    mapped_scopes = scope_mapping[0].get("options", {})
    assert {"Global", "Pipeline", "Run"} <= set(mapped_scopes)

    silver = _load("bioetl-silver-reject-explorer.json")
    assert "Reset once" in str(_panel(silver, 1).get("options", {}).get("content"))
    for variable in silver.get("templating", {}).get("list", []):
        description = str(variable.get("description", ""))
        assert "Warning reason" in description
        assert "Recovery:" in description


def test_rf005_incident_hierarchy_and_semantic_encoding() -> None:
    overview = _load("bioetl-overview-v2.json")
    assert _panel(overview, 215)["gridPos"]["y"] == 7
    assert _panel(overview, 9601)["gridPos"]["y"] == 24
    assert _panel(overview, 9018).get("type") == "state-timeline"
    assert _panel(overview, 9020).get("type") == "state-timeline"

    provider = _load("bioetl-provider-health-v2.json")
    failure_rate = _panel(provider, 104)
    assert failure_rate.get("type") == "stat"
    assert failure_rate.get("options", {}).get("colorMode") == "value"
    assert (
        failure_rate.get("fieldConfig", {})
        .get("defaults", {})
        .get("thresholds", {})
        .get("steps", [])[0]
        .get("color")
        == "gray"
    )

    dq = _load("bioetl-dq-v2.json")
    freshness = _panel(dq, 8)
    assert "hours; SLA 24/72" in str(freshness.get("title"))
    assert freshness.get("fieldConfig", {}).get("defaults", {}).get("unit") == "h"
    assert [
        step.get("value")
        for step in freshness.get("fieldConfig", {})
        .get("defaults", {})
        .get("thresholds", {})
        .get("steps", [])
    ] == [None, 24, 72]

    alerts = _load("bioetl-alerts-slo.json")
    assert _panel(alerts, 2).get("options", {}).get("colorMode") == "value"
    critical_steps = (
        _panel(alerts, 3)
        .get("fieldConfig", {})
        .get("defaults", {})
        .get("thresholds", {})
        .get("steps", [])
    )
    assert critical_steps[1] == {"color": "red", "value": 1}


def test_rf006_progressive_disclosure_reduces_first_path() -> None:
    control = _load("bioetl-control-plane-v1.json")
    root_panels = list(control.get("panels", []))
    assert max(panel["gridPos"]["y"] for panel in root_panels) <= 29
    control_rows = [panel for panel in root_panels if panel.get("type") == "row"]
    assert len(control_rows) == 5
    assert all(
        panel.get("collapsed") is True and panel.get("panels") for panel in control_rows
    )

    overview = _load("bioetl-overview-v2.json")
    inputs = _panel(overview, 9002)
    assert inputs["gridPos"] == {"h": 6, "w": 24, "x": 0, "y": 17}
    root_ids = {panel.get("id") for panel in overview.get("panels", [])}
    assert not ({9003, 9004, 9005, 9006, 9007, 9013} & root_ids)
    diagnostics = _panel(overview, 9012)
    assert {panel.get("id") for panel in diagnostics.get("panels", [])} == {
        9021,
        9003,
        9004,
        9005,
        9006,
        9007,
        9013,
    }
    for row_id in (9014, 9009, 9012):
        assert _panel(overview, row_id).get("collapsed") is True
    assert _panel(overview, 9600).get("collapsed") is False
    assert 9601 in root_ids
    assert [
        _panel(overview, panel_id)["gridPos"]["y"]
        for panel_id in (9600, 9601, 9014, 9009, 9012)
    ] == [23, 24, 30, 31, 32]

    runtime = _load("bioetl-runtime.json")
    for row_id in (252, 253, 254, 255):
        assert _panel(runtime, row_id).get("collapsed") is True

    alerts = _load("bioetl-alerts-slo.json")
    assert _panel(alerts, 5)["gridPos"]["h"] == 6

    silver = _load("bioetl-silver-reject-explorer.json")
    assert _panel(silver, 16).get("type") == "row"
    assert _panel(silver, 15).get("type") == "row"
    assert _panel(silver, 10)["gridPos"]["h"] == 3


def test_rf007_counts_and_dense_legends_are_bounded() -> None:
    runtime = _load("bioetl-runtime.json")
    for panel_id in (240, 241):
        assert (
            _panel(runtime, panel_id)
            .get("fieldConfig", {})
            .get("defaults", {})
            .get("decimals")
            == 0
        )
    assert _panel(runtime, 240).get("targets", [{}])[0].get("legendFormat") == (
        "{{stage}}"
    )

    dq = _load("bioetl-dq-v2.json")
    for panel_id in (1, 10, 11, 153, 155):
        legend = _panel(dq, panel_id).get("options", {}).get("legend")
        if isinstance(legend, dict):
            assert legend.get("showLegend") is False
        assert "full identifiers remain available" in str(
            _panel(dq, panel_id).get("description", "")
        )
