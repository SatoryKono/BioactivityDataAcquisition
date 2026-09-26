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
"""Unit tests for live observability diagnostic validators."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError

import pytest

from scripts.ops.observability import validate_live_observability as vlo


pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, body: bytes, *, code: int = 200) -> None:
        self._body = body
        self.code = code

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload).encode("utf-8")


def test_check_prometheus_health_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        vlo,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(b"Prometheus is Healthy.\n"),
    )

    result = vlo.check_prometheus_health("http://prometheus:9090", 1.0)

    assert result.status == "pass"
    assert result.details is not None
    assert result.details["url"] == "http://prometheus:9090/-/healthy"
    assert "Healthy" in result.details["response"]


def test_check_prometheus_health_unexpected_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        vlo,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(b"NotReady"),
    )

    result = vlo.check_prometheus_health("http://prometheus:9090", 1.0)

    assert result.status == "fail"
    assert result.details is not None
    assert result.details["response"] == "NotReady"


def test_check_prometheus_health_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: object, **kwargs: object) -> object:
        raise HTTPError(
            "http://prometheus:9090/-/healthy", 503, "down", hdrs=None, fp=None
        )

    monkeypatch.setattr(vlo, "urlopen", _raise)

    result = vlo.check_prometheus_health("http://prometheus:9090", 1.0)

    assert result.status == "fail"
    assert result.details is not None
    assert result.details["url"] == "http://prometheus:9090/-/healthy"
    assert "error" in result.details


def test_check_prometheus_targets_malformed_and_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads = iter(
        [
            {"status": "error", "error": "boom"},
            {
                "status": "success",
                "data": {
                    "activeTargets": [
                        {
                            "health": "up",
                            "labels": {"job": "bioetl", "instance": "a"},
                        },
                        {
                            "health": "down",
                            "labels": {"job": "node", "instance": "b"},
                            "lastError": "connection refused",
                        },
                    ]
                },
            },
        ]
    )

    monkeypatch.setattr(
        vlo,
        "_fetch_json",
        lambda *args, **kwargs: next(payloads),
    )

    bad = vlo.check_prometheus_targets("http://prometheus:9090", 1.0)
    assert bad.status == "fail"
    assert bad.details is not None
    assert bad.details["api_response"]["status"] == "error"

    partial = vlo.check_prometheus_targets("http://prometheus:9090", 1.0)
    assert partial.status == "partial"
    assert partial.details is not None
    assert partial.details["up_targets"] == 1
    assert partial.details["down_targets"] == 1
    assert partial.details["down_targets_details"][0]["last_error"] == (
        "connection refused"
    )


def test_load_repo_environment_preserves_process_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, bool]] = []

    def fake_load_dotenv(*, dotenv_path: object, override: bool) -> None:
        calls.append((dotenv_path, override))
        monkeypatch.setenv("GF_SECURITY_ADMIN_PASSWORD", "from-repo-env")

    monkeypatch.delenv("GF_SECURITY_ADMIN_PASSWORD", raising=False)
    monkeypatch.setattr(vlo, "load_dotenv", fake_load_dotenv)

    vlo._load_repo_environment()

    assert calls == [(vlo.REPO_ENV_PATH, False)]
    assert vlo.resolve_grafana_password() == "from-repo-env"


def test_resolve_grafana_password_prefers_grafana_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GRAFANA_PASSWORD", "from-grafana")
    monkeypatch.setenv("GF_SECURITY_ADMIN_PASSWORD", "from-gf")
    assert vlo.resolve_grafana_password() == "from-grafana"


def test_resolve_grafana_password_falls_back_to_gf_security(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GRAFANA_PASSWORD", raising=False)
    monkeypatch.delenv("GRAFANA_ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("GF_SECURITY_ADMIN_PASSWORD", "from-gf")
    assert vlo.resolve_grafana_password() == "from-gf"


def test_resolve_grafana_password_has_no_committed_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GRAFANA_PASSWORD", raising=False)
    monkeypatch.delenv("GF_SECURITY_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("GRAFANA_ADMIN_PASSWORD", raising=False)
    assert vlo.resolve_grafana_password() == ""
    assert vlo.DEFAULT_GRAFANA_PASSWORD == ""


def test_check_grafana_datasources_fails_without_password() -> None:
    result = vlo.check_grafana_datasources("http://grafana:3000", "admin", "", 1.0)
    assert result.status == "fail"
    assert result.details is not None
    assert result.details["error"] == "missing_grafana_password"


def test_check_grafana_datasources_requires_ops_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        vlo,
        "_fetch_json",
        lambda *args, **kwargs: [
            {"name": "Prometheus", "uid": "prometheus"},
        ],
    )
    result = vlo.check_grafana_datasources(
        "http://grafana:3000", "admin", "secret", 1.0
    )
    assert result.status == "partial"
    assert result.details is not None
    assert result.details["has_prometheus"] is True
    assert result.details["has_ops_http"] is False


def test_check_grafana_datasources_passes_with_prometheus_and_ops_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        vlo,
        "_fetch_json",
        lambda *args, **kwargs: [
            {"name": "Prometheus", "uid": "prometheus"},
            {"name": "BioETL Ops HTTP", "uid": "bioetl-ops-http"},
        ],
    )
    result = vlo.check_grafana_datasources(
        "http://grafana:3000", "admin", "secret", 1.0
    )
    assert result.status == "pass"
    assert result.details is not None
    assert result.details["has_ops_http"] is True


@pytest.mark.parametrize(
    ("ops_name", "ops_uid"),
    [
        (vlo.EXPECTED_OPS_HTTP_DATASOURCE_NAME, "stale-ops-http"),
        ("Stale Ops HTTP", vlo.EXPECTED_OPS_HTTP_DATASOURCE_UID),
    ],
)
def test_check_grafana_datasources_requires_matching_ops_identity(
    monkeypatch: pytest.MonkeyPatch,
    ops_name: str,
    ops_uid: str,
) -> None:
    monkeypatch.setattr(
        vlo,
        "_fetch_json",
        lambda *args, **kwargs: [
            {"name": "Prometheus", "uid": "prometheus"},
            {"name": ops_name, "uid": ops_uid},
        ],
    )

    result = vlo.check_grafana_datasources(
        "http://grafana:3000", "admin", "secret", 1.0
    )

    assert result.status == "partial"
    assert result.details is not None
    assert result.details["has_ops_http"] is False


def test_check_grafana_datasources_http_auth_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*args: object, **kwargs: object) -> object:
        raise HTTPError(
            "http://grafana:3000/api/datasources",
            401,
            "unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(vlo, "_fetch_json", _raise)

    result = vlo.check_grafana_datasources("http://grafana:3000", "admin", "bad", 1.0)

    assert result.status == "fail"
    assert result.details is not None
    assert result.details["code"] == 401


def test_check_grafana_dashboards_fails_without_password_before_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_fetch(*args: object, **kwargs: object) -> object:
        raise AssertionError(f"unexpected Grafana request: {args}, {kwargs}")

    monkeypatch.setattr(vlo, "_fetch_json", fail_fetch)

    result = vlo.check_grafana_dashboards("http://grafana:3000", "admin", "   ", 1.0)

    assert result.status == "fail"
    assert result.details is not None
    assert result.details["error"] == "missing_grafana_password"


def test_check_grafana_dashboards_accepts_shipped_portfolio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dashboards = [{"uid": uid} for uid in sorted(vlo.EXPECTED_BIOETL_DASHBOARD_UIDS)]
    dashboards.append({"uid": "unrelated-dashboard"})
    monkeypatch.setattr(vlo, "_fetch_json", lambda *args, **kwargs: dashboards)

    result = vlo.check_grafana_dashboards("http://grafana:3000", "admin", "secret", 1.0)

    assert result.status == "pass"
    assert result.details is not None
    assert result.details["expected_bioetl_dashboards"] == 7
    assert result.details["missing_bioetl_dashboard_uids"] == []
    assert "7 shipped UIDs expected" in result.message


def test_check_grafana_dashboards_reports_missing_shipped_uid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_uid = "bioetl-run-explorer-v1"
    dashboards = [
        {"uid": uid}
        for uid in sorted(vlo.EXPECTED_BIOETL_DASHBOARD_UIDS - {missing_uid})
    ]
    monkeypatch.setattr(vlo, "_fetch_json", lambda *args, **kwargs: dashboards)

    result = vlo.check_grafana_dashboards("http://grafana:3000", "admin", "secret", 1.0)

    assert result.status == "partial"
    assert result.details is not None
    assert result.details["missing_bioetl_dashboard_uids"] == [missing_uid]


def test_validation_result_serializes_diagnostic_fields() -> None:
    result = vlo.ValidationResult(
        check_name="prometheus_health",
        status="fail",
        message="down",
        details={"url": "http://x/-/healthy", "error": "timeout"},
    )
    report = vlo.ValidationReport(
        prometheus_url="http://prom",
        grafana_url="http://grafana",
        timestamp=result.timestamp,
        results=[result],
        summary={"fail": 1},
    )
    payload = json.loads(json.dumps(vlo.asdict(report)))

    assert payload["results"][0]["details"]["url"] == "http://x/-/healthy"
    assert payload["results"][0]["details"]["error"] == "timeout"
    assert payload["summary"] == {"fail": 1}
