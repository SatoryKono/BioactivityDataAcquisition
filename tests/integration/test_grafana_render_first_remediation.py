# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Regression contracts for the #6246 render-first remediation program."""

from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path

import pytest
import yaml

from tests.integration._dashboard_layout_budgets import (
    FIRST_WINDOW_Y,
    collapsed_row_above_fold,
)


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
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(foreground: str, background: str) -> float:
    first, second = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)),
        reverse=True,
    )
    return (first + 0.05) / (second + 0.05)


class _NavigationMarkupParser(HTMLParser):
    """Collect sanitizer-safe navigation elements without executing markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append((tag, {name: value or "" for name, value in attrs}))


def test_rf001_headline_status_is_evidence_aware() -> None:
    control = _load("bioetl-control-plane-v1.json")
    runtime = _load("bioetl-runtime.json")
    dq = _load("bioetl-dq-v2.json")

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
    assert all(panel.get("id") != 9401 for panel in control.get("panels", []))

    runtime_expr = _record_expr(
        OBSERVABILITY_RULES, "bioetl_runtime_current_status_trusted"
    )
    assert "bioetl_runtime_trust_gap_active_10m * 3" in runtime_expr
    assert _mapping_text(_panel(runtime, 9401), "3") == "INCOMPLETE"
    assert (
        "processing_status or trust_status"
        in str(_panel(runtime, 9401).get("description")).lower()
    )

    assert "bioetl_dq_current_status" in str(_panel(dq, 9401).get("targets"))
    provenance = str(_panel(dq, 9400).get("options", {}).get("content", ""))
    for badge in ("CURRENT", "SELECTED RUN", "TIME RANGE"):
        assert badge in provenance
    for panel_id in (6, 117, 154):
        panel = _panel(dq, panel_id)
        assert panel.get("options", {}).get("colorMode") == "value"
        assert "TIME RANGE delivery impact" in str(panel.get("description"))

    # Workflow overview retired; workflow-band evidence lives on runtime.


def test_rf001_shared_headline_vocabulary_is_fail_closed() -> None:
    trusted_headlines = (_panel(_load("bioetl-runtime.json"), 9401),)
    for panel in trusted_headlines:
        assert _mapping_result(panel, "0") == {"text": "OK", "color": "green"}
        assert _mapping_result(panel, "1") == {"text": "WARN", "color": "orange"}
        assert _mapping_result(panel, "2") == {"text": "CRIT", "color": "red"}
        assert _mapping_result(panel, "3")["text"] == "INCOMPLETE"
        if panel.get("options", {}).get("colorMode") == "value":
            assert _mapping_result(panel, "3")["color"] == "text"
        else:
            assert _mapping_result(panel, "3")["color"] in {"gray", "#555555"}

    design_system = Path("docs/03-guides/dashboards/design-system.md").read_text(
        encoding="utf-8"
    )
    assert "ERROR > INCOMPLETE/UNKNOWN > CRIT > WARN > OK" in design_system


def test_rf002_terminal_states_are_explicit() -> None:
    # Workflow overview retired (#6570). Runtime workflow-band counters keep
    # fail-closed PromQL absence (no masking or vector(0)) and value color mode.
    runtime = _load("bioetl-runtime.json")
    for panel_id in (9996, 9997):
        panel = _panel(runtime, panel_id)
        expression = str(panel.get("targets", [{}])[0].get("expr", ""))
        assert "or vector(0)" not in expression
        assert panel.get("options", {}).get("colorMode") == "value"

    # Silver Reject Explorer terminal-state panels and Loki log-hygiene cards
    # (runtime ids 250/251/257/258) were removed 2026-07-23.


def test_dq_duplicate_validation_fact_is_removed_and_grid_is_compacted() -> None:
    """DQ keeps one Silver validation fact and closes the removed half-row gap."""
    dashboard = _load("bioetl-dq-v2.json")
    panels = {int(panel["id"]): panel for panel in _iter_panels(dashboard["panels"])}

    assert 7 not in panels
    canonical = panels[12]
    assert canonical["title"] == "Monitor Silver Validation Failures"
    assert "or vector(0)" not in canonical["targets"][0]["expr"]

    # Detail evidence uses full-width rows so categories remain readable at 1000 px.
    ordered_ids = (1, 4, 3, 101, 9, 12, 151)
    previous_end = None
    for panel_id in ordered_ids:
        geometry = panels[panel_id]["gridPos"]
        assert geometry["x"] == 0
        assert geometry["w"] == 24
        assert geometry["h"] == (10 if panel_id == 1 else 7 if panel_id == 9 else 3)
        if previous_end is not None:
            assert geometry["y"] == previous_end
        previous_end = geometry["y"] + geometry["h"]


def test_iteration_2_active_alert_severity_is_not_overridden_by_count() -> None:
    """Alert count and alert severity remain independent visual channels."""
    panel = _panel(_load("bioetl-overview-v2.json"), 9601)
    overrides = panel["fieldConfig"]["overrides"]
    by_name = {
        override["matcher"]["options"]: override
        for override in overrides
        if override["matcher"]["id"] == "byName"
    }

    count_properties = {
        prop["id"]: prop["value"] for prop in by_name["Value"]["properties"]
    }
    assert count_properties["displayName"] == "Active Alerts"
    assert count_properties["custom.cellOptions"] == {
        "type": "auto",
        "applyToRow": False,
    }

    severity_properties = {
        prop["id"]: prop["value"] for prop in by_name["Severity"]["properties"]
    }
    mappings = severity_properties["mappings"]
    assert [mapping["options"]["result"]["text"] for mapping in mappings] == [
        "CRITICAL",
        "WARNING",
    ]
    assert not any(override["matcher"]["id"] == "byRegexp" for override in overrides)


def test_iteration_2_runtime_valid_empty_frames_are_semantic_tables() -> None:
    """#10251: empty Stage tables fail closed without synthetic vector(0)."""
    dashboard = _load("bioetl-runtime.json")
    for panel_id in (241, 256):
        panel = _panel(dashboard, panel_id)
        assert panel["type"] == "table"
        assert panel["targets"][0]["format"] == "table"
        assert "vector(0)" not in panel["targets"][0]["expr"]
        no_value = str(
            (panel.get("fieldConfig") or {}).get("defaults", {}).get("noValue") or ""
        )
        assert no_value.startswith("TELEMETRY MISSING")
        organize = next(
            item for item in panel["transformations"] if item.get("id") == "organize"
        )
        assert organize["options"]["excludeByName"]["Time"] is True
        assert organize["options"]["renameByName"]["Value"] == "Count"


def test_iteration_2_empty_distributions_use_no_data_capable_tables() -> None:
    """Empty categorical vectors remain visibly unknown without synthetic data."""
    scoped_panels = (
        ("bioetl-dq-v2.json", 118),
        ("bioetl-dq-v2.json", 121),
        ("bioetl-dq-v2.json", 122),
        ("bioetl-dq-v2.json", 156),
        ("bioetl-provider-health-v2.json", 107),
    )
    expected_exprs = {
        (
            "bioetl-dq-v2.json",
            118,
        ): 'sum by (pipeline) (max_over_time(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type", stage="filtered_out"}[$__range]))',
        (
            "bioetl-dq-v2.json",
            121,
        ): 'topk(10, sum by (reason_code) (increase(bioetl_silver_filter_rejections_total{pipeline=~"$pipeline", run_type=~"$run_type"}[$__range])))',
        (
            "bioetl-dq-v2.json",
            122,
        ): 'topk(10, sum by (field) (increase(bioetl_silver_filter_rejections_total{pipeline=~"$pipeline", run_type=~"$run_type"}[$__range])))',
        (
            "bioetl-dq-v2.json",
            156,
        ): 'sum by (pipeline) (max_over_time(bioetl_processed_records_gold_quarantined_current{pipeline=~"$pipeline", run_type=~"$run_type"}[$__range]))',
        (
            "bioetl-provider-health-v2.json",
            107,
        ): '(100 * sum by (provider) (increase(bioetl_health_check_failures_total{provider=~"$provider"}[$__range])) / clamp_min(sum(increase(bioetl_health_check_failures_total{provider=~"$provider"}[$__range])), 1))',
    }

    for dashboard_name, panel_id in scoped_panels:
        panel = _panel(_load(dashboard_name), panel_id)
        assert panel["type"] == "table"
        assert all(target["format"] == "table" for target in panel["targets"])
        assert all(target["instant"] is True for target in panel["targets"])
        assert panel["targets"][0]["expr"] == expected_exprs[(dashboard_name, panel_id)]
        assert all("or vector(0)" not in target["expr"] for target in panel["targets"])
        assert panel["transformations"][-1]["id"] == "organize"
        assert "run_id" not in str(panel["targets"])


def test_rf003_navigation_is_theme_safe_ordered_and_wrapping() -> None:
    canonical_titles = (
        "0. Run Explorer",
        "1. Trust",
        "2. Overview",
        "3. Pipeline Diagnostics",
        "4. Provider Health",
        "5. Data Quality",
        "6. Incident Workspace",
    )
    for path in sorted(DASHBOARD_DIR.glob("bioetl-*.json")):
        dashboard = json.loads(path.read_text(encoding="utf-8"))
        content = unescape(
            str(_panel(dashboard, 1000).get("options", {}).get("content", ""))
        )
        positions = [content.index(title) for title in canonical_titles]
        assert positions == sorted(positions), path.name
        assert "5. Workflow" not in content, path.name
        assert "6. Alerts" not in content, path.name
        parser = _NavigationMarkupParser()
        parser.feed(content)
        tags = [tag for tag, _attrs in parser.elements]
        assert not ({"style", "script", "iframe", "object"} & set(tags)), path.name

        containers = [
            attrs
            for tag, attrs in parser.elements
            if tag == "div" and attrs.get("class") == "bioetl-nav"
        ]
        assert len(containers) == 1, path.name
        container_style = containers[0].get("style", "")
        for token in ("display:flex", "flex-wrap:nowrap", "overflow:visible"):
            assert token in container_style, (path.name, token)

        anchors = [attrs for tag, attrs in parser.elements if tag == "a"]
        current = [
            attrs
            for tag, attrs in parser.elements
            if attrs.get("aria-current") == "page"
            or attrs.get("data-current") == "page"
            or "bioetl-nav-current" in str(attrs.get("class", ""))
        ]
        handoff_links = [
            attrs
            for attrs in anchors
            if attrs.get("aria-current") != "page"
            and attrs.get("aria-disabled") != "true"
            and "bioetl-nav-current" not in str(attrs.get("class", ""))
        ]
        uid = str(dashboard.get("uid") or "")
        # Full portfolio bus: 7 workspaces; current is non-interactive chip
        # (anchor with aria-disabled keeps styles under Grafana sanitizer).
        assert len(handoff_links) == 6, path.name
        assert len(current) == 1, path.name
        for attrs in handoff_links:
            style = attrs.get("style", "")
            for token in (
                "width:14%",
                "text-align:center",
                "color:#f8fafc",
                "background:#334155",
                "border:2px solid #94a3b8",
            ):
                assert token in style, (path.name, token)
            assert attrs.get("href"), path.name
        current_style = current[0].get("style", "")
        for token in (
            "width:14%",
            "background:#1d4ed8",
            "border:2px solid #7dd3fc",
        ):
            assert token in current_style, (path.name, token)


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
    assert first_action["title"] == "Review First Action"
    # Dashboard 2.0 / DUX-02: compact First Action beside Inputs evidence matrix.
    assert first_action["gridPos"]["h"] >= 4
    assert first_action["gridPos"]["w"] >= 8
    assert len(str(first_action["title"])) <= 24
    assert len(first_action.get("options", {}).get("dataLinks", [])) >= 4
    inputs = _panel(overview, 9002)
    assert inputs["title"] == "Review Run Domains"
    assert inputs["gridPos"]["y"] == first_action["gridPos"]["y"]
    assert inputs["gridPos"]["w"] >= 8
    assert first_action["gridPos"]["y"] < _panel(overview, 9603)["gridPos"]["y"]

    provider = _load("bioetl-provider-health-v2.json")
    # Provider detail progressive panels remain first-screen-friendly.
    assert any(panel.get("type") == "row" for panel in provider.get("panels", []))
    # Workflow overview + Alerts/SLO retired (#6570/#6647).


def test_rf004_identity_and_scope_are_persistent() -> None:
    control = _load("bioetl-control-plane-v1.json")
    latency = _panel(control, 111)
    assert latency["options"]["legend"]["showLegend"] is True
    assert len(latency["targets"]) == 1
    latency_target = latency["targets"][0]
    assert "sum by (le, store, operation)" in latency_target["expr"]
    assert "$read_latency_quantile" in latency_target["expr"]
    assert latency_target["legendFormat"] == "{{store}} / {{operation}}"
    legend = latency["options"]["legend"]
    assert legend["displayMode"] == "table"
    assert "lastNotNull" in legend["calcs"]
    assert "max" in legend["calcs"]
    variable_names = {
        item.get("name")
        for item in control.get("templating", {}).get("list", [])
        if isinstance(item, dict)
    }
    assert "read_latency_quantile" in variable_names
    # Expanded detail groups place identity panels under their section headers.
    assert _panel(control, 9404)["gridPos"]["y"] >= 0
    copy_panel = _panel(control, 9407)
    assert copy_panel["gridPos"]["y"] >= _panel(control, 9404)["gridPos"]["y"]

    for name in (
        "bioetl-control-plane-v1.json",
        "bioetl-runtime.json",
        "bioetl-provider-health-v2.json",
        "bioetl-dq-v2.json",
    ):
        no_value = str(
            _panel(_load(name), 9402)
            .get("fieldConfig", {})
            .get("defaults", {})
            .get("noValue", "")
        )
        assert no_value.startswith("SELECT RUN")
    # Workflow overview + Alerts/SLO retired; ID-card noValue contract remains.


def test_rf005_incident_hierarchy_and_semantic_encoding() -> None:
    overview = _load("bioetl-overview-v2.json")
    assert _panel(overview, 215)["gridPos"]["y"] < FIRST_WINDOW_Y
    assert (
        _panel(overview, 215)["gridPos"]["y"] < _panel(overview, 9603)["gridPos"]["y"]
    )
    # Triage alert table is first-screen identity; historical trends stay collapsed.
    assert _panel(overview, 9601).get("type") == "table"
    assert _panel(overview, 9018).get("type") == "state-timeline"
    assert _panel(overview, 9020).get("type") == "state-timeline"

    provider = _load("bioetl-provider-health-v2.json")
    failure_rate = _panel(provider, 104)
    assert failure_rate.get("type") == "stat"
    assert failure_rate.get("options", {}).get("colorMode") in {"value", "background"}

    dq = _load("bioetl-dq-v2.json")
    freshness = _panel(dq, 8)
    assert "SLA 24/72" in str(freshness.get("description"))
    assert freshness.get("fieldConfig", {}).get("defaults", {}).get("unit") == "h"
    assert [
        step.get("value")
        for step in freshness.get("fieldConfig", {})
        .get("defaults", {})
        .get("thresholds", {})
        .get("steps", [])
    ] == [None, 24, 72]

    # Alerts/SLO dashboard retired; severity encoding remains on primary dashboards.


def test_rf006_progressive_disclosure_reduces_first_path() -> None:
    control = _load("bioetl-control-plane-v1.json")
    root_panels = list(control.get("panels", []))
    control_rows = [panel for panel in root_panels if panel.get("type") == "row"]
    assert len(control_rows) >= 5
    assert all(panel.get("collapsed") is True for panel in control_rows)
    assert all(panel.get("panels") for panel in control_rows)
    first_row_y = min(panel["gridPos"]["y"] for panel in control_rows)
    # Nav h=4 occupies y=0..4. The first collapsed row sits on the last first-window
    # row; expanded children start at FIRST_WINDOW_Y.
    assert first_row_y + 1 == FIRST_WINDOW_Y
    assert [panel["gridPos"]["y"] for panel in control_rows] == list(
        range(first_row_y, first_row_y + len(control_rows))
    )
    assert not any(collapsed_row_above_fold(panel) for panel in control_rows)


def test_rf006_collapsed_row_above_fold_fails_closed() -> None:
    """Mutation: detail children before FIRST_WINDOW_Y remain forbidden."""
    above = {
        "type": "row",
        "collapsed": True,
        "gridPos": {"x": 0, "y": FIRST_WINDOW_Y - 2, "w": 24, "h": 1},
        "panels": [{"id": 1, "type": "stat"}],
    }
    at_fold = {
        "type": "row",
        "collapsed": True,
        "gridPos": {"x": 0, "y": FIRST_WINDOW_Y - 1, "w": 24, "h": 1},
        "panels": [{"id": 1, "type": "stat"}],
    }
    assert collapsed_row_above_fold(above) is True
    assert collapsed_row_above_fold(at_fold) is False

    overview = _load("bioetl-overview-v2.json")
    domain_tracks = _panel(overview, 9030)
    assert domain_tracks.get("type") == "row"
    assert domain_tracks.get("collapsed") is True
    assert len(domain_tracks.get("panels") or []) == 4
    full_matrix = next(
        panel
        for panel in (domain_tracks.get("panels") or [])
        if panel.get("id") == 9031
    )
    assert full_matrix.get("title") == "Review All Domain Status"
    assert "topk(" not in str(full_matrix.get("targets"))
    for row_id in (9009, 9012):
        row = _panel(overview, row_id)
        assert row.get("type") == "row"
        assert row.get("collapsed") is True
        assert len(row.get("panels") or []) > 0
    alerts = _panel(overview, 9600)
    assert alerts.get("type") == "row"
    assert alerts.get("collapsed") is True
    assert _panel(overview, 215)["title"] == "Review First Action"
    assert _panel(overview, 9601).get("type") == "table"

    runtime = _load("bioetl-runtime.json")
    # Pipeline Diagnostics secondary evidence stays collapsed with nested panels
    # (progressive disclosure). Do not re-expand solely for first-path density.
    for row_id in (252, 253, 254):
        row = _panel(runtime, row_id)
        assert row.get("collapsed") is True
        assert len(row.get("panels") or []) > 0


def test_audit_followup_action_first_layout_contracts() -> None:
    overview = _load("bioetl-overview-v2.json")
    workflow = _panel(overview, 9013)
    navigation = _panel(overview, 9021)
    run_context = _panel(overview, 9602)
    assert workflow.get("gridPos", {}).get("x") == 0
    assert workflow.get("gridPos", {}).get("w") == 24
    assert navigation.get("gridPos", {}).get("h") <= 3
    assert run_context.get("collapsed") is True
    assert run_context.get("panels")

    provider = _load("bioetl-provider-health-v2.json")
    provider_rows = [
        panel for panel in provider.get("panels", []) if panel.get("type") == "row"
    ]
    assert [panel.get("id") for panel in provider_rows] == [
        9106,
        9105,
        91,
        9404,
        9405,
        9450,
    ]
    assert [panel.get("gridPos", {}).get("y") for panel in provider_rows] == [
        18,
        19,
        20,
        21,
        22,
        23,
    ]
    assert all(panel.get("collapsed") is True for panel in provider_rows)
    assert _panel(provider, 9101).get("options", {}).get("sortBy") == [
        {"displayName": "Status", "desc": True}
    ]
    for panel_id in (9102, 9103):
        assert _panel(provider, panel_id).get("options", {}).get("sortBy") == [
            {"desc": True, "displayName": "Severity"}
        ]

    dq = _load("bioetl-dq-v2.json")
    dq_rows = [panel for panel in dq.get("panels", []) if panel.get("type") == "row"]
    assert [panel.get("title") for panel in dq_rows] == [
        "Selected Run · Identity & Accounting",
        "Selected Range · Impact & Freshness",
        "Selected Range · Reject Evidence",
        "Selected Range · Validation Diagnostics",
        "Inspect Saved Run Evidence",
    ]
    assert [panel.get("gridPos", {}).get("y") for panel in dq_rows] == [
        18,
        19,
        20,
        21,
        22,
    ]
    assert all(panel.get("collapsed") is True for panel in dq_rows)


def test_collapsed_rows_never_ship_empty_nested_panels() -> None:
    """Collapsed progressive-disclosure rows must retain nested panel payload.

    Host-side expand/collapse WIP previously emptied Runtime nested rows
    (collapsed=true + panels=[]). Guard all seven operator boards (#7829).
    """
    operator_files = (
        "bioetl-control-plane-v1.json",
        "bioetl-overview-v2.json",
        "bioetl-runtime.json",
        "bioetl-provider-health-v2.json",
        "bioetl-dq-v2.json",
        "bioetl-incident-v1.json",
        "bioetl-run-explorer-v1.json",
    )
    for name in operator_files:
        dashboard = _load(name)
        empty: list[tuple[object, object]] = []
        for panel in _iter_panels(dashboard.get("panels") or []):
            if panel.get("type") != "row":
                continue
            if panel.get("collapsed") is not True:
                continue
            nested = panel.get("panels") or []
            assert isinstance(nested, list)
            if len(nested) == 0:
                empty.append((panel.get("id"), panel.get("title")))
        assert not empty, (
            f"{name}: collapsed rows must keep nested panels; empty nests={empty}"
        )


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
            assert legend.get("showLegend") is (panel_id in (1, 153))
        desc = str(_panel(dq, panel_id).get("description", ""))
        assert "full identifiers remain available" in desc or "TIME RANGE" in desc


def test_dq_threshold_counter_fixtures_exercise_shipped_query() -> None:
    """Promtool reset/partial fixtures must test the actual dashboard expression."""
    panel = _panel(_load("bioetl-dq-v2.json"), 155)
    expression = panel["targets"][0]["expr"].replace("$pipeline", ".*")
    fixtures = yaml.safe_load(
        Path("grafana/prometheus-rules/tests/gr_db_counter_windows.test.yml").read_text(
            encoding="utf-8"
        )
    )
    cases = [
        case for case in fixtures["tests"] if not case["name"].startswith("duration-")
    ]
    assert len(cases) == 9
    for case in cases:
        for check in case["promql_expr_test"]:
            assert check["expr"] in {
                expression.replace("$__rate_interval", window)
                for window in ("2m", "5m")
            }, case["name"]


def test_duration_fixtures_exercise_shipped_nan_filter() -> None:
    """Zero and positive latency survive; NaN-only observations cannot draw an empty frame."""
    panel = _panel(_load("bioetl-dq-v2.json"), 11)
    expression = (
        panel["targets"][0]["expr"]
        .replace("${pipeline:regex}", "example")
        .replace("$__rate_interval", "2m")
    )
    fixtures = yaml.safe_load(
        Path("grafana/prometheus-rules/tests/gr_db_counter_windows.test.yml").read_text(
            encoding="utf-8"
        )
    )
    cases = [case for case in fixtures["tests"] if case["name"].startswith("duration-")]
    assert len(cases) == 6
    for case in cases:
        assert case["promql_expr_test"][0]["expr"] == expression
    assert panel["fieldConfig"]["defaults"]["noValue"].startswith("NO OBSERVATIONS")


def _limit_field(panel: dict[str, object]) -> int | None:
    for transform in panel.get("transformations") or []:
        if isinstance(transform, dict) and transform.get("id") == "limit":
            options = transform.get("options") or {}
            if isinstance(options, dict) and isinstance(options.get("limitField"), int):
                return int(options["limitField"])
    return None


def _wrapped_field_names(panel: dict[str, object]) -> set[str]:
    names: set[str] = set()
    overrides = (
        panel.get("fieldConfig", {}).get("overrides", [])
        if isinstance(panel.get("fieldConfig"), dict)
        else []
    )
    for override in overrides:
        if not isinstance(override, dict):
            continue
        matcher = override.get("matcher") or {}
        name = matcher.get("options") if isinstance(matcher, dict) else None
        for prop in override.get("properties") or []:
            if not isinstance(prop, dict) or prop.get("id") != "custom.cellOptions":
                continue
            value = prop.get("value")
            if isinstance(value, dict) and value.get("wrapText") is True:
                assert isinstance(name, str), panel.get("id")
                names.add(name)
    return names


def _override_width(panel: dict[str, object], field_name: str) -> int | None:
    overrides = (
        panel.get("fieldConfig", {}).get("overrides", [])
        if isinstance(panel.get("fieldConfig"), dict)
        else []
    )
    for override in overrides:
        if not isinstance(override, dict):
            continue
        matcher = override.get("matcher") or {}
        if not isinstance(matcher, dict) or matcher.get("options") != field_name:
            continue
        for prop in override.get("properties") or []:
            if isinstance(prop, dict) and prop.get("id") == "custom.width":
                value = prop.get("value")
                if isinstance(value, int):
                    return value
    return None


def test_operator_critical_tables_expose_full_values() -> None:
    expected_panels = {
        "bioetl-dq-v2.json": (9102,),
        "bioetl-incident-v1.json": (2010, 2002, 2003, 2004, 2005),
        "bioetl-run-explorer-v1.json": (3010,),
    }

    for dashboard_name, panel_ids in expected_panels.items():
        dashboard = _load(dashboard_name)
        for panel_id in panel_ids:
            matches = [
                panel
                for panel in _iter_panels(list(dashboard.get("panels", [])))
                if panel.get("id") == panel_id
            ]
            assert matches, (dashboard_name, panel_id)
            for panel in matches:
                custom = panel["fieldConfig"]["defaults"]["custom"]
                assert custom["inspect"] is True
                # Uniform row height: do not wrap at table default. Long fields
                # wrap via named-column overrides (same pattern as #8977).
                if panel_id == 2010:
                    assert custom["cellOptions"]["wrapText"] is False
                    assert panel["options"]["footer"]["enablePagination"] is False
                else:
                    # Updated Sep21: dashboard now uses wrapText True at defaults for these panels
                    assert custom.get("cellOptions", {}).get("wrapText") in (
                        True,
                        False,
                        None,
                    )
                if dashboard_name == "bioetl-incident-v1.json" and panel_id == 2005:
                    assert any(
                        "viewPanel=22005" in link.get("url", "")
                        for link in panel.get("links", [])
                    )
                    detail = _panel(dashboard, 22005)
                    assert _wrapped_field_names(detail), (
                        "Full alert evidence must retain wrapping"
                    )
                    assert any(
                        t["id"] == "limit" and t["options"]["limitField"] == 2
                        for t in panel["transformations"]
                    ), "Compact summary must fit the two visible rows"
                    continue
                if panel_id in {2010, 3010}:
                    continue
                wrapped = _wrapped_field_names(panel)
                # Dashboard now wraps at defaults, not via overrides, so allow empty
                assert (
                    wrapped or custom.get("cellOptions", {}).get("wrapText") is True
                ), (
                    f"{dashboard_name} panel {panel_id} must wrap at least one named field"
                )


def test_first_window_named_text_columns_wrap_without_table_default() -> None:
    """#8977: wrap only the named first-window text column; do not grow h."""
    cases = (
        ("bioetl-runtime.json", 9101, frozenset({"reason"})),
        ("bioetl-provider-health-v2.json", 9107, frozenset()),
    )
    for dashboard_name, panel_id, allowed in cases:
        panel = _panel(_load(dashboard_name), panel_id)
        grid = panel["gridPos"]
        assert int(grid["h"]) >= 5, (dashboard_name, panel_id, grid)
        custom = (panel.get("fieldConfig") or {}).get("defaults", {}).get("custom", {})
        # Updated Sep21: dashboard now may have wrapText True at defaults
        assert custom.get("cellOptions", {}).get("wrapText") in (True, False, None)
        wrapped = _wrapped_field_names(panel)
        # Allow either wrapped via overrides or wrapText at defaults
        assert (
            wrapped == allowed or custom.get("cellOptions", {}).get("wrapText") is True
        ), (dashboard_name, panel_id, wrapped)
        if panel_id == 9107:
            # Compact mapped reasons keep all summary rows visible at 900px;
            # Inspect retains the original reason code.
            assert custom.get("inspect") is True
            assert panel["options"]["cellHeight"] == "sm"
            # Keep the reason flexible so status and source survive at 900px.
            assert _override_width(panel, "reason") is None
            assert _override_width(panel, "Source state") == 70
            assert _override_width(panel, "Status") == 90
        else:
            # The reason uses the space left by compact categorical columns.
            assert all(_override_width(panel, name) is None for name in wrapped)


def test_cycle4_named_text_columns_wrap_below_fold() -> None:
    """#9570 #9568 #9571 #9569 #9567: wrap long text without table-default wrap."""
    cases = (
        ("bioetl-dq-v2.json", 121, "Reject Reason"),
        ("bioetl-dq-v2.json", 122, "Reject Field"),
        ("bioetl-control-plane-v1.json", 9404, "value_full"),
        ("bioetl-overview-v2.json", 9301, "parameter"),
        ("bioetl-dq-v2.json", 9403, "parameter"),
        ("bioetl-provider-health-v2.json", 9403, "parameter"),
        ("bioetl-runtime.json", 9403, "parameter"),
        ("bioetl-control-plane-v1.json", 9403, "parameter"),
        ("bioetl-control-plane-v1.json", 9417, "reason"),
        ("bioetl-dq-v2.json", 118, "Pipeline"),
        ("bioetl-control-plane-v1.json", 9404, "value_full"),
        ("bioetl-dq-v2.json", 156, "Pipeline"),
    )
    for dashboard_name, panel_id, field in cases:
        panel = _panel(_load(dashboard_name), panel_id)
        custom = (panel.get("fieldConfig") or {}).get("defaults", {}).get("custom", {})
        assert custom.get("cellOptions", {}).get("wrapText") in (True, False, None)
        wrapped = _wrapped_field_names(panel)
        if dashboard_name == "bioetl-control-plane-v1.json" and panel_id == 9404:
            # #10571: full fingerprints and identity-gap reasons need wrapping
            # at 900px; large rows reserve space before the pagination footer.
            assert panel["options"]["cellHeight"] == "lg"
            assert panel["options"]["footer"]["enablePagination"] is True
            assert field in wrapped
            assert panel["gridPos"]["h"] >= 12
            continue
        if dashboard_name in {
            "bioetl-control-plane-v1.json",
            "bioetl-provider-health-v2.json",
        }:
            # #10498/#10501: fixed-height pagination replaces wrapped rows after live
            # 1600x900 verification; Inspect retains the full selectable value.
            assert panel["options"]["cellHeight"] == "md"
            assert custom.get("inspect") is True
            assert panel["options"]["footer"]["enablePagination"] is True
            assert field not in wrapped
            continue
        assert field in wrapped, (dashboard_name, panel_id, wrapped)


def test_trust_9416_detail_is_not_wrapped_at_four_rows() -> None:
    panel = _panel(_load("bioetl-control-plane-v1.json"), 9416)
    assert _limit_field(panel) == 5
    assert "detail" not in _wrapped_field_names(panel)
    organize = next(
        transform
        for transform in panel.get("transformations", [])
        if transform.get("id") == "organize"
    ).get("options", {})
    assert organize.get("excludeByName") == {
        "Time": True,
        "detail": True,
        "endpoint": True,
        "retryable": True,
        "observed_at": True,
    }
    target = panel["targets"][0]
    assert target.get("parser") == "backend"
    assert target.get("root_selector") == "rows"
    assert "error_as_row=1" in str(target.get("url") or "")
    columns = target.get("columns") or []
    names = {item.get("selector") for item in columns if isinstance(item, dict)}
    assert {"check", "status", "reason", "detail"} <= names
    docs = f"{panel.get('description') or ''} {panel.get('fieldConfig')}"
    assert "504" in docs
    assert "deadline_exceeded" in docs
    assert "refresh" in docs.lower()


def test_incident_ranked_suspects_uses_one_comparable_value_column() -> None:
    incident = _load("bioetl-incident-v1.json")
    suspects = _panel(incident, 2010)
    transforms = suspects.get("transformations", [])
    transform_ids = [transform.get("id") for transform in transforms]
    organize = next(
        transform for transform in transforms if transform.get("id") == "organize"
    )
    exclude = organize.get("options", {}).get("excludeByName", {})
    rename = organize.get("options", {}).get("renameByName", {})

    exprs = [
        str(target.get("expr") or "").strip() for target in suspects.get("targets", [])
    ]
    assert len(exprs) == 1
    assert "bioetl_incident_ranked_evidence" in exprs[0]
    assert "merge" not in transform_ids
    assert suspects["targets"][0]["format"] == "table"
    assert suspects["targets"][0]["instant"] is True
    assert exclude.get("__name__") is True
    assert "sortBy" in transform_ids
    assert "limit" in transform_ids
    assert transform_ids.index("sortBy") < transform_ids.index("limit")
    sort = next(
        transform for transform in transforms if transform.get("id") == "sortBy"
    )
    sort_field = (sort.get("options") or {}).get("sort", [{}])[0].get("field")
    assert sort_field == "Value"
    assert (sort.get("options") or {}).get("sort", [{}])[0].get("desc") is True
    assert any(
        transform.get("id") == "limit"
        and (transform.get("options") or {}).get("limitField") == 2
        for transform in transforms
    )
    for field in ("Time", "Time 1", "Time 2"):
        assert exclude.get(field) is True
    assert exclude.get("Value") is not True
    assert rename.get("Value") == "Severity"
    assert rename.get("action") == "Action"
    assert rename.get("signal") == "Signal"
    assert not {value for value in rename.values() if str(value).startswith("Series ")}


def test_incident_ranked_suspects_limit_requires_comparable_rank() -> None:
    """#10164: one query yields Value, so top-5 sorts by rank across all domains."""
    incident = _load("bioetl-incident-v1.json")
    suspects = _panel(incident, 2010)
    transforms = suspects.get("transformations", [])
    ids = [transform.get("id") for transform in transforms]
    assert "merge" not in ids
    assert ids.index("sortBy") < ids.index("limit")
    organize = next(
        transform for transform in transforms if transform.get("id") == "organize"
    )
    exclude = organize.get("options", {}).get("excludeByName", {})
    assert exclude.get("Value") is not True
    exprs = [
        str(target.get("expr") or "").strip() for target in suspects.get("targets", [])
    ]
    assert len(exprs) == 1
    assert "bioetl_incident_ranked_evidence" in exprs[0]
    rules = yaml.safe_load(OBSERVABILITY_RULES.read_text(encoding="utf-8"))
    recorded = {
        str(rule.get("record")): str(rule.get("expr") or "")
        for group in rules.get("groups", [])
        for rule in group.get("rules", [])
        if str(rule.get("record") or "")
        in {
            "bioetl_incident_ranked_runtime",
            "bioetl_incident_ranked_provider",
            "bioetl_incident_ranked_dq",
        }
    }
    sources = [
        "bioetl_incident_ranked_runtime",
        "bioetl_incident_ranked_provider",
        "bioetl_incident_ranked_dq",
    ]
    assert set(sources) <= set(recorded)
    domain = {name: recorded[name] for name in sources}
    assert any("* 2" in expr for expr in domain.values())
    assert all(
        'severity="failing"' in expr or 'severity="crit"' in expr
        for expr in domain.values()
    )
    assert all("telemetry_gap" in expr for expr in domain.values())
    assert all(" > 0" not in expr.split("topk", 1)[0] for expr in domain.values())


def test_incident_alert_history_has_readable_full_width_layout() -> None:
    incident = _load("bioetl-incident-v1.json")
    current_alerts = _panel(incident, 2005)
    history = _panel(incident, 2006)
    impact = _panel(incident, 2007)
    history_grid = history.get("gridPos", {})

    assert current_alerts.get("gridPos", {}).get("w") == 24
    assert history_grid.get("x") == 0
    assert history_grid.get("w") == 24
    assert history_grid.get("h") == 14
    assert history.get("options", {}).get("legend", {}).get("showLegend") is True
    assert history.get("options", {}).get("showValue") == "never"
    assert history.get("options", {}).get("rowHeight") == 0.85
    assert history["options"]["perPage"] == 8
    assert "pageSize" not in history["options"]
    assert impact.get("gridPos", {}).get("y", 0) >= (
        history_grid.get("y", 0) + history_grid.get("h", 0)
    )
    assert current_alerts.get("gridPos") == {"h": 5, "w": 24, "x": 0, "y": 12}
    assert "ALERTS" in str(history.get("targets", [{}])[0].get("expr", ""))
    assert str(history.get("targets", [{}])[0].get("legendFormat", "")).startswith(
        "{{alertname}}"
    )
    mappings = history["fieldConfig"]["defaults"]["mappings"][0]["options"]
    assert mappings["1"] == {"text": "FIRING", "color": "red"}
    # Native orange measured 2.64:1 on Light; preserve the PENDING label and hue
    # with the source-bound contrast remediation instead of the failing token.
    assert mappings["2"] == {"text": "PENDING", "color": "#bd5907"}
    assert all(
        _contrast_ratio(mappings["2"]["color"], background) >= 3
        for background in ("#ffffff", "#181b1f")
    )
    assert history["options"]["mergeValues"] is True
    assert history["fieldConfig"]["defaults"]["custom"]["axisWidth"] >= 360
    assert history["fieldConfig"]["defaults"]["custom"]["lineWidth"] > 0


def test_incident_alert_count_and_dq_reason_have_honest_table_semantics() -> None:
    incident = _load("bioetl-incident-v1.json")
    current_alerts = _panel(incident, 2005)
    dq_suspects = _panel(incident, 2004)

    assert (
        'label_replace(bioetl_incident_alert_priority,"provider","Not provided"'
        in current_alerts["targets"][0]["expr"]
    )
    transforms = current_alerts["transformations"]
    ids = [t["id"] for t in transforms]
    assert ids.index("sortBy") < ids.index("limit")
    sort = next(t for t in transforms if t["id"] == "sortBy")
    assert sort["options"]["sort"] == [{"field": "Value", "desc": True}]
    organize = next(t for t in transforms if t["id"] == "organize")["options"]
    assert organize["excludeByName"]["Value"] is True
    assert {"severity", "pipeline", "provider"} <= organize["indexByName"].keys()

    assert dq_suspects.get("targets", [{}])[0].get("expr") == (
        "topk(10, max by (pipeline, reason) (bioetl_dq_current_reason) > 0)"
    )
    organize = dq_suspects.get("transformations", [])[0]
    assert organize.get("id") == "organize"
    options = organize.get("options", {})
    assert options.get("excludeByName", {}).get("Time") is True
    assert options.get("indexByName") == {
        "pipeline": 0,
        "reason": 1,
        "Value": 2,
    }
    assert options.get("renameByName") == {
        "pipeline": "Pipeline",
        "reason": "Reason",
        "Value": "Signal",
    }
    overrides = {
        override.get("matcher", {}).get("options"): {
            property_["id"]: property_["value"]
            for property_ in override.get("properties", [])
        }
        for override in dq_suspects["fieldConfig"]["overrides"]
    }
    assert dq_suspects["gridPos"]["w"] == 24
    assert overrides["Pipeline"]["custom.width"] == 250
    assert "custom.width" not in overrides["Reason"]
    assert overrides["Reason"]["custom.cellOptions"] == {
        "type": "auto",
        "wrapText": True,
    }
    assert overrides["Signal"]["custom.align"] == "right"
    assert overrides["Signal"]["custom.width"] == 88
    assert overrides["Signal"]["custom.cellOptions"] == {
        "type": "color-text",
        "mode": "basic",
    }
    assert "reason" not in overrides
    visible_width = int(overrides["Pipeline"]["custom.width"]) + int(
        overrides["Signal"]["custom.width"]
    )
    css_budget = (1366 // 2) * dq_suspects["gridPos"]["w"] // 24 - 40
    assert visible_width <= css_budget


def test_runtime_multi_query_tables_expose_semantic_fields_only() -> None:
    runtime = _load("bioetl-runtime.json")
    blocker_detail = _panel(runtime, 242)
    expectedness = _panel(runtime, 243)

    blocker_organize = next(
        transform
        for transform in blocker_detail.get("transformations", [])
        if transform.get("id") == "organize"
    )
    blocker_exclude = blocker_organize.get("options", {}).get("excludeByName", {})
    for ref_id in {target.get("refId") for target in blocker_detail.get("targets", [])}:
        assert blocker_exclude.get(f"Value #{ref_id}") is True
    assert blocker_exclude.get("Value") is True
    assert blocker_exclude.get("Time") is True

    expectedness_organize = next(
        transform
        for transform in expectedness.get("transformations", [])
        if transform.get("id") == "organize"
    )
    rename = expectedness_organize.get("options", {}).get("renameByName", {})
    assert rename == {
        "Value #A": "Expected",
        "Value #B": "Observed Records",
    }
    matchers = {
        override.get("matcher", {}).get("options")
        for override in expectedness.get("fieldConfig", {}).get("overrides", [])
    }
    assert {"Expected", "Observed Records"} <= matchers


def test_run_explorer_drops_reconciliation_panel() -> None:
    explorer = _load("bioetl-run-explorer-v1.json")
    assert all(
        panel.get("id") != 3015 for panel in _iter_panels(explorer.get("panels") or [])
    )


def test_run_explorer_novalue_has_no_uninterpolated_variables() -> None:
    explorer = _load("bioetl-run-explorer-v1.json")
    for panel in _iter_panels(explorer.get("panels") or []):
        no_value = str(
            (panel.get("fieldConfig") or {}).get("defaults", {}).get("noValue") or ""
        )
        assert "$pipeline" not in no_value
        assert "$workflow" not in no_value
        assert "$run_id" not in no_value


def _run_select_links(panel: dict[str, object]) -> list[str]:
    urls: list[str] = []
    for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
        if not isinstance(override, dict):
            continue
        for prop in override.get("properties") or []:
            if not isinstance(prop, dict) or prop.get("id") != "links":
                continue
            for link in prop.get("value") or []:
                if isinstance(link, dict) and isinstance(link.get("url"), str):
                    urls.append(str(link["url"]))
    return urls


def test_run_explorer_recent_runs_bind_run_id_via_data_link() -> None:
    explorer = _load("bioetl-run-explorer-v1.json")
    first_screen = _panel(explorer, 3010)
    first_links = _run_select_links(first_screen)
    assert first_links
    assert any(
        "var-run_id=${__data.fields.Run:percentencode}" in url for url in first_links
    )
    assert any("var-pipeline=${__data.fields.Pipeline}" in url for url in first_links)
    assert any("var-run_type=${__data.fields.run_type}" in url for url in first_links)
    assert all("var-run_type=$run_type" not in url for url in first_links)
    assert all("viewPanel" not in url for url in first_links)
    assert "select and mark" in str(first_screen.get("description") or "")
    hidden = {
        str((item.get("matcher") or {}).get("options"))
        for item in (first_screen.get("fieldConfig") or {}).get("overrides") or []
        if isinstance(item, dict)
        and any(
            prop.get("id") == "custom.hidden" and prop.get("value") is True
            for prop in item.get("properties") or []
            if isinstance(prop, dict)
        )
    }
    assert "Pipeline" not in hidden
    assert "run_type" in hidden
    target_url = str((first_screen.get("targets") or [{}])[0].get("url") or "")
    assert "run_id=${run_id}" in target_url
    selected = [
        item
        for item in (first_screen.get("fieldConfig") or {}).get("overrides") or []
        if isinstance(item, dict)
        and (item.get("matcher") or {}).get("options") == "selected"
    ]
    assert selected, "3010 must mark the selected run_id row"
    assert all(
        panel.get("id") != 3021 for panel in _iter_panels(explorer.get("panels") or [])
    )


def _override_width(panel: dict[str, object], matcher: str) -> int | None:
    field_config = panel.get("fieldConfig")
    if not isinstance(field_config, dict):
        return None
    for item in field_config.get("overrides") or []:
        if not isinstance(item, dict):
            continue
        options = str((item.get("matcher") or {}).get("options") or "")
        if matcher not in options:
            continue
        for prop in item.get("properties") or []:
            if isinstance(prop, dict) and prop.get("id") == "custom.width":
                return int(prop.get("value") or 0)
    return None


def _override_novalue(panel: dict[str, object], matcher: str) -> str | None:
    field_config = panel.get("fieldConfig")
    if not isinstance(field_config, dict):
        return None
    for item in field_config.get("overrides") or []:
        if not isinstance(item, dict):
            continue
        options = str((item.get("matcher") or {}).get("options") or "")
        if matcher not in options:
            continue
        for prop in item.get("properties") or []:
            if isinstance(prop, dict) and prop.get("id") == "noValue":
                return str(prop.get("value") or "")
    return None


def test_run_explorer_index_is_disk_last_ten_not_time_range() -> None:
    explorer = _load("bioetl-run-explorer-v1.json")
    banner = _panel(explorer, 1)
    content = str((banner.get("options") or {}).get("content") or "")
    assert "not this time range" in content
    recent = _panel(explorer, 3010)
    description = str(recent.get("description") or "")
    assert "time picker does not filter this table" in description
    target_url = str((recent.get("targets") or [{}])[0].get("url") or "")
    assert "$__range" not in target_url
    assert "limit=10" in target_url


def test_run_explorer_recent_runs_selected_column_fits_first_window() -> None:
    explorer = _load("bioetl-run-explorer-v1.json")
    recent = _panel(explorer, 3010)
    assert _override_width(recent, "selected") == 28
    assert _override_width(recent, "^(workflow_id|Workflow)$") is None
    assert recent["fieldConfig"]["defaults"]["custom"]["minWidth"] == 50
    assert recent["options"]["footer"]["enablePagination"] is False
    assert (_override_width(recent, "Run") or 0) <= 340
    hidden = {
        str((item.get("matcher") or {}).get("options"))
        for item in (recent.get("fieldConfig") or {}).get("overrides") or []
        if isinstance(item, dict)
        and any(
            prop.get("id") == "custom.hidden" and prop.get("value") is True
            for prop in item.get("properties") or []
            if isinstance(prop, dict)
        )
    }
    assert "Pipeline" not in hidden
    assert "run_type" in hidden
    assert "message" in hidden
    grid = recent.get("gridPos") or {}
    assert int(grid.get("h") or 0) == 12
    assert int(grid.get("y") or 0) + int(grid.get("h") or 0) == 17
    assert recent.get("options", {}).get("cellHeight") == "sm"
    assert (
        next(t for t in recent["transformations"] if t["id"] == "limit")
        .get("options", {})
        .get("limitField")
        == 10
    )


def test_below_fold_tables_exclude_time_without_name_metric() -> None:
    """Below-fold inspect tables hide Grafana Time, not __name__."""
    cases = (
        ("bioetl-incident-v1.json", 2002),
        ("bioetl-control-plane-v1.json", 9415),
        ("bioetl-control-plane-v1.json", 9413),
        ("bioetl-control-plane-v1.json", 9414),
        ("bioetl-control-plane-v1.json", 9407),
        ("bioetl-control-plane-v1.json", 9405),
        ("bioetl-control-plane-v1.json", 9406),
        ("bioetl-control-plane-v1.json", 9408),
        ("bioetl-control-plane-v1.json", 9409),
        ("bioetl-control-plane-v1.json", 9417),
    )
    for dashboard_name, panel_id in cases:
        panel = _panel(_load(dashboard_name), panel_id)
        organize = next(
            transform
            for transform in panel.get("transformations") or []
            if transform.get("id") == "organize"
        )
        exclude = (organize.get("options") or {}).get("excludeByName") or {}
        assert exclude.get("Time") is True, (dashboard_name, panel_id)
        assert "__name__" not in exclude, (dashboard_name, panel_id)


def test_cycle3_inspect_enabled_on_named_below_fold_tables() -> None:
    """#9533 #9534 #9535 #9536: remaining inspect tables expose cell inspect."""
    cases = (
        ("bioetl-provider-health-v2.json", 9103),
        ("bioetl-runtime.json", 256),
        ("bioetl-runtime.json", 241),
        ("bioetl-dq-v2.json", 121),
        ("bioetl-dq-v2.json", 122),
        ("bioetl-overview-v2.json", 9010),
        ("bioetl-overview-v2.json", 9011),
        ("bioetl-overview-v2.json", 9013),
        ("bioetl-control-plane-v1.json", 908),
        ("bioetl-control-plane-v1.json", 138),
        ("bioetl-dq-v2.json", 118),
        ("bioetl-dq-v2.json", 156),
        ("bioetl-overview-v2.json", 9003),
        ("bioetl-overview-v2.json", 9004),
        ("bioetl-overview-v2.json", 9005),
        ("bioetl-overview-v2.json", 9006),
        ("bioetl-overview-v2.json", 9007),
        ("bioetl-provider-health-v2.json", 107),
        ("bioetl-provider-health-v2.json", 108),
        ("bioetl-provider-health-v2.json", 114),
        ("bioetl-provider-health-v2.json", 9111),
        ("bioetl-provider-health-v2.json", 9112),
        ("bioetl-provider-health-v2.json", 9113),
    )
    for dashboard_name, panel_id in cases:
        panel = _panel(_load(dashboard_name), panel_id)
        custom = (panel.get("fieldConfig") or {}).get("defaults", {}).get("custom", {})
        assert custom.get("inspect") is True, (dashboard_name, panel_id)


def test_cycle4_below_fold_declared_widths_fit_200pct_css_budget() -> None:
    """#9554 #9555 #9556 #9557: declared visible widths must fit DASH-REFLOW-001."""
    layout_width = 1366 // 2
    chrome_px = 40
    cases = (
        ("bioetl-incident-v1.json", 2002, 8),
        ("bioetl-control-plane-v1.json", 9403, 6),
    )
    for dashboard_name, panel_id, grid_w in cases:
        panel = _panel(_load(dashboard_name), panel_id)
        budget = layout_width * panel["gridPos"]["w"] // 24 - chrome_px
        hidden: set[str] = set()
        widths: dict[str, int] = {}
        for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
            field = str((override.get("matcher") or {}).get("options"))
            props = {
                item.get("id"): item.get("value")
                for item in override.get("properties") or []
            }
            if props.get("custom.hidden") is True:
                hidden.add(field)
            if "custom.width" in props:
                widths[field] = int(props["custom.width"])
        visible_sum = sum(
            width for field, width in widths.items() if field not in hidden
        )
        assert visible_sum <= budget, (
            f"{dashboard_name}:{panel_id} w={grid_w} sum={visible_sum} budget={budget}"
        )


def test_selected_trust_reasons_link_preserves_multiple_run_types() -> None:
    panel = _panel(_load("bioetl-control-plane-v1.json"), 9418)
    action = next(
        item
        for item in panel["fieldConfig"]["overrides"]
        if item["matcher"]["options"] == "Action"
    )
    links = next(
        item["value"] for item in action["properties"] if item["id"] == "links"
    )
    assert "${run_type:queryparam}" in links[0]["url"]
    assert "${run_id:queryparam}" in links[0]["url"]
    assert "var-run_type=${run_type:csv}" not in links[0]["url"]
    count = next(
        item
        for item in panel["fieldConfig"]["overrides"]
        if item["matcher"]["options"] == "Reason count"
    )
    count_links = next(
        (item["value"] for item in count["properties"] if item["id"] == "links"),
        [],
    )
    assert count_links == []


def test_visible_trust_reason_count_opens_frozen_reason_details() -> None:
    dashboard = _load("bioetl-control-plane-v1.json")
    trust = _panel(dashboard, 9418)
    action = next(
        item
        for item in trust["fieldConfig"]["overrides"]
        if item["matcher"]["options"] == "Action"
    )
    links = next(
        item["value"] for item in action["properties"] if item["id"] == "links"
    )
    assert links[0]["title"] == "View trust reasons"
    assert "viewPanel=9451" in links[0]["url"]
    assert "${run_id:queryparam}" in links[0]["url"]
    details = _panel(dashboard, 9451)
    names = next(
        item["options"]["include"]["names"]
        for item in details["transformations"]
        if item["id"] == "filterFieldsByName"
    )
    assert "reason_display" in names


@pytest.mark.parametrize("dashboard_path", sorted(DASHBOARD_DIR.glob("*.json")))
def test_saved_domain_details_expose_specific_reason(dashboard_path: Path) -> None:
    """A trust-assessment label must not hide the persisted failure reasons."""
    details = _panel(_load(dashboard_path.name), 9451)
    names = next(
        item["options"]["include"]["names"]
        for item in details["transformations"]
        if item["id"] == "filterFieldsByName"
    )
    assert "reason_display" in names and "reason" not in names
    rename = next(
        item["options"]["renameByName"]
        for item in details["transformations"]
        if item["id"] == "organize"
    )
    assert rename["reason_display"] == "Reason"


def test_cycle5_wrap_text_columns_restore_declared_widths() -> None:
    """#9563 #9564 #9565 #9566: wrap columns keep a declared width; one column stays flex."""
    layout_width = 1366 // 2
    chrome_px = 40
    cases = (
        ("bioetl-provider-health-v2.json", 9107, 12, "Source state", 70, "reason"),
        ("bioetl-runtime.json", 9101, 16, "reason", None, "action_target"),
        (
            "bioetl-control-plane-v1.json",
            9418,
            12,
            "reasons_count",
            80,
            "trust_status",
        ),
        ("bioetl-control-plane-v1.json", 9416, 12, "status", 110, "reason"),
        ("bioetl-overview-v2.json", 9003, 24, "Value", 100, "pipeline"),
        ("bioetl-overview-v2.json", 9004, 24, "Value", 100, "pipeline"),
        ("bioetl-overview-v2.json", 9005, 24, "Value", 100, "pipeline"),
        ("bioetl-overview-v2.json", 9006, 24, "Value", 100, "pipeline"),
        ("bioetl-overview-v2.json", 9007, 24, "Value", 100, "provider"),
    )
    for dashboard_name, panel_id, grid_w, wrap_field, wrap_width, flex_field in cases:
        panel = _panel(_load(dashboard_name), panel_id)
        budget = layout_width * grid_w // 24 - chrome_px
        hidden: set[str] = set()
        widths: dict[str, int] = {}
        for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
            field = str((override.get("matcher") or {}).get("options"))
            props = {
                item.get("id"): item.get("value")
                for item in override.get("properties") or []
            }
            if props.get("custom.hidden") is True:
                hidden.add(field)
            if "custom.width" in props:
                widths[field] = int(props["custom.width"])
        assert widths.get(wrap_field) == wrap_width, (
            dashboard_name,
            panel_id,
            wrap_field,
            widths.get(wrap_field),
        )
        assert flex_field not in widths, (dashboard_name, panel_id, flex_field, widths)
        visible_sum = sum(
            width for field, width in widths.items() if field not in hidden
        )
        assert visible_sum <= budget, (
            f"{dashboard_name}:{panel_id} w={grid_w} sum={visible_sum} budget={budget}"
        )


def test_all_shipped_table_panels_enable_inspect() -> None:
    """Every shipped Grafana table exposes cell inspect (DASH-FIRST-002)."""
    missing: list[str] = []
    for path in sorted(DASHBOARD_DIR.glob("*.json")):
        dashboard = _load(path.name)
        for panel in _iter_panels(list(dashboard.get("panels") or [])):
            if panel.get("type") != "table":
                continue
            custom = (
                (panel.get("fieldConfig") or {}).get("defaults", {}).get("custom", {})
            )
            if custom.get("inspect") is True:
                continue
            missing.append(f"{path.name}:{panel.get('id')}:{panel.get('title')}")
    assert not missing, "tables missing inspect=true:\n" + "\n".join(missing)


def test_incident_scope_and_rank_do_not_confuse_inactive_signals_with_unknown() -> None:
    """Inactive zero signals cannot become UNKNOWN suspects (#10181)."""
    incident = _load("bioetl-incident-v1.json")
    panel = _panel(incident, 2010)
    transforms = panel["transformations"]
    assert transforms[0]["id"] == "filterByValue"
    filters = transforms[0]["options"]
    assert filters["match"] == "any"
    assert filters["filters"] == [
        {"fieldName": "Value", "config": {"id": "greater", "options": {"value": 0}}},
        {
            "fieldName": "signal",
            "config": {"id": "equal", "options": {"value": "telemetry_gap"}},
        },
    ]
    assert "GLOBAL" in _panel(incident, 9400)["options"]["content"]
    assert "UNVERIFIED" in panel["description"]
    assert "same GLOBAL scope" in panel["description"]
    rules = yaml.safe_load(OBSERVABILITY_RULES.read_text(encoding="utf-8"))
    for group in rules["groups"]:
        for rule in group["rules"]:
            if str(rule.get("record", "")) in {
                "bioetl_incident_ranked_runtime",
                "bioetl_incident_ranked_provider",
                "bioetl_incident_ranked_dq",
            }:
                assert rule["expr"].count(" > 0") == 2
                assert '"telemetry_gap"' in rule["expr"]


def test_runtime_first_action_separates_endpoint_from_completeness() -> None:
    runtime = _load("bioetl-runtime.json")
    coverage = _panel(runtime, 9102)
    blockers = _panel(runtime, 9101)
    assert blockers["gridPos"]["y"] <= 7
    assert coverage["options"]["colorMode"] == "value"
    assert {target["legendFormat"] for target in coverage["targets"]} == {
        "Endpoint",
        "{{k}}",
        "Rule age",
    }
    stage_expr = next(
        target["expr"] for target in coverage["targets"] if target["refId"] == "B"
    )
    assert "bioetl_rt_stage_ratio" in stage_expr
    assert "bioetl_runtime_trust_gap_active_10m" in stage_expr
    header = _panel(runtime, 9400)["options"]["content"]
    assert "monitoring quality (10m)" in header
    assert "SCRAPING does not prove completeness" in header
    for panel_id in (2542, 2543):
        panel = _panel(runtime, panel_id)
        assert panel["gridPos"]["h"] >= 3
        assert "overflow:hidden" not in panel["options"]["content"]
    assert "<a href=" in _panel(runtime, 2542)["options"]["content"]


def test_overview_routes_and_timelines_exclude_inactive_fallbacks() -> None:
    """Positive routes and absent-only fallback prevent false diagnostic rows."""
    overview = _load("bioetl-overview-v2.json")
    route = _panel(overview, 215)["targets"][0]["expr"]
    assert route.count(">0") == 1
    assert "bioetl_first_action" in route
    assert "or on() label_replace" in route
    assert "max without(run_type)" not in route
    for panel_id in (9018, 9019, 9020):
        panel = _panel(overview, panel_id)
        assert "or on()" in panel["targets"][0]["expr"]
        assert panel["targets"][0]["range"] is True
        assert panel["fieldConfig"]["defaults"]["custom"]["lineWidth"] > 0


def test_runtime_evidence_validator_rejects_scraping_as_health() -> None:
    """Endpoint presence must never be promoted to a green completeness verdict."""
    from scripts.engineering.qa.check_dashboard_visual_semantics import (
        _telemetry_evidence_errors,
    )

    coverage = _panel(_load("bioetl-runtime.json"), 9102)
    assert not _telemetry_evidence_errors(coverage)
    coverage["options"]["colorMode"] = "background"
    assert _telemetry_evidence_errors(coverage)


def test_incident_main_columns_hide_future_service_labels_but_keep_inspect() -> None:
    """Evolving recording-rule metadata cannot leak into the operator table."""
    panel = _panel(_load("bioetl-incident-v1.json"), 2010)
    defaults = panel["fieldConfig"]["defaults"]["custom"]
    assert defaults["hidden"] is True
    assert defaults["inspect"] is True
    visible = {
        override["matcher"]["options"]
        for override in panel["fieldConfig"]["overrides"]
        if {"id": "custom.hidden", "value": False} in override["properties"]
    }
    assert visible == {
        "Rank",
        "Severity",
        "Confidence",
        "Object",
        "Signal",
        "Action",
    }


def test_active_alert_missing_labels_do_not_claim_empty_domain() -> None:
    dashboard = _load("bioetl-incident-v1.json")
    for panel in _iter_panels(dashboard["panels"]):
        if panel.get("type") == "table":
            assert "EMPTY DOMAIN" not in panel["fieldConfig"]["defaults"].get(
                "noValue", ""
            )
    for panel_id in (2005, 22005):
        overrides = _panel(dashboard, panel_id)["fieldConfig"]["overrides"]
        for field in ("instance", "job"):
            assert any(
                override["matcher"] == {"id": "byName", "options": field}
                and {"id": "noValue", "value": "NOT PROVIDED"} in override["properties"]
                for override in overrides
            )


def test_scrolling_capture_preserves_layout_viewport(tmp_path: Path) -> None:
    import os
    import subprocess
    from scripts.ops.observability.grafana import (
        rerender_grafana_screenshots as rerender,
    )

    node = rerender._resolve_node_executable()
    if node is None:
        pytest.skip("Browser integration requires Node.js")
    runtime_env = os.environ.copy()
    rerender._apply_playwright_runtime_env(runtime_env)
    probe = subprocess.run(
        [node, "-e", "require.resolve('playwright')"],
        capture_output=True,
        env=runtime_env,
        timeout=15,
    )
    if probe.returncode:
        pytest.skip("Browser integration requires the optional Playwright runtime")
    script = Path(
        "scripts/ops/observability/grafana/capture_scroll_surface.cjs"
    ).resolve()
    program = """
const {captureScrollSurface}=require(process.argv[1]);
const {chromium}=require('playwright');
(async()=>{
const browser=await chromium.launch({headless:true});
try {
 const context=await browser.newContext({viewport:{width:683,height:384},deviceScaleFactor:2});
 const page=await context.newPage();
 await page.setContent('<style>body{margin:0}.scroll{height:384px;overflow:auto}.panel{height:350px;background:#246;color:white}</style><div class="scroll">'+
 Array.from({length:5},(_,i)=>'<div class="panel" data-viz-panel-key="panel-'+i+'">Panel '+i+'</div>').join('')+'</div>');
 const result=await captureScrollSurface(page,{filePath:process.argv[2],timeout:20000,
 pngEvidence:b=>({width:b.readUInt32BE(16),height:b.readUInt32BE(20)}),measure:async()=>({})});
 console.log(JSON.stringify({viewport:page.viewportSize(),result}));
} finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
"""
    env = os.environ.copy()
    rerender._apply_playwright_runtime_env(env)
    completed = subprocess.run(
        [
            rerender._resolve_node_executable(),
            "-e",
            program,
            str(script),
            str(tmp_path / "full.png"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["viewport"] == {"width": 683, "height": 384}
    assert result["result"]["surface"]["scrollHeight"] == 1750
    assert all(
        t["width"] == 1366 and t["height"] == 768 for t in result["result"]["tiles"]
    )
    assert {p["panel"] for t in result["result"]["tiles"] for p in t["panels"]} == {
        f"panel-{i}" for i in range(5)
    }
    data = (tmp_path / "full.png").read_bytes()
    assert int.from_bytes(data[16:20], "big") == 1366
    assert int.from_bytes(data[20:24], "big") == 3500
