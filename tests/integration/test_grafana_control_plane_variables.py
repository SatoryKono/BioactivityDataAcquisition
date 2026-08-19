"""Integration contracts for Grafana control-plane variable sources."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import load_dashboard

pytestmark = pytest.mark.integration


def test_control_plane_dashboard_uses_control_plane_native_variable_sources() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    variable_map = {
        var.get("name"): var
        for var in dashboard.get("templating", {}).get("list", [])
        if var.get("name")
    }

    pipeline_var = variable_map.get("pipeline")
    run_type_var = variable_map.get("run_type")
    assert pipeline_var is not None
    assert run_type_var is not None

    pipeline_query = pipeline_var.get("query", {})
    run_type_query = run_type_var.get("query", {})
    assert isinstance(pipeline_query, dict)
    infinity = pipeline_query.get("infinityQuery", {})
    assert isinstance(infinity, dict)
    pipeline_url = str(infinity.get("url", ""))
    run_type_query_text = (
        run_type_query.get("query", "") if isinstance(run_type_query, dict) else ""
    )

    assert "/ops/control-plane/filter-options" in pipeline_url
    assert "dimension=pipeline" in pipeline_url
    assert pipeline_var.get("datasource") == "BioETL Ops HTTP"
    assert "bioetl_control_plane_run_type_universe" in run_type_query_text
    assert "bioetl_control_plane_manifest_writes_total" not in run_type_query_text
    assert "bioetl_records_processed_total" not in run_type_query_text
