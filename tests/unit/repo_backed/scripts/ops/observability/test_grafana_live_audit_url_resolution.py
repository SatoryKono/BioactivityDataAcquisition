"""Repo-backed Grafana live-audit URL resolution tests."""

from pathlib import Path
from typing import Any

import pytest

from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject


pytestmark = pytest.mark.repo_backed


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
