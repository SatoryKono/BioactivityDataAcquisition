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
        "$run_id",
        "$quarantine_run_id",
        "$payload_hash",
        "$workflow",
        "$workflow_context",
        "$status",
        "$pipeline_context_exact",
        "$step_status",
        "$step_kind",
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-provider-health-v2",
        "bioetl-dq-v2",
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


def test_run_explorer_defaults_browse_all_without_selecting_an_exact_run() -> None:
    variables = _variables("bioetl-run-explorer-v1.json")
    for name in ("workflow", "pipeline", "run_type"):
        assert variables[name]["includeAll"] is True
        assert variables[name]["current"]["value"] == "$__all"
        assert variables[name]["allValue"] == ".*"
        assert variables[name]["skipUrlSync"] is False
    assert variables["pipeline"]["multi"] is False
    assert variables["run_id"]["current"]["value"] == "-"


def test_variable_defaults_follow_repo_aligned_contract() -> None:
    overview = _variables("bioetl-overview-v2.json")
    assert set(overview) == {
        "workflow",
        "pipeline",
        "run_type",
        "run_id",
        # Hidden helper feeding the 9002 'Open Provider Health' handoff
        # (var-provider=${provider_for_pipeline:percentencode}).
        "provider_for_pipeline",
    }
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
    assert overview["run_id"].get("sort") == 0

    for dashboard_name in (
        "bioetl-control-plane-v1.json",
        "bioetl-dq-v2.json",
        "bioetl-incident-v1.json",
    ):
        variables = _variables(dashboard_name)
        pipeline = variables["pipeline"]
        run_type = variables["run_type"]
        run_id = variables["run_id"]
        assert pipeline.get("multi") is False
        assert pipeline.get("includeAll") is True
        assert pipeline.get("current", {}).get("value") == "$__all"
        assert run_type.get("includeAll") is True
        # SEL-P0/P2: non-Overview native default is backfill (fallback policy).
        assert run_type.get("current", {}).get("value") == "backfill"
        assert run_id.get("sort") == 0
        assert run_id.get("current", {}).get("value") == "-"

    stage = _variables("bioetl-dq-v2.json")["stage"]
    assert stage.get("includeAll") is True
    assert stage.get("current", {}).get("value") == "$__all"
    assert stage.get("current", {}).get("text") == "All"
    for retired in (
        "bioetl-runtime.json",
        "bioetl-provider-health-v2.json",
        "bioetl-workflow-overview.json",
    ):
        assert not (Path("grafana/dashboards") / retired).exists()


def test_variable_reference_explains_role_specific_exceptions() -> None:
    text = _VARIABLE_REFERENCE.read_text(encoding="utf-8")
    required_tokens = {
        "Primary operator dashboards expose the shared context shell",
        "single-select with Include All across primary dashboards",
        "`$pipeline` is single-select",
        "`$run_id` is HTTP-backed control-plane identity context",
        "Retired boards (do not reintroduce)",
    }
    missing = sorted(token for token in required_tokens if token not in text)
    assert not missing, (
        f"Variable reference must explain repo-specific exceptions: {missing}"
    )
