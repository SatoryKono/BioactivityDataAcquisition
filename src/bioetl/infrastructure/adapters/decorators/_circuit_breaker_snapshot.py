"""Build typed snapshots from circuit-breaker ports and legacy test doubles."""

from __future__ import annotations

from typing import Any, cast

from bioetl.domain.ports import CircuitBreakerPort
from bioetl.infrastructure.adapters.circuit_breaker_contract import (
    CircuitBreakerSnapshot,
)


def _recovery_timeout(circuit_breaker: CircuitBreakerPort) -> float:
    getter = getattr(circuit_breaker, "get_recovery_timeout", None)
    if callable(getter):
        return float(cast(Any, getter()))  # Any: legacy breaker duck type
    return float(
        cast(
            Any,  # Any: legacy breaker attribute
            getattr(circuit_breaker, "recovery_timeout", 60.0),
        )
    )


def _positive_timestamp(value: object) -> float | None:
    if isinstance(value, int | float) and not isinstance(value, bool) and value > 0:
        return float(value)
    return None


def _last_failure_time(circuit_breaker: CircuitBreakerPort) -> float | None:
    getter = getattr(circuit_breaker, "get_last_failure_time", None)
    if callable(getter):
        return _positive_timestamp(getter())
    raw = getattr(circuit_breaker, "last_failure_time", None)
    if raw is None:
        raw = getattr(circuit_breaker, "_last_failure_time", None)
    return _positive_timestamp(raw)


def snapshot_from_port(
    circuit_breaker: CircuitBreakerPort,
) -> CircuitBreakerSnapshot:
    """Prefer a typed public snapshot, retaining compatibility for old doubles."""
    snapshot_fn = getattr(circuit_breaker, "snapshot", None)
    if callable(snapshot_fn):
        snapshot = snapshot_fn()
        if isinstance(snapshot, CircuitBreakerSnapshot):
            return snapshot
    return CircuitBreakerSnapshot(
        state=circuit_breaker.get_state(),
        failure_count=circuit_breaker.get_failure_count(),
        recovery_timeout=_recovery_timeout(circuit_breaker),
        last_failure_time=_last_failure_time(circuit_breaker),
    )
