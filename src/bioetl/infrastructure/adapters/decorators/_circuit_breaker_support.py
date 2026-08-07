"""Private support helpers for CircuitBreakerDataSourceDecorator."""

from __future__ import annotations

import time
from typing import Any, cast

from bioetl.domain.exceptions import CircuitBreakerOpenError
from bioetl.domain.ports import CircuitBreakerPort, LoggerPort
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.circuit_breaker_contract import (
    CircuitBreakerSnapshot,
    evaluate_attempt,
)


def _recovery_timeout(circuit_breaker: CircuitBreakerPort) -> float:
    """Resolve recovery timeout from public getter or legacy attribute."""
    recovery_timeout_getter = getattr(circuit_breaker, "get_recovery_timeout", None)
    if callable(recovery_timeout_getter):
        return float(cast(Any, recovery_timeout_getter()))  # Any: legacy breaker duck type
    return float(
        cast(
            Any,  # Any: legacy breaker attribute
            getattr(circuit_breaker, "recovery_timeout", 60.0),
        )
    )


def _as_positive_timestamp(value: object) -> float | None:
    """Return a positive epoch timestamp or None."""
    if isinstance(value, int | float) and not isinstance(value, bool) and value > 0:
        return float(value)
    return None


def _last_failure_time(circuit_breaker: CircuitBreakerPort) -> float | None:
    """Resolve last failure time from public getter or legacy attributes."""
    last_failure_getter = getattr(circuit_breaker, "get_last_failure_time", None)
    if callable(last_failure_getter):
        return _as_positive_timestamp(last_failure_getter())
    raw = getattr(circuit_breaker, "last_failure_time", None)
    if raw is None:
        raw = getattr(circuit_breaker, "_last_failure_time", None)
    return _as_positive_timestamp(raw)


def _snapshot_from_port(circuit_breaker: CircuitBreakerPort) -> CircuitBreakerSnapshot:
    """Build typed state snapshot from public circuit-breaker port accessors.

    Preference order:
    1. Optional public ``snapshot()`` when it returns ``CircuitBreakerSnapshot``
    2. Public port methods ``get_state`` / ``get_failure_count`` /
       ``get_recovery_timeout`` / ``get_last_failure_time``
    3. Legacy public attribute / private-field fallbacks for older mocks
    """
    snapshot_fn = getattr(circuit_breaker, "snapshot", None)
    if callable(snapshot_fn):
        maybe_snapshot = snapshot_fn()
        if isinstance(maybe_snapshot, CircuitBreakerSnapshot):
            return maybe_snapshot

    return CircuitBreakerSnapshot(
        state=circuit_breaker.get_state(),
        failure_count=circuit_breaker.get_failure_count(),
        recovery_timeout=_recovery_timeout(circuit_breaker),
        last_failure_time=_last_failure_time(circuit_breaker),
    )


def raise_if_circuit_open(
    *,
    circuit_breaker: CircuitBreakerPort,
    provider_name: str,
    logger: LoggerPort | None,
) -> None:
    """Raise the canonical open-circuit error when the guard is open."""
    snapshot = _snapshot_from_port(circuit_breaker)
    decision = evaluate_attempt(snapshot, now=time.monotonic())
    if decision.allow_request:
        return

    if logger is not None:
        logger.warning(
            "circuit_breaker_rejecting",
            provider=provider_name,
            state=snapshot.state.value,
            failure_count=snapshot.failure_count,
        )

    raise CircuitBreakerOpenError(
        provider=provider_name,
        retry_after=decision.retry_after,
    )


def log_failure_recorded(
    logger: LoggerPort | None,
    *,
    circuit_breaker: CircuitBreakerPort,
    provider_name: str,
    error: Exception,
) -> None:
    """Emit the canonical failure-recorded log when logger is configured."""
    if logger is None:
        return

    snapshot = _snapshot_from_port(circuit_breaker)
    logger.warning(
        "circuit_breaker_failure_recorded",
        provider=provider_name,
        state=snapshot.state.value,
        failure_count=snapshot.failure_count,
        error_type=type(error).__name__,
    )


def unhealthy_status_if_circuit_open(
    *,
    circuit_breaker: CircuitBreakerPort,
    provider_name: str,
    logger: LoggerPort | None,
) -> HealthStatus | None:
    """Return ``UNHEALTHY`` when open circuit should short-circuit health checks."""
    snapshot = _snapshot_from_port(circuit_breaker)
    decision = evaluate_attempt(snapshot, now=time.monotonic())
    if decision.allow_request:
        return None

    if logger is not None:
        logger.info(
            "health_check_skipped_circuit_open",
            provider=provider_name,
            failure_count=snapshot.failure_count,
        )

    return HealthStatus.UNHEALTHY


def log_manual_reset(logger: LoggerPort | None, *, provider_name: str) -> None:
    """Emit the canonical manual-reset log entry when logger is configured."""
    if logger is None:
        return

    logger.info(
        "circuit_breaker_manual_reset",
        provider=provider_name,
    )
