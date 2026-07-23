"""Unified Grafana variable inventory and behavior contract."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import load_dashboard


pytestmark = pytest.mark.integration

_VARIABLE_REFERENCE = Path("docs/03-guides/dashboards/variable-reference.md")


def _variables(dashboard_file: str) -> dict[str, dict]:
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    return {
        variable.get("name"): variable
        for variable in dashboard.get("templating", {}).get("list", [])
        if variable.get("name")
    }


def test_variable_reference_documents_all_shipped_dashboard_variables() -> None:
    text = _VARIABLE_REFERENCE.read_text(encoding="utf-8")
    required_tokens = {
        "Grafana Dashboard Variable Reference",
        "selector-contracts.yaml",
        "$pipeline",
        "$run_type",
        "$stage",
        "$provider",
        "$pipeline_context",
        "$adapter",
        "$reason_code",
        "$field",
        "$run_id",
        "$quarantine_run_id",
        "$payload_hash",
        "$workflow",
        "$workflow_context",
        "$status",
        "$run_type_context",
        "$run_type_context_exact",
        "$provider_context",
        "$provider_context_exact",
        "$pipeline_context_exact",
        "$step_status",
        "$step_kind",
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-provider-health-v2",
        "bioetl-dq-v2",
        "bioetl-workflow-overview",
    }
    missing = sorted(token for token in required_tokens if token not in text)
    assert not missing, f"Unified variable reference is missing tokens: {missing}"


def test_all_dashboard_variables_have_non_empty_descriptions() -> None:
    for dashboard_path in sorted(Path("grafana/dashboards").glob("*.json")):
        dashboard = load_dashboard(dashboard_path)
        for variable in dashboard.get("templating", {}).get("list", []):
            name = variable.get("name")
            if not name:
                continue
            description = str(variable.get("description", "")).strip()
            assert description, (
                f"{dashboard_path.name}:{name} must define a non-empty description"
            )


def test_variable_defaults_follow_repo_aligned_contract() -> None:
    overview = _variables("bioetl-overview-v2.json")
    assert set(overview) == {"workflow", "pipeline", "run_type", "run_id"}
    assert overview["workflow"].get("includeAll") is True
    assert overview["workflow"].get("multi") is False
    assert overview["workflow"].get("current", {}).get("text") == "All"
    assert overview["pipeline"].get("multi") is False
    assert overview["pipeline"].get("includeAll") is True
    assert overview["pipeline"].get("current", {}).get("text") == "All"
    assert overview["run_type"].get("includeAll") is True
    assert overview["run_type"].get("current", {}).get("text") == "All"
    assert overview["run_id"].get("multi") is False
    assert overview["run_id"].get("includeAll") is False
    assert overview["run_id"].get("current", {}).get("value") == "-"

    for dashboard_name in (
        "bioetl-control-plane-v1.json",
        "bioetl-runtime.json",
        "bioetl-dq-v2.json",
    ):
        variables = _variables(dashboard_name)
        pipeline = variables["pipeline"]
        run_type = variables["run_type"]
        assert pipeline.get("multi") is False
        assert pipeline.get("includeAll") is False
        assert pipeline.get("current", {}).get("value") == "unknown"
        assert run_type.get("includeAll") is True
        assert run_type.get("current", {}).get("value") == "$__all"

    provider = _variables("bioetl-provider-health-v2.json")
    assert provider["workflow"].get("multi") is False
    assert provider["workflow"].get("includeAll") is True
    assert provider["workflow"].get("current", {}).get("value") == "$__all"
    assert provider["pipeline"].get("multi") is False
    assert provider["pipeline"].get("includeAll") is False
    assert provider["pipeline"].get("current", {}).get("value") == "unknown"
    assert provider["run_type"].get("includeAll") is True
    assert provider["run_type"].get("current", {}).get("value") == "$__all"
    assert provider["run_id"].get("multi") is False
    assert provider["run_id"].get("includeAll") is False
    assert provider["run_id"].get("current", {}).get("value") == "-"
    assert provider["provider"].get("multi") is False
    assert provider["provider"].get("includeAll") is False
    assert provider["provider"].get("current", {}).get("value") == "unknown"
    assert provider["pipeline_context"].get("hide") == 2
    assert provider["pipeline_context"].get("current", {}).get("value") == "unknown"

    workflow = _variables("bioetl-workflow-overview.json")
    assert set(workflow) == {
        "workflow",
        "workflow_context",
        "pipeline",
        "run_type",
        "run_id",
        "status",
        "pipeline_context",
        "pipeline_context_exact",
        "run_type_context",
        "run_type_context_exact",
        "provider_context",
        "provider_context_exact",
        "step_status",
        "step_kind",
    }
    for name in ("workflow", "status", "step_status", "step_kind"):
        assert workflow[name].get("includeAll") is True
        assert workflow[name].get("current", {}).get("value") == "$__all"
    assert workflow["workflow"].get("multi") is False
    assert workflow["pipeline"].get("multi") is False
    assert workflow["pipeline"].get("includeAll") is False
    assert workflow["pipeline"].get("current", {}).get("value") == "unknown"
    assert workflow["run_type"].get("includeAll") is True
    assert workflow["run_type"].get("current", {}).get("value") == "$__all"
    assert workflow["run_id"].get("multi") is False
    assert workflow["run_id"].get("includeAll") is False
    assert workflow["run_id"].get("current", {}).get("value") == "-"
    assert workflow["workflow_context"].get("hide") == 2
    assert workflow["workflow_context"].get("current", {}).get("value") == "All"
    assert workflow["pipeline_context"].get("hide") == 2
    assert workflow["pipeline_context"].get("current", {}).get("value") == "unknown"
    assert workflow["pipeline_context_exact"].get("hide") == 2
    assert (
        workflow["pipeline_context_exact"].get("current", {}).get("value") == "unknown"
    )
    assert workflow["run_type_context"].get("hide") == 2
    assert workflow["run_type_context"].get("current", {}).get("value") == "All"
    assert workflow["run_type_context_exact"].get("hide") == 2
    assert workflow["run_type_context_exact"].get("current", {}).get("value") == "All"
    assert workflow["provider_context"].get("hide") == 2
    assert workflow["provider_context"].get("current", {}).get("value") == "unknown"
    assert workflow["provider_context_exact"].get("hide") == 2
    assert (
        workflow["provider_context_exact"].get("current", {}).get("value") == "unknown"
    )
    # Silver Reject Explorer variables removed with the dashboard (2026-07-23).


def test_variable_reference_explains_role_specific_exceptions() -> None:
    text = _VARIABLE_REFERENCE.read_text(encoding="utf-8")
    required_tokens = {
        "`bioetl-workflow-overview` exposes the shared context shell",
        "`$workflow_context` | `bioetl-workflow-overview` | Hidden context var",
        "`$pipeline_context` | `bioetl-workflow-overview` | Hidden context var",
        "`$pipeline_context_exact` | `bioetl-workflow-overview` | Hidden exact-run handoff var",
        "`$run_type_context` | `bioetl-workflow-overview` | Hidden context var",
        "`$run_type_context_exact` | `bioetl-workflow-overview` | Hidden exact-run handoff var",
        "`$provider_context` | `bioetl-workflow-overview` | Hidden context var",
        "`$provider_context_exact` | `bioetl-workflow-overview` | Hidden exact-run handoff var",
        "run_type` always uses include-all fallback",
        "Primary operator dashboards `0..5` expose the shared context shell",
        "single-select with Include All across primary dashboards",
        "Pipeline-scoped operator dashboards use single-select `$pipeline`, except",
        "`bioetl-overview-v2` uses control-plane-backed `$run_id=-`",
    }
    missing = sorted(token for token in required_tokens if token not in text)
    assert not missing, (
        f"Variable reference must explain repo-specific exceptions: {missing}"
    )
