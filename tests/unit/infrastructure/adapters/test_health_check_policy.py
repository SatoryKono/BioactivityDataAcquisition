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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for adapter health-check policy helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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
            fallback_status=HealthStatus.DEGRADED,
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


def test_resolve_failure_health_status_degrades_connection_error() -> None:
    assert (
        resolve_failure_health_status(
            error=ConnectionError("offline"),
            fallback_status=HealthStatus.DEGRADED,
        )
        is HealthStatus.DEGRADED
    )


def test_resolve_failure_health_status_preserves_nontransient_fallback() -> None:
    request = Request("GET", "https://example.test/health")
    response = Response(status_code=404, request=request)
    error = HTTPStatusError("missing", request=request, response=response)
    assert (
        resolve_failure_health_status(
            error=error,
            fallback_status=HealthStatus.DEGRADED,
        )
        is HealthStatus.DEGRADED
    )


def test_get_consecutive_health_failures_fails_closed() -> None:
    circuit_breaker = MagicMock()
    circuit_breaker.get_failure_count.side_effect = ValueError("bad count")
    assert get_consecutive_health_failures(circuit_breaker) == 1


def test_fallback_health_status_fails_closed() -> None:
    with patch(
        "bioetl.infrastructure.adapters.http.health.assess_health_from_circuit_breaker",
        side_effect=RuntimeError("bad state"),
    ):
        assert fallback_health_status(MagicMock()) is HealthStatus.UNHEALTHY


def test_build_error_context_fails_closed() -> None:
    circuit_breaker = MagicMock()
    circuit_breaker.get_state.side_effect = KeyError("missing")
    assert build_error_context(circuit_breaker) == {
        "circuit_breaker_state": None,
        "circuit_breaker_failures": 0,
    }
