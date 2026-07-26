"""Coverage tranche tests for preflight observability helpers (#6480)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from types import SimpleNamespace

from bioetl.application.core.preflight._observability import (
    emit_preflight_health_results,
)
from bioetl.domain.types import HealthStatus


class _Observer:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def emit_health_check_result(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


def test_emit_preflight_health_results_noop_for_missing_report() -> None:
    host = SimpleNamespace(_runtime=SimpleNamespace(), _observer=_Observer())
    emit_preflight_health_results(host, None, runner_stage="preflight")
    assert host._observer.calls == []


def test_emit_preflight_health_results_forwards_component_results() -> None:
    observer = _Observer()
    host = SimpleNamespace(
        _runtime=SimpleNamespace(health_check_mode="lenient"),
        _observer=observer,
    )
    result = SimpleNamespace(
        component="chembl",
        status=HealthStatus.UNHEALTHY,
        duration_seconds=0.25,
        provider="chembl",
        latency_ms=12.5,
        probe_fallback_reason="timeout",
    )
    report = SimpleNamespace(results=[result])
    emit_preflight_health_results(host, report, runner_stage="preflight")
    assert len(observer.calls) == 1
    call = observer.calls[0]
    assert call["component"] == "chembl"
    assert call["healthy"] is False
    assert call["duration_ms"] == 250.0
    assert call["health_check_mode"] == "lenient"
    assert call["runner_stage"] == "preflight"
    assert call["health_status"] == HealthStatus.UNHEALTHY.value


def test_emit_preflight_health_results_defaults_health_check_mode() -> None:
    observer = _Observer()
    host = SimpleNamespace(_runtime=SimpleNamespace(), _observer=observer)
    result = SimpleNamespace(
        component="local",
        status=HealthStatus.HEALTHY,
        duration_seconds=0.1,
        provider="local",
        latency_ms=1.0,
        probe_fallback_reason=None,
    )
    emit_preflight_health_results(
        host,
        SimpleNamespace(results=[result]),
        runner_stage="startup",
    )
    assert observer.calls[0]["healthy"] is True
    assert observer.calls[0]["health_check_mode"] == "strict"
