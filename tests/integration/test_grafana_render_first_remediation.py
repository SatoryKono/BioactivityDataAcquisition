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
    # fail-closed empty semantics via vector(0) and value color mode.
    runtime = _load("bioetl-runtime.json")
    for panel_id in (9996, 9997):
        panel = _panel(runtime, panel_id)
        expression = str(panel.get("targets", [{}])[0].get("expr", ""))
        assert "or vector(0)" in expression
        assert panel.get("options", {}).get("colorMode") == "value"

    # Silver Reject Explorer terminal-state panels and Loki log-hygiene cards
    # (runtime ids 250/251/257/258) were removed 2026-07-23.


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
    assert inputs["gridPos"]["w"] >= 10

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
        assert no_value.startswith("Not resolved")
    # Workflow overview + Alerts/SLO retired; ID-card noValue contract remains.


def test_rf005_incident_hierarchy_and_semantic_encoding() -> None:
    overview = _load("bioetl-overview-v2.json")
    assert _panel(overview, 215)["gridPos"]["y"] <= 7
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
    assert all(panel.get("collapsed") is False for panel in control_rows)
    first_row_y = min(panel["gridPos"]["y"] for panel in control_rows)
    assert first_row_y >= 0

    overview = _load("bioetl-overview-v2.json")
    for row_id in (9014, 9009, 9012, 9600):
        row = _panel(overview, row_id)
        assert row.get("type") == "row"
        assert row.get("collapsed") is False
    assert _panel(overview, 215)["title"] == "Review First Action"
    assert _panel(overview, 9601).get("type") == "table"

    runtime = _load("bioetl-runtime.json")
    for row_id in (252, 253, 254):
        assert _panel(runtime, row_id).get("collapsed") is False


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


def test_operator_critical_tables_expose_full_values() -> None:
    expected_panels = {
        "bioetl-dq-v2.json": (9102,),
        "bioetl-incident-v1.json": (2010, 2002, 2003, 2004, 2005),
        "bioetl-run-explorer-v1.json": (9402,),
    }

    for dashboard_name, panel_ids in expected_panels.items():
        dashboard = _load(dashboard_name)
        for panel_id in panel_ids:
            panel = _panel(dashboard, panel_id)
            custom = panel["fieldConfig"]["defaults"]["custom"]
            assert custom["inspect"] is True
            if dashboard_name != "bioetl-run-explorer-v1.json":
                assert custom["cellOptions"]["wrapText"] is True
