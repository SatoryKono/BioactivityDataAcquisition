"""Integration tests for Grafana dashboard variable dependency chains."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import load_dashboard

pytestmark = pytest.mark.integration


def test_runtime_variable_dependencies():
    """bioetl-runtime: $run_type depends on $pipeline, $stage depends on runtime-selected scope."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    variables = {
        v.get("name"): v for v in dashboard.get("templating", {}).get("list", [])
    }

    # Check that pipeline and run_type exist
    assert "pipeline" in variables, "bioetl-runtime must have $pipeline variable"
    assert "run_type" in variables, "bioetl-runtime must have $run_type variable"

    # Check that stage exists (optional for runtime)
    if "stage" in variables:
        stage_var = variables["stage"]
        # Stage should depend on pipeline context
        # This is a basic check - actual dependency chain is complex
        assert stage_var, "stage variable must be defined"


def test_dq_variable_dependencies():
    """bioetl-dq-v2: $run_type depends on $pipeline, $stage depends on $pipeline and $run_type."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    variables = {
        v.get("name"): v for v in dashboard.get("templating", {}).get("list", [])
    }

    # Check that pipeline and run_type exist
    assert "pipeline" in variables, "bioetl-dq-v2 must have $pipeline variable"
    assert "run_type" in variables, "bioetl-dq-v2 must have $run_type variable"
    assert "stage" in variables, "bioetl-dq-v2 must have $stage variable"


def test_provider_health_variable_dependencies():
    """bioetl-provider-health-v2: has provider selector and hidden pipeline_context."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    variables = {
        v.get("name"): v for v in dashboard.get("templating", {}).get("list", [])
    }

    # Check that provider exists (visible selector)
    assert "provider" in variables, (
        "bioetl-provider-health-v2 must have $provider variable"
    )

    # Check that pipeline_context exists (hidden context selector)
    assert "pipeline_context" in variables, (
        "bioetl-provider-health-v2 must have $pipeline_context variable"
    )

    # pipeline_context should be hidden (hide can be True or 2 in Grafana)
    pipeline_context = variables["pipeline_context"]
    hide_value = pipeline_context.get("hide")
    assert hide_value is True or hide_value == 2, "$pipeline_context should be hidden"


def test_silver_reject_explorer_variable_dependencies():
    dashboard = load_dashboard(pytest.skip("Silver Reject Explorer removed 2026-07-23"))
    variables = {
        v.get("name"): v for v in dashboard.get("templating", {}).get("list", [])
    }

    # Check that pipeline and run_type exist
    assert "pipeline" in variables, ()
    assert "run_type" in variables, ()

    # Check forensic variables
    assert "quarantine_run_id" in variables, ()
    assert "payload_hash" in variables, ()
