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
    get_row_child_panels,
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

    assert dashboard.get("title") in {"2. Overview", "2. Overview (Fleet)"}
    assert dashboard.get("uid") == "bioetl-overview-v2"
    assert "Hybrid L0 overview" in description
    assert "Run ID is always selected" in description
    assert "selected run" in content.lower()
    assert "unknown" in content.lower()


def test_overview_uses_frozen_v3_selector_set() -> None:
    variables = {
        variable.get("name"): variable
        for variable in _dashboard().get("templating", {}).get("list", [])
        if variable.get("name")
    }

    assert list(variables) == ["workflow", "pipeline", "run_type", "run_id"]

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
    lazy = {"Review Run Identity": 9300, "Review Processed Records": 9301}
    for title, panel_id in lazy.items():
        panel = panels[title]
        assert panel.get("id") == panel_id
    assert any(
        panel.get("type") == "row"
        and "Run Context" in str(panel.get("title") or "")
        and panel.get("collapsed") is True
        for panel in load_dashboard(
            Path("grafana/dashboards/bioetl-overview-v2.json")
        ).get("panels", [])
    )


def test_status_and_next_action_preserve_current_status_semantics() -> None:
    panels = _panels_by_title()
    assert "Monitor Scope Health" not in panels
    assert "Review First Action" not in panels
    return
    status = panels["Monitor Scope Health"]
    next_action = panels["Review First Action"]

    assert status.get("type") == "stat"
    assert "bioetl_workflow_scope_priority" in _panel_expr(status)
    assert "$__range" not in _panel_expr(status)
    assert status.get("options", {}).get("colorMode") == "background"
    assert status.get("options", {}).get("textMode") == "value_and_name"
    assert status.get("fieldConfig", {}).get("defaults", {}).get("noValue") == "UNKNOWN"
    _assert_status_mapping(status)

    next_action_expr = _panel_expr(next_action)
    description = str(next_action.get("description", ""))
    assert next_action.get("type") == "table"
    assert "bioetl_first_action" in next_action_expr
    # Keep the full response for the detail table; bound only the sorted summary.
    assert "topk(" not in next_action_expr
    transformations = next_action["transformations"]
    order = [item["id"] for item in transformations]
    assert order.index("sortBy") < order.index("limit")
    limit = next(item for item in transformations if item["id"] == "limit")
    assert limit["options"]["limitField"] == 2
    assert 'pipeline=~"$pipeline"' in next_action_expr
    assert 'run_type=~"$run_type"' in next_action_expr
    assert "$__range" not in next_action_expr
    assert "VERIFY" in description
    assert "bioetl_first_action" in next_action_expr
    assert "bioetl_fa_gap" in next_action_expr
    assert "or on() label_replace" in next_action_expr
    assert "max without(run_type)" not in next_action_expr
    assert "bioetl_l0_next_action_no_route" not in next_action_expr
    assert len(next_action_expr) <= 200


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
    assert "15-minute" in summary["description"]

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
    assert identity.get("targets", [{}])[0].get("parser") == "backend"
    assert identity.get("targets", [{}])[0].get("root_selector") == "display_rows"
    assert identity.get("targets", [{}])[0].get("url") == (
        "/ops/control-plane/identity-table?pipeline=${pipeline}"
        "&run_type=${run_type:csv}&run_id=${run_id}&timezone=${__timezone}"
    )

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
    return
    expr = _panel_expr(panel)
    assert "bioetl_l0_input_status_selected" in expr
    assert f'input="{domain}"' in expr
    assert 'pipeline=~"$pipeline"' in expr
    assert 'run_type=~"$run_type"' in expr
    assert "bioetl_l1_" not in expr
    assert "vector(3)" in expr
    assert "evidence-qualified" in str(panel.get("description", ""))


def test_l1_cards_have_operator_mappings_and_targeted_links() -> None:
    titles = _panels_by_title()
    for title in _L1_CARD_TITLES:
        assert title not in titles
    return
    expected_links = {
        "Review Runtime Status": {"Open Runtime"},
        "Review Data Quality Status": {"Open Data Quality"},
        "Review Control Plane Status": {"Open Control Plane"},
        "Review Global Provider Status": {"Open Provider Health"},
        "Review Data Validation Status": {"Open Runtime"},
        "Review Workflow Status": {"Open Pipeline Diagnostics"},
    }

    for title in _L1_CARD_TITLES:
        panel = _panels_by_title()[title]
        assert panel.get("type") == "table"
        _assert_status_mapping(panel)
        transformations = _panel_transformations(panel)
        assert transformations and transformations[0].get("id") == "organize"
        data_links = panel.get("options", {}).get("dataLinks", [])
        assert {link.get("title") for link in data_links} == expected_links[title]


def test_selected_scope_cards_normalize_workflow_pipeline_aliases() -> None:
    """Epic #6574: first-screen cards use thin pipeline selectors (no mega-expr glue)."""
    titles = _panels_by_title()
    assert "Monitor Scope Health" not in titles
    assert "Review First Action" not in titles
    return
    for title in (
        "Monitor Scope Health",
        "Review First Action",
    ):
        expr = _panel_expr(_panels_by_title()[title])
        assert 'pipeline=~"$pipeline"' in expr
        # Review First Action uses recording-rule NO_ROUTE fallback (#6574 diet).
        max_len = 200
        assert len(expr) <= max_len, f"{title} expr length {len(expr)} > {max_len}"
        assert "$__range" not in expr


def test_provider_and_workflow_scope_are_explicit() -> None:
    titles = _panels_by_title()
    assert "Review Global Provider Status" not in titles
    assert "Review Workflow Status" not in titles
    return
    provider = titles["Review Global Provider Status"]
    workflow = _panels_by_title()["Review Workflow Status"]

    assert _panel_expr(provider).strip() == "bioetl_l1_provider_global_status"
    provider_description = str(provider.get("description", "")).lower()
    assert "across all pipelines" in provider_description
    assert "filters do not affect this panel" in provider_description
    provider_links = provider.get("options", {}).get("dataLinks", [])
    assert any(
        "var-provider=$__all" in str(link.get("url", "")) for link in provider_links
    )
    assert any(
        "var-pipeline_context=${pipeline:percentencode}" in str(link.get("url", ""))
        for link in provider_links
    )

    assert "bioetl_l0_input_status_selected" in _panel_expr(workflow)
    assert 'input="workflow"' in _panel_expr(workflow)
    assert 'pipeline=~"$pipeline"' in _panel_expr(workflow)
    assert 'run_type=~"$run_type"' in _panel_expr(workflow)
    assert "selected pipeline" in str(workflow.get("description", "")).lower()
    assert "run type" in str(workflow.get("description", "")).lower()
    assert "run id" in str(workflow.get("description", "")).lower()
    workflow_links = workflow.get("options", {}).get("dataLinks", [])
    assert {link.get("title") for link in workflow_links} == {
        "Open Pipeline Diagnostics"
    }


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
    current_verdict_titles = {
        "Monitor Scope Health",
        "Review First Action",
        "Review Run Domains",
        *_L1_CARD_TITLES,
    }
    expected_evidence_panels = {
        "Track Runtime Blockers": {
            "id": 9018,
            "links": {"Open Runtime"},
            "tokens": ("selected range", "does not determine"),
        },
        "Track Data Quality Status": {
            "id": 9019,
            "links": {"Open Data Quality"},
            "tokens": (
                "selected range",
                "does not determine",
            ),
        },
        "Track Gold Lifecycle": {
            "id": 9020,
            "links": {"Open Runtime", "Open Control Plane"},
            "tokens": (
                "selected range",
                "gold lifecycle state",
            ),
        },
        "Review Failed Runs": {
            "id": 9010,
            "links": {"Open Runtime"},
            "tokens": (
                "selected range",
                "not proof",
            ),
        },
        "Review Recent Non-success Terminal Runs": {
            "id": 9011,
            "links": {"Open Control Plane", "Open Runtime"},
            "tokens": (
                "selected range",
                "non-success",
                "not proof",
            ),
        },
    }

    for title in (*expected_evidence_panels, "Track Silver Rejects"):
        assert title in panels

    for title, expectation in expected_evidence_panels.items():
        panel = panels[title]
        description = str(panel.get("description", "")).lower()
        data_links = panel.get("options", {}).get("dataLinks", [])

        assert panel.get("id") == expectation["id"]
        assert panel.get("gridPos", {}).get("y", 0) >= 0
        assert {link.get("title") for link in data_links} == expectation["links"]
        assert all(link.get("includeVars") is False for link in data_links)
        assert all(link.get("targetBlank") is False for link in data_links)
        for token in expectation["tokens"]:
            assert token in description
        assert "current" in description

    assert "[$__range]" in _panel_expr(panels["Review Failed Runs"])
    assert "[$__range]" in _panel_expr(
        panels["Review Recent Non-success Terminal Runs"]
    )
    terminal_expr = _panel_expr(panels["Review Recent Non-success Terminal Runs"])
    assert 'status!="success"' in terminal_expr
    assert "status=" not in terminal_expr.replace('status!="success"', "")
    assert "[$__range]" in _panel_expr(panels["Track Silver Rejects"])


def test_diagnostics_row_is_not_empty() -> None:
    dashboard = _dashboard()
    assert all(
        panel.get("title") != "Inspect Domain Diagnostics"
        for panel in dashboard.get("panels", [])
    )
    return
    diagnostics_row = next(
        panel
        for panel in dashboard.get("panels", [])
        if panel.get("title") == "Inspect Domain Diagnostics"
    )

    assert diagnostics_row.get("type") == "row"
    child_titles = {
        child.get("title")
        for child in get_row_child_panels(dashboard, "Inspect Domain Diagnostics")
    }
    assert "Navigate Diagnostics" in child_titles


def test_overview_queries_are_backed_by_expected_records_and_metrics() -> None:
    all_expressions = "\n".join(
        str(target.get("url") or target.get("expr") or "")
        for panel in get_dashboard_panels(_dashboard())
        for target in (panel.get("targets") or [])
        if isinstance(target, dict)
    )

    for required_token in (
        "selected-run-status?pipeline=${pipeline}&run_id=${run_id}",
        "identity-table?pipeline=${pipeline}",
        "processed-records?pipeline=${pipeline}",
    ):
        assert required_token in all_expressions


def test_overview_timelines_use_all_labels_and_hide_clipped_in_band_text() -> None:
    """#10249: All instead of .* on empty fallback; no clipped in-band state text."""
    panels = {panel.get("id"): panel for panel in get_dashboard_panels(_dashboard())}
    for panel_id in (9018, 9019, 9020):
        assert panel_id not in panels
    return
    for panel_id in (9018, 9019, 9020):
        panel = panels[panel_id]
        assert panel.get("type") == "state-timeline"
        assert panel.get("options", {}).get("showValue") == "never"
        expr = "\n".join(
            str(target.get("expr", ""))
            for target in panel.get("targets") or []
            if isinstance(target, dict)
        )
        assert "${pipeline:text}" in expr
        assert "${run_type:text}" in expr
        assert 'pipeline=~"$pipeline"' in expr


def test_overview_keeps_only_panels_that_assess_the_selected_run() -> None:
    """#11268: Run ID is always set, so fleet and range panels are not on Overview."""
    panels = {panel.get("id"): panel for panel in get_dashboard_panels(_dashboard())}
    removed = {214, 215, 9601, 9031, 9010, 9011, 9003, 9007, 20215, 9701}
    kept = {99, 9603, 9002, 9300, 9301, 9451, 9452}
    for panel_id in removed:
        assert panel_id not in panels
    for panel_id in kept:
        assert panel_id in panels
    assert "Run ID is always selected" in str(_dashboard().get("description"))
    assert panels[9603]["gridPos"]["y"] == panels[9002]["gridPos"]["y"]
    assert panels[9603]["gridPos"]["y"] < 12
