from __future__ import annotations

import pytest

from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("proved", [True, False])
def test_generation_gap_review_keeps_warning_and_requires_evidence(proved, monkeypatch):
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-incident-v1",
        panel_id=105,
        title="Checkpoint latency",
        source_kind="prometheus",
        semantic_kind="prometheus_query",
        target_ref_id="A",
    )
    monkeypatch.setattr(audit_subject, "effective_panel_specs", lambda: (spec,))
    monkeypatch.setattr(
        audit_subject,
        "_collect_empty_witnesses",
        lambda *_args, historical_reset=False: (historical_reset and proved, []),
    )
    classification, detail = audit_subject._qualify_empty_panel(
        spec, audit_subject._parse_args([]), "guarded histogram", [], "No estimate"
    )
    result = audit_subject.AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=105,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status="ok",
        classification=classification,
        detail=detail,
        query_preview="guarded histogram",
        target_ref_id="A",
    )
    gate = audit_subject.semantic_gate_evidence([result])
    assert gate["status"] == ("pass" if proved else "review_required")
    if proved:
        assert "WARN" in detail
        assert gate["panel_outcomes"][0]["decision"] == "pass_reviewed"


def test_selected_run_http_aliases_are_resolved() -> None:
    config = audit_subject._parse_args(
        ["--pipeline", "chembl_assay", "--run-id", "abc"]
    )
    rendered = audit_subject._substitute_dashboard_tokens(
        "?pipeline=${selected_pipeline:percentencode}&run_id=${selected_run_id:percentencode}&workflow=${workflow:csv}",
        config,
    )
    assert rendered == "?pipeline=chembl_assay&run_id=abc&workflow=All"


@pytest.mark.parametrize(
    "error_key", ("verdict", "run_verdict", "replay_readiness_now")
)
def test_query_error_is_not_successful_nonempty_http_result(error_key: str) -> None:
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-overview-v2",
        panel_id=9002,
        title="Domains",
        source_kind="http",
        semantic_kind="http_endpoint",
        required=False,
    )
    payload: dict[str, object] = {
        error_key: "QUERY ERROR",
        "reason": "evidence_read_failed",
        "domains": [{"verdict": "QUERY ERROR"}],
    }
    status, classification, detail = audit_subject._classify_http_panel_payload(
        spec,
        payload,
    )
    assert (status, classification) == ("error", "endpoint_execution_error")
    assert "evidence_read_failed" in detail


def test_http_table_nested_query_error_is_not_endpoint_failure() -> None:
    """Row-level QUERY ERROR must not trip the top-level endpoint error keys."""
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-overview-v2",
        panel_id=9100,
        title="Stage funnel",
        source_kind="http",
        semantic_kind="http_table",
        required=False,
    )
    status, classification, detail = audit_subject._classify_http_panel_payload(
        spec,
        {"rows": [{"stage_id": "silver", "verdict": "QUERY ERROR"}]},
    )
    assert (status, classification) == ("ok", "nonempty_table")
    assert "rows" in detail.lower() or "table" in detail.lower()


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
