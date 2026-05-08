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
        "$pipeline",
        "$run_type",
        "$stage",
        "$provider",
        "$pipeline_context",
        "$adapter",
        "$reason_code",
        "$field",
        "$run_id",
        "$payload_hash",
        "$workflow",
        "$status",
        "$step_status",
        "$step_kind",
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-provider-health-v2",
        "bioetl-dq-v2",
        "bioetl-silver-reject-explorer",
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
    assert overview["pipeline"].get("multi") is False
    assert overview["pipeline"].get("includeAll") is True
    assert overview["pipeline"].get("current", {}).get("text") == "All"
    assert overview["run_type"].get("current", {}).get("text") == "All"

    for dashboard_name in (
        "bioetl-control-plane-v1.json",
        "bioetl-runtime.json",
        "bioetl-dq-v2.json",
        "bioetl-silver-reject-explorer.json",
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
    assert provider["provider"].get("multi") is False
    assert provider["provider"].get("includeAll") is False
    assert provider["provider"].get("current", {}).get("value") == "unknown"
    assert provider["pipeline_context"].get("hide") == 2
    assert provider["pipeline_context"].get("current", {}).get("value") == "unknown"

    workflow = _variables("bioetl-workflow-overview.json")
    assert set(workflow) == {"workflow", "status", "step_status", "step_kind"}
    for name in workflow:
        assert workflow[name].get("includeAll") is True
        assert workflow[name].get("current", {}).get("value") == "$__all"

    explorer = _variables("bioetl-silver-reject-explorer.json")
    assert explorer["run_id"].get("multi") is False
    assert explorer["run_id"].get("includeAll") is False
    assert explorer["payload_hash"].get("type") == "textbox"
    assert explorer["payload_hash"].get("current", {}).get("value") == ""


def test_variable_reference_explains_role_specific_exceptions() -> None:
    text = _VARIABLE_REFERENCE.read_text(encoding="utf-8")
    required_tokens = {
        "`bioetl-workflow-overview` does not use `$pipeline` / `$run_type`",
        "`bioetl-silver-reject-explorer` requires single-select `$pipeline`",
        "run_type` always uses include-all fallback",
        "Pipeline-scoped operator dashboards используют single-select `$pipeline`",
        "кроме `bioetl-overview-v2`",
    }
    missing = sorted(token for token in required_tokens if token not in text)
    assert not missing, f"Variable reference must explain repo-specific exceptions: {missing}"
