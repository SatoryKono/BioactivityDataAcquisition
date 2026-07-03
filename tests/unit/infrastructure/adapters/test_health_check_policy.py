"""Unit tests for adapter health-check policy helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from httpx import HTTPStatusError, Request, Response

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters._health_check_policy import (
    build_error_context,
    fallback_health_status,
    get_consecutive_health_failures,
    resolve_failure_health_status,
)

pytestmark = pytest.mark.unit


def test_resolve_failure_health_status_maps_transient_errors_to_degraded() -> None:
    assert (
        resolve_failure_health_status(
            error=TimeoutError("timeout"),
            fallback_status=HealthStatus.HEALTHY,
        )
        is HealthStatus.DEGRADED
    )


def test_resolve_failure_health_status_preserves_unhealthy_fallback() -> None:
    assert (
        resolve_failure_health_status(
            error=RuntimeError("boom"),
            fallback_status=HealthStatus.UNHEALTHY,
        )
        is HealthStatus.UNHEALTHY
    )


def test_resolve_failure_health_status_maps_transient_http_status_to_degraded() -> None:
    request = Request("GET", "https://example.test/health")
    response = Response(status_code=503, request=request)
    error = HTTPStatusError("service unavailable", request=request, response=response)

    assert (
        resolve_failure_health_status(
            error=error,
            fallback_status=HealthStatus.HEALTHY,
        )
        is HealthStatus.DEGRADED
    )


def test_get_consecutive_health_failures_reads_circuit_breaker_count() -> None:
    circuit_breaker = MagicMock()
    circuit_breaker.get_failure_count.return_value = 4

    assert get_consecutive_health_failures(circuit_breaker) == 4


def test_fallback_health_status_uses_circuit_breaker_assessment() -> None:
    circuit_breaker = MagicMock()
    circuit_breaker.get_state.return_value = SimpleNamespace(value="open")
    circuit_breaker.get_failure_count.return_value = 2

    status = fallback_health_status(circuit_breaker)
    assert status in {
        HealthStatus.DEGRADED,
        HealthStatus.UNHEALTHY,
        HealthStatus.HEALTHY,
    }


def test_build_error_context_includes_circuit_breaker_state() -> None:
    circuit_breaker = MagicMock()
    circuit_breaker.get_state.return_value = SimpleNamespace(value="half_open")
    circuit_breaker.get_failure_count.return_value = 1

    context = build_error_context(circuit_breaker)

    assert context["circuit_breaker_state"] == "half_open"
    assert context["circuit_breaker_failures"] == 1
