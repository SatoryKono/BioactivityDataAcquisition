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

    recovery_timeout_getter = getattr(circuit_breaker, "get_recovery_timeout", None)
    if callable(recovery_timeout_getter):
        recovery_timeout = float(cast(Any, recovery_timeout_getter()))
    else:
        recovery_timeout = float(cast(Any, getattr(circuit_breaker, "recovery_timeout", 60.0)))

    last_failure_getter = getattr(circuit_breaker, "get_last_failure_time", None)
    if callable(last_failure_getter):
        raw_lft = last_failure_getter()
        last_failure_time = (
            float(raw_lft)
            if isinstance(raw_lft, int | float) and not isinstance(raw_lft, bool) and raw_lft > 0
            else None
        )
    else:
        raw_last_failure_time = getattr(circuit_breaker, "last_failure_time", None)
        if raw_last_failure_time is None:
            raw_last_failure_time = getattr(circuit_breaker, "_last_failure_time", None)
        last_failure_time = (
            float(raw_last_failure_time)
            if isinstance(raw_last_failure_time, int | float)
            and not isinstance(raw_last_failure_time, bool)
            and raw_last_failure_time > 0
            else None
        )

    return CircuitBreakerSnapshot(
        state=circuit_breaker.get_state(),
        failure_count=circuit_breaker.get_failure_count(),
        recovery_timeout=recovery_timeout,
        last_failure_time=last_failure_time,
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
