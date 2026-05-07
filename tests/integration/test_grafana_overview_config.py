"""Integration tests for the shipped BioETL Overview v2 dashboard."""

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

_STATUS_TEXTS = ("UNKNOWN", "OK", "WARN", "CRIT")


def _panels_by_title() -> dict[str, dict]:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    return {
        str(panel.get("title")): panel
        for panel in get_dashboard_panels(dashboard)
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
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    scope_panel = next(
        panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") == "L0 Overview Scope"
    )
    content = str(scope_panel.get("options", {}).get("content", ""))
    description = str(dashboard.get("description", ""))

    assert dashboard.get("title") == "1. Overview"
    assert dashboard.get("uid") == "bioetl-overview-v2"
    assert "L0 Overview" in description
    assert "what is broken now" in (description + content).lower()
    assert "what is broken now" in content.lower()
    assert (
        "rows marked <strong>unknown</strong> mean no recent signal" in content.lower()
    )
    assert (
        "blank current-status tables indicate a projection regression"
        in content.lower()
    )


def test_overview_answer_row_is_compact_and_current_only() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    answer_panels = [
        panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("gridPos", {}).get("y") == 4
    ]
    answer_titles = {panel.get("title") for panel in answer_panels}

    assert answer_titles == {"System Status", "Next Action", "L0 Inputs"}


def test_system_status_panel_preserves_current_status_semantics() -> None:
    panel = _panels_by_title()["System Status"]
    expr = _panel_expr(panel)
    options = panel.get("options", {})

    assert panel.get("type") == "stat"
    assert "bioetl_l0_status" in expr
    assert "$__range" not in expr
    assert options.get("textMode") == "value"
    assert options.get("graphMode") == "none"
    _assert_status_mapping(panel)


def test_next_action_panel_exposes_action_route_details() -> None:
    panel = _panels_by_title()["Next Action"]
    expr = _panel_expr(panel)
    description = str(panel.get("description", ""))
    transformations = _panel_transformations(panel)
    data_links = panel.get("options", {}).get("dataLinks", [])

    assert panel.get("type") == "table"
    assert "bioetl_l0_next_action_route" in expr
    assert "topk(1" in expr
    assert 'pipeline=~"$pipeline"' in expr
    assert 'run_type=~"$run_type"' in expr
    assert "> 0" not in expr
    assert "label_replace(vector(0)" in expr
    assert "selected_scope_not_present" in expr
    assert "$__range" not in expr
    assert panel.get("gridPos", {}).get("w") == 11
    assert transformations and transformations[0].get("id") == "organize"
    excluded = transformations[0].get("options", {}).get("excludeByName", {})
    for hidden_field in ("Time", "__name__", "Value", "action_dashboard_uid"):
        assert excluded.get(hidden_field) is True
    assert "NO_ROUTE" in description
    assert "bioetl_overview_pipeline_run_type_universe" in description
    assert "provider=unknown" in description
    assert "resets scope" in description
    for label_name in ("action_target", "action_reason", "action_dashboard_uid"):
        assert label_name in description
    assert {link.get("title") for link in data_links} == {
        "Open Runtime",
        "Open Control Plane",
        "Open Data Quality",
        "Open Provider Health",
        "Open Workflow (Reset Scope)",
    }
    defaults_serialized = json.dumps(panel.get("fieldConfig", {}).get("defaults", {}))
    assert "NO_ROUTE" in defaults_serialized
    overrides_serialized = json.dumps(panel.get("fieldConfig", {}).get("overrides", []))
    assert "gold_lifecycle_blocking" in overrides_serialized
    assert "no_route" in overrides_serialized
    assert "selected_scope_not_present" in overrides_serialized


def test_current_l0_l1_tables_have_operator_mappings() -> None:
    for title in (
        "L0 Inputs",
        "Runtime Blockers",
        "DQ Status",
        "Gold Lifecycle",
        "Control Plane",
        "Provider Global",
        "Workflow Selected",
        "Workflow Global",
    ):
        panel = _panels_by_title()[title]
        assert panel.get("type") == "table"
        _assert_status_mapping(panel)


def test_current_tables_hide_prometheus_noise_and_use_human_column_names() -> None:
    expected_renames = {
        "Next Action": ("Pipeline",),
        "L0 Inputs": ("Input", "Status"),
        "Runtime Blockers": ("Pipeline", "Status"),
        "DQ Status": ("Pipeline", "Status"),
        "Gold Lifecycle": ("Pipeline", "Status"),
        "Control Plane": ("Pipeline", "Status"),
        "Provider Global": ("Provider", "Status"),
        "Workflow Selected": ("Pipeline", "Status"),
        "Workflow Global": ("Pipeline", "Status"),
    }

    for title, renamed_fields in expected_renames.items():
        panel = _panels_by_title()[title]
        transformations = _panel_transformations(panel)

        assert transformations and transformations[0].get("id") == "organize"
        options = transformations[0].get("options", {})
        excluded = options.get("excludeByName", {})
        assert excluded.get("Time") is True
        assert excluded.get("__name__") is True
        rename_by_name = options.get("renameByName", {})
        for renamed_field in renamed_fields:
            assert renamed_field in rename_by_name.values(), (
                f"Panel {title!r} must expose {renamed_field!r} as a human column name"
            )


def test_current_status_tables_apply_status_color_to_entire_row() -> None:
    expected_titles = (
        "L0 Inputs",
        "Runtime Blockers",
        "DQ Status",
        "Gold Lifecycle",
        "Control Plane",
        "Provider Global",
        "Workflow Selected",
        "Workflow Global",
    )

    for title in expected_titles:
        panel = _panels_by_title()[title]
        overrides = panel.get("fieldConfig", {}).get("overrides", [])
        color_background_overrides = [
            override
            for override in overrides
            if any(
                prop.get("id") == "custom.cellOptions"
                and prop.get("value", {}).get("type") == "color-background"
                and prop.get("value", {}).get("applyToRow") is True
                for prop in override.get("properties", [])
            )
        ]
        assert color_background_overrides, (
            f"Panel {title!r} must apply status color to the entire row"
        )


def test_l0_inputs_and_gold_lifecycle_column_order_is_operator_first() -> None:
    expected = {
        "L0 Inputs": {
            "input": 0,
            "Value": 1,
        },
        "Gold Lifecycle": {
            "pipeline": 0,
            "Value": 1,
        },
    }

    for title, ordering in expected.items():
        panel = _panels_by_title()[title]
        transformations = _panel_transformations(panel)
        organize = transformations[0].get("options", {}).get("indexByName", {})
        for field_name, field_index in ordering.items():
            assert organize.get(field_name) == field_index, (
                f"Panel {title!r} must keep {field_name!r} at column index {field_index}"
            )


def test_operator_panels_expand_compact_layout_for_readability() -> None:
    assert _panels_by_title()["System Status"].get("gridPos", {}).get("w") == 5
    assert _panels_by_title()["Next Action"].get("gridPos", {}).get("w") == 11
    assert _panels_by_title()["L0 Inputs"].get("gridPos", {}).get("w") == 8
    assert _panels_by_title()["Gold Lifecycle"].get("gridPos", {}).get("w") == 6
    assert _panels_by_title()["System Status"].get("gridPos", {}).get("h") == 8
    assert _panels_by_title()["Next Action"].get("gridPos", {}).get("h") == 8
    assert _panels_by_title()["L0 Inputs"].get("gridPos", {}).get("h") == 8


def test_triage_row_is_rebalanced_without_overlap() -> None:
    expected = {
        "Runtime Blockers": {"x": 0, "w": 6},
        "DQ Status": {"x": 6, "w": 6},
        "Control Plane": {"x": 12, "w": 6},
        "Gold Lifecycle": {"x": 18, "w": 6},
    }

    for title, placement in expected.items():
        grid_pos = _panels_by_title()[title].get("gridPos", {})
        assert grid_pos.get("y") == 12
        assert grid_pos.get("h") == 7
        assert grid_pos.get("x") == placement["x"]
        assert grid_pos.get("w") == placement["w"]


def test_global_scope_row_gives_workflow_panels_more_room() -> None:
    expected = {
        "Provider Global": {"x": 0, "w": 8},
        "Workflow Selected": {"x": 8, "w": 8},
        "Workflow Global": {"x": 16, "w": 8},
    }

    for title, placement in expected.items():
        grid_pos = _panels_by_title()[title].get("gridPos", {})
        assert grid_pos.get("y") == 19
        assert grid_pos.get("h") == 7
        assert grid_pos.get("x") == placement["x"]
        assert grid_pos.get("w") == placement["w"]


def test_collapsed_support_rows_follow_trends_in_operator_order() -> None:
    range_evidence = _panels_by_title()["Range Evidence (Historical / Recent History)"]
    diagnostics = _panels_by_title()["Diagnostics & Docs (Logs / Traces / Raw Metrics)"]

    assert range_evidence.get("gridPos", {}).get("y") == 35
    assert diagnostics.get("gridPos", {}).get("y") == 36
    assert range_evidence.get("gridPos", {}).get("y") < diagnostics.get(
        "gridPos", {}
    ).get("y")


def test_range_evidence_band_uses_full_row_width() -> None:
    expected = {
        "Historical Failures": {"x": 0, "w": 8, "h": 6},
        "Recent Terminal Runs": {"x": 8, "w": 8, "h": 6},
        "Silver Rejects + Rate": {"x": 16, "w": 8, "h": 6},
    }

    for title, placement in expected.items():
        grid_pos = _panels_by_title()[title].get("gridPos", {})
        assert grid_pos.get("x") == placement["x"]
        assert grid_pos.get("w") == placement["w"]
        assert grid_pos.get("h") == placement["h"]


def test_current_panels_do_not_mix_in_range_evidence() -> None:
    for title in (
        "System Status",
        "Next Action",
        "L0 Inputs",
        "Runtime Blockers",
        "DQ Status",
        "Gold Lifecycle",
        "Control Plane",
        "Provider Global",
        "Workflow Selected",
        "Workflow Global",
    ):
        expr = _panel_expr(_panels_by_title()[title])
        assert "$__range" not in expr


def test_gold_lifecycle_panel_uses_explicit_state_projection() -> None:
    panel = _panels_by_title()["Gold Lifecycle"]
    expr = _panel_expr(panel)
    description = str(panel.get("description", ""))

    assert "bioetl_l1_gold_lifecycle_status" in expr
    assert "max by (pipeline)" in expr
    assert 'run_type=~"$run_type"' in expr
    assert "worst lifecycle status per pipeline" in description


def test_l0_inputs_panel_uses_selected_scope_projection() -> None:
    panel = _panels_by_title()["L0 Inputs"]
    expr = _panel_expr(panel)
    data_links = panel.get("options", {}).get("dataLinks", [])

    assert "bioetl_l0_input_status_selected" in expr
    assert "max by (input)" in expr
    assert 'pipeline=~"$pipeline"' in expr
    assert 'run_type=~"$run_type"' in expr
    assert {link.get("title") for link in data_links} == {
        "Open Runtime",
        "Open Control Plane",
        "Open Data Quality",
        "Open Provider Health",
        "Open Workflow (Reset Scope)",
    }


def test_provider_and_workflow_scope_are_explicit() -> None:
    provider = _panels_by_title()["Provider Global"]
    workflow_selected = _panels_by_title()["Workflow Selected"]
    workflow_global = _panels_by_title()["Workflow Global"]

    assert _panel_expr(provider).strip() == "bioetl_l1_provider_global_status"
    assert "intentionally ignores selected pipeline/run_type" in str(
        provider.get("description", "")
    )
    provider_links = provider.get("options", {}).get("dataLinks", [])
    assert any("var-provider=unknown" in str(link.get("url", "")) for link in provider_links)
    assert "bioetl_l1_workflow_selected_status" in _panel_expr(workflow_selected)
    workflow_links = workflow_selected.get("options", {}).get("dataLinks", [])
    assert {link.get("title") for link in workflow_links} == {
        "Open Workflow (Reset Scope)"
    }
    assert "resets scope" in str(workflow_selected.get("description", "")).lower()
    assert "bioetl_l1_workflow_global_status" in _panel_expr(workflow_global)


def test_range_evidence_panels_keep_run_type_scope() -> None:
    failures = _panels_by_title()["Historical Failures"]
    terminals = _panels_by_title()["Recent Terminal Runs"]

    failures_expr = _panel_expr(failures)
    terminals_expr = _panel_expr(terminals)

    assert "sum by (pipeline, run_type)" in failures_expr
    assert 'run_type=~"$run_type"' in failures_expr
    assert "[$__range]" in failures_expr
    assert "sum by (pipeline, status)" in terminals_expr
    assert 'run_type=~"$run_type"' in terminals_expr
    assert 'status!="success"' in terminals_expr
    assert "[$__range]" in terminals_expr


def test_range_evidence_tables_hide_raw_prometheus_columns() -> None:
    expected = {
        "Historical Failures": ("Pipeline", "Run Type", "Failures"),
        "Recent Terminal Runs": ("Pipeline", "Terminal Status", "Runs"),
    }

    for title, renamed_fields in expected.items():
        panel = _panels_by_title()[title]
        transformations = _panel_transformations(panel)

        assert panel.get("type") == "table"
        assert transformations and transformations[0].get("id") == "organize"
        options = transformations[0].get("options", {})
        excluded = options.get("excludeByName", {})
        assert excluded.get("Time") is True
        assert excluded.get("__name__") is True
        rename_by_name = options.get("renameByName", {})
        for renamed_field in renamed_fields:
            assert renamed_field in rename_by_name.values()


def test_diagnostics_row_is_not_empty() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    diagnostics_row = next(
        panel
        for panel in dashboard.get("panels", [])
        if panel.get("title") == "Diagnostics & Docs (Logs / Traces / Raw Metrics)"
    )

    assert diagnostics_row.get("type") == "row"
    child_titles = {child.get("title") for child in diagnostics_row.get("panels", [])}
    assert "Diagnostics Navigation" in child_titles


def test_overview_uses_only_expected_variables_and_target_scoped_links() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    variables = {
        variable.get("name")
        for variable in dashboard.get("templating", {}).get("list", [])
        if variable.get("name")
    }
    links = {link.get("title"): link for link in dashboard.get("links", [])}

    assert variables == {"pipeline", "run_type"}
    assert all(link.get("includeVars") is False for link in links.values())

    for title in ("2. Runtime", "0. Control Plane", "4. Data Quality"):
        url = str(links[title].get("url", ""))
        assert "var-pipeline=$pipeline" in url
        assert "var-run_type=$run_type" in url
        assert "${__url_time_range}" in url

    for title in ("3. Provider Health", "5. Workflow"):
        url = str(links[title].get("url", ""))
        assert "var-pipeline=" not in url
        assert "var-run_type=" not in url
        assert "${__url_time_range}" in url


def test_overview_pipeline_defaults_to_all_and_panels_use_resolved_prometheus_uid() -> (
    None
):
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    variables = {
        variable.get("name"): variable
        for variable in dashboard.get("templating", {}).get("list", [])
        if variable.get("name")
    }
    pipeline = variables["pipeline"]

    assert pipeline.get("includeAll") is True
    assert pipeline.get("multi") is False
    assert pipeline.get("current", {}).get("value") == "$__all"
    assert pipeline.get("current", {}).get("text") == "All"

    for panel in get_dashboard_panels(dashboard):
        datasource = panel.get("datasource")
        if not isinstance(datasource, dict):
            continue
        if datasource.get("type") != "prometheus":
            continue
        assert datasource.get("uid") == "prometheus", (
            f"Panel {panel.get('title')!r} must use resolved Prometheus uid"
        )


def test_overview_queries_are_backed_by_recording_rules_and_runtime_metrics() -> None:
    all_expressions = "\n".join(
        get_panel_expressions(
            load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
        )
    )

    for required_token in (
        "bioetl_l0_status",
        "bioetl_l0_next_action_route",
        "bioetl_l0_input_status_selected",
        "bioetl_l1_gold_lifecycle_status",
        "bioetl_l1_control_plane_current_status",
        "bioetl_pipeline_runs_total",
    ):
        assert required_token in all_expressions


def test_overview_hero_logic_uses_selected_scope_projection_contract() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    expressions = "\n".join(get_panel_expressions(dashboard))

    assert "bioetl_l0_status" in expressions
    assert "bioetl_l0_next_action_route" in expressions
    assert "bioetl_l0_input_status_selected" in expressions
