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
    """Fleet runtime evidence retains pipeline/run_type dependencies on Incident."""
    variables = _templating_map("grafana/dashboards/bioetl-incident-v1.json")
    # Phase 4.5: selected_* removed from Incident (unused outside Overview/DQ).
    assert {
        "workflow",
        "pipeline",
        "run_type",
        "run_id",
        "provider",
        "read_latency_quantile",
    } == set(variables)
    query = str(variables["run_type"].get("definition") or "")
    assert "filter-options?dimension=run_type" in query
    assert "${pipeline}" in query
    assert variables["run_type"]["current"]["value"] == "$__all"
    assert "provider_for_pipeline" not in variables
    assert variables["run_id"]["datasource"] == {
        "type": "yesoreyeram-infinity-datasource",
        "uid": "bioetl-ops-http",
    }
    assert variables["read_latency_quantile"]["current"]["value"] == "0.95"


def test_overview_variable_dependencies():
    """Run Overview owns runtime context after Pipeline Diagnostics retirement."""
    variables = _templating_map("grafana/dashboards/bioetl-overview-v2.json")
    assert {"workflow", "pipeline", "run_type", "run_id"} <= variables.keys()
    assert "filter-options?dimension=run_type" in variables["run_type"]["definition"]
    assert variables["run_type"]["current"]["value"] == "$__all"
    run_query = variables["run_id"]["definition"]
    for selector in ("${workflow}", "${pipeline}", "${run_type:csv}"):
        assert selector in run_query
    assert "stage" not in variables


def test_dq_variable_dependencies():
    """bioetl-dq-v2: Phase 4.1 drops unused $stage; pipeline/run_type remain."""
    variables = _templating_map("grafana/dashboards/bioetl-dq-v2.json")

    assert "pipeline" in variables, "bioetl-dq-v2 must have $pipeline variable"
    assert "run_type" in variables, "bioetl-dq-v2 must have $run_type variable"
    assert "stage" not in variables
    assert "provider_for_pipeline" not in variables


def test_provider_health_variable_dependencies():
    """Saved Provider Evidence uses exact run identity, not legacy fleet selectors."""
    variables = _templating_map("grafana/dashboards/bioetl-overview-v2.json")
    assert {
        "provider",
        "adapter",
        "pipeline_context",
        "provider_for_pipeline",
    }.isdisjoint(variables)
    assert variables["run_id"]["datasource"] == {
        "type": "yesoreyeram-infinity-datasource",
        "uid": "bioetl-ops-http",
    }
    assert variables["run_id"]["multi"] is False
    assert not Path("grafana/dashboards/bioetl-provider-health-v2.json").exists()


def test_overview_provider_context_is_derived_from_pipeline():
    """Provider evidence reuses Overview donor 9002 (no fleet provider helper var)."""
    variables = _templating_map("grafana/dashboards/bioetl-overview-v2.json")
    assert "provider_for_pipeline" not in variables
    assert not {"provider", "pipeline_context", "adapter"} & variables.keys()
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panels = {panel["id"]: panel for panel in dashboard["panels"]}
    donor = panels[9002]["targets"][0]
    assert donor["url"].startswith("/ops/observability/selected-run-status?")
    assert "pipeline=${pipeline}" in donor["url"]
    assert "run_id=${run_id}" in donor["url"]
    for panel_id in (9480, 9481):
        target = panels[panel_id]["targets"][0]
        assert target.get("panelId") == 9002
        assert target["withTransforms"] is False


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
    paths = ("grafana/dashboards/bioetl-incident-v1.json",)
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
