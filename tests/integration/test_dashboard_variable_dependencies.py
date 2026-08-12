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
"""Integration tests for Grafana dashboard variable dependency chains."""

import re
from pathlib import Path

import pytest

from tests.integration._grafana_test_support import load_dashboard

pytestmark = pytest.mark.integration


def _templating_map(path: str) -> dict[str, dict]:
    dashboard = load_dashboard(Path(path))
    return {v.get("name"): v for v in dashboard.get("templating", {}).get("list", [])}


_PROVIDER_DERIVATION_STAGES = (
    ("hint", "unknown", "src", r".*"),
    (
        "hint",
        "$1",
        "src",
        r"^(?:workflow_)?([^_|]+)(?:_[^|]*)?[|].*$",
    ),
    (
        "hint",
        "$1",
        "src",
        r"^(?:unknown|[$]__all|All|[.][*]|)[|]"
        r"(?:workflow_)?([^_|]+)(?:_[^|]*)?$",
    ),
    (
        "hint",
        "unknown",
        "hint",
        r"^(?:unknown|[$]|[$]__all|All|[.][*]|)$",
    ),
)


def _apply_label_replace(
    labels: dict[str, str],
    destination: str,
    replacement: str,
    source: str,
    pattern: str,
) -> dict[str, str]:
    """Model PromQL label_replace for deterministic selector contract tests."""
    match = re.fullmatch(pattern, labels.get(source, ""))
    if match is None:
        return labels
    rendered = replacement
    for index, value in enumerate(match.groups(), start=1):
        rendered = rendered.replace(f"${index}", value or "")
    return {**labels, destination: rendered}


def _derive_provider(pipeline: str, workflow: str) -> str:
    """Evaluate the shared bounded provider derivation without live Grafana."""
    labels = {"src": f"{pipeline}|{workflow}"}
    for stage in _PROVIDER_DERIVATION_STAGES:
        labels = _apply_label_replace(labels, *stage)
    return labels["hint"]


def test_runtime_variable_dependencies():
    """bioetl-runtime: $run_type depends on $pipeline, $stage defaults to All."""
    variables = _templating_map("grafana/dashboards/bioetl-runtime.json")

    assert "pipeline" in variables, "bioetl-runtime must have $pipeline variable"
    assert "run_type" in variables, "bioetl-runtime must have $run_type variable"
    assert "stage" in variables, "bioetl-runtime must have $stage variable"
    stage_var = variables["stage"]
    assert stage_var.get("includeAll") is True
    assert stage_var.get("current", {}).get("value") == "$__all"
    assert stage_var.get("current", {}).get("text") == "All"


def test_dq_variable_dependencies():
    """bioetl-dq-v2: $stage depends on pipeline/run_type and defaults to All."""
    variables = _templating_map("grafana/dashboards/bioetl-dq-v2.json")

    assert "pipeline" in variables, "bioetl-dq-v2 must have $pipeline variable"
    assert "run_type" in variables, "bioetl-dq-v2 must have $run_type variable"
    assert "stage" in variables, "bioetl-dq-v2 must have $stage variable"
    stage_var = variables["stage"]
    assert stage_var.get("includeAll") is True
    assert stage_var.get("current", {}).get("value") == "$__all"
    assert stage_var.get("current", {}).get("text") == "All"


def test_provider_health_variable_dependencies():
    """bioetl-provider-health-v2: provider derives from pipeline/workflow."""
    variables = _templating_map("grafana/dashboards/bioetl-provider-health-v2.json")

    assert "provider" in variables, (
        "bioetl-provider-health-v2 must have $provider variable"
    )
    provider = variables["provider"]
    query = str(provider.get("definition") or "")
    assert "query_result(" in query
    assert "${pipeline}" in query and "${workflow}" in query
    assert provider.get("current", {}).get("value") == "unknown"

    assert "pipeline_context" in variables, (
        "bioetl-provider-health-v2 must have $pipeline_context variable"
    )
    pipeline_context = variables["pipeline_context"]
    hide_value = pipeline_context.get("hide")
    assert hide_value is True or hide_value == 2, "$pipeline_context should be hidden"


def test_incident_provider_derives_from_pipeline_or_workflow():
    """bioetl-incident-v1: provider derives from pipeline/workflow, else unknown."""
    variables = _templating_map("grafana/dashboards/bioetl-incident-v1.json")
    provider = variables["provider"]
    query = str(provider.get("definition") or "")
    assert "query_result(" in query
    assert "${pipeline}" in query and "${workflow}" in query
    assert provider.get("current", {}).get("value") == "unknown"
    assert provider.get("includeAll") is False
    assert provider.get("multi") is False


def test_provider_derivation_queries_are_re2_compatible_and_in_sync():
    """Shared provider derivation must parse without Grafana selector errors."""
    paths = (
        "grafana/dashboards/bioetl-provider-health-v2.json",
        "grafana/dashboards/bioetl-incident-v1.json",
    )
    definitions = [
        str(_templating_map(path)["provider"].get("definition") or "") for path in paths
    ]

    assert len(set(definitions)) == 1
    definition = definitions[0]
    assert "(?!" not in definition, "RE2 does not support negative lookahead"
    assert r"\|" not in definition, "PromQL strings reject an escaped pipe"
    assert "[|]" in definition
    assert "[$]__all" in definition
    assert "[.][*]" in definition
    assert definition.count("label_replace(") == 5
    for _destination, _replacement, _source, pattern in _PROVIDER_DERIVATION_STAGES:
        assert pattern in definition
    for path in paths:
        provider = _templating_map(path)["provider"]
        query = provider.get("query")
        assert isinstance(query, dict)
        assert query.get("query") == definition

    cases = {
        "explicit pipeline": ("chembl_assay", "chembl_baseline", "chembl"),
        "workflow-prefixed pipeline": (
            "workflow_chembl_assay",
            "pubchem_baseline",
            "chembl",
        ),
        "unknown pipeline workflow fallback": (
            "unknown",
            "workflow_pubchem_activity",
            "pubchem",
        ),
        "empty pipeline workflow fallback": (
            "",
            "chembl_baseline",
            "chembl",
        ),
        "pipeline sentinel workflow fallback": (
            "$__all",
            "chembl_baseline",
            "chembl",
        ),
        "saved default pair": ("unknown", "$__all", "unknown"),
        "literal All": ("unknown", "All", "unknown"),
        "wildcard All": ("unknown", ".*", "unknown"),
        "empty inputs": ("", "", "unknown"),
        "unknown inputs": ("unknown", "unknown", "unknown"),
        "workflow aggregate": (
            "unknown",
            "workflow_chembl_activity|workflow_pubchem_activity",
            "unknown",
        ),
        "explicit pipeline with workflow aggregate": (
            "chembl_assay",
            "workflow_chembl_activity|workflow_pubchem_activity",
            "chembl",
        ),
    }
    for case, (pipeline, workflow, expected) in cases.items():
        assert _derive_provider(pipeline, workflow) == expected, case


