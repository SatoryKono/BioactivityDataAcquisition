"""Unit tests for circuit-breaker snapshot compatibility helpers."""

from __future__ import annotations

from typing import cast

import pytest

from bioetl.domain.ports import CircuitBreakerPort
from bioetl.domain.types import CircuitBreakerState
from bioetl.infrastructure.adapters.circuit_breaker_contract import (
    CircuitBreakerSnapshot,
)
from bioetl.infrastructure.adapters.decorators._circuit_breaker_snapshot import (
    snapshot_from_port,
)


pytestmark = pytest.mark.unit


class _LegacyBreaker:
    recovery_timeout = 30.0
    last_failure_time: object = None
    _last_failure_time: object = 42.0

    def get_state(self) -> CircuitBreakerState:
        return CircuitBreakerState.OPEN

    def get_failure_count(self) -> int:
        return 3


class _GetterBreaker(_LegacyBreaker):
    def snapshot(self) -> object:
        return {"legacy": True}

    def get_recovery_timeout(self) -> float:
        return 12.5

    def get_last_failure_time(self) -> object:
        return True


class _TypedSnapshotBreaker(_LegacyBreaker):
    def __init__(self, snapshot: CircuitBreakerSnapshot) -> None:
        self._snapshot = snapshot

    def snapshot(self) -> CircuitBreakerSnapshot:
        return self._snapshot


def test_snapshot_from_port_prefers_typed_public_snapshot() -> None:
    expected = CircuitBreakerSnapshot(
        state=CircuitBreakerState.HALF_OPEN,
        failure_count=2,
        recovery_timeout=5.0,
        last_failure_time=10.0,
    )

    actual = snapshot_from_port(
        cast(CircuitBreakerPort, _TypedSnapshotBreaker(expected))
    )

    assert actual is expected


def test_snapshot_from_port_uses_legacy_getters_and_rejects_boolean_timestamp() -> None:
    actual = snapshot_from_port(cast(CircuitBreakerPort, _GetterBreaker()))

    assert actual == CircuitBreakerSnapshot(
        state=CircuitBreakerState.OPEN,
        failure_count=3,
        recovery_timeout=12.5,
        last_failure_time=None,
    )


def test_snapshot_from_port_falls_back_to_legacy_attributes() -> None:
    actual = snapshot_from_port(cast(CircuitBreakerPort, _LegacyBreaker()))

    assert actual == CircuitBreakerSnapshot(
        state=CircuitBreakerState.OPEN,
        failure_count=3,
        recovery_timeout=30.0,
        last_failure_time=42.0,
    )
