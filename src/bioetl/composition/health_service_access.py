# Casts below are boundary-only (lazy import of composition owner types).
# Prefer Protocol-typed seams when rewriting this module (ARCH-CR2-06 / #7011).
"""Narrow health-service access seam for first-party interface callers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.ops.health_service import HealthService
    from bioetl.application.services.quality.quarantine_service import QuarantineService
    from bioetl.composition.bootstrap.cli.health import (
        HealthServerDependencies as _HealthServerDependencies,
    )
    from bioetl.composition._resource_management import (
        QuarantineRuntimeServiceProtocol as _QuarantineRuntimeServiceProtocol,
    )

    HealthServerDependencies = _HealthServerDependencies
    HealthServerDependenciesProtocol = _HealthServerDependencies
    QuarantineRuntimeServiceProtocol = _QuarantineRuntimeServiceProtocol
else:
    HealthServerDependencies = object
    HealthServerDependenciesProtocol = object
    QuarantineRuntimeServiceProtocol = object

__all__ = [
    "get_health_server_dependencies",
    "get_health_service",
    "get_quarantine_runtime_service",
    "get_quarantine_service",
]


def get_health_server_dependencies(
    *,
    data_root: Path | None = None,
) -> HealthServerDependencies:
    """Load health-listener dependencies through one composition owner seam."""
    from bioetl.composition._services import get_health_server_dependencies as _impl

    if data_root is None:
        return _impl()
    return _impl(data_root=data_root)


def get_health_service() -> HealthService:
    """Load the health service through one composition owner seam."""
    from bioetl.composition._services import get_health_service as _impl

    return _impl()


def get_quarantine_runtime_service(
    pipeline: str,
) -> QuarantineRuntimeServiceProtocol:
    """Load a pipeline-scoped quarantine runtime service through one owner seam."""
    from bioetl.composition._resource_management import (
        get_quarantine_runtime_service as _impl,
    )

    return _impl(pipeline)


def get_quarantine_service(*, data_root: Path | None = None) -> QuarantineService:
    """Load the quarantine admin service through one composition owner seam."""
    from bioetl.composition._services import get_quarantine_service as _impl

    if data_root is None:
        return _impl()
    return _impl(data_root=data_root)
