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
    assert "bioetl_control_plane_current_status_trusted" in str(
        _panel(control, 9401).get("targets")
    )
    assert _mapping_text(_panel(control, 9401), "3") == "INCOMPLETE"

    runtime_expr = _record_expr(
        OBSERVABILITY_RULES, "bioetl_runtime_current_status_trusted"
    )
    assert "bioetl_runtime_trust_gap_active_10m * 3" in runtime_expr
    assert _mapping_text(_panel(runtime, 9401), "3") == "INCOMPLETE"
    assert (
        "telemetry gap makes the verdict incomplete"
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

    expected_geometry = {
        3: {"x": 6, "y": 62, "w": 6, "h": 4},
        4: {"x": 0, "y": 62, "w": 6, "h": 4},
        101: {"x": 12, "y": 62, "w": 6, "h": 4},
        9: {"x": 18, "y": 62, "w": 6, "h": 4},
        12: {"x": 0, "y": 66, "w": 6, "h": 4},
        151: {"x": 6, "y": 66, "w": 6, "h": 4},
    }
    for panel_id, geometry in expected_geometry.items():
        assert panels[panel_id]["gridPos"] == geometry


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
        "type": "color-text",
        "applyToRow": False,
    }

    severity_properties = {
        prop["id"]: prop["value"] for prop in by_name["severity"]["properties"]
    }
    mappings = severity_properties["mappings"]
    assert [mapping["options"]["result"]["text"] for mapping in mappings] == [
        "CRITICAL",
        "WARNING",
    ]
    assert not any(override["matcher"]["id"] == "byRegexp" for override in overrides)


def test_iteration_2_runtime_valid_empty_frames_are_semantic_tables() -> None:
    """Bounded Runtime fallbacks expose semantic labels instead of raw frames."""
    dashboard = _load("bioetl-runtime.json")
    expected = {
        241: ("run_type", "No records in range"),
        256: ("error_code", "No errors in range"),
    }
    for panel_id, (detail_field, detail_text) in expected.items():
        panel = _panel(dashboard, panel_id)
        assert panel["type"] == "table"
        assert panel["targets"][0]["format"] == "table"
        assert "label_replace(label_replace(vector(0)" in panel["targets"][0]["expr"]
        organize = panel["transformations"][-1]
        assert organize["id"] == "organize"
        assert organize["options"]["excludeByName"]["Time"] is True
        assert organize["options"]["renameByName"]["Value"] == "Count"

        overrides = {
            override["matcher"]["options"]: override
            for override in panel["fieldConfig"]["overrides"]
            if override["matcher"]["id"] == "byName"
        }
        assert (
            overrides["stage"]["properties"][0]["value"][0]["options"]["none"]["text"]
            == "VALID EMPTY"
        )
        assert (
            overrides[detail_field]["properties"][0]["value"][0]["options"]["none"][
                "text"
            ]
            == detail_text
        )


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
        "0. Trust",
        "1. Overview",
        "2. Pipeline Diagnostics",
        "3. Provider Health",
        "4. Data Quality",
        "5. Incident Workspace",
        "6. Run Explorer",
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
        for token in ("display:flex", "flex-wrap:wrap", "overflow:visible"):
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
                "flex:1 1 120px",
                "text-align:center",
                "color:#f8fafc",
                "background:#334155",
                "border:1px solid #94a3b8",
            ):
                assert token in style, (path.name, token)
            assert attrs.get("href"), path.name
        current_style = current[0].get("style", "")
        for token in (
            "flex:1 1 120px",
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
    assert inputs["title"] == "Review Domain Status"
    assert inputs["gridPos"]["y"] == first_action["gridPos"]["y"]
    assert inputs["gridPos"]["w"] >= 8
    assert _panel(overview, 9603)["gridPos"]["y"] < first_action["gridPos"]["y"]

    provider = _load("bioetl-provider-health-v2.json")
    # Provider detail progressive panels remain first-screen-friendly.
    assert any(panel.get("type") == "row" for panel in provider.get("panels", []))
    # Workflow overview + Alerts/SLO retired (#6570/#6647).


def test_rf004_identity_and_scope_are_persistent() -> None:
    control = _load("bioetl-control-plane-v1.json")
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
        _panel(overview, 9603)["gridPos"]["y"] < _panel(overview, 215)["gridPos"]["y"]
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
    # layout-budgets.yaml:first_window_y — collapsed rows start at the visual fold.
    assert first_row_y == FIRST_WINDOW_Y
    assert [panel["gridPos"]["y"] for panel in control_rows] == list(
        range(FIRST_WINDOW_Y, FIRST_WINDOW_Y + len(control_rows))
    )
    assert not any(collapsed_row_above_fold(panel) for panel in control_rows)


def test_rf006_collapsed_row_above_fold_fails_closed() -> None:
    """Mutation: a collapsed diagnostic row at FIRST_WINDOW_Y - 1 is above the fold."""
    above = {
        "type": "row",
        "collapsed": True,
        "gridPos": {"x": 0, "y": FIRST_WINDOW_Y - 1, "w": 24, "h": 1},
        "panels": [{"id": 1, "type": "stat"}],
    }
    at_fold = {
        "type": "row",
        "collapsed": True,
        "gridPos": {"x": 0, "y": FIRST_WINDOW_Y, "w": 24, "h": 1},
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
    assert [panel.get("id") for panel in provider_rows] == [9106, 9105, 91, 9404, 9405]
    assert [panel.get("gridPos", {}).get("y") for panel in provider_rows] == [
        18,
        19,
        20,
        21,
        22,
    ]
    assert all(panel.get("collapsed") is True for panel in provider_rows)
    for panel_id in (9101, 9102, 9103):
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
    ]
    assert [panel.get("gridPos", {}).get("y") for panel in dq_rows] == [
        18,
        19,
        20,
        21,
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
            assert legend.get("showLegend") is False
        assert "full identifiers remain available" in str(
            _panel(dq, panel_id).get("description", "")
        )


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
        "bioetl-run-explorer-v1.json": (3022,),
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
                assert custom.get("cellOptions", {}).get("wrapText") is not True
                if dashboard_name == "bioetl-run-explorer-v1.json" and panel_id == 3022:
                    continue
                wrapped = _wrapped_field_names(panel)
                assert wrapped, (
                    f"{dashboard_name} panel {panel_id} must wrap at least one named field"
                )


def test_first_window_named_text_columns_wrap_without_table_default() -> None:
    """#8977: wrap only the named first-window text column; do not grow h."""
    cases = (
        ("bioetl-runtime.json", 9101, frozenset({"reason"})),
        ("bioetl-provider-health-v2.json", 9107, frozenset({"reason"})),
    )
    for dashboard_name, panel_id, allowed in cases:
        panel = _panel(_load(dashboard_name), panel_id)
        grid = panel["gridPos"]
        assert int(grid["h"]) >= 5, (dashboard_name, panel_id, grid)
        custom = (panel.get("fieldConfig") or {}).get("defaults", {}).get("custom", {})
        assert custom.get("cellOptions", {}).get("wrapText") is not True
        wrapped = _wrapped_field_names(panel)
        assert wrapped == allowed, (dashboard_name, panel_id, wrapped)
        assert any(
            (_override_width(panel, name) is None)
            or ((_override_width(panel, name) or 0) >= 260)
            for name in wrapped
        )


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


def test_incident_ranked_suspects_hides_merged_activation_fields() -> None:
    incident = _load("bioetl-incident-v1.json")
    suspects = _panel(incident, 2010)
    organize = next(
        transform
        for transform in suspects.get("transformations", [])
        if transform.get("id") == "organize"
    )
    exclude = organize.get("options", {}).get("excludeByName", {})

    assert len(suspects.get("targets", [])) == 3
    assert all(
        "topk(5," in str(target.get("expr") or "")
        for target in suspects.get("targets", [])
    )
    assert any(
        transform.get("id") == "limit"
        and (transform.get("options") or {}).get("limitField") == 5
        for transform in suspects.get("transformations", [])
    )
    for field in (
        "Time",
        "Time 1",
        "Time 2",
        "Value",
        "Value #A",
        "Value #B",
        "Value #C",
    ):
        assert exclude.get(field) is True
    assert not {
        value
        for value in organize.get("options", {}).get("renameByName", {}).values()
        if str(value).startswith("Series ")
    }


def test_incident_alert_history_has_readable_full_width_layout() -> None:
    incident = _load("bioetl-incident-v1.json")
    current_alerts = _panel(incident, 2005)
    history = _panel(incident, 2006)
    impact = _panel(incident, 2007)
    history_grid = history.get("gridPos", {})

    assert current_alerts.get("gridPos", {}).get("w") == 24
    assert history_grid.get("x") == 0
    assert history_grid.get("w") == 24
    assert history_grid.get("h") == 8
    assert history.get("options", {}).get("legend", {}).get("showLegend") is False
    assert history.get("options", {}).get("showValue") == "always"
    assert history.get("options", {}).get("rowHeight") == 1.0
    assert impact.get("gridPos", {}).get("y", 0) >= (
        history_grid.get("y", 0) + history_grid.get("h", 0)
    )
    assert current_alerts.get("gridPos", {}).get("y", 0) >= 18
    assert "ALERTS" in str(history.get("targets", [{}])[0].get("expr", ""))
    assert str(history.get("targets", [{}])[0].get("legendFormat", "")).startswith(
        "{{alertstate}}"
    )
    color_overrides = {
        override.get("matcher", {}).get("options"): {
            prop.get("id"): prop.get("value") for prop in override.get("properties", [])
        }
        for override in history.get("fieldConfig", {}).get("overrides", [])
    }
    assert color_overrides[".*firing.*"]["color"] == {
        "mode": "fixed",
        "fixedColor": "red",
    }
    assert (
        color_overrides[".*firing.*"]["mappings"][0]["options"]["1"]["text"] == "FIRING"
    )
    assert (
        color_overrides[".*pending.*"]["mappings"][0]["options"]["1"]["text"]
        == "PENDING"
    )
    assert color_overrides[".*pending.*"]["color"] == {
        "mode": "fixed",
        "fixedColor": "orange",
    }


def test_incident_alert_count_and_dq_reason_have_honest_table_semantics() -> None:
    incident = _load("bioetl-incident-v1.json")
    current_alerts = _panel(incident, 2005)
    dq_suspects = _panel(incident, 2004)

    assert current_alerts.get("targets", [{}])[0].get("expr") == (
        'count by (alertname, alertstate) (ALERTS{alertstate=~"firing|pending"})'
    )
    count_override = next(
        override
        for override in current_alerts["fieldConfig"]["overrides"]
        if override.get("matcher", {}).get("options")
        == r"^(Value|#Value|Value \(.*\)|value)$"
    )
    count_properties = {
        property_["id"]: property_["value"]
        for property_ in count_override["properties"]
    }
    assert count_properties == {
        "custom.cellOptions": {"type": "auto"},
        "custom.align": "right",
        "custom.width": 120,
        "displayName": "Active Alerts",
    }

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
    assert overrides["Pipeline"]["custom.width"] == 70
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
    assert visible_width <= 187


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
    assert any("var-run_id=${__value.raw}" in url for url in first_links)
    assert any("var-pipeline=${__data.fields.Pipeline}" in url for url in first_links)
    assert all("viewPanel=" not in url for url in first_links)
    assert "viewPanel" not in str(first_screen.get("description") or "")
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
    assert "Pipeline" in hidden
    target_url = str((first_screen.get("targets") or [{}])[0].get("url") or "")
    assert "run_id=${run_id}" in target_url
    selected = [
        item
        for item in (first_screen.get("fieldConfig") or {}).get("overrides") or []
        if isinstance(item, dict)
        and (item.get("matcher") or {}).get("options") == "selected"
    ]
    assert selected, "3010 must mark the selected run_id row"
    identity = _panel(explorer, 3022)
    assert str(
        identity.get("fieldConfig", {}).get("defaults", {}).get("noValue", "")
    ).startswith("SELECT RUN")
    assert all(
        panel.get("id") != 3021 for panel in _iter_panels(explorer.get("panels") or [])
    )


def test_run_explorer_selected_run_details_row_nests_forensics() -> None:
    """REC-03: Selected Run Details must collapse nested forensic panels."""
    explorer = _load("bioetl-run-explorer-v1.json")
    row = next(panel for panel in explorer.get("panels", []) if panel.get("id") == 3099)
    assert row.get("type") == "row"
    assert row.get("collapsed") is True
    nested = {
        panel.get("id"): panel
        for panel in row.get("panels") or []
        if isinstance(panel, dict)
    }
    nested_ids = set(nested)
    assert {3011, 3012, 3013, 3014, 3022, 3023} <= nested_ids
    assert 3015 not in nested_ids
    assert 3021 not in nested_ids
    assert 3001 not in nested_ids
    identity_grid = nested[3022].get("gridPos") or {}
    records_grid = nested[3023].get("gridPos") or {}
    funnel_grid = nested[3011].get("gridPos") or {}
    reasons_grid = nested[3012].get("gridPos") or {}
    timings_grid = nested[3014].get("gridPos") or {}
    assert int(identity_grid.get("h") or 0) >= 14
    assert int(records_grid.get("h") or 0) >= 14
    assert int(records_grid.get("w") or 0) == int(reasons_grid.get("w") or 0)
    assert int(identity_grid.get("w") or 0) + int(records_grid.get("w") or 0) == 24
    assert int(funnel_grid.get("w") or 0) + int(reasons_grid.get("w") or 0) == 24
    assert funnel_grid.get("y") == reasons_grid.get("y")
    assert int(timings_grid.get("h") or 0) <= 4

    # Forensics must not remain as root siblings.
    root_ids = {panel.get("id") for panel in explorer.get("panels") or []}
    assert 3015 not in root_ids


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
    assert _override_width(recent, "selected") == 36
    assert (_override_width(recent, "Workflow") or 0) == 72
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
    assert "Pipeline" in hidden
    assert "message" in hidden
    grid = recent.get("gridPos") or {}
    assert int(grid.get("h") or 0) == 12
    assert recent.get("options", {}).get("cellHeight") == "sm"
    assert (recent.get("transformations") or [{}])[0].get("options", {}).get(
        "limitField"
    ) == 10


def test_run_explorer_funnel_removals_empty_is_emdash_not_valid_empty() -> None:
    explorer = _load("bioetl-run-explorer-v1.json")
    row = next(panel for panel in explorer.get("panels", []) if panel.get("id") == 3099)
    nested = {
        panel.get("id"): panel
        for panel in row.get("panels") or []
        if isinstance(panel, dict)
    }
    funnel = nested[3011]
    defaults = str(
        (funnel.get("fieldConfig") or {}).get("defaults", {}).get("noValue") or ""
    )
    assert defaults.startswith("VALID EMPTY")
    assert _override_novalue(funnel, "Removals") == "—"
    assert (_override_width(funnel, "Removals") or 0) >= 280


def test_run_explorer_artifact_ref_wraps_below_fold() -> None:
    explorer = _load("bioetl-run-explorer-v1.json")
    row = next(panel for panel in explorer.get("panels", []) if panel.get("id") == 3099)
    assert row.get("collapsed") is True
    nested = {
        panel.get("id"): panel
        for panel in row.get("panels") or []
        if isinstance(panel, dict)
    }
    artifacts = nested[3013]
    assert int((artifacts.get("gridPos") or {}).get("h") or 0) >= 8
    assert (_override_width(artifacts, "ref") or 0) == 640
    organize = next(
        transform
        for transform in artifacts.get("transformations") or []
        if transform.get("id") == "organize"
    )
    exclude = (organize.get("options") or {}).get("excludeByName") or {}
    assert exclude.get("Time") is True
    assert "__name__" not in exclude
    wrap = False
    for item in (artifacts.get("fieldConfig") or {}).get("overrides") or []:
        if not isinstance(item, dict):
            continue
        if str((item.get("matcher") or {}).get("options") or "") != "ref":
            continue
        for prop in item.get("properties") or []:
            if not isinstance(prop, dict) or prop.get("id") != "custom.cellOptions":
                continue
            value = prop.get("value") or {}
            wrap = bool(isinstance(value, dict) and value.get("wrapText") is True)
    assert wrap is True


def test_below_fold_tables_exclude_time_without_name_metric() -> None:
    """Below-fold inspect tables hide Grafana Time, not __name__."""
    cases = (
        ("bioetl-run-explorer-v1.json", 3011),
        ("bioetl-run-explorer-v1.json", 3014),
        ("bioetl-incident-v1.json", 2002),
        ("bioetl-incident-v1.json", 2005),
        ("bioetl-control-plane-v1.json", 9415),
        ("bioetl-control-plane-v1.json", 9413),
        ("bioetl-control-plane-v1.json", 9414),
        ("bioetl-control-plane-v1.json", 9407),
        ("bioetl-control-plane-v1.json", 9405),
        ("bioetl-control-plane-v1.json", 9406),
        ("bioetl-control-plane-v1.json", 9408),
        ("bioetl-control-plane-v1.json", 9409),
        ("bioetl-control-plane-v1.json", 9417),
        ("bioetl-run-explorer-v1.json", 3022),
        ("bioetl-run-explorer-v1.json", 3011),
        ("bioetl-run-explorer-v1.json", 3012),
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
    funnel = _panel(_load("bioetl-run-explorer-v1.json"), 3011)
    custom = (funnel.get("fieldConfig") or {}).get("defaults", {}).get("custom", {})
    assert custom.get("inspect") is True


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
        ("bioetl-provider-health-v2.json", 9111),
        ("bioetl-provider-health-v2.json", 9112),
        ("bioetl-provider-health-v2.json", 9113),
        ("bioetl-provider-health-v2.json", 107),
        ("bioetl-provider-health-v2.json", 108),
        ("bioetl-provider-health-v2.json", 114),
    )
    for dashboard_name, panel_id in cases:
        panel = _panel(_load(dashboard_name), panel_id)
        custom = (panel.get("fieldConfig") or {}).get("defaults", {}).get("custom", {})
        assert custom.get("inspect") is True, (dashboard_name, panel_id)


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
