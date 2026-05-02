"""Public health-oriented composition API."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.services.health_service import HealthService
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.composition._resource_management import (
        QuarantineRuntimeServiceProtocol,
    )
    from bioetl.composition.bootstrap.cli.health import (
        HealthServerDependencies as HealthServerDependencies,
    )
    from bioetl.domain.ports import HealthMonitorPort, MetricsPort, QuarantinePort

    class ObservabilitySettingsProtocol(Protocol):
        metrics_enabled: bool
        metrics_server_enabled: bool
        metrics_fail_fast: bool
        metrics_retry_count: int
        metrics_retry_delay: float

    class RuntimeSettingsProtocol(Protocol):
        observability: ObservabilitySettingsProtocol
        metrics_port: int
        metrics_addr: str

    def get_health_server_dependencies() -> HealthServerDependenciesProtocol: ...

    def get_runtime_settings() -> RuntimeSettingsProtocol: ...

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
    "get_quarantine_port",
    "get_quarantine_runtime_service",
    "get_quarantine_service",
    "get_runtime_settings",
]

_SERVICES_MODULE = "bioetl.composition._services"
_BOOTSTRAP_HEALTH_MODULE = "bioetl.composition.bootstrap.cli.health"
_RESOURCE_MANAGEMENT_MODULE = "bioetl.composition._resource_management"
_PUBLIC_EXPORTS = {
    "HealthServerDependencies": _BOOTSTRAP_HEALTH_MODULE,
    "get_health_server_dependencies": _SERVICES_MODULE,
    "get_health_service": _SERVICES_MODULE,
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


def get_runtime_settings() -> object:
    """Load runtime settings through the composition boundary."""
    from bioetl.infrastructure.config import get_settings

    return get_settings()


def __dir__() -> list[str]:
    """Expose lazy exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
