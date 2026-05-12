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
    assert "Select exactly one pipeline" in content
    assert "explorer-only" in content
    assert "default 24h forensic window" in content, (
        "Silver Reject Explorer scope note must include default forensic window banner"
    )

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
    assert panel.get("gridPos", {}).get("y", 999) <= 7
    content = str(panel.get("options", {}).get("content", ""))
    assert "First action:" in content
    assert "zero-reject workflow run is an intentional empty explorer state" in content
    assert "Zero matching rows" in content
    assert "unsupported filter chains" in content
    assert "bronze_records=0" in content
    assert "UNKNOWN" in content


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
    assert "zero-reject workflow run" in combined
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
    """DQ reject count panel should hand off directly; breakdown panels should guide the same handoff."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    for panel_title in ("Track: Silver Filter Rejects in Range",):
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


@pytest.mark.parametrize(
    "panel_title",
    [
        "Inspect: Top Silver Reject Reasons (Pareto)",
        "Inspect: Top Silver Reject Fields",
    ],
)
def test_dq_breakdown_panels_reference_top_level_explorer_handoff(
    panel_title: str,
) -> None:
    """Breakdown panels should direct operators to the top-level Explorer handoff."""
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
    assert "top-level" in description
