"""Unit tests for port factory functions."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
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


@pytest.mark.unit
def test_create_lock_returns_lock_port() -> None:
    """create_lock returns an instance satisfying LockPort."""
    lock = create_lock()
    assert isinstance(lock, LockPort)


@pytest.mark.unit
def test_create_checkpoint_returns_checkpoint_port(tmp_path: Path) -> None:
    """create_checkpoint returns an instance satisfying CheckpointPort."""
    storage_ctx = SimpleNamespace(checkpoints_path=tmp_path)
    checkpoint = create_checkpoint(storage_ctx)  # type: ignore[arg-type]
    assert isinstance(checkpoint, CheckpointPort)


@pytest.mark.unit
def test_create_quarantine_returns_quarantine_port(tmp_path: Path) -> None:
    """create_quarantine returns an instance satisfying QuarantinePort."""
    settings = SimpleNamespace(quarantine_path=tmp_path)
    quarantine = create_quarantine(settings)  # type: ignore[arg-type]
    assert isinstance(quarantine, QuarantinePort)


@pytest.mark.unit
def test_create_metrics_with_prometheus_enabled() -> None:
    """create_metrics returns PrometheusMetrics when enabled."""
    settings = SimpleNamespace(metrics_enabled=True)
    metrics = create_metrics(settings)  # type: ignore[arg-type]
    assert isinstance(metrics, MetricsPort)


@pytest.mark.unit
def test_create_metrics_with_noop() -> None:
    """create_metrics returns NoOpMetrics when disabled."""
    settings = SimpleNamespace(metrics_enabled=False)
    metrics = create_metrics(settings)  # type: ignore[arg-type]
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

    def _observe_histogram() -> None:
        return None

    def _increment_counter() -> None:
        return None

    candidate = SimpleNamespace(
        observe_histogram=_observe_histogram,
        increment_counter=_increment_counter,
        # missing set_gauge, etc.
    )
    assert is_metrics_port_like(candidate) is False
