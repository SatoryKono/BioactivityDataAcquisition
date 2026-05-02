"""Focused Grafana contract checks for Silver reject summary surfaces."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
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
            if item.get("title") == "Silver Filter Reject Accounting Mismatch"
        ),
        None,
    )
    assert panel is not None, (
        "Panel 'Silver Filter Reject Accounting Mismatch' not found"
    )

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert expressions, (
        "Panel 'Silver Filter Reject Accounting Mismatch' must define a query target"
    )
    assert any(
        "bioetl_silver_filter_reject_total_mismatch_15m" in expr for expr in expressions
    ), (
        "Silver Filter Reject Accounting Mismatch must use the shipped "
        "bioetl_silver_filter_reject_total_mismatch_15m recording rule"
    )
    assert any("[$__range]" in expr for expr in expressions), (
        "Silver Filter Reject Accounting Mismatch must respect the selected "
        "Grafana time range"
    )


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-overview-v2.json", "Silver Filter Rejects"),
        ("bioetl-dq-v2.json", "Silver Filter Rejects"),
        ("bioetl-dq-v2.json", "Silver Filter Rejects by Pipeline"),
        ("bioetl-runtime.json", "Silver Filter Rejects"),
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


def test_silver_filter_reject_rate_uses_selected_time_range() -> None:
    """Silver filter reject rate must follow the active dashboard time range."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Silver Filter Reject Rate"
        ),
        None,
    )
    assert panel is not None, "Panel 'Silver Filter Reject Rate' not found"

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert any("[$__range]" in expr for expr in expressions), (
        "Silver Filter Reject Rate must use the selected Grafana time range"
    )


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
            if panel.get("title") == "Scope"
        ),
        None,
    )
    assert note_panel is not None, "Silver Reject Explorer must define Scope note"
    content = note_panel.get("options", {}).get("content", "")
    assert "Select exactly one pipeline" in content
    assert "explorer-only" in content

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
        ("Top Silver Reject Reasons", "reason_code"),
        ("Top Silver Reject Fields", "field"),
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
        ("bioetl-overview-v2.json", "Silver Filter Rejects"),
        ("bioetl-dq-v2.json", "Silver Filter Rejects"),
        ("bioetl-runtime.json", "Silver Filter Rejects"),
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
            if item.get("title") == "Filtered Records Table"
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
    url = str(payload_link.get("url", ""))
    assert "${__url_time_range}" in url or ("${__from}" in url and "${__to}" in url), (
        "Payload drilldown link must preserve forensic time scope"
    )
    description = str(panel.get("description", ""))
    assert "latest 100" in description.lower()


def test_dq_reject_breakdown_panels_link_to_silver_reject_explorer() -> None:
    """DQ reject breakdown panels should hand off to Silver Reject Explorer."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    for panel_title in ("Top Silver Reject Reasons", "Top Silver Reject Fields"):
        panel = next(
            (
                item
                for item in get_dashboard_panels(dashboard)
                if item.get("title") == panel_title
            ),
            None,
        )
        assert panel is not None
        links = panel.get("options", {}).get("dataLinks", [])
        explorer_link = next(
            (
                link
                for link in links
                if "/d/bioetl-silver-reject-explorer/bioetl-silver-reject-explorer"
                in str(link.get("url", ""))
            ),
            None,
        )
        assert explorer_link is not None, (
            f"{panel_title!r} must expose Explorer handoff"
        )
        assert "${__url_time_range}" in str(explorer_link.get("url", ""))
