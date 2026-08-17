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

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    get_panel_expressions,
    get_row_child_panels,
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
    return {
        str(panel.get("title")): panel
        for panel in get_dashboard_panels(_dashboard())
        if panel.get("title")
    }


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

    assert dashboard.get("title") in {"1. Overview", "1. Overview (Fleet)"}
    assert dashboard.get("uid") == "bioetl-overview-v2"
    assert "Hybrid L0 overview" in description
    assert "what is broken or degraded right now" in content.lower()
    assert "status + first action" in content.lower()


def test_overview_uses_frozen_v3_selector_set() -> None:
    variables = {
        variable.get("name"): variable
        for variable in _dashboard().get("templating", {}).get("list", [])
        if variable.get("name")
    }

    assert list(variables) == ["workflow", "pipeline", "run_type", "run_id"]

    for name in ("workflow", "pipeline", "run_type"):
        variable = variables[name]
        assert variable.get("datasource") == {
            "type": "prometheus",
            "uid": "prometheus",
        }
        assert variable.get("includeAll") is True
        assert variable.get("current", {}).get("text") == "All"
        assert variable.get("current", {}).get("value") == "$__all"

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
    assert infinity_query.get("root_selector") == "$.items"
    assert infinity_query.get("url_options", {}).get("method") == "GET"
    query_url = str(infinity_query.get("url", ""))
    assert "/ops/control-plane/filter-options" in query_url
    assert "dimension=run_id" in query_url
    assert "response_shape=list" in query_url
    assert "workflow=${workflow}" in query_url
    assert "pipeline=${pipeline}" in query_url
    assert "run_type=${run_type:csv}" in query_url


def test_first_screen_layout_matches_reviewed_progressive_disclosure_baseline() -> None:
    """Epic #6570/#6573/DRM-R: Status/First Action/Inputs on first path; shell lazy."""
    panels = _panels_by_title()
    # Stable panel IDs; coordinates are contractual bands (not frozen DUX pixels).
    assert panels["Inspect Scope & Evidence"].get("id") == 99
    assert panels["Monitor Fleet Health"].get("id") == 214
    assert panels["Review First Action"].get("id") == 215
    assert panels["Review Domain Status"].get("id") == 9002
    assert panels["Inspect Scope & Evidence"].get("gridPos", {}).get("y") == 4
    assert panels["Monitor Fleet Health"].get("gridPos", {}).get("y") == 4
    assert panels["Review First Action"].get("gridPos", {}).get("y") <= 8
    assert panels["Review Domain Status"].get("gridPos", {}).get("y") == panels[
        "Review First Action"
    ].get("gridPos", {}).get("y")
    # RFA Phase 1: equal first-screen split so Action column is not squeezed.
    assert panels["Review First Action"].get("gridPos", {}).get("w", 0) >= 12
    assert panels["Review Domain Status"].get("gridPos", {}).get("w", 0) >= 12
    assert panels["Review Domain Status"].get("gridPos", {}).get("x") == panels[
        "Review First Action"
    ].get("gridPos", {}).get("x", 0) + panels["Review First Action"].get(
        "gridPos", {}
    ).get("w", 0)
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
    status = panels["Monitor Fleet Health"]
    next_action = panels["Review First Action"]

    assert status.get("type") == "stat"
    assert "bioetl_l0_status" in _panel_expr(status)
    assert "$__range" not in _panel_expr(status)
    assert status.get("options", {}).get("colorMode") == "background"
    assert status.get("options", {}).get("textMode") == "value"
    assert status.get("fieldConfig", {}).get("defaults", {}).get("noValue") == "UNKNOWN"
    _assert_status_mapping(status)

    next_action_expr = _panel_expr(next_action)
    description = str(next_action.get("description", ""))
    assert next_action.get("type") == "table"
    assert "bioetl_l0_next_action_route" in next_action_expr
    # RFA-00: up to four urgency-ordered routes; single-pipeline still ranks via topk.
    assert "topk(4" in next_action_expr
    assert 'pipeline=~"$pipeline"' in next_action_expr
    assert 'run_type=~"$run_type"' in next_action_expr
    assert "$__range" not in next_action_expr
    assert "NO_ROUTE" in description or "no_route" in next_action_expr
    # #6574: compact recording-rule fallback (preferred) or legacy label_replace.
    assert (
        "bioetl_l0_next_action_no_route" in next_action_expr
        or "selected_scope_not_present" in next_action_expr
    )
    # #8748: no_route only when the selected scope has no route series.
    assert "absent(" in next_action_expr
    assert "or bioetl_l0_next_action_no_route)" not in next_action_expr
    assert len(next_action_expr) <= 200


def test_review_domain_status_is_deviation_first_and_capped() -> None:
    """#8898: first-window domain matrix is top-four; full matrix stays below fold."""
    panels = _panels_by_title()
    summary = panels["Review Domain Status"]
    full_matrix = panels["Review All Domain Status"]
    summary_expr = _panel_expr(summary)
    full_expr = _panel_expr(full_matrix)

    assert summary.get("id") == 9002
    assert "topk(4" in summary_expr
    assert "bioetl_l0_input_status_selected" in summary_expr
    assert len(summary_expr) <= 200
    assert "four worst" in str(summary.get("description", "")).lower()

    assert full_matrix.get("id") == 9031
    assert "topk(" not in full_expr
    assert "max by (input)" in full_expr
    assert "bioetl_l0_input_status_selected" in full_expr
    content = str(panels["Inspect Scope & Evidence"].get("options", {}).get("content", ""))
    assert "set a concrete" not in content
    assert "What is broken or degraded right now?" in content

    # Phase 2: Priority is a short color-background badge; Action is sole color-text CTA.
    overrides = next_action.get("fieldConfig", {}).get("overrides", [])
    value_override = next(
        (
            item
            for item in overrides
            if item.get("matcher", {}).get("options") in {"Value", "Priority"}
        ),
        None,
    )
    assert value_override is not None
    value_props = {
        prop.get("id"): prop.get("value")
        for prop in value_override.get("properties", [])
    }
    priority_cell = value_props.get("custom.cellOptions", {})
    assert priority_cell.get("type") == "color-background"
    assert priority_cell.get("applyToRow") is not True, (
        "Priority badge must not paint the whole row (verdict-ontology anti-pattern)"
    )

    # Short Priority badges (RUNTIME/CP/DQ/…) live on field defaults mappings.
    priority_maps = {}
    for mapping in (
        next_action.get("fieldConfig", {}).get("defaults", {}).get("mappings") or []
    ):
        if mapping.get("type") == "value":
            priority_maps.update(mapping.get("options") or {})
    for score, badge in {
        "0": "NR",
        "5": "MON",
        "10": "WF",
        "20": "PROV",
        "30": "DQ",
        "35": "GOLD",
        "40": "CP",
        "50": "RUNTIME",
    }.items():
        assert score in priority_maps, f"missing Priority map for score {score}"
        assert priority_maps[score].get("text") == badge
        assert len(str(priority_maps[score].get("text") or "")) <= 8

    action_override = next(
        (
            item
            for item in overrides
            if item.get("matcher", {}).get("options") == "action_target"
        ),
        None,
    )
    assert action_override is not None
    action_props = {
        prop.get("id"): prop.get("value")
        for prop in action_override.get("properties", [])
    }
    assert action_props.get("custom.cellOptions", {}).get("type") == "color-text"
    assert next_action.get("options", {}).get("cellHeight") == "sm"
    assert int(action_props.get("custom.width") or 0) >= 180, (
        "Action column must be wide enough to avoid truncation at default density"
    )
    # Short operator labels (panel dataLinks keep full Open* CTA titles).
    action_maps = {}
    for mapping in action_props.get("mappings") or []:
        if mapping.get("type") == "value":
            action_maps.update(mapping.get("options") or {})
    for key, text in {
        "runtime": "Runtime",
        "control_plane": "Control Plane",
        "dq": "DQ",
        "provider": "Provider",
        "monitor": "Monitor",
        "no_route": "No route",
        "workflow": "Runtime (wf)",
    }.items():
        assert key in action_maps, f"missing Action map for {key}"
        assert action_maps[key].get("text") == text
        assert len(str(action_maps[key].get("text") or "")) <= 16
    links = action_props.get("links") or []
    assert links, "Action column must expose row-aware board links"
    assert any(
        "bioetl-runtime" in str(link.get("url", ""))
        and "${__data.fields.pipeline}" in str(link.get("url", ""))
        for link in links
    ), "Action links must pass the row pipeline into target dashboards"
    assert any("var-provider=unknown" in str(link.get("url", "")) for link in links), (
        "Provider Action link must fail-close provider=unknown"
    )

    organize = next(
        (
            transform
            for transform in next_action.get("transformations", [])
            if transform.get("id") == "organize"
        ),
        None,
    )
    assert organize is not None
    exclude = organize.get("options", {}).get("excludeByName", {})
    # Keep action_dashboard_uid for field links; hide via field override instead.
    assert exclude.get("action_dashboard_uid") is not True
    hidden_route_override = next(
        (
            item
            for item in overrides
            if item.get("matcher", {}).get("options") == "action_dashboard_uid"
        ),
        None,
    )
    assert hidden_route_override is not None
    hidden_route_properties = {
        property_.get("id"): property_.get("value")
        for property_ in hidden_route_override.get("properties", [])
    }
    assert hidden_route_properties.get("custom.hidden") is True
    assert exclude.get("Value") is not True
    # Action-first hierarchy: Action → Priority → Why → Pipeline.
    index_by_name = organize.get("options", {}).get("indexByName", {})
    assert index_by_name.get("action_target") == 0
    assert index_by_name.get("Value") == 1
    assert index_by_name.get("action_reason") == 2
    assert index_by_name.get("pipeline") == 3


def test_identity_panel_uses_run_id_without_leaking_to_prometheus_queries() -> None:
    identity = _panels_by_title()["Review Run Identity"]

    assert identity.get("datasource") == "BioETL Ops HTTP"
    assert identity.get("targets", [{}])[0].get("parser") == "backend"
    assert identity.get("targets", [{}])[0].get("root_selector") == "rows"
    assert identity.get("targets", [{}])[0].get("url") == (
        "/ops/control-plane/identity-table?pipeline=${pipeline}"
        "&run_type=${run_type:csv}&run_id=${run_id}"
    )

    prometheus_expressions = "\n".join(get_panel_expressions(_dashboard()))
    assert "$run_id" not in prometheus_expressions
    assert "${run_id}" not in prometheus_expressions


def test_l1_cards_have_operator_mappings_and_targeted_links() -> None:
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
    for title in (
        "Monitor Fleet Health",
        "Review First Action",
        "Review Domain Status",
    ):
        expr = _panel_expr(_panels_by_title()[title])
        assert 'pipeline=~"$pipeline"' in expr
        # Review First Action uses recording-rule NO_ROUTE fallback (#6574 diet).
        max_len = 200
        assert len(expr) <= max_len, f"{title} expr length {len(expr)} > {max_len}"
        assert "$__range" not in expr


def test_provider_and_workflow_scope_are_explicit() -> None:
    provider = _panels_by_title()["Review Global Provider Status"]
    workflow = _panels_by_title()["Review Workflow Status"]

    assert _panel_expr(provider).strip() == "bioetl_l1_provider_global_status"
    provider_description = str(provider.get("description", "")).lower()
    assert "across all pipelines" in provider_description
    assert "filters do not affect this panel" in provider_description
    provider_links = provider.get("options", {}).get("dataLinks", [])
    assert any(
        "var-provider=unknown" in str(link.get("url", "")) for link in provider_links
    )
    assert any(
        "var-pipeline_context=$pipeline" in str(link.get("url", ""))
        for link in provider_links
    )

    assert "bioetl_l1_workflow_global_status" in _panel_expr(workflow)
    assert 'pipeline!="test_pipe"' in _panel_expr(workflow)
    assert 'pipeline=~"$pipeline"' in _panel_expr(workflow)
    assert 'label_replace(label_replace(vector(1), "pipeline_raw", "$pipeline"' in (
        _panel_expr(workflow)
    )
    assert (
        "selected workflow and pipeline" in str(workflow.get("description", "")).lower()
    )
    assert "run type" in str(workflow.get("description", "")).lower()
    assert "run id" in str(workflow.get("description", "")).lower()
    workflow_links = workflow.get("options", {}).get("dataLinks", [])
    assert {link.get("title") for link in workflow_links} == {
        "Open Pipeline Diagnostics"
    }


def test_range_evidence_and_trend_rows_are_retained() -> None:
    panels = _panels_by_title()
    current_verdict_titles = {
        "Monitor Fleet Health",
        "Review First Action",
        "Review Domain Status",
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
        "Review Recent Terminal Runs": {
            "id": 9011,
            "links": {"Open Control Plane", "Open Runtime"},
            "tokens": (
                "selected range",
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
    assert "[$__range]" in _panel_expr(panels["Review Recent Terminal Runs"])
    assert "[$__range]" in _panel_expr(panels["Track Silver Rejects"])


def test_diagnostics_row_is_not_empty() -> None:
    dashboard = _dashboard()
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
    all_expressions = "\n".join(get_panel_expressions(_dashboard()))

    for required_token in (
        "bioetl_l0_status",
        "bioetl_l0_next_action_route",
        "bioetl_l0_input_status_selected",
        "bioetl_l1_gold_lifecycle_status",
        "bioetl_l1_control_plane_current_status",
        "bioetl_pipeline_runs_total",
        "bioetl_l1_workflow_global_status",
        "bioetl_records_processed_total",
    ):
        assert required_token in all_expressions
