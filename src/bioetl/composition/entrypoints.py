"""Explicit composition root (S5 / #9601, ADR-058).

Typed factory registry for application/domain ports. ``*_api.py`` modules
remain thin adapters. Full DI framework is intentionally not introduced
(local-only determinism, ADR-010).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from importlib import import_module
from typing import cast

from bioetl.composition._pipeline_execution import (
    ensure_metrics_server_started as ensure_metrics_server_started,
)
from bioetl.composition._services import (
    get_contract_migration_service as get_contract_migration_service,
)
from bioetl.composition._services import (
    get_pipeline_runner_service as get_pipeline_runner_service,
)
from bioetl.composition._services import get_vacuum_service as get_vacuum_service
from bioetl.composition.contracts import (
    MedallionLifecycleServiceProtocol as MedallionLifecycleServiceProtocol,
)
from bioetl.composition.resources_runtime import (
    get_lifecycle_service as get_lifecycle_service,
)
from bioetl.composition.resources_runtime import preview_cleanup as preview_cleanup

__all__ = [
    "MedallionLifecycleServiceProtocol",
    "ensure_metrics_server_started",
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
_COMPAT_EXPORT_TARGETS = {
    "bootstrap_composite_runner": "bioetl.composition.composite_catalog",
    "create_pipeline_runner": "bioetl.composition.execution_api",
    "load_composite_config": "bioetl.composition.composite_catalog",
    "run_pipeline": "bioetl.composition.execution_api",
}


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


def __getattr__(name: str) -> object:
    """Resolve retained execution/composite attributes without widening ``__all__``."""
    module_name = _COMPAT_EXPORT_TARGETS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(module_name), name)
