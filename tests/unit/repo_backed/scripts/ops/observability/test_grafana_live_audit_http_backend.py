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
