"""Unit tests for port factory functions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.services.port_factories import (
    create_checkpoint,
    create_lock,
    create_metrics,
    create_quarantine,
    is_metrics_port_like,
)
from bioetl.domain.ports import CheckpointPort, LockPort, MetricsPort, QuarantinePort
from bioetl.infrastructure.config import Settings


@dataclass(frozen=True, slots=True)
class _StorageContext:
    _checkpoints_path: Path

    @property
    def checkpoints_path(self) -> Path:
        return self._checkpoints_path


@pytest.fixture
def storage_ctx(tmp_path: Path) -> _StorageContext:
    return _StorageContext(_checkpoints_path=tmp_path)


@pytest.mark.unit
def test_create_lock_returns_lock_port() -> None:
    """create_lock returns an instance satisfying LockPort."""
    lock = create_lock()
    assert isinstance(lock, LockPort)


@pytest.mark.unit
def test_create_checkpoint_returns_checkpoint_port(
    storage_ctx: _StorageContext,
) -> None:
    """create_checkpoint returns an instance satisfying CheckpointPort."""
    checkpoint = create_checkpoint(storage_ctx)
    assert isinstance(checkpoint, CheckpointPort)


@pytest.mark.unit
def test_create_quarantine_returns_quarantine_port(tmp_path: Path) -> None:
    """create_quarantine returns an instance satisfying QuarantinePort."""
    settings = Settings(data_dir=tmp_path)
    quarantine = create_quarantine(settings)
    assert isinstance(quarantine, QuarantinePort)


@pytest.mark.unit
def test_create_metrics_with_prometheus_enabled() -> None:
    """create_metrics returns PrometheusMetrics when enabled."""
    settings = Settings(metrics_enabled=True)
    metrics = create_metrics(settings)
    assert isinstance(metrics, MetricsPort)


@pytest.mark.unit
def test_create_metrics_with_noop() -> None:
    """create_metrics returns NoOpMetrics when disabled."""
    settings = Settings(metrics_enabled=False)
    metrics = create_metrics(settings)
    assert isinstance(metrics, MetricsPort)


@pytest.mark.unit
def test_is_metrics_port_like_true() -> None:
    """is_metrics_port_like returns True for objects with all required methods."""
    candidate = MagicMock(
        spec=[
            "observe_histogram",
            "increment_counter",
            "set_gauge",
            "close",
        ]
    )
    assert is_metrics_port_like(candidate) is True


@pytest.mark.unit
def test_is_metrics_port_like_false_missing_method() -> None:
    """is_metrics_port_like returns False when a method is missing."""

    @dataclass
    class _IncompleteMetricsPort:
        def observe_histogram(self, *args: object, **kwargs: object) -> None:
            return None

        def increment_counter(self, *args: object, **kwargs: object) -> None:
            return None

        def close(self) -> None:
            return None

    candidate = _IncompleteMetricsPort()
    assert is_metrics_port_like(candidate) is False
