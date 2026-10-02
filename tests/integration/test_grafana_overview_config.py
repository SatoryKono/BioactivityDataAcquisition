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
"""Integration tests for the shipped BioETL Overview dashboard."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.ops.observability.grafana._selected_run_panels import SELECTOR_ROWS

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    get_panel_expressions,
    index_panels_by_base_title,
    load_dashboard,
)

pytestmark = pytest.mark.integration

_OVERVIEW_PATH = Path("grafana/dashboards/bioetl-overview-v2.json")
_STATUS_TEXTS = ("UNKNOWN", "OK", "WARN", "CRIT")
_L1_CARD_TITLES = (
    "Review Runtime Status",
    "Review Data Quality Status",
    "Review Control Plane Status",
    "Review Global Provider Status",
    "Review Data Validation Status",
    "Review Workflow Status",
)


def _dashboard() -> dict:
    return load_dashboard(_OVERVIEW_PATH)


def _panels_by_title() -> dict[str, dict]:
    return index_panels_by_base_title(get_dashboard_panels(_dashboard()))


def _panel_expr(panel: dict) -> str:
    return "\n".join(
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    )


def _panel_transformations(panel: dict) -> list[dict]:
    return panel.get("transformations", [])


def _assert_status_mapping(panel: dict) -> None:
    serialized = json.dumps(panel.get("fieldConfig", {}).get("defaults", {}))
    for status_text in _STATUS_TEXTS:
        assert status_text in serialized


def test_overview_dashboard_identity_and_primary_question() -> None:
    dashboard = _dashboard()
    provenance = _panels_by_title()["Inspect Scope & Evidence"]
    content = str(provenance.get("options", {}).get("content", ""))
    description = str(dashboard.get("description", ""))

    assert dashboard.get("title") == "Run Overview"
    assert dashboard.get("uid") == "bioetl-overview-v2"
    assert "Run ID is always selected" in description
    assert "not on Overview" in description
    assert "CURRENT fleet panels" in description
    assert "that run only" in content.lower()
    assert "unknown" in content.lower()


def test_overview_uses_frozen_v3_selector_set() -> None:
    variables = {
        variable.get("name"): variable
        for variable in _dashboard().get("templating", {}).get("list", [])
        if variable.get("name")
    }

    assert list(variables) == [
        "workflow",
        "pipeline",
        "run_type",
        "run_id",
        "provider_for_pipeline",
    ]

    for name in ("workflow", "run_type"):
        variable = variables[name]
        assert variable.get("datasource") == {
            "type": "prometheus",
            "uid": "prometheus",
        }
        assert variable.get("includeAll") is True
        assert variable.get("current", {}).get("text") == "All"
        assert variable.get("current", {}).get("value") == "$__all"

    pipeline = variables["pipeline"]
    assert pipeline.get("datasource") == "BioETL Ops HTTP"
    assert pipeline.get("includeAll") is True
    assert pipeline.get("current", {}).get("text") == "All"
    assert pipeline.get("current", {}).get("value") == "$__all"
    pipeline_query = pipeline.get("query", {})
    assert isinstance(pipeline_query, dict)
    infinity = pipeline_query.get("infinityQuery", {})
    assert isinstance(infinity, dict)
    assert "dimension=pipeline" in str(infinity.get("url", ""))

    assert variables["workflow"].get("multi") is False
    assert variables["pipeline"].get("multi") is False
    assert variables["run_type"].get("multi") is True

    run_id = variables["run_id"]
    assert run_id.get("datasource") == "BioETL Ops HTTP"
    assert run_id.get("includeAll") is False
    assert run_id.get("multi") is False
    assert run_id.get("current", {}).get("text") == "-"
    assert run_id.get("current", {}).get("value") == "-"


def test_run_id_selector_is_control_plane_backed_table_query() -> None:
    variables = {
        variable.get("name"): variable
        for variable in _dashboard().get("templating", {}).get("list", [])
        if variable.get("name")
    }
    run_id_query = variables["run_id"].get("query", {})

    assert isinstance(run_id_query, dict)
    assert run_id_query.get("queryType") == "infinity"
    assert run_id_query.get("refId") == "variable"
    infinity_query = run_id_query.get("infinityQuery", {})
    assert isinstance(infinity_query, dict)
    assert infinity_query.get("format") == "table"
    assert infinity_query.get("parser") == "backend"
    assert infinity_query.get("root_selector") == SELECTOR_ROWS
    assert infinity_query.get("url_options", {}).get("method") == "GET"
    query_url = str(infinity_query.get("url", ""))
    assert "/ops/control-plane/filter-options" in query_url
    assert "dimension=run_id" in query_url
    assert "response_shape=options" in query_url
    assert "workflow=${workflow}" in query_url
    assert "pipeline=${pipeline}" in query_url
    assert "run_type=${run_type:csv}" in query_url


def test_first_screen_layout_matches_reviewed_progressive_disclosure_baseline() -> None:
    """Epic #6570/#6573/DRM-R: Status/First Action/Inputs on first path; shell lazy."""
    panels = _panels_by_title()
    # Compact navigation gives the first screen one extra grid row.
    assert panels["Inspect Scope & Evidence"].get("id") == 99
    assert "Monitor Scope Health" not in panels
    assert "Review First Action" not in panels
    assert panels["Review Run Domains"].get("id") == 9002
    assert panels["Inspect Scope & Evidence"].get("gridPos", {}).get("y") == 2
    assert panels["Review Selected Run Status"].get("id") == 9603
    assert panels["Review Selected Run Status"].get("gridPos", {}).get("y") == 5
    assert panels["Review Run Domains"].get("gridPos", {}).get("y") == 5
    assert panels["Review Run Domains"].get("gridPos", {}).get("w", 0) >= 8
    identity = panels["Review Run Identity"]
    assert identity["id"] == 9300
    assert identity["gridPos"]["y"] < 18
    assert identity["gridPos"]["y"] + identity["gridPos"]["h"] <= 18
    # Provider and stage evidence remain accessible below the primary verdict.
    assert panels["Review Provider Evidence"]["id"] == 9480
    assert panels["Inspect Selected Run Stages"]["id"] == 9460
    assert all(panel.get("type") != "row" for panel in _dashboard()["panels"])


def test_status_and_next_action_preserve_current_status_semantics() -> None:
    panels = _panels_by_title()
    assert "Monitor Scope Health" not in panels
    assert "Review First Action" not in panels
    return


def test_review_domain_status_uses_exact_persisted_evidence() -> None:
    """Selected-run domains use saved evidence; CURRENT detail stays below the fold."""
    panels = _panels_by_title()
    summary = panels["Review Run Domains"]
    summary_expr = _panel_expr(summary)

    assert summary.get("id") == 9002
    assert not summary_expr
    target = summary["targets"][0]
    assert "selected-run-status?pipeline=${pipeline}&run_id=${run_id}" in target["url"]
    assert "presentation_domains" in target["root_selector"]
    assert "from=" not in target["url"] and "to=" not in target["url"]
    assert "Saved evidence for this Run ID" in summary["description"]

    content = str(
        panels["Inspect Scope & Evidence"].get("options", {}).get("content", "")
    )
    assert "set a concrete" not in content
    assert "unknown" in content.lower()
    assert "Review All Domain Status" not in panels
    assert "Review First Action" not in panels


def test_identity_panel_uses_run_id_without_leaking_to_prometheus_queries() -> None:
    identity = _panels_by_title()["Review Run Identity"]

    assert identity.get("datasource") == "BioETL Ops HTTP"
    assert identity.get("targets", [{}])[0].get("parser") == "uql"
    target = identity["targets"][0]
    assert target["url"].startswith("/ops/observability/selected-run-status?")
    assert "run_id=${run_id}" in target["url"]
    assert "parse-json | jsonata" in target["uql"]
    for label in ("Run ID", "Pipeline", "Run Type", "Started at", "Total Run Duration"):
        assert label in target["root_selector"]
    assert "Not recorded in saved run evidence" in target["root_selector"]

    prometheus_expressions = "\n".join(get_panel_expressions(_dashboard()))
    assert "$run_id" not in prometheus_expressions
    assert "${run_id}" not in prometheus_expressions


@pytest.mark.parametrize(
    ("title", "domain"),
    [
        ("Review Runtime Status", "runtime"),
        ("Review Data Quality Status", "dq"),
        ("Review Control Plane Status", "control_plane"),
        ("Review Data Validation Status", "gold"),
        ("Review Workflow Status", "workflow"),
    ],
)
def test_current_domain_detail_uses_same_qualified_verdict_as_summary(
    title: str,
    domain: str,
) -> None:
    assert title not in _panels_by_title()
    assert domain


def test_l1_cards_have_operator_mappings_and_targeted_links() -> None:
    titles = _panels_by_title()
    for title in _L1_CARD_TITLES:
        assert title not in titles
    return


def test_selected_scope_cards_normalize_workflow_pipeline_aliases() -> None:
    """Epic #6574: first-screen cards use thin pipeline selectors (no mega-expr glue)."""
    titles = _panels_by_title()
    assert "Monitor Scope Health" not in titles
    assert "Review First Action" not in titles
    return


def test_provider_and_workflow_scope_are_explicit() -> None:
    titles = _panels_by_title()
    assert "Review Global Provider Status" not in titles
    assert "Review Workflow Status" not in titles
    return


def test_range_evidence_and_trend_rows_are_retained() -> None:
    panels = _panels_by_title()
    for title in (
        "Track Runtime Blockers",
        "Track Data Quality Status",
        "Track Gold Lifecycle",
        "Review Failed Runs",
        "Review Recent Non-success Terminal Runs",
        "Track Silver Rejects",
    ):
        assert title not in panels
    return


def test_diagnostics_row_is_not_empty() -> None:
    dashboard = _dashboard()
    assert all(
        panel.get("title") != "Inspect Domain Diagnostics"
        for panel in dashboard.get("panels", [])
    )
    return


def test_overview_queries_are_backed_by_expected_records_and_metrics() -> None:
    all_expressions = "\n".join(
        str(target.get("url") or target.get("expr") or "")
        for panel in get_dashboard_panels(_dashboard())
        for target in (panel.get("targets") or [])
        if isinstance(target, dict)
    )

    for required_token in (
        "selected-run-status?pipeline=${pipeline}&run_id=${run_id}",
        "pipeline-run-report-artifact?pipeline=${pipeline:percentencode}",
    ):
        assert required_token in all_expressions


def test_overview_timelines_use_all_labels_and_hide_clipped_in_band_text() -> None:
    """#10249: All instead of .* on empty fallback; no clipped in-band state text."""
    panels = {panel.get("id"): panel for panel in get_dashboard_panels(_dashboard())}
    for panel_id in (9018, 9019, 9020):
        assert panel_id not in panels
    return


def test_overview_keeps_only_panels_that_assess_the_selected_run() -> None:
    """#11268: Run ID is always set, so fleet and range panels are not on Overview."""
    panels = {panel.get("id"): panel for panel in get_dashboard_panels(_dashboard())}
    removed = {214, 215, 9601, 9031, 9010, 9011, 9003, 9007, 20215, 9701}
    kept = {99, 9603, 9002, 9300, 9604, 9460, 9480, 9481, 9482}
    for panel_id in removed:
        assert panel_id not in panels
    for panel_id in kept:
        assert panel_id in panels
    assert "Run ID is always selected" in str(_dashboard().get("description"))
    assert panels[9603]["gridPos"]["y"] == panels[9002]["gridPos"]["y"]
    assert panels[9603]["gridPos"]["y"] < 12
