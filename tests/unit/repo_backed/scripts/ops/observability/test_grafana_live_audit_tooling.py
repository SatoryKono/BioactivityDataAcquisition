# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from scripts.ops import __main__ as ops_router
from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject
from tests.helpers import assert_router_python_command

pytestmark = pytest.mark.repo_backed


def test_live_audit_router_exposes_command() -> None:
    assert_router_python_command(
        ops_router,
        "audit-live-grafana",
        expected_target="observability/grafana/audit_live_grafana_panels.py",
    )


def test_live_audit_reviewed_specs_cover_semantically_sensitive_panels() -> None:
    covered = {
        (spec.dashboard_uid, spec.panel_id): spec.title
        for spec in audit_subject.REVIEWED_PANEL_SPECS
    }

    assert (
        covered[("bioetl-control-plane-v1", 132)]
        == "Monitor: Manifest Write Failure Ratio"
    )
    assert (
        covered[("bioetl-control-plane-v1", 133)]
        == "Monitor: Ledger Append Failure Ratio"
    )
    assert (
        covered[("bioetl-control-plane-v1", 892)]
        == "Monitor: Checkpoint Freshness Lag (seconds)"
    )
    assert covered[("bioetl-control-plane-v1", 9402)] == "ID"
    assert covered[("bioetl-control-plane-v1", 9403)] == "Processed Records"
    assert covered[("bioetl-dq-v2", 101)] == "Review: Latest Successful Data Timestamp"
    assert covered[("bioetl-dq-v2", 8)] == (
        "Time Range · Worst Freshness Age (hours; SLA 24/72)"
    )
    assert covered[("bioetl-dq-v2", 9402)] == "ID"
    assert covered[("bioetl-dq-v2", 9403)] == "Processed Records"
    assert ("bioetl-silver-reject-explorer", 3) not in covered
    assert covered[("bioetl-overview-v2", 9301)] == "Processed Records"
    assert covered[("bioetl-runtime", 9403)] == "Processed Records"
    assert covered[("bioetl-provider-health-v2", 9403)] == "Processed Records"
    assert ("bioetl-workflow-overview", 9403) not in covered


def test_live_audit_classifies_prometheus_zero_and_nonzero_results() -> None:
    zero_payload = {
        "status": "success",
        "data": {"resultType": "vector", "result": [{"value": [1, "0"]}]},
    }
    nonzero_payload = {
        "status": "success",
        "data": {"resultType": "scalar", "result": [1, "5"]},
    }

    assert audit_subject._classify_prometheus_payload(zero_payload)[0] == "zero_result"
    assert (
        audit_subject._classify_prometheus_payload(nonzero_payload)[0]
        == "nonzero_result"
    )


@pytest.mark.parametrize(
    ("panel_id", "title", "expr"),
    [
        (
            8,
            "Time Range · Worst Freshness Age (hours; SLA 24/72)",
            "(max(clamp_min(time() - max_over_time(bioetl_data_freshness_seconds"
            '{pipeline=~"$pipeline"}[$__range]), 0))) / 3600',
        ),
        (
            101,
            "Review: Latest Successful Data Timestamp",
            "max(max_over_time(bioetl_data_freshness_seconds"
            '{pipeline=~"$pipeline"}[$__range])) * 1000',
        ),
    ],
)
def test_live_audit_treats_missing_freshness_as_explicit_telemetry_gap(
    monkeypatch: Any,
    panel_id: int,
    title: str,
    expr: str,
) -> None:
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-dq-v2",
        panel_id=panel_id,
        title=title,
        source_kind="prometheus",
        semantic_kind="freshness",
    )
    panel = {"targets": [{"expr": expr}]}
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="smoke",
        pipeline="chembl_activity",
        run_type="incremental",
        run_id="audit-run",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )
    monkeypatch.setattr(
        audit_subject,
        "_fetch_json",
        lambda *_args, **_kwargs: {
            "status": "success",
            "data": {"resultType": "vector", "result": []},
        },
    )

    result = audit_subject._audit_prometheus_panel(spec, panel, config)

    assert result.status == "ok"
    assert result.classification == "telemetry_missing"
    assert "UNKNOWN" in result.detail


def test_live_audit_default_timeout_covers_bounded_loki_range_queries() -> None:
    assert audit_subject.DEFAULT_REQUEST_TIMEOUT_SECONDS == 15.0
    assert audit_subject.MAX_LOKI_RANGE_HOURS == 1


def test_live_audit_treats_checkpoint_freshness_unknown_as_valid_unknown_state(
    monkeypatch: Any,
) -> None:
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-control-plane-v1",
        panel_id=892,
        title="Monitor: Checkpoint Freshness Lag (seconds)",
        source_kind="http",
        semantic_kind="freshness",
    )
    panel = {
        "targets": [
            {"url": "/ops/control-plane/checkpoint-freshness?pipeline=${pipeline}"}
        ]
    }
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="All",
        pipeline="chembl_target",
        run_type="incremental",
        run_id="-",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    monkeypatch.setattr(
        audit_subject,
        "_fetch_json",
        lambda *_args, **_kwargs: {"status": "UNKNOWN", "age_seconds": None},
    )

    result = audit_subject._audit_http_panel(
        spec,
        panel,
        config,
        app_base_url="http://localhost:8081",
    )

    assert result.classification == "unknown_result"
    assert result.status == "ok"


def test_live_audit_classifies_http_zero_state_and_nonzero() -> None:
    zero_payload = {"total": 0, "bronze_records": 0, "reject_ratio": 0.0}
    nonzero_payload = {"total": 2, "bronze_records": 10, "reject_ratio": 0.2}

    assert (
        audit_subject._classify_http_payload(zero_payload)[0]
        == "zero_state_unknown_denominator"
    )
    assert audit_subject._classify_http_payload(nonzero_payload)[0] == "nonzero_result"


def test_semantic_gate_maps_unknown_denominator_to_review_required(
    monkeypatch: Any,
) -> None:
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-silver-reject-explorer",
        panel_id=3,
        title="Track Reject Rate vs Bronze",
        source_kind="http",
        semantic_kind="http_summary",
        target_ref_id="A",
    )
    result = audit_subject.AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status="ok",
        classification="zero_state_unknown_denominator",
        detail="fixture",
        query_preview="fixture",
        target_ref_id=spec.target_ref_id,
    )
    monkeypatch.setattr(audit_subject, "effective_panel_specs", lambda: (spec,))

    evidence = audit_subject.semantic_gate_evidence([result])

    assert evidence["status"] == "review_required"
    assert evidence["review_count"] == 1
    assert evidence["panel_outcomes"][0]["canonical_classification"] == (
        "unknown_result"
    )
    assert evidence["panel_outcomes"][0]["decision"] == "review"


def test_semantic_gate_treats_unregistered_classification_as_review_required(
    monkeypatch: Any,
) -> None:
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-runtime",
        panel_id=250,
        title="Inspect Warning Logs",
        source_kind="loki",
        semantic_kind="loki_query",
        target_ref_id="A",
    )
    result = audit_subject.AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status="ok",
        classification="unregistered_fixture_state",
        detail="fixture",
        query_preview="fixture",
        target_ref_id=spec.target_ref_id,
    )
    monkeypatch.setattr(audit_subject, "effective_panel_specs", lambda: (spec,))

    evidence = audit_subject.semantic_gate_evidence([result])

    assert evidence["status"] == "review_required"
    assert evidence["review_count"] == 1
    assert evidence["unregistered_classification_policy"] == "review_required"
    assert evidence["panel_outcomes"][0]["decision"] == "review"


def test_live_audit_classifies_http_freshness_zero_and_empty() -> None:
    zero_payload = {"status": "OK", "age_seconds": 0.0}
    empty_payload = {"status": "UNKNOWN", "age_seconds": None}

    assert (
        audit_subject._classify_http_freshness_payload(zero_payload)[0] == "zero_result"
    )
    assert (
        audit_subject._classify_http_freshness_payload(empty_payload)[0]
        == "unknown_result"
    )


def test_live_audit_parse_args_uses_grafana_env_defaults(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setenv("GRAFANA_BASE_URL", "http://grafana.local:3000")
    monkeypatch.setenv("GRAFANA_USERNAME", "viewer")
    monkeypatch.setenv("GRAFANA_PASSWORD", "secret")

    config = audit_subject._parse_args(
        [
            "--workflow",
            "chembl_target",
            "--run-id",
            "run-123",
            "--output",
            str(tmp_path / "audit.json"),
        ]
    )

    assert config.app_base_url == "http://localhost:8081"
    assert config.loki_base_url == "http://localhost:3100"
    assert config.tempo_base_url == "http://localhost:3200"
    assert config.grafana_base_url == "http://grafana.local:3000"
    assert config.grafana_username == "viewer"
    assert config.grafana_password == "secret"
    assert config.workflow == "chembl_target"
    assert config.run_id == "run-123"


def test_live_audit_substitutes_workflow_and_run_id_tokens() -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    rendered = audit_subject._substitute_dashboard_tokens(
        "/ops/control-plane/identity-table?workflow=${workflow}&pipeline=${pipeline}"
        "&run_type=${run_type:csv}&run_id=${run_id}",
        config,
    )

    assert "workflow=chembl_target" in rendered
    assert "pipeline=chembl_target" in rendered
    assert "run_type=backfill" in rendered
    assert "run_id=run-123" in rendered


def test_live_audit_substitutes_grafana_rate_interval() -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    rendered = audit_subject._substitute_dashboard_tokens(
        "rate(metric_bucket[$__rate_interval]) "
        "or rate(metric_bucket[${__rate_interval}])",
        config,
    )

    assert "$__rate_interval" not in rendered
    assert "${__rate_interval}" not in rendered
    assert rendered == "rate(metric_bucket[5m]) or rate(metric_bucket[5m])"


def test_live_audit_substitutes_hidden_workflow_context_tokens() -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    rendered = audit_subject._substitute_dashboard_tokens(
        'metric{pipeline=~"$pipeline_context",run_type=~"$run_type_context",'
        'provider=~"$provider_hint",step_kind=~"$step_kind",status=~"$step_status"}',
        config,
    )

    assert "$pipeline_context" not in rendered
    assert "$run_type_context" not in rendered
    assert "$provider_hint" not in rendered
    assert "$step_kind" not in rendered
    assert "$step_status" not in rendered
    assert 'pipeline=~"chembl_target"' in rendered
    assert 'run_type=~"backfill"' in rendered
    assert 'provider=~"chembl"' in rendered
    assert 'step_kind=~".*"' in rendered
    assert 'status=~".*"' in rendered


def test_live_audit_scopes_silver_reject_explorer_to_target_run_id() -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    rendered = audit_subject._substitute_dashboard_tokens(
        "/ops/quarantine/filtered-stats?pipeline=${pipeline}"
        "&run_id=${quarantine_run_id}&from=${__from:date:iso}",
        config,
    )

    assert "run_id=run-123" in rendered
    assert "${quarantine_run_id}" not in rendered


def test_live_audit_classifies_empty_filtered_records_by_row_count() -> None:
    classification, detail = audit_subject._classify_http_records_payload(
        {"items": [], "total": 0, "limit": 50, "offset": 0}
    )

    assert classification == "zero_result"
    assert "zero rows" in detail


def test_live_audit_classifies_nonempty_filtered_records_by_row_count() -> None:
    classification, detail = audit_subject._classify_http_records_payload(
        {"items": [{"payload_hash": "abc"}], "total": 1, "limit": 50, "offset": 0}
    )

    assert classification == "nonempty_result"
    assert "returned rows" in detail


def test_live_audit_rejects_filtered_records_total_items_drift() -> None:
    classification, detail = audit_subject._classify_http_records_payload(
        {"items": [], "total": 1, "limit": 50, "offset": 0}
    )

    assert classification == "invalid_shape"
    assert "disagree" in detail


def test_live_audit_loki_panel_uses_query_range(monkeypatch: Any) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="",
        grafana_password="",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-runtime",
        panel_id=250,
        title="Inspect Warning Logs",
        source_kind="loki",
        semantic_kind="loki_query",
        target_ref_id="A",
        required=False,
    )
    panel = {
        "targets": [
            {
                "refId": "A",
                "expr": 'count_over_time({job="bioetl"}[$__range])',
            }
        ]
    }
    captured: dict[str, str] = {}
    readiness_responses = iter(("starting", "ready"))
    readiness_calls: list[str] = []
    readiness_sleeps: list[float] = []

    def fake_fetch_text(url: str, *, timeout_seconds: float) -> str:
        assert url == "http://localhost:3100/ready"
        assert 0 < timeout_seconds <= 2.0
        readiness_calls.append(url)
        return next(readiness_responses)

    def fake_fetch_json(url: str, *, timeout_seconds: float) -> object:
        assert 0 < timeout_seconds <= config.request_timeout_seconds
        captured["url"] = url
        return {"status": "success", "data": {"result": []}}

    monkeypatch.setattr(audit_subject, "_fetch_text", fake_fetch_text)
    monkeypatch.setattr(audit_subject, "_fetch_json", fake_fetch_json)
    monkeypatch.setattr(audit_subject, "sleep", readiness_sleeps.append)

    result = audit_subject._audit_loki_panel(spec, panel, config)

    assert "/loki/api/v1/query_range?" in captured["url"]
    assert "start=" in captured["url"]
    assert "end=" in captured["url"]
    assert "limit=100" in captured["url"]
    query = parse_qs(urlparse(captured["url"]).query)
    assert query["query"] == ['count_over_time({job="bioetl"}[1h])']
    assert int(query["end"][0]) - int(query["start"][0]) == 3_600_000_000_000
    assert result.status == "ok"
    assert result.classification == "expected_empty"
    assert "endpoint=query_range" in result.detail
    assert "range_hours=1" in result.detail
    assert readiness_calls == [
        "http://localhost:3100/ready",
        "http://localhost:3100/ready",
    ]
    assert readiness_sleeps == [audit_subject.LOKI_READINESS_POLL_INTERVAL_SECONDS]


def test_live_audit_loki_instant_panel_uses_bounded_query_endpoint(
    monkeypatch: Any,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="",
        grafana_password="",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-runtime",
        panel_id=257,
        title="Inspect Top Warning Events by Event / Logger / Range",
        source_kind="loki",
        semantic_kind="loki_query",
        target_ref_id="A",
    )
    panel = {
        "targets": [
            {
                "refId": "A",
                "expr": 'count_over_time({job="bioetl"}[$__range])',
                "instant": True,
            }
        ]
    }
    captured: dict[str, str] = {}

    def fake_fetch_json(url: str, *, timeout_seconds: float) -> object:
        assert 0 < timeout_seconds <= config.request_timeout_seconds
        captured["url"] = url
        return {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [{"metric": {"event": "warning"}, "value": [1, "1"]}],
            },
        }

    monkeypatch.setattr(audit_subject, "_fetch_text", lambda *_args, **_kwargs: "ready")
    monkeypatch.setattr(audit_subject, "_fetch_json", fake_fetch_json)

    result = audit_subject._audit_loki_panel(spec, panel, config)

    assert "/loki/api/v1/query?" in captured["url"]
    assert "/query_range?" not in captured["url"]
    query = parse_qs(urlparse(captured["url"]).query)
    assert query["query"] == ['count_over_time({job="bioetl"}[1h])']
    assert "time" in query
    assert "start" not in query
    assert "end" not in query
    assert result.status == "ok"
    assert result.classification == "nonempty_result"
    assert "endpoint=query" in result.detail


@pytest.mark.parametrize("fetch_fails", [False, True])
def test_live_audit_loki_panel_fails_when_total_latency_exceeds_budget(
    monkeypatch: Any,
    fetch_fails: bool,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="",
        grafana_password="",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-runtime",
        panel_id=250,
        title="Inspect Warning Logs",
        source_kind="loki",
        semantic_kind="loki_query",
        target_ref_id="A",
    )
    panel = {"targets": [{"refId": "A", "expr": '{job="bioetl"}'}]}
    monotonic_values = iter((100.0, 100.2, 115.2))

    monkeypatch.setattr(audit_subject, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(audit_subject, "_fetch_text", lambda *_args, **_kwargs: "ready")

    def fake_fetch_json(*_args: object, **_kwargs: object) -> object:
        if fetch_fails:
            raise OSError("late transport failure")
        return {
            "status": "success",
            "data": {"resultType": "streams", "result": []},
        }

    monkeypatch.setattr(audit_subject, "_fetch_json", fake_fetch_json)

    result = audit_subject._audit_loki_panel(spec, panel, config)

    assert result.status == "error"
    assert result.classification == "timeout_budget_exceeded"
    assert "budget_seconds=15.000" in result.detail
    if fetch_fails:
        assert "last_readiness=OSError: late transport failure" in result.detail


def test_live_audit_loki_panel_fails_when_readiness_polling_exhausts_budget(
    monkeypatch: Any,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="",
        grafana_password="",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
        request_timeout_seconds=0.5,
    )
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-runtime",
        panel_id=250,
        title="Inspect Warning Logs",
        source_kind="loki",
        semantic_kind="loki_query",
        target_ref_id="A",
    )
    panel = {"targets": [{"refId": "A", "expr": '{job="bioetl"}'}]}
    monotonic_values = iter((100.0, 100.4, 100.6, 100.6))
    readiness_sleeps: list[float] = []

    monkeypatch.setattr(audit_subject, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(
        audit_subject, "_fetch_text", lambda *_args, **_kwargs: "starting"
    )
    monkeypatch.setattr(
        audit_subject,
        "_fetch_json",
        lambda *_args, **_kwargs: pytest.fail(
            "query must not run before Loki is ready"
        ),
    )
    monkeypatch.setattr(audit_subject, "sleep", readiness_sleeps.append)

    result = audit_subject._audit_loki_panel(spec, panel, config)

    assert result.status == "error"
    assert result.classification == "timeout_budget_exceeded"
    assert "readiness polling" in result.detail
    assert "last_readiness=unexpected /ready response" in result.detail
    assert readiness_sleeps == [pytest.approx(0.1)]


def test_live_audit_loki_fixtures_execute_positive_and_empty_paths(
    monkeypatch: Any,
) -> None:
    fixture_path = Path("tests/fixtures/grafana/loki_runtime_panel_events.jsonl")
    fixtures = {
        item["kind"]: item
        for item in (
            json.loads(line)
            for line in fixture_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="",
        grafana_password="",
        workflow="chembl_activity",
        pipeline="chembl_activity",
        run_type="backfill",
        run_id="fixture-run",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )
    monkeypatch.setattr(audit_subject, "_fetch_text", lambda *_args, **_kwargs: "ready")

    # Shipped runtime Loki panels were removed; drive audit path via synthetic
    # panel targets so fixture payloads remain exerciseable.
    synthetic_panel = {
        "targets": [
            {
                "refId": "A",
                "expr": '{job="bioetl"} | json',
            }
        ]
    }
    positive_cases = (("warning", 250), ("warning", 257), ("malformed", 251))
    for kind, panel_id in positive_cases:
        spec = audit_subject.PanelAuditSpec(
            dashboard_uid="bioetl-runtime",
            panel_id=panel_id,
            title=f"fixture-panel-{panel_id}",
            source_kind="loki",
            semantic_kind="loki_query",
            target_ref_id="A",
            required=False,
        )
        panel_result = fixtures[kind]["panel_results"][str(panel_id)]
        monkeypatch.setattr(
            audit_subject,
            "_fetch_json",
            lambda *_args, _panel_result=panel_result, **_kwargs: {
                "status": "success",
                "data": _panel_result,
            },
        )

        result = audit_subject._audit_loki_panel(spec, synthetic_panel, config)

        assert result.status == "ok"
        assert result.classification == "nonempty_result"

    for panel_id in fixtures["empty"]["expected_panel_ids"]:
        spec = audit_subject.PanelAuditSpec(
            dashboard_uid="bioetl-runtime",
            panel_id=panel_id,
            title=f"fixture-panel-{panel_id}",
            source_kind="loki",
            semantic_kind="loki_query",
            target_ref_id="A",
            required=False,
        )
        panel_result = fixtures["empty"]["panel_results"][str(panel_id)]
        monkeypatch.setattr(
            audit_subject,
            "_fetch_json",
            lambda *_args, _panel_result=panel_result, **_kwargs: {
                "status": "success",
                "data": _panel_result,
            },
        )

        result = audit_subject._audit_loki_panel(spec, synthetic_panel, config)

        assert result.status == "ok"
        assert result.classification == "expected_empty"


def test_live_audit_effective_specs_include_generated_loki_and_tempo_coverage() -> None:
    specs = audit_subject.effective_panel_specs()
    source_kinds = {spec.source_kind for spec in specs}

    # Discovery always covers Prometheus/HTTP. Loki/Tempo appear only when the
    # shipped dashboard JSON still contains those datasources.
    assert {"prometheus", "http"}.issubset(source_kinds)
    assert len(specs) >= len(audit_subject.REVIEWED_PANEL_SPECS)
    assert not any(
        spec.dashboard_uid == "bioetl-runtime" and spec.source_kind == "loki"
        for spec in specs
    )


def test_live_audit_requires_curated_runtime_loki_panels() -> None:
    required_loki_panel_ids = {
        spec.panel_id
        for spec in audit_subject.effective_panel_specs()
        if spec.dashboard_uid == "bioetl-runtime"
        and spec.source_kind == "loki"
        and spec.required
    }

    # Runtime Loki log-hygiene panels were removed from the shipped dashboard.
    assert required_loki_panel_ids == set()


def test_live_audit_required_reviewed_specs_use_concrete_target_refs() -> None:
    missing_refs = [
        f"{spec.dashboard_uid}#{spec.panel_id}"
        for spec in audit_subject.effective_panel_specs()
        if spec.required
        and spec.source_kind in {"http", "prometheus"}
        and not spec.target_ref_id
    ]

    assert missing_refs == []


def test_dashboard_json_has_no_backup_artifacts_in_active_dashboard_tree() -> None:
    backup_files = sorted(Path("grafana/dashboards").glob("*.backup"))

    assert backup_files == []


def test_alerts_slo_dashboard_is_first_class_shipped_surface() -> None:
    dashboard_path = Path("grafana/dashboards/bioetl-alerts-slo.json")
    if not dashboard_path.is_file():
        pytest.skip("bioetl-alerts-slo.json retired from shipping surface (epic #6647)")
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    variables = {
        item.get("name") for item in dashboard.get("templating", {}).get("list", [])
    }

    assert dashboard["uid"] == "bioetl-alerts-slo"
    assert dashboard["title"] == "6. Alerts & SLO"
    assert {"workflow", "pipeline", "run_type"}.issubset(variables)
    assert "run_id" not in variables
    assert "ALERTS" in json.dumps(dashboard)


def test_silver_reject_explorer_keeps_shared_shell_context_outside_forensic_scope() -> (
    None
):
    dashboard_path = Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    if not dashboard_path.exists():
        pytest.skip("Silver Reject Explorer removed 2026-07-23")
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    variables = {
        item.get("name") for item in dashboard.get("templating", {}).get("list", [])
    }
    serialized = json.dumps(dashboard)

    assert {"pipeline", "run_type"}.issubset(variables)
    assert "workflow" not in variables
    assert "run_id" not in variables
    assert "var-workflow=$workflow" not in serialized
    assert "var-run_id=$run_id" not in serialized
    assert "var-quarantine_run_id=$run_id" not in serialized
    assert "quarantine_run_id remains the forensic row filter" in serialized


def test_silver_reject_explorer_generic_links_do_not_receive_primary_run_context() -> (
    None
):
    for path in Path("grafana/dashboards").glob("*.json"):
        if path.name == "bioetl-silver-reject-explorer.json":
            continue
        dashboard = json.loads(path.read_text(encoding="utf-8"))

        def walk(value: object) -> None:
            if isinstance(value, dict):
                for key, nested in value.items():
                    if key == "uid":
                        continue
                    walk(nested)
                return
            if isinstance(value, list):
                for nested in value:
                    walk(nested)
                return
            if not isinstance(value, str):
                return
            if "bioetl-silver-reject-explorer" not in value or not value.startswith(
                "/d/"
            ):
                return
            assert "var-pipeline=" in value
            assert "var-run_type=" in value
            assert "var-workflow=" not in value
            assert "var-run_id=" not in value
            assert "var-quarantine_run_id=$run_id" not in value

        walk(dashboard)


def test_runtime_log_hygiene_trend_uses_aggregated_loki_range_queries() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-runtime.json").read_text(encoding="utf-8")
    )

    def walk_panels(panels: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for panel in panels:
            result.append(panel)
            nested = panel.get("panels")
            if isinstance(nested, list):
                result.extend(walk_panels(nested))
        return result

    panel = next(
        (item for item in walk_panels(dashboard["panels"]) if item.get("id") == 258),
        None,
    )
    if panel is None:
        pytest.skip(
            "Runtime Loki log-hygiene trend panel (id=258) removed from shipped dashboard"
        )
    expressions = {target["refId"]: target["expr"] for target in panel["targets"]}

    assert expressions["A"].startswith("sum(count_over_time(")
    assert expressions["B"].startswith("sum(count_over_time(")
    assert "No data means" in panel["description"]


def test_prometheus_dashboard_panels_do_not_filter_on_run_id_labels() -> None:
    for path in Path("grafana/dashboards").glob("*.json"):
        dashboard = json.loads(path.read_text(encoding="utf-8"))

        def walk_panels(panels: list[dict[str, Any]]) -> list[dict[str, Any]]:
            result: list[dict[str, Any]] = []
            for panel in panels:
                result.append(panel)
                nested = panel.get("panels")
                if isinstance(nested, list):
                    result.extend(walk_panels(nested))
            return result

        for panel in walk_panels(dashboard.get("panels", [])):
            for target in panel.get("targets", []) or []:
                expr = target.get("expr")
                if not isinstance(expr, str):
                    continue
                assert "run_id" not in expr, (
                    f"{path}:{panel.get('id')} must keep run_id out of "
                    "Prometheus/LogQL metric labels"
                )


def test_run_id_independent_metric_panels_disclose_scope() -> None:
    scope_terms = (
        "selected-range",
        "global",
        "current",
        "range",
        "not filtered",
        "workflow",
        "provider",
        "pipeline",
        "status",
        "alert",
        "slo",
        "freshness",
        "scope",
        "selected",
    )
    missing_scope: list[str] = []
    for path in Path("grafana/dashboards").glob("*.json"):
        dashboard = json.loads(path.read_text(encoding="utf-8"))

        def walk_panels(panels: list[dict[str, Any]]) -> list[dict[str, Any]]:
            result: list[dict[str, Any]] = []
            for panel in panels:
                result.append(panel)
                nested = panel.get("panels")
                if isinstance(nested, list):
                    result.extend(walk_panels(nested))
            return result

        for panel in walk_panels(dashboard.get("panels", [])):
            for target in panel.get("targets", []) or []:
                expr = target.get("expr")
                if not isinstance(expr, str) or not expr.strip():
                    continue
                text = (
                    f"{panel.get('title', '')} {panel.get('description', '')}".lower()
                )
                if not any(term in text for term in scope_terms):
                    missing_scope.append(
                        f"{path}:{panel.get('id')}:{panel.get('title')}"
                    )

    assert missing_scope == []


def test_workflow_status_titles_make_selected_range_scope_visible() -> None:
    dashboard_path = Path("grafana/dashboards/bioetl-workflow-overview.json")
    if not dashboard_path.is_file():
        pytest.skip(
            "bioetl-workflow-overview.json retired from shipping surface (epic #6647)"
        )
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    titles = {panel.get("id"): panel.get("title") for panel in dashboard["panels"]}

    assert titles[9401] == "Status"
    assert titles[9404] == "Pipeline Status"


def test_live_audit_isolates_non_required_panel_execution_failures(
    monkeypatch: Any,
) -> None:
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-runtime",
        panel_id=250,
        title="Inspect Warning Logs",
        source_kind="loki",
        semantic_kind="loki_query",
        target_ref_id="A",
        required=False,
    )
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    monkeypatch.setattr(audit_subject, "effective_panel_specs", lambda: (spec,))
    monkeypatch.setattr(audit_subject, "_find_panel", lambda _spec: {})
    monkeypatch.setattr(
        audit_subject,
        "_audit_loki_panel",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("timed out")),
    )

    results = audit_subject.run_audit(config)

    assert len(results) == 1
    assert results[0].status == "ok"
    assert results[0].classification == "blocked_unavailable"


def test_live_audit_normalizes_docker_gateway_to_localhost() -> None:
    assert (
        audit_subject._normalize_host_access_url("http://host.docker.internal:8081")
        == "http://localhost:8081"
    )


def test_live_audit_adds_zero_bind_fallback_for_localhost() -> None:
    assert (
        audit_subject._zero_bind_access_url("http://localhost:8081")
        == "http://0.0.0.0:8081"
    )
    assert (
        audit_subject._zero_bind_access_url("http://127.0.0.1:8081")
        == "http://0.0.0.0:8081"
    )
    assert audit_subject._zero_bind_access_url("http://example.test:8081") is None


def test_live_audit_resolves_http_backend_from_datasource_candidates(
    monkeypatch: Any,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="All",
        pipeline="chembl_target",
        run_type="incremental",
        run_id="-",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    monkeypatch.setattr(
        audit_subject,
        "_discover_http_datasource_url",
        lambda *_args, **_kwargs: "http://host.docker.internal:8081",
    )

    def fake_fetch_json(url: str, *, timeout_seconds: float) -> object:
        assert timeout_seconds == config.request_timeout_seconds
        if url == "http://localhost:8081/health/live":
            return {"status": "ok"}
        raise OSError(url)

    monkeypatch.setattr(audit_subject, "_fetch_json", fake_fetch_json)

    assert audit_subject._resolve_app_base_url(config) == "http://localhost:8081"


def test_live_audit_resolves_http_backend_through_grafana_datasource_proxy(
    monkeypatch: Any,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="All",
        pipeline="chembl_target",
        run_type="incremental",
        run_id="-",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        audit_subject,
        "_discover_http_datasource_url",
        lambda *_args, **_kwargs: None,
    )

    def fake_request_json(
        url: str, *, auth_header: str, timeout_seconds: float
    ) -> object:
        captured["url"] = url
        captured["auth_header"] = auth_header
        assert timeout_seconds == config.request_timeout_seconds
        return {"status": "ok"}

    def fake_fetch_json(url: str, *, timeout_seconds: float) -> object:
        raise OSError(url)

    monkeypatch.setattr(audit_subject, "_request_json", fake_request_json)
    monkeypatch.setattr(audit_subject, "_fetch_json", fake_fetch_json)

    assert (
        audit_subject._resolve_app_base_url(config)
        == "http://localhost:3000/api/datasources/proxy/uid/quarantine-explorer"
    )
    assert captured["url"].endswith(
        "/api/datasources/proxy/uid/quarantine-explorer/health/live"
    )
    assert captured["auth_header"].startswith("Basic ")


def test_live_audit_strips_userinfo_before_authenticated_proxy_request(
    monkeypatch: Any,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://admin:changeme@localhost:3000/api/datasources/proxy/uid/quarantine-explorer",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="ignored",
        grafana_password="ignored",
        workflow="All",
        pipeline="chembl_target",
        run_type="incremental",
        run_id="-",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )
    captured: dict[str, str] = {}

    def fake_request_json(
        url: str, *, auth_header: str, timeout_seconds: float
    ) -> object:
        captured["url"] = url
        captured["auth_header"] = auth_header
        return {"status": "ok"}

    monkeypatch.setattr(audit_subject, "_request_json", fake_request_json)

    payload = audit_subject._fetch_json_with_optional_auth(
        f"{config.app_base_url}/health/live",
        config=config,
        timeout_seconds=5,
    )

    assert payload == {"status": "ok"}
    assert captured["url"] == (
        "http://localhost:3000/api/datasources/proxy/uid/"
        "quarantine-explorer/health/live"
    )
    assert captured["auth_header"].startswith("Basic ")


def test_live_audit_resolves_zero_bind_backend_when_localhost_is_unreachable(
    monkeypatch: Any,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="All",
        pipeline="chembl_target",
        run_type="incremental",
        run_id="-",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    monkeypatch.setattr(
        audit_subject,
        "_discover_http_datasource_url",
        lambda *_args, **_kwargs: None,
    )

    def fake_fetch_json(url: str, *, timeout_seconds: float) -> object:
        assert timeout_seconds == config.request_timeout_seconds
        if url == "http://0.0.0.0:8081/health/live":
            return {"status": "ok"}
        raise OSError(url)

    monkeypatch.setattr(audit_subject, "_fetch_json", fake_fetch_json)
    monkeypatch.setattr(
        audit_subject,
        "_request_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("proxy down")),
    )

    assert audit_subject._resolve_app_base_url(config) == "http://0.0.0.0:8081"
