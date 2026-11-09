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
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject

pytestmark = pytest.mark.repo_backed


def test_live_audit_resolves_http_backend_from_datasource_candidates(
    monkeypatch: Any,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8000",
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
        lambda *_args, **_kwargs: "http://host.docker.internal:8000",
    )

    def fake_fetch_json(url: str, *, timeout_seconds: float) -> object:
        assert timeout_seconds == config.request_timeout_seconds
        if url == "http://localhost:8000/health/live":
            return {"status": "ok"}
        raise OSError(url)

    monkeypatch.setattr(audit_subject, "_fetch_json", fake_fetch_json)

    assert audit_subject._resolve_app_base_url(config) == "http://localhost:8000"


def test_live_audit_resolves_http_backend_through_grafana_datasource_proxy(
    monkeypatch: Any,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8000",
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
        == "http://localhost:3000/api/datasources/proxy/uid/bioetl-ops-http"
    )
    assert captured["url"].endswith(
        "/api/datasources/proxy/uid/bioetl-ops-http/health/live"
    )
    assert captured["auth_header"].startswith("Basic ")


def test_live_audit_strips_userinfo_before_authenticated_proxy_request(
    monkeypatch: Any,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://admin:changeme@localhost:3000/api/datasources/proxy/uid/bioetl-ops-http",
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
        "http://localhost:3000/api/datasources/proxy/uid/bioetl-ops-http/health/live"
    )
    assert captured["auth_header"].startswith("Basic ")


def test_replay_status_panels_resolve_donor_and_explain_empty_values() -> None:
    specs = {
        spec.panel_id: spec
        for spec in audit_subject.effective_panel_specs()
        if spec.dashboard_uid == "bioetl-control-plane-v1"
    }
    for panel_id in (9422, 9423):
        spec = specs[panel_id]
        panel = audit_subject._find_panel(spec)
        target = audit_subject._select_target(panel, spec, field="url")
        assert target is not None
        assert target["url"].startswith("/ops/observability/selected-run-status?")
        assert panel["fieldConfig"]["defaults"]["noValue"] == (
            "UNKNOWN"
            if panel_id == 9422
            else "SELECT RUN if no Run ID is selected. QUERY ERROR if the request failed."
        )


def test_control_plane_table_contracts_are_not_processed_records() -> None:
    for panel_id, contract in (
        (9408, "control_plane_identity_evidence_v1"),
        (9406, "control_plane_identity_evidence_v1"),
        (9414, "control_plane_validation_evidence_v1"),
    ):
        spec = next(
            spec
            for spec in audit_subject.REVIEWED_PANEL_SPECS
            if spec.dashboard_uid == "bioetl-control-plane-v1"
            and spec.panel_id == panel_id
        )
        assert audit_subject._classify_http_panel_payload(
            spec,
            {
                "contract": contract,
                "resolved_via": "run_id",
                "rows": [{"status": "ok"}],
            },
        )[:2] == ("ok", "nonempty_table")


def test_replay_audit_uses_projected_frames_instead_of_donor_rows() -> None:
    from bioetl.interfaces.http._selected_run_unavailable import unavailable_status

    specs = {
        spec.panel_id: spec
        for spec in audit_subject.REVIEWED_PANEL_SPECS
        if spec.dashboard_uid == "bioetl-control-plane-v1"
        and spec.panel_id in (9422, 9423)
    }
    for spec in specs.values():
        missing = unavailable_status("chembl_activity", "-", "НЕТ ЗАПУСКОВ", "empty")
        assert missing["rows"]
        assert audit_subject._classify_http_panel_payload(spec, missing)[:2] == (
            "error",
            "no_data",
        )
        failed = unavailable_status(
            "chembl_activity", "-", "QUERY ERROR", "backend error"
        )
        assert audit_subject._classify_http_panel_payload(spec, failed)[:2] == (
            "error",
            "endpoint_execution_error",
        )

    available = {"replay_readiness": [{"verdict": "READY"}], "rows": [{"domain": "dq"}]}
    assert audit_subject._classify_http_panel_payload(specs[9422], available)[:2] == (
        "ok",
        "nonempty_table",
    )
    assert audit_subject._classify_http_panel_payload(specs[9423], available)[:2] == (
        "error",
        "no_data",
    )
    available["replay_checks"] = [{"code": "identity", "result": "unknown"}]
    assert audit_subject._classify_http_panel_payload(specs[9423], available)[:2] == (
        "error",
        "no_data",
    )
    incomplete = {
        **available,
        "replay_readiness": [{"verdict": "INSUFFICIENT"}],
    }
    for spec in specs.values():
        assert audit_subject._classify_http_panel_payload(spec, incomplete)[:2] == (
            "error",
            "no_data",
        )
    available["replay_checks"] = [{"code": "identity", "result": "pass"}]
    assert audit_subject._classify_http_panel_payload(specs[9423], available)[:2] == (
        "ok",
        "nonempty_table",
    )


@pytest.mark.parametrize("verdict", ["BLOCKED", "UNSUPPORTED"])
def test_replay_negative_verdict_is_valid_audit_evidence(verdict: str) -> None:
    spec = next(
        spec
        for spec in audit_subject.REVIEWED_PANEL_SPECS
        if spec.dashboard_uid == "bioetl-control-plane-v1" and spec.panel_id == 9422
    )
    status, classification, detail = audit_subject._classify_http_panel_payload(
        spec, {"replay_readiness": [{"verdict": verdict}]}
    )
    assert (status, classification) == ("ok", "replay_not_ready")
    result = audit_subject.AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status=status,
        classification=classification,
        detail=detail,
        query_preview="",
        target_ref_id=spec.target_ref_id,
    )
    assert audit_subject.semantic_gate_evidence([result])["status"] == "pass"
