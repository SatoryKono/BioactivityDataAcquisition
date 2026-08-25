"""Explicit composition root (S5 / #9601, ADR-058).

Typed factory registry for application/domain ports. ``*_api.py`` modules
remain thin adapters. Full DI framework is intentionally not introduced
(local-only determinism, ADR-010).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import cast

from bioetl.composition._pipeline_execution import (
    ensure_metrics_server_started as ensure_metrics_server_started,
)
from bioetl.composition._resource_management import (
    MedallionLifecycleServiceProtocol as MedallionLifecycleServiceProtocol,
)
from bioetl.composition._resource_management import (
    get_lifecycle_service as get_lifecycle_service,
)
from bioetl.composition._resource_management import preview_cleanup as preview_cleanup
from bioetl.composition._services import (
    get_bronze_cleanup_service as get_bronze_cleanup_service,
)
from bioetl.composition._services import (
    get_contract_migration_service as get_contract_migration_service,
)
from bioetl.composition._services import (
    get_pipeline_runner_service as get_pipeline_runner_service,
)
from bioetl.composition._services import get_vacuum_service as get_vacuum_service

__all__ = [
    "MedallionLifecycleServiceProtocol",
    "ensure_metrics_server_started",
    "get_bronze_cleanup_service",
    "get_contract_migration_service",
    "get_lifecycle_service",
    "get_pipeline_runner_service",
    "get_vacuum_service",
    "preview_cleanup",
    "register",
    "registered_ports",
    "resolve",
]

_REGISTRY: dict[type[object], Callable[[], object]] = {}


def register[T](port: type[T], factory: Callable[[], T]) -> None:
    """Register a zero-arg factory for a port/protocol type."""
    _REGISTRY[cast(type[object], port)] = cast(Callable[[], object], factory)


def resolve[T](port: type[T]) -> T:
    """Resolve a registered port factory."""
    factory = _REGISTRY.get(cast(type[object], port))
    if factory is None:
        raise KeyError(f"no composition factory registered for {port!r}")
    return cast(T, factory())


def registered_ports() -> Mapping[type[object], Callable[[], object]]:
    """Return a snapshot of the composition factory registry."""
    return dict(_REGISTRY)
