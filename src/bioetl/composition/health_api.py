"""Public health-oriented composition API."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = [
    "HealthServerDependencies",
    "get_health_server_dependencies",
    "get_health_service",
    "get_quarantine_port",
    "get_quarantine_service",
]

_SERVICES_MODULE = "bioetl.composition._services"
_BOOTSTRAP_HEALTH_MODULE = "bioetl.composition.bootstrap.cli.health"
_PUBLIC_EXPORTS = {
    "HealthServerDependencies": _BOOTSTRAP_HEALTH_MODULE,
    "get_health_server_dependencies": _SERVICES_MODULE,
    "get_health_service": _SERVICES_MODULE,
    "get_quarantine_port": _SERVICES_MODULE,
    "get_quarantine_service": _SERVICES_MODULE,
}

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.services.health_service import HealthService
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.composition.bootstrap.cli.health import (
        HealthServerDependencies as _HealthServerDependencies,
    )
    from bioetl.domain.ports import QuarantinePort

HealthServerDependencies: "type[_HealthServerDependencies]"
get_health_server_dependencies: "Callable[[], _HealthServerDependencies]"
get_health_service: "Callable[[], HealthService]"
get_quarantine_port: "Callable[[], QuarantinePort]"
get_quarantine_service: "Callable[[], QuarantineService]"


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
