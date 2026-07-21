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

    result = vlo.check_prometheus_health("http://prom.example", 1.0)

    assert result.status == "pass"
    assert result.details is not None
    assert result.details["url"] == "http://prom.example/-/healthy"
    assert "Healthy" in result.details["response"]


def test_check_prometheus_health_unexpected_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        vlo,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(b"NotReady"),
    )

    result = vlo.check_prometheus_health("http://prom.example", 1.0)

    assert result.status == "fail"
    assert result.details is not None
    assert result.details["response"] == "NotReady"


def test_check_prometheus_health_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: object, **kwargs: object) -> object:
        raise HTTPError(
            "http://prom.example/-/healthy", 503, "down", hdrs=None, fp=None
        )

    monkeypatch.setattr(vlo, "urlopen", _raise)

    result = vlo.check_prometheus_health("http://prom.example", 1.0)

    assert result.status == "fail"
    assert result.details is not None
    assert result.details["url"] == "http://prom.example/-/healthy"
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

    bad = vlo.check_prometheus_targets("http://prom.example", 1.0)
    assert bad.status == "fail"
    assert bad.details is not None
    assert bad.details["api_response"]["status"] == "error"

    partial = vlo.check_prometheus_targets("http://prom.example", 1.0)
    assert partial.status == "partial"
    assert partial.details is not None
    assert partial.details["up_targets"] == 1
    assert partial.details["down_targets"] == 1
    assert partial.details["down_targets_details"][0]["last_error"] == (
        "connection refused"
    )


def test_check_grafana_datasources_http_auth_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*args: object, **kwargs: object) -> object:
        raise HTTPError(
            "http://grafana.example/api/datasources",
            401,
            "unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(vlo, "_fetch_json", _raise)

    result = vlo.check_grafana_datasources(
        "http://grafana.example", "admin", "bad", 1.0
    )

    assert result.status == "fail"
    assert result.details is not None
    assert result.details["code"] == 401


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
