"""Integration tests for Grafana overview dashboard configuration."""

import json
from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    get_panel_expressions,
    load_dashboard,
)

pytestmark = pytest.mark.integration

def test_overview_dashboard_contains_control_plane_and_lineage_metrics():
    """Ensure overview dashboard keeps summary control-plane and lineage signals."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    all_expressions = "\n".join(get_panel_expressions(dashboard))

    required_metrics = [
        "bioetl_control_plane_manifest_writes_total",
        "bioetl_control_plane_ledger_appends_total",
        "bioetl_checkpoint_compatibility_events_total",
        "bioetl_lineage_refs_missing_total",
    ]
    missing = [metric for metric in required_metrics if metric not in all_expressions]
    assert not missing, f"Overview dashboard missing metrics: {missing}"


def test_overview_dashboard_has_l0_primary_question() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    description = dashboard.get("description", "")
    scope_panel = next(
        (
            panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title") == "L0 Overview Scope"
        ),
        None,
    )
    assert scope_panel is not None
    content = scope_panel.get("options", {}).get("content", "")

    expected_question = (
        "what is currently broken or degraded in BioETL, and where should the "
        "operator drill down first"
    )
    assert dashboard.get("title") == "1. BioETL Overview"
    assert dashboard.get("uid") == "bioetl-overview-v2"
    assert "L0 Overview" in description
    assert expected_question.lower() in (description + content).lower()
    assert "sre-data-platform" in description + content


def test_overview_answer_row_has_max_seven_panels() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    answer_panels = [
        panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("gridPos", {}).get("y") == 4
    ]
    answer_titles = {panel.get("title") for panel in answer_panels}

    assert 3 <= len(answer_panels) <= 7
    assert answer_titles == {
        "System Status",
        "Next Action",
        "Failed Runs in Range",
        "Worst Backlog Stage",
        "Worst Lag Stage",
        "Flow Balance",
    }


def test_overview_has_system_status_panel() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    panel = panels.get("System Status")

    assert panel is not None
    assert panel.get("type") == "stat"
    mapping_text = json.dumps(
        panel.get("fieldConfig", {}).get("defaults", {}).get("mappings", [])
    )
    for expected_status in ("OK", "DEGRADED", "BROKEN", "UNKNOWN"):
        assert expected_status in mapping_text

    expr = "\n".join(
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    for recording_rule in (
        "bioetl_runtime_alert_condition_pipeline_runs_failed_15m",
        "bioetl_runtime_alert_condition_stage_backlog_active_15m",
        "bioetl_runtime_alert_condition_stage_lag_high_15m",
        "bioetl_runtime_alert_condition_gold_write_missing_15m",
    ):
        assert recording_rule in expr, (
            f"System Status must use recording rule {recording_rule}"
        )
    for metric_name in (
        "bioetl_dq_validation_failures_total",
        "bioetl_control_plane_manifest_writes_total",
        "bioetl_checkpoint_compatibility_events_total",
        "bioetl_lineage_refs_missing_total",
    ):
        assert metric_name in expr
    assert 'severity="hard_fail"' in expr
    assert "[$__range]" in expr
    assert "or vector(0)" in expr


def test_overview_has_next_action_panel() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Next Action"
        ),
        None,
    )

    assert panel is not None
    assert panel.get("type") == "stat"
    serialized_panel = json.dumps(panel)
    for expected_target in (
        "Open 2. Runtime",
        "Open 4. Data Quality",
        "Open 3. Provider Health",
        "Open Control Plane v1",
        "Open 6. Workflow Overview",
    ):
        assert expected_target in serialized_panel
    assert "Runtime > CP > DQ > Provider > Workflow" in serialized_panel


def test_overview_does_not_render_yield_green_without_denominator() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    assert "Overall Yield" not in panels
    panel = panels.get("Flow Balance")
    assert panel is not None
    assert panel.get("type") == "table"
    assert "Bronze input is zero or missing" in panel.get("description", "")

    expr = "\n".join(
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    for expected_snippet in (
        'stage="bronze"',
        'stage="gold"',
        'stage="filtered_out"',
        "bioetl_dq_records_quarantined_total",
        "clamp_min(",
        "[$__range]",
    ):
        assert expected_snippet in expr


def test_overview_backlog_and_lag_panels_expose_stage() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    expectations = {
        "Worst Backlog Stage": "bioetl_stage_backlog_records",
        "Worst Lag Stage": "bioetl_stage_lag_seconds",
    }
    for panel_title, metric_name in expectations.items():
        panel = panels.get(panel_title)
        assert panel is not None
        assert panel.get("type") == "table"
        expr = "\n".join(
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        )
        assert metric_name in expr
        assert "topk(1" in expr
        assert "by (stage)" in expr
        assert "[$__range]" in expr


def test_critical_panels_expose_open_actionable_datalinks() -> None:
    """Critical stat/gauge/table panels must expose at least one Open <target> data link."""
    critical_panel_titles = {
        "bioetl-overview-v2.json": {
            "System Status",
            "Runtime Status",
            "Data Quality Status",
            "Control Plane Status",
            "Provider Status",
            "Workflow Status",
            "Worst Backlog Stage",
            "Worst Lag Stage",
        }
    }

    for dashboard_name, titles in critical_panel_titles.items():
        dashboard = load_dashboard(Path(f"grafana/dashboards/{dashboard_name}"))
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }

        for panel_title in titles:
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"Missing critical panel: {panel_title} in {dashboard_name}"
            )
            assert panel.get("type") in {"stat", "gauge", "table"}

            data_links = panel.get("options", {}).get("dataLinks", [])
            assert data_links, f"{panel_title} must define at least one data link"
            assert any(
                isinstance(link, dict)
                and isinstance(link.get("title"), str)
                and link["title"].startswith("Open ")
                and isinstance(link.get("url"), str)
                and link["url"].strip()
                for link in data_links
            ), f"{panel_title} must expose an actionable Open <target> link"


def test_overview_handoff_cards_show_status_and_reason() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    expected_status_cards = {
        "Runtime Status": "/d/bioetl-runtime/bioetl-runtime",
        "Data Quality Status": "/d/bioetl-dq-v2",
        "Control Plane Status": "/d/bioetl-control-plane-v1/bioetl-control-plane-v1",
        "Provider Status": "/d/bioetl-provider-health-v2/bioetl-provider-health-v2",
        "Workflow Status": "/d/bioetl-workflow-overview/bioetl-workflow-overview",
    }
    for panel_title, expected_url in expected_status_cards.items():
        panel = panels.get(panel_title)
        assert panel is not None
        assert panel.get("type") == "stat"
        serialized_panel = json.dumps(panel)
        for expected_status in ("OK", "DEGRADED", "BROKEN", "UNKNOWN"):
            assert expected_status in serialized_panel
        assert "Reason:" in serialized_panel
        assert "Next:" in serialized_panel
        assert expected_url in serialized_panel


def test_overview_no_duplicate_green_zero_cards() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    titles = {
        panel.get("title")
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    removed_or_merged_titles = {
        "Overall Yield",
        "Active Stage Backlog",
        "Worst Stage Lag",
        "DQ Blocking",
        "Control Plane Unsafe",
        "Provider Degraded",
        "Runtime Handoff",
        "Data Quality Handoff",
        "Control Plane Handoff",
        "Provider Handoff",
        "Workflow Handoff",
        "Silver Filter Reject Rate",
    }
    assert titles.isdisjoint(removed_or_merged_titles)


def test_overview_does_not_use_forensic_variables() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    variables = {
        var.get("name")
        for var in dashboard.get("templating", {}).get("list", [])
        if var.get("name")
    }
    serialized = json.dumps(dashboard)

    assert variables == {"pipeline", "run_type"}
    for forbidden in ("run_id", "payload_hash", "execution"):
        assert forbidden not in variables
        assert f"$${forbidden}" not in serialized
        assert f"${forbidden}" not in serialized


def test_overview_no_distribution_pie_panels() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = get_dashboard_panels(dashboard)
    titles = {panel.get("title") for panel in panels}
    pie_titles = {
        panel.get("title") for panel in panels if panel.get("type") == "piechart"
    }

    assert "Stage Distribution in Range" not in titles
    assert "Pipeline Distribution in Range" not in titles
    assert not pie_titles


def test_overview_summary_queries_use_range_semantics() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    count_panels = {
        "System Status",
        "Next Action",
        "Failed Runs in Range",
        "Recent Activity",
        "Runtime Status",
        "Data Quality Status",
        "Control Plane Status",
        "Provider Status",
        "Workflow Status",
        "DQ Hard Blockers",
        "Control-plane Blockers",
        "Global Provider Degradation",
        "Manifest / Ledger Failures",
        "Checkpoint Incompatibilities",
        "Lineage Refs Missing",
        "Silver Rejects Count + Rate",
    }

    for panel_title in count_panels:
        panel = panels.get(panel_title)
        assert panel is not None, f"Overview dashboard missing {panel_title!r}"
        expressions = [
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        assert expressions
        assert any("increase(" in expr and "[$__range]" in expr for expr in expressions)

    trend_panels = {
        "Processing Volume by Stage",
        "Pipeline Run Outcomes",
        "Stage Backlog Trend",
        "Stage Lag Trend",
    }
    for panel_title in trend_panels:
        panel = panels.get(panel_title)
        assert panel is not None, f"Overview dashboard missing {panel_title!r}"
        expressions = [
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        assert any("[$__interval]" in expr for expr in expressions)


def test_overview_links_are_target_scoped() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    links = {link.get("title"): link for link in dashboard.get("links", [])}

    assert links
    assert all(link.get("includeVars") is False for link in links.values())
    assert "includeVars=true" not in json.dumps(links)
    for title in ("2. Runtime", "Control Plane v1", "4. Data Quality"):
        url = str(links[title].get("url", ""))
        assert "var-pipeline=$pipeline" in url
        assert "var-run_type=$run_type" in url
        assert "${__url_time_range}" in url
    for title in ("3. Provider Health", "6. Workflow Overview"):
        url = str(links[title].get("url", ""))
        assert "var-pipeline=" not in url
        assert "var-run_type=" not in url
        assert "${__url_time_range}" in url


def test_overview_contains_runtime_dq_provider_control_workflow_status_cards() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    expected = {
        "Runtime Status": "/d/bioetl-runtime/bioetl-runtime",
        "Data Quality Status": "/d/bioetl-dq-v2",
        "Control Plane Status": "/d/bioetl-control-plane-v1/bioetl-control-plane-v1",
        "Provider Status": "/d/bioetl-provider-health-v2/bioetl-provider-health-v2",
        "Workflow Status": "/d/bioetl-workflow-overview/bioetl-workflow-overview",
    }
    for title, expected_url in expected.items():
        panel = panels.get(title)
        assert panel is not None, f"Overview dashboard missing {title!r}"
        links = panel.get("fieldConfig", {}).get("defaults", {}).get("links", [])
        assert any(expected_url in link.get("url", "") for link in links)


def test_overview_dashboard_exposes_workflow_overview_handoff() -> None:
    """Overview should expose workflow dashboard in shipped operator navigation."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    workflow_link = next(
        (
            link
            for link in dashboard.get("links", [])
            if str(link.get("url", "")).startswith(
                "/d/bioetl-workflow-overview/bioetl-workflow-overview"
            )
        ),
        None,
    )
    assert workflow_link is not None, (
        "Overview dashboard must expose a Workflow Overview handoff"
    )
    assert workflow_link.get("title") == "6. Workflow Overview"
    assert workflow_link.get("includeVars") is False, (
        "Workflow Overview handoff must not pass unrelated dashboard variables"
    )
    url = str(workflow_link.get("url", ""))
    assert "${__url_time_range}" in url, (
        "Workflow Overview handoff must preserve the active Grafana time range"
    )
    assert "var-pipeline=" not in url and "var-run_type=" not in url, (
        "Workflow Overview handoff must not leak pipeline/run_type into workflow scope"
    )


def test_overview_dashboard_surfaces_backlog_and_stage_lag_metrics() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    all_expressions = "\n".join(get_panel_expressions(dashboard))

    required_metrics = [
        "bioetl_records_processed_total",
        "bioetl_stage_backlog_records",
        "bioetl_stage_lag_seconds",
    ]
    missing = [metric for metric in required_metrics if metric not in all_expressions]
    assert not missing, f"Overview dashboard missing metrics: {missing}"


def test_overview_failed_runs_uses_run_metric_and_selected_time_range() -> None:
    """Overview failure indicator must use bounded failed-run events."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Failed Runs in Range"
        ),
        None,
    )
    assert panel is not None, "Panel 'Failed Runs in Range' not found"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any("bioetl_pipeline_runs_total" in expr for expr in expressions), (
        "Failed Runs in Range must use bioetl_pipeline_runs_total"
    )
    assert any('status="failed"' in expr for expr in expressions)
    assert any("[$__range]" in expr for expr in expressions), (
        "Failed Runs in Range must use the selected Grafana time range"
    )


def test_overview_processing_volume_panel_splits_units() -> None:
    """Processing-volume panel must stay record-only; backlog and lag must be separate."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }

    processing = panels.get("Processing Volume by Stage")
    assert processing is not None
    processing_expr = "\n".join(
        target.get("expr", "")
        for target in processing.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_records_processed_total" in processing_expr
    assert "bioetl_stage_backlog_records" not in processing_expr
    assert "bioetl_stage_lag_seconds" not in processing_expr

    worst_backlog = panels.get("Worst Backlog Stage")
    assert worst_backlog is not None
    worst_backlog_expr = "\n".join(
        target.get("expr", "")
        for target in worst_backlog.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_stage_backlog_records" in worst_backlog_expr
    assert "topk(1" in worst_backlog_expr
    assert "by (stage)" in worst_backlog_expr
    assert "[$__range]" in worst_backlog_expr

    backlog = panels.get("Stage Backlog Trend")
    assert backlog is not None
    backlog_expr = "\n".join(
        target.get("expr", "")
        for target in backlog.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_stage_backlog_records" in backlog_expr
    assert "[$__interval]" in backlog_expr

    worst_lag = panels.get("Worst Lag Stage")
    assert worst_lag is not None
    worst_lag_expr = "\n".join(
        target.get("expr", "")
        for target in worst_lag.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_stage_lag_seconds" in worst_lag_expr
    assert "topk(1" in worst_lag_expr
    assert "by (stage)" in worst_lag_expr
    assert "[$__range]" in worst_lag_expr

    lag = panels.get("Stage Lag Trend")
    assert lag is not None
    lag_expr = "\n".join(
        target.get("expr", "")
        for target in lag.get("targets", [])
        if isinstance(target.get("expr"), str)
    )
    assert "bioetl_stage_lag_seconds" in lag_expr
    assert "[$__interval]" in lag_expr
    assert lag.get("fieldConfig", {}).get("defaults", {}).get("unit") == "s"
