"""Port factory functions for local deployment adapters.

Extracted from BaseServicesFactory to keep factory.py within LOC limits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.composition.observability_resolution import resolve_metrics_port
from bioetl.domain.ports import (
    CheckpointPort,
    LockPort,
    MetricsPort,
    QuarantinePort,
    SettingsPort,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings

from bioetl.application.ports.storage import StorageContextProtocol as _StorageContextLike

from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.infrastructure.quarantine import UnifiedQuarantineAdapter


__all__ = [
    "create_checkpoint",
    "create_lock",
    "create_metrics",
    "create_quarantine",
    "is_metrics_port_like",
]


def create_lock() -> LockPort:
    """Create in-memory lock for local deployment."""

    lock = MemoryLock()
    assert isinstance(lock, LockPort), (
        f"MemoryLock must implement LockPort, got {type(lock)}"
    )
    return lock


def create_checkpoint(storage_ctx: _StorageContextLike) -> CheckpointPort:
    """Create local filesystem checkpoint."""

    checkpoint = LocalCheckpointAdapter(base_path=storage_ctx.checkpoints_path)
    assert isinstance(checkpoint, CheckpointPort), (
        f"LocalCheckpointAdapter must implement CheckpointPort, got {type(checkpoint)}"
    )
    return checkpoint


def create_quarantine(settings: SettingsPort) -> QuarantinePort:
    """Create unified quarantine storage."""

    quarantine = UnifiedQuarantineAdapter(base_path=str(settings.quarantine_path))
    assert isinstance(quarantine, QuarantinePort), (
        f"UnifiedQuarantineAdapter must implement QuarantinePort, got {type(quarantine)}"
    )
    return quarantine


def create_metrics(settings: SettingsPort) -> MetricsPort:
    """Create metrics port based on settings."""
    metrics: object = resolve_metrics_port(
        metrics=None,
        settings=cast("Settings", settings),
    )

    if isinstance(metrics, MetricsPort):
        assert isinstance(metrics, MetricsPort), (
            f"Metrics adapter must implement MetricsPort, got {type(metrics)}"
        )
        return metrics
    if is_metrics_port_like(metrics):
        return cast("MetricsPort", metrics)
    raise TypeError(f"Metrics adapter must implement MetricsPort, got {type(metrics)}")


def is_metrics_port_like(candidate: object) -> bool:
    """Duck-typed fallback for patched test doubles."""
    required_methods = (
        "observe_histogram",
        "increment_counter",
        "set_gauge",
        "close",
    )
    return all(
        callable(getattr(candidate, method_name, None))
        for method_name in required_methods
    )
