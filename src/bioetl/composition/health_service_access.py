# Casts below are boundary-only (lazy import of composition owner types).
# Prefer Protocol-typed seams when rewriting this module (ARCH-CR2-06 / #7011).
"""Narrow health-service access seam for first-party interface callers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from bioetl.composition import _resource_management, _services
from bioetl.composition.factories.pipeline import _preflight_health_monitor

if TYPE_CHECKING:
    from bioetl.composition.contracts.health import BronzeCleanupServiceProtocol
    from bioetl.application.services.ops.health_service import HealthService
    from bioetl.application.services.quality.quarantine_service import QuarantineService
    from bioetl.composition.bootstrap.cli.health import (
        HealthServerDependencies as _HealthServerDependencies,
    )
    from bioetl.composition._resource_management import (
        QuarantineRuntimeServiceProtocol as _QuarantineRuntimeServiceProtocol,
    )
    from bioetl.domain.ports import MetricsPort

    HealthServerDependencies = _HealthServerDependencies
    HealthServerDependenciesProtocol = _HealthServerDependencies
    QuarantineRuntimeServiceProtocol = _QuarantineRuntimeServiceProtocol
else:
    HealthServerDependencies = object
    HealthServerDependenciesProtocol = object
    QuarantineRuntimeServiceProtocol = object

__all__ = [
    "get_bronze_cleanup_service",
    "get_health_server_dependencies",
    "get_health_service",
    "get_quarantine_runtime_service",
    "get_quarantine_service",
    "rehydrate_checkpoint_gauges",
    "rehydrate_provider_health_gauges",
]


def get_health_server_dependencies(
    *,
    data_root: Path | None = None,
) -> HealthServerDependencies:
    """Load health-listener dependencies through one composition owner seam."""
    if data_root is None:
        return _services.get_health_server_dependencies()
    return _services.get_health_server_dependencies(data_root=data_root)


def get_health_service() -> HealthService:
    """Load the health service through one composition owner seam."""
    return cast("HealthService", _services.get_health_service())


def get_quarantine_runtime_service(
    pipeline: str,
) -> QuarantineRuntimeServiceProtocol:
    """Load a pipeline-scoped quarantine runtime service through one owner seam."""
    return _resource_management.get_quarantine_runtime_service(pipeline)


def get_quarantine_service(*, data_root: Path | None = None) -> QuarantineService:
    """Load the quarantine admin service through one composition owner seam."""
    if data_root is None:
        return _services.get_quarantine_service()
    return _services.get_quarantine_service(data_root=data_root)


def rehydrate_provider_health_gauges(metrics: MetricsPort) -> int:
    """Publish CURRENT provider-health gauges through one composition owner seam."""
    return _preflight_health_monitor.rehydrate_provider_health_gauges(metrics)


def rehydrate_checkpoint_gauges(metrics: MetricsPort) -> int:
    """Restore checkpoint timestamps through the configured storage owner."""
    from bioetl.composition.runtime_builders.config_access import get_settings
    from bioetl.infrastructure.checkpoint.metrics_rehydrate import (
        rehydrate_checkpoint_metrics,
    )
    from bioetl.infrastructure.time import SystemClock

    return rehydrate_checkpoint_metrics(
        metrics, get_settings().checkpoint_path, now=SystemClock().now()
    )


def get_bronze_cleanup_service() -> BronzeCleanupServiceProtocol:
    """Load Bronze cleanup through the ops/health owner seam (#9620)."""
    return _services.get_bronze_cleanup_service()
