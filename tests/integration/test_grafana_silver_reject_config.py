"""Focused Grafana contract checks for Silver reject summary surfaces."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    get_row_child_panels,
    load_dashboard,
)


pytestmark = pytest.mark.integration


def test_silver_filter_reject_accounting_mismatch_panel_uses_reconciliation_rule() -> (
    None
):
    """DQ dashboard must surface the shipped reject-accounting reconciliation rule."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor: Silver Filter Reject Accounting Mismatch"
        ),
        None,
    )
    assert panel is not None, (
        "Panel 'Monitor: Silver Filter Reject Accounting Mismatch' not found"
    )

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert expressions, (
        "Panel 'Monitor: Silver Filter Reject Accounting Mismatch' must define a query target"
    )
    assert any(
        "bioetl_silver_filter_reject_total_mismatch_15m" in expr for expr in expressions
    ), (
        "Monitor: Silver Filter Reject Accounting Mismatch must use the shipped "
        "bioetl_silver_filter_reject_total_mismatch_15m recording rule"
    )
    assert any("[$__range]" in expr for expr in expressions), (
        "Monitor: Silver Filter Reject Accounting Mismatch must respect the selected "
        "Grafana time range"
    )
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    threshold_steps = defaults.get("thresholds", {}).get("steps", [])
    assert threshold_steps[-1].get("value") == 1
    assert panel.get("options", {}).get("colorMode") == "backgroundSolid"


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-dq-v2.json", "Track: Silver Filter Rejects in Range"),
        ("bioetl-dq-v2.json", "Inspect: Silver Filter Rejects by Pipeline"),
    ],
)
def test_silver_filter_reject_panels_use_filtered_out_stage(
    dashboard_file: str, panel_title: str
) -> None:
    """Silver filter rejects must stay separate from DQ quarantine semantics."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel '{panel_title}' not found in {dashboard_file}"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert expressions, f"Panel '{panel_title}' in {dashboard_file} has no expressions"
    assert any("bioetl_records_processed_total" in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must use "
        "bioetl_records_processed_total"
    )
    assert any('stage="filtered_out"' in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must filter on stage=\"filtered_out\""
    )
    assert any("[$__range]" in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must use the selected Grafana time range"
    )


def test_gold_reject_panel_uses_gold_outcome_recording_rules() -> None:
    """Gold reject surface must not reuse Silver filtered_out semantics."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect: Gold Reject Outcomes by Pipeline"
        ),
        None,
    )

    assert panel is not None
    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    joined = "\n".join(expressions)
    assert "bioetl_processed_records_gold_quarantined_current" in joined
    assert "bioetl_processed_records_gold_excluded_by_contract_current" in joined
    assert 'stage="filtered_out"' not in joined
    assert "bioetl_silver_filter_rejections_total" not in joined
    assert "[$__range]" in joined

    description = str(panel.get("description", "")).lower()
    assert "gold contract" in description
    assert "semantic" in description
    assert "silver structural" in description
    assert "filtered_out_silver" in description

    links = [
        *panel.get("links", []),
        *panel.get("options", {}).get("dataLinks", []),
    ]
    assert all(
        "bioetl-silver-reject-explorer" not in str(link.get("url", ""))
        for link in links
    )


def test_silver_filter_reject_rate_uses_selected_time_range() -> None:
    """Silver filter reject rate must follow the active dashboard time range."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Silver Rejects + Rate"
        ),
        None,
    )
    assert panel is not None, "Panel 'Silver Rejects + Rate' not found"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any("[$__range]" in expr for expr in expressions), (
        "Silver Filter Reject Rate must use the selected Grafana time range"
    )


def test_dq_reject_row_orders_trust_then_causes_then_scope_distribution() -> None:
    """Collapsed reject disclosure must order trust, causes, then scope detail."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    row = next(
        (
            item
            for item in dashboard.get("panels", [])
            if item.get("type") == "row"
            and item.get("title")
            == "Silver Structural / Gold Contract-Semantic Rejects"
        ),
        None,
    )
    assert row is not None
    assert row.get("collapsed") is True
    nested = {
        panel.get("title"): panel
        for panel in get_row_child_panels(
            dashboard, "Silver Structural / Gold Contract-Semantic Rejects"
        )
    }
    expected_titles = {
        "Monitor: Silver Filter Reject Accounting Mismatch",
        "Inspect: Top Silver Reject Reasons (Pareto)",
        "Inspect: Top Silver Reject Fields",
        "Inspect: Silver Filter Rejects by Pipeline",
        "Inspect: Gold Reject Outcomes by Pipeline",
    }
    assert expected_titles.issubset(nested)
    ordering = {
        title: (
            nested[title].get("gridPos", {}).get("y", 999)
            - row.get("gridPos", {}).get("y", 0),
            nested[title].get("gridPos", {}).get("x", 999),
        )
        for title in expected_titles
    }
    assert ordering["Monitor: Silver Filter Reject Accounting Mismatch"] == (1, 0)
    assert ordering["Inspect: Top Silver Reject Reasons (Pareto)"] == (6, 0)
    assert ordering["Inspect: Top Silver Reject Fields"] == (6, 12)
    assert ordering["Inspect: Silver Filter Rejects by Pipeline"] == (12, 0)
    assert ordering["Inspect: Gold Reject Outcomes by Pipeline"] == (12, 12)
    assert (
        nested["Monitor: Silver Filter Reject Accounting Mismatch"]
        .get("gridPos", {})
        .get("w")
        == 24
    )
    for panel_title in expected_titles - {
        "Monitor: Silver Filter Reject Accounting Mismatch"
    }:
        assert nested[panel_title].get("gridPos", {}).get("w") == 12


def test_dq_validation_diagnostics_groups_failures_then_runtime_then_trends() -> None:
    """Collapsed validation detail must preserve context-to-handoff hierarchy."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    row = next(
        (
            item
            for item in dashboard.get("panels", [])
            if item.get("type") == "row"
            and item.get("title")
            == "Validation Failures / Runtime Diagnostics / Trends"
        ),
        None,
    )
    assert row is not None
    assert row.get("collapsed") is True
    nested = {
        panel.get("title"): panel
        for panel in get_row_child_panels(
            dashboard, "Validation Failures / Runtime Diagnostics / Trends"
        )
    }
    expected_titles = {
        "Track Range Evidence: Bronze -> Silver -> Gold",
        "Track: Source Records in Range (Bronze)",
        "Track: Clean Records in Range (Gold)",
        "Track: Silver Validation Failures in Range",
        "Review: Latest Successful Data Timestamp",
        "Inspect: Quarantine by Error Type",
        "Monitor: Silver Validation Failures",
        "Monitor: Gold Strict Validation Failures",
        "Track: Anomalies Detected",
        "Track: DQ Check Duration (p95)",
        "Track: DQ Threshold Events in Range Trend",
        "Track: Data Quality Score Trend (Volume-weighted)",
        "Review: Lineage Handoff to Control Plane",
        "Review: Aggregate Control-plane Handoff",
    }
    assert set(nested) == expected_titles
    row_y = row.get("gridPos", {}).get("y", 0)
    assert nested["Track Range Evidence: Bronze -> Silver -> Gold"].get(
        "gridPos", {}
    ) == {"h": 5, "w": 24, "x": 0, "y": row_y + 1}

    context_titles = {
        "Track: Source Records in Range (Bronze)",
        "Track: Clean Records in Range (Gold)",
        "Track: Silver Validation Failures in Range",
        "Review: Latest Successful Data Timestamp",
    }
    failure_titles = {
        "Inspect: Quarantine by Error Type",
        "Monitor: Silver Validation Failures",
        "Monitor: Gold Strict Validation Failures",
    }
    runtime_titles = {
        "Track: Anomalies Detected",
        "Track: DQ Check Duration (p95)",
    }
    trend_titles = {
        "Track: DQ Threshold Events in Range Trend",
        "Track: Data Quality Score Trend (Volume-weighted)",
    }
    handoff_titles = {
        "Review: Lineage Handoff to Control Plane",
        "Review: Aggregate Control-plane Handoff",
    }

    def _ys(titles: set[str]) -> list[int]:
        return [nested[title].get("gridPos", {}).get("y", -1) for title in titles]

    assert max(_ys(context_titles)) <= min(_ys(failure_titles))
    assert max(_ys(failure_titles)) < min(_ys(runtime_titles))
    assert max(_ys(runtime_titles)) < min(_ys(trend_titles))
    assert max(_ys(trend_titles)) < min(_ys(handoff_titles))

    for left_title, right_title in (
        (
            "Monitor: Silver Validation Failures",
            "Monitor: Gold Strict Validation Failures",
        ),
        ("Track: Anomalies Detected", "Track: DQ Check Duration (p95)"),
        (
            "Track: DQ Threshold Events in Range Trend",
            "Track: Data Quality Score Trend (Volume-weighted)",
        ),
    ):
        pair = [nested[left_title], nested[right_title]]
        assert {panel.get("gridPos", {}).get("x") for panel in pair} == {0, 12}
        assert {panel.get("gridPos", {}).get("w") for panel in pair} == {12}
        assert len({panel.get("gridPos", {}).get("y") for panel in pair}) == 1
    for title in handoff_titles:
        grid = nested[title].get("gridPos", {})
        assert grid.get("x") == 0
        assert grid.get("w") == 24


def test_dq_quarantine_breakdown_prefers_bar_comparison_over_pie_share() -> None:
    """Quarantine breakdown should optimize category comparison, not composition-only pie slices."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect: Quarantine by Error Type"
        ),
        None,
    )
    assert panel is not None
    assert panel.get("type") == "bargauge"
    assert panel.get("options", {}).get("orientation") == "horizontal"
    assert "Horizontal bars are intentional" in str(panel.get("description", ""))


@pytest.mark.parametrize(
    "panel_title",
    [
        "Monitor: Silver Filter Reject Accounting Mismatch",
        "Monitor: Silver Validation Failures",
        "Monitor: Gold Strict Validation Failures",
    ],
)
def test_dq_failure_monitors_use_background_severity_and_nonzero_red(
    panel_title: str,
) -> None:
    """Hard monitors should escalate visually when failures become non-zero."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None
    assert panel.get("options", {}).get("colorMode") == "backgroundSolid"
    steps = (
        panel.get("fieldConfig", {})
        .get("defaults", {})
        .get("thresholds", {})
        .get("steps", [])
    )
    assert any(
        step.get("value") == 0 and step.get("color") == "green" for step in steps
    )
    assert any(step.get("value") == 1 and step.get("color") == "red" for step in steps)


def test_silver_reject_explorer_pipeline_scope_is_single_select_and_fail_closed() -> (
    None
):
    """Explorer must enforce one concrete pipeline for quarantine-backed reads."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    )
    variable_map = {
        variable.get("name"): variable
        for variable in dashboard.get("templating", {}).get("list", [])
        if variable.get("name")
    }

    pipeline_var = variable_map["pipeline"]
    assert pipeline_var.get("multi") is False
    assert pipeline_var.get("includeAll") is False

    note_panel = next(
        (
            panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title") == "Inspect Explorer Scope"
        ),
        None,
    )
    assert note_panel is not None, (
        "Silver Reject Explorer must define Inspect Explorer Scope note"
    )
    content = note_panel.get("options", {}).get("content", "")
    description = str(note_panel.get("description", ""))
    assert "choose one concrete pipeline" in content
    assert "Variable warning:" in content
    assert "Reset once" in content
    assert "check Backend Health" in content
    assert "Origin dashboards own shared workflow/run_id shell context" in description
    assert "never owns shared workflow or run_id selectors" in description
    assert "pipeline/run_type forensic" in description
    assert dashboard.get("time", {}).get("from") == "now-24h"

    for panel in get_dashboard_panels(dashboard):
        for target in panel.get("targets", []):
            url = target.get("url", "")
            if not isinstance(url, str) or "/ops/quarantine/" not in url:
                continue
            assert "pipeline=${pipeline:csv}" not in url, (
                "Quarantine Explorer URLs must not pass multi-pipeline CSV scope"
            )
            assert "pipeline=${pipeline}" in url, (
                "Quarantine Explorer URLs must pass one concrete pipeline value"
            )


@pytest.mark.parametrize(
    ("panel_title", "label_name"),
    [
        ("Inspect: Top Silver Reject Reasons (Pareto)", "reason_code"),
        ("Inspect: Top Silver Reject Fields", "field"),
    ],
)
def test_silver_filter_breakdown_panels_use_bounded_breakdown_metric(
    panel_title: str, label_name: str
) -> None:
    """Reason/field breakdown panels must use the bounded Silver breakdown metric."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel '{panel_title}' not found in bioetl-dq-v2.json"

    targets = [
        target for target in panel.get("targets", []) if isinstance(target, dict)
    ]
    assert targets, f"Panel '{panel_title}' must define at least one query target"
    expressions = [
        target.get("expr", "")
        for target in targets
        if isinstance(target.get("expr"), str)
    ]
    assert any(
        "bioetl_silver_filter_rejections_total" in expr for expr in expressions
    ), f"Panel '{panel_title}' must use bioetl_silver_filter_rejections_total"
    assert any(f"by ({label_name})" in expr for expr in expressions), (
        f"Panel '{panel_title}' must group by {label_name}"
    )
    assert any("[$__range]" in expr for expr in expressions), (
        f"Panel '{panel_title}' must use the selected Grafana time range"
    )
    assert all(target.get("instant") is True for target in targets), (
        f"Panel '{panel_title}' must use instant Prometheus queries"
    )


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-dq-v2.json", "Track: Silver Filter Rejects in Range"),
    ],
)
def test_silver_filter_rejects_summary_panels_use_instant_queries(
    dashboard_file: str, panel_title: str
) -> None:
    """Selected-range reject totals should be evaluated as instant summaries."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel '{panel_title}' not found in {dashboard_file}"

    targets = [
        target for target in panel.get("targets", []) if isinstance(target, dict)
    ]
    assert targets, (
        f"Panel '{panel_title}' in {dashboard_file} must define a query target"
    )
    assert all(target.get("instant") is True for target in targets), (
        f"Panel '{panel_title}' in {dashboard_file} must use instant Prometheus queries"
    )


def test_silver_reject_explorer_payload_link_preserves_time_scope() -> None:
    """Payload-hash self-link should keep the active time range."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect Filtered Records Table"
        ),
        None,
    )
    assert panel is not None
    links = panel.get("fieldConfig", {}).get("defaults", {}).get("links", [])
    payload_link = next(
        (
            link
            for link in links
            if link.get("title") == "Open same dashboard with this payload_hash"
        ),
        None,
    )
    assert payload_link is not None
    assert payload_link.get("targetBlank") is False, (
        "Payload drilldown link must stay in the same tab to preserve forensic flow"
    )
    url = str(payload_link.get("url", ""))
    assert "${__url_time_range}" in url or ("${__from}" in url and "${__to}" in url), (
        "Payload drilldown link must preserve forensic time scope"
    )
    description = str(panel.get("description", ""))
    assert "latest 100" in description.lower()

    cli_titles = {
        "Open quarantine CLI command",
        "Copy quarantine resolve command for this payload_hash",
    }
    cli_links = [link for link in links if link.get("title") in cli_titles]
    assert {link.get("title") for link in cli_links} == cli_titles
    for link in cli_links:
        assert str(link.get("url", "")).startswith("data:text/plain,"), (
            "CLI handoff links must remain data:text/plain payloads"
        )
        assert link.get("targetBlank") is True, (
            "CLI handoff links must open in a new tab instead of replacing the explorer"
        )


def test_silver_reject_explorer_backend_health_marker_uses_live_health_probe() -> None:
    """Explorer must expose a first-screen backend trust marker via /health/live."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Explorer Backend Health"
        ),
        None,
    )
    assert panel is not None, (
        "Silver Reject Explorer must define a backend health marker panel"
    )
    assert panel.get("datasource") == "Quarantine Explorer"
    assert panel.get("type") == "table"
    assert panel.get("id") == 13
    assert panel.get("gridPos", {}).get("y", 999) <= 11

    targets = panel.get("targets", [])
    assert targets, "Explorer backend health marker must define a query target"
    target = targets[0]
    assert target.get("url") == "/health/live"
    assert target.get("root_selector") == "$.checks.server"

    no_value = str(panel.get("fieldConfig", {}).get("defaults", {}).get("noValue", ""))
    assert no_value.startswith("ERROR")
    assert "/health/live" in no_value
    assert "blank or loading is forbidden" in no_value
    description = str(panel.get("description", ""))
    for token in ("HEALTHY", "ERROR", "VALID EMPTY", "blank", "loading"):
        assert token in description


def test_silver_reject_explorer_first_action_documents_no_data_semantics() -> None:
    """Explorer must make 0-vs-no-data interpretation visible on first screen."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Review: First Action / No-Data Semantics"
        ),
        None,
    )
    assert panel is not None
    assert panel.get("gridPos", {}).get("y", 999) <= 11
    content = str(panel.get("options", {}).get("content", ""))
    assert "One action:" in content
    assert "confirm Backend Health and one concrete pipeline" in content
    assert "VALID EMPTY = successful zero rows" in content
    assert "TELEMETRY ABSENT" in content
    assert "QUERY ERROR" in content
    assert "DATASOURCE ERROR" in content
    assert "expand Trends only for non-zero rejects" in content
    assert "Records only after narrowing" in content


def test_silver_reject_explorer_scope_banner_documents_zero_reject_workflow_case() -> (
    None
):
    """Scope note must explain the intentional zero-reject workflow empty state."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect Explorer Scope"
        ),
        None,
    )
    assert panel is not None
    combined = " ".join(
        (
            str(panel.get("description", "")),
            str(panel.get("options", {}).get("content", "")),
        )
    ).lower()
    assert "zero-reject workflow" in combined
    assert "interpretation" in combined
    assert "bronze denominator" in combined


@pytest.mark.parametrize(
    "panel_title",
    [
        "Monitor Filtered Records Total",
        "Track Reject Rate vs Bronze",
        "Inspect Run Scope Summary",
        "Inspect Top Reject Reasons",
        "Inspect Top Reject Fields",
        "Inspect Top Reason Signatures",
        "Inspect Selected Record Details",
    ],
)
def test_silver_reject_explorer_panels_have_specific_triage_descriptions(
    panel_title: str,
) -> None:
    """Panel descriptions should explain selected-range triage semantics, not generic status copy."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None
    description = str(panel.get("description", ""))
    assert "Selected-range" in description or "selected-range" in description
    assert "Status mapping: 0 = healthy/ok" not in description
    assert any(
        token in description for token in ("No data", "UNKNOWN", "Empty", "empty", "0")
    )


@pytest.mark.parametrize(
    "panel_title",
    [
        "Monitor Filtered Records Total",
        "Track Reject Rate vs Bronze",
        "Inspect Run Scope Summary",
        "Inspect Filtered Records Table",
        "Inspect Selected Record Details",
    ],
)
def test_silver_reject_explorer_datasource_trust_copy_distinguishes_empty_scope_and_backend_failure(
    panel_title: str,
) -> None:
    """HTTP-backed explorer panels must explain empty-result vs backend-failure semantics."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None
    description = str(panel.get("description", ""))
    no_value = str(panel.get("fieldConfig", {}).get("defaults", {}).get("noValue", ""))
    combined = f"{description} {no_value}"
    assert any(
        token in combined
        for token in ("Quarantine Explorer", "backend", "API", "datasource")
    )
    assert any(
        token in combined
        for token in (
            "zero matching rows",
            "No rejected records for current filters",
            "No data",
            "missing/empty",
            "empty summary",
            "excluded record",
        )
    )
    assert any(
        token in combined
        for token in (
            "UNKNOWN",
            "error state",
            "datasource",
            "datasource failure",
            "filter chain",
        )
    )


def test_silver_reject_summary_panels_use_quarantine_explorer_stats_endpoint() -> None:
    """Summary panels must validate the real Quarantine Explorer stats path."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    )
    expected_titles = {
        "Monitor Filtered Records Total",
        "Track Reject Rate vs Bronze",
        "Inspect Run Scope Summary",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_titles
    }
    assert set(panels) == expected_titles

    for title, panel in panels.items():
        assert panel.get("datasource") == "Quarantine Explorer", (
            f"{title} must use Quarantine Explorer datasource"
        )
        targets = panel.get("targets", [])
        assert targets, f"{title} must define a query target"
        url = str(targets[0].get("url", ""))
        assert "/ops/quarantine/filtered-stats" in url, (
            f"{title} must read from the real filtered-stats datasource path"
        )


def test_silver_reject_summary_panels_tie_zero_state_to_datasource_response() -> None:
    """Explorer copy must distinguish real zero-reject results from datasource UNKNOWN."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    )
    expected_phrases = {
        "Monitor Filtered Records Total": (
            "0 is normal only when Quarantine Explorer responds",
            "No data or datasource errors are UNKNOWN",
        ),
        "Track Reject Rate vs Bronze": (
            "Selected-range reject_ratio, bronze_records, and total from /ops/quarantine/filtered-stats",
            "bronze_records=0 means the denominator is missing/empty and the signal is UNKNOWN",
        ),
        "Inspect Run Scope Summary": (
            "Quarantine Explorer responds",
            "zero-reject workflow run is therefore a legitimate empty explorer state",
        ),
    }

    for panel in get_dashboard_panels(dashboard):
        title = panel.get("title")
        if title not in expected_phrases:
            continue
        description = str(panel.get("description", ""))
        for phrase in expected_phrases[title]:
            assert phrase in description, (
                f"{title} must document datasource-backed zero-state semantics: {phrase}"
            )


def test_dq_reject_panels_link_to_silver_reject_explorer() -> None:
    """DQ reject panels should hand off directly into the Silver Reject Explorer."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    for panel_title in (
        "Track: Silver Filter Rejects in Range",
        "Inspect: Top Silver Reject Reasons (Pareto)",
        "Inspect: Top Silver Reject Fields",
    ):
        panel = next(
            (
                item
                for item in get_dashboard_panels(dashboard)
                if item.get("title") == panel_title
            ),
            None,
        )
        assert panel is not None
        links = [
            *panel.get("links", []),
            *panel.get("options", {}).get("dataLinks", []),
        ]
        explorer_link = next(
            (
                link
                for link in links
                if link.get("uid") == "bioetl-silver-reject-explorer"
                or "/d/bioetl-silver-reject-explorer/bioetl-silver-reject-explorer"
                in str(link.get("url", ""))
            ),
            None,
        )
        assert explorer_link is not None, (
            f"{panel_title!r} must expose Explorer handoff"
        )
        assert explorer_link.get("keepTime") is True or "${__url_time_range}" in str(
            explorer_link.get("url", "")
        )
        url = str(explorer_link.get("url", ""))
        assert "var-pipeline=" in url
        assert "var-run_type=" in url

        if panel_title == "Inspect: Top Silver Reject Reasons (Pareto)":
            assert "var-reason_code=" in url
        if panel_title == "Inspect: Top Silver Reject Fields":
            assert "var-field=" in url
        if panel_title == "Track: Silver Filter Rejects in Range":
            assert "var-reason_code=" not in url
            assert "var-field=" not in url


def test_dq_pipeline_breakdown_handoff_does_not_mislabel_pipeline_as_reason() -> None:
    """Pipeline breakdown handoff must preserve only pipeline/run_type scope."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect: Silver Filter Rejects by Pipeline"
        ),
        None,
    )
    assert panel is not None

    links = [
        *panel.get("links", []),
        *panel.get("options", {}).get("dataLinks", []),
    ]
    explorer_link = next(
        (
            link
            for link in links
            if "/d/bioetl-silver-reject-explorer/bioetl-silver-reject-explorer"
            in str(link.get("url", ""))
        ),
        None,
    )
    assert explorer_link is not None
    url = str(explorer_link.get("url", ""))
    assert "var-pipeline=${__series.name}" in url
    assert "var-run_type=" in url
    assert "var-reason_code=" not in url
    assert "var-field=" not in url


@pytest.mark.parametrize(
    ("panel_title", "required_phrase"),
    [
        (
            "Inspect: Top Silver Reject Reasons (Pareto)",
            "drilldown",
        ),
        (
            "Inspect: Top Silver Reject Fields",
            "drilldown",
        ),
    ],
)
def test_dq_breakdown_panels_describe_direct_explorer_drilldowns(
    panel_title: str,
    required_phrase: str,
) -> None:
    """Breakdown panels should describe the scoped Explorer drilldown behavior."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None
    description = str(panel.get("description", ""))
    assert "Silver Reject Explorer" in description
    assert required_phrase in description


@pytest.mark.parametrize(
    ("panel_title", "forbidden_snippet"),
    [
        (
            "Inspect: Silver Filter Rejects by Pipeline",
            'label_replace(vector(0), "pipeline", "no_events"',
        ),
        (
            "Inspect: Top Silver Reject Reasons (Pareto)",
            'label_replace(vector(0), "reason_code", "none"',
        ),
        (
            "Inspect: Top Silver Reject Fields",
            'label_replace(vector(0), "field", "none"',
        ),
        (
            "Inspect: Quarantine by Error Type",
            'label_replace(vector(0), "error_type", "none"',
        ),
        (
            "Track: Anomalies Detected",
            'label_replace(label_replace(vector(0), "severity", "none"',
        ),
    ],
)
def test_dq_breakdown_panels_do_not_invent_synthetic_placeholder_categories(
    panel_title: str,
    forbidden_snippet: str,
) -> None:
    """Diagnostic breakdown panels should preserve empty-state semantics instead of fake labels."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None
    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert expressions
    assert all(forbidden_snippet not in expr for expr in expressions), (
        f"{panel_title} must not invent synthetic placeholder categories"
    )


@pytest.mark.parametrize(
    ("panel_title", "expected_no_value"),
    [
        (
            "Inspect: Silver Filter Rejects by Pipeline",
            "No filtered-out samples in range",
        ),
        (
            "Inspect: Top Silver Reject Reasons (Pareto)",
            "No reject reason samples in range",
        ),
        ("Inspect: Top Silver Reject Fields", "No reject field samples in range"),
        ("Inspect: Quarantine by Error Type", "No quarantined records in range"),
        ("Track: Anomalies Detected", "No anomaly events in range"),
    ],
)
def test_dq_breakdown_panels_publish_honest_empty_state_copy(
    panel_title: str,
    expected_no_value: str,
) -> None:
    """Operator-facing breakdown panels must explain empty states without fake domain labels."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("noValue") == expected_no_value


@pytest.mark.parametrize(
    "panel_title",
    [
        "Inspect: Silver Filter Rejects by Pipeline",
        "Inspect: Top Silver Reject Reasons (Pareto)",
        "Inspect: Top Silver Reject Fields",
        "Inspect: Quarantine by Error Type",
        "Track: Anomalies Detected",
    ],
)
def test_dq_breakdown_panels_document_no_data_as_absence_of_observations(
    panel_title: str,
) -> None:
    """Descriptions must frame no-data as missing observations, not synthetic domain values."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None
    description = str(panel.get("description", ""))
    assert "No data means" in description
    assert "must not invent" in description


def test_silver_reject_trend_panels_use_filtered_timeseries_endpoint() -> None:
    """Trend panels must use the dedicated filtered-timeseries backend path."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    )
    expected_titles = {
        "Track Filtered Rejects Over Time",
        "Track Reject Ratio vs Bronze Over Time",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_titles
    }
    assert set(panels) == expected_titles

    for title, panel in panels.items():
        assert panel.get("datasource") == "Quarantine Explorer"
        assert panel.get("type") == "timeseries"
        targets = panel.get("targets", [])
        assert targets, f"{title} must define a query target"
        url = str(targets[0].get("url", ""))
        assert "/ops/quarantine/filtered-timeseries" in url
        assert "bucket=1h" in url
