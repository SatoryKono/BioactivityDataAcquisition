"""Private support helpers for CircuitBreakerDataSourceDecorator."""

from __future__ import annotations

import time

from bioetl.domain.exceptions import CircuitBreakerOpenError
from bioetl.domain.ports import CircuitBreakerPort, LoggerPort
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.circuit_breaker_contract import (
    evaluate_attempt,
)
from bioetl.infrastructure.adapters.decorators._circuit_breaker_snapshot import (
    snapshot_from_port,
)


def raise_if_circuit_open(
    *,
    circuit_breaker: CircuitBreakerPort,
    provider_name: str,
    logger: LoggerPort | None,
) -> None:
    """Raise the canonical open-circuit error when the guard is open."""
    snapshot = snapshot_from_port(circuit_breaker)
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

    snapshot = snapshot_from_port(circuit_breaker)
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
    snapshot = snapshot_from_port(circuit_breaker)
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
