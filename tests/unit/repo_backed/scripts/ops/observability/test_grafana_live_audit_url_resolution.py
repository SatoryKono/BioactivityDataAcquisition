"""Repo-backed Grafana live-audit URL resolution tests."""

from pathlib import Path
from typing import Any

import pytest

from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject


pytestmark = pytest.mark.repo_backed


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

    expected_timeout = config.request_timeout_seconds

    def fake_fetch_json_with_optional_auth(
        url: str, *, config: object, timeout_seconds: float
    ) -> object:
        _ = config
        assert timeout_seconds == expected_timeout
        if url == "http://0.0.0.0:8081/health/live":
            return {"status": "ok"}
        raise OSError(url)

    # Probe path uses _fetch_json_with_optional_auth, not bare _fetch_json.
    monkeypatch.setattr(
        audit_subject,
        "_fetch_json_with_optional_auth",
        fake_fetch_json_with_optional_auth,
    )
    assert "http://0.0.0.0:8081" in audit_subject._candidate_app_base_urls(config)
    assert audit_subject._resolve_app_base_url(config) == "http://0.0.0.0:8081"
