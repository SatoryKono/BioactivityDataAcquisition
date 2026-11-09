"""Regression coverage for selected-run tokens and endpoint error semantics."""

import pytest

from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject


pytestmark = pytest.mark.repo_backed


def test_selected_run_http_aliases_are_resolved() -> None:
    config = audit_subject._parse_args(
        ["--pipeline", "chembl_assay", "--run-id", "abc"]
    )
    rendered = audit_subject._substitute_dashboard_tokens(
        "?pipeline=${selected_pipeline:percentencode}&run_id=${selected_run_id:percentencode}&workflow=${workflow:csv}",
        config,
    )
    assert rendered == "?pipeline=chembl_assay&run_id=abc&workflow=All"


def test_query_error_is_not_successful_nonempty_http_result() -> None:
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-overview-v2",
        panel_id=9002,
        title="Domains",
        source_kind="http",
        semantic_kind="http_endpoint",
        required=False,
    )
    status, classification, detail = audit_subject._classify_http_panel_payload(
        spec,
        {
            "verdict": "QUERY ERROR",
            "reason": "evidence_read_failed",
            "domains": [{"verdict": "QUERY ERROR"}],
        },
    )
    assert (status, classification) == ("error", "endpoint_execution_error")
    assert "evidence_read_failed" in detail


def test_all_regex_scope_keeps_http_catalog_value() -> None:
    config = audit_subject._parse_args([])
    assert (
        audit_subject._substitute_dashboard_tokens("${workflow:regex}", config) == ".*"
    )
    assert (
        audit_subject._substitute_dashboard_tokens("${workflow:csv}", config) == "All"
    )
    for token in ("$workflow", "${workflow}"):
        assert (
            audit_subject._substitute_dashboard_tokens(token, config, prometheus=True)
            == ".*"
        )
        assert audit_subject._substitute_dashboard_tokens(token, config) == "All"
