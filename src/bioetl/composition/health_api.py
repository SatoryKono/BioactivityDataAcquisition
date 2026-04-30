"""Public health-oriented composition API."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.services.health_service import HealthService
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.composition._resource_management import (
        QuarantineManagerProtocol,
        QuarantineRuntimeServiceProtocol,
    )
    from bioetl.composition.bootstrap.cli.health import (
        HealthServerDependencies as HealthServerDependencies,
    )
    from bioetl.domain.ports import HealthMonitorPort, MetricsPort, QuarantinePort

    def get_health_server_dependencies() -> HealthServerDependenciesProtocol: ...

    def get_quarantine_manager(pipeline: str) -> QuarantineManagerProtocol: ...

    def get_quarantine_runtime_service(
        pipeline: str,
    ) -> QuarantineRuntimeServiceProtocol: ...

    def get_health_service() -> HealthService: ...

    def get_quarantine_port() -> QuarantinePort: ...

    def get_quarantine_service() -> QuarantineService: ...


__all__ = [
    "HealthServerDependencies",
    "HealthServerDependenciesProtocol",
    "get_health_server_dependencies",
    "get_health_service",
    "get_quarantine_manager",
    "get_quarantine_port",
    "get_quarantine_runtime_service",
    "get_quarantine_service",
]

_SERVICES_MODULE = "bioetl.composition._services"
_BOOTSTRAP_HEALTH_MODULE = "bioetl.composition.bootstrap.cli.health"
_RESOURCE_MANAGEMENT_MODULE = "bioetl.composition._resource_management"
_PUBLIC_EXPORTS = {
    "HealthServerDependencies": _BOOTSTRAP_HEALTH_MODULE,
    "get_health_server_dependencies": _SERVICES_MODULE,
    "get_health_service": _SERVICES_MODULE,
    "get_quarantine_manager": _RESOURCE_MANAGEMENT_MODULE,
    "get_quarantine_port": _SERVICES_MODULE,
    "get_quarantine_runtime_service": _RESOURCE_MANAGEMENT_MODULE,
    "get_quarantine_service": _SERVICES_MODULE,
}


class HealthServerDependenciesProtocol(Protocol):
    """Typed view of health-server dependencies exposed through the facade."""

    health_monitor: HealthMonitorPort
    metrics: MetricsPort


def __getattr__(name: str) -> object:
    """Resolve health exports lazily to avoid CLI import fan-out."""
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
