"""Integration tests for the shipped BioETL Overview dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    get_panel_expressions,
    load_dashboard,
)

pytestmark = pytest.mark.integration

_OVERVIEW_PATH = Path("grafana/dashboards/bioetl-overview-v2.json")
_STATUS_TEXTS = ("UNKNOWN", "OK", "WARN", "CRIT")
_L1_CARD_TITLES = (
    "Runtime",
    "Data Quality",
    "Control Plane",
    "Provider",
    "Data Validation",
    "Workflow",
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
    provenance = _panels_by_title()["Provenance"]
    content = str(provenance.get("options", {}).get("content", ""))
    description = str(dashboard.get("description", ""))

    assert dashboard.get("title") == "1. Overview"
    assert dashboard.get("uid") == "bioetl-overview-v2"
    assert "Hybrid L0 overview" in description
    assert "what is broken or degraded right now" in content.lower()
    assert "where should the operator drill down first" in content.lower()


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
    assert run_id.get("datasource") == "Quarantine Explorer"
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


def test_first_screen_layout_matches_overview_v3_baseline() -> None:
    expected = {
        "Provenance": {"id": 99, "x": 0, "y": 3, "w": 16, "h": 4},
        "Status": {"id": 214, "x": 16, "y": 3, "w": 8, "h": 4},
        "ID": {"id": 9300, "x": 0, "y": 7, "w": 10},
        "Processed Records": {"id": 9301, "x": 10, "y": 7, "w": 6},
        "First Action": {"id": 215, "x": 16, "y": 7, "w": 8},
        "Control Plane": {"id": 9006, "x": 0, "y": 17, "w": 5, "h": 5},
        "Runtime": {"id": 9003, "x": 5, "y": 17, "w": 4, "h": 5},
        "Data Quality": {"id": 9004, "x": 9, "y": 17, "w": 5, "h": 5},
        "Provider": {"id": 9007, "x": 14, "y": 17, "w": 4, "h": 5},
        "Data Validation": {"id": 9005, "x": 18, "y": 17, "w": 6, "h": 5},
        "Inputs": {"id": 9002, "x": 0, "y": 22, "w": 12, "h": 8},
        "Workflow": {"id": 9013, "x": 12, "y": 22, "w": 12, "h": 8},
    }

    for title, placement in expected.items():
        panel = _panels_by_title()[title]
        grid_pos = panel.get("gridPos", {})
        assert panel.get("id") == placement["id"]
        for key in ("x", "w"):
            assert grid_pos.get(key) == placement[key], (
                f"Panel {title!r} must keep Overview v3 {key} placement"
            )
        expected_y = placement["y"]
        if title in {
            "Control Plane",
            "Runtime",
            "Data Quality",
            "Provider",
            "Data Validation",
        }:
            assert grid_pos.get("y") in {expected_y, expected_y + 4}, (
                f"Panel {title!r} must keep reviewed summary-row y placement"
            )
        elif title in {"Inputs", "Workflow"}:
            assert grid_pos.get("y") in {expected_y, expected_y + 4}, (
                f"Panel {title!r} must keep reviewed evidence-row y placement"
            )
        else:
            assert grid_pos.get("y") == expected_y, (
                f"Panel {title!r} must keep Overview v3 y placement"
            )
        expected_height = placement.get("h")
        if expected_height is not None:
            assert grid_pos.get("h") == expected_height, (
                f"Panel {title!r} must keep Overview v3 h placement"
            )
        else:
            assert grid_pos.get("h") in {6, 10}, (
                f"Panel {title!r} must keep reviewed shared-row height"
            )


def test_status_and_next_action_preserve_current_status_semantics() -> None:
    panels = _panels_by_title()
    status = panels["Status"]
    next_action = panels["First Action"]

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
    assert "topk(1" in next_action_expr
    assert 'pipeline=~"$pipeline"' in next_action_expr
    assert 'run_type=~"$run_type"' in next_action_expr
    assert "$__range" not in next_action_expr
    assert "NO_ROUTE" in description
    assert "selected_scope_not_present" in next_action_expr
    assert "bioetl_overview_pipeline_run_type_universe" in description


def test_identity_panel_uses_run_id_without_leaking_to_prometheus_queries() -> None:
    identity = _panels_by_title()["ID"]

    assert identity.get("datasource") == "Quarantine Explorer"
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
        "Runtime": {"Open Runtime"},
        "Data Quality": {"Open Data Quality"},
        "Control Plane": {"Open Control Plane"},
        "Provider": {"Open Provider Health"},
        "Data Validation": {"Open Runtime"},
        "Workflow": {"Open Workflow"},
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
    for title in (
        "Status",
        "First Action",
        "Inputs",
        "Runtime",
        "Data Quality",
        "Control Plane",
        "Data Validation",
    ):
        expr = _panel_expr(_panels_by_title()[title])
        assert 'label_replace(vector(1), "pipeline_raw", "$pipeline"' in expr
        assert '"^(?:workflow_)?(.*)$"' in expr


def test_provider_and_workflow_scope_are_explicit() -> None:
    provider = _panels_by_title()["Provider"]
    workflow = _panels_by_title()["Workflow"]

    assert _panel_expr(provider).strip() == "bioetl_l1_provider_global_status"
    assert "intentionally ignores selected pipeline/run_type" in str(
        provider.get("description", "")
    )
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
    workflow_links = workflow.get("options", {}).get("dataLinks", [])
    assert {link.get("title") for link in workflow_links} == {"Open Workflow"}


def test_range_evidence_and_trend_rows_are_retained() -> None:
    panels = _panels_by_title()
    current_verdict_titles = {
        "Status",
        "First Action",
        "Inputs",
        "Control Plane",
        "Runtime",
        "Data Quality",
        "Provider",
        "Data Validation",
        "Workflow",
    }
    expected_evidence_panels = {
        "Runtime Blockers Trend": {
            "id": 9018,
            "links": {"Open Runtime"},
            "tokens": ("selected-range", "l1 runtime evidence", "does not determine"),
        },
        "DQ Status Trend": {
            "id": 9019,
            "links": {"Open Data Quality"},
            "tokens": (
                "selected-range",
                "l1 data quality evidence",
                "does not determine",
            ),
        },
        "Gold Lifecycle Trend": {
            "id": 9020,
            "links": {"Open Runtime", "Open Control Plane"},
            "tokens": (
                "selected-range",
                "l1 data-validation lifecycle evidence",
                "lifecycle_state",
            ),
        },
        "Historical Failures": {
            "id": 9010,
            "links": {"Open Runtime"},
            "tokens": (
                "selected-range historical failure evidence only",
                "does not determine",
                "not proof",
            ),
        },
        "Recent Terminal Runs": {
            "id": 9011,
            "links": {"Open Control Plane", "Open Runtime"},
            "tokens": (
                "selected-range terminal-run evidence only",
                "does not determine",
                "not proof",
            ),
        },
    }

    for title in (*expected_evidence_panels, "Silver Rejects + Rate"):
        assert title in panels

    for title, expectation in expected_evidence_panels.items():
        panel = panels[title]
        description = str(panel.get("description", "")).lower()
        data_links = panel.get("options", {}).get("dataLinks", [])

        assert panel.get("id") == expectation["id"]
        assert panel.get("gridPos", {}).get("y", 0) > max(
            panels[current_title].get("gridPos", {}).get("y", 0)
            for current_title in current_verdict_titles
        )
        assert {link.get("title") for link in data_links} == expectation["links"]
        assert all(link.get("includeVars") is False for link in data_links)
        assert all(link.get("targetBlank") is False for link in data_links)
        for token in expectation["tokens"]:
            assert token in description
        assert "l0 status" in description
        assert "first action" in description or "next action" in description

    assert "[$__range]" in _panel_expr(panels["Historical Failures"])
    assert "[$__range]" in _panel_expr(panels["Recent Terminal Runs"])
    assert "[$__range]" in _panel_expr(panels["Silver Rejects + Rate"])


def test_diagnostics_row_is_not_empty() -> None:
    dashboard = _dashboard()
    diagnostics_row = next(
        panel
        for panel in dashboard.get("panels", [])
        if panel.get("title") == "Diagnostics & Docs (Logs / Traces / Raw Metrics)"
    )

    assert diagnostics_row.get("type") == "row"
    child_titles = {child.get("title") for child in diagnostics_row.get("panels", [])}
    assert "Diagnostics Navigation" in child_titles


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
