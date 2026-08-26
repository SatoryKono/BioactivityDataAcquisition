"""Public health-oriented composition API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, cast

from bioetl.composition.lazy_exports import (
    LazyExportTarget,
    install_cached_public_exports,
)

if TYPE_CHECKING:
    from bioetl.application.services.ops.health_service import HealthService
    from bioetl.application.services.quality.quarantine_service import QuarantineService
    from bioetl.composition._resource_management import (
        QuarantineRuntimeServiceProtocol,
    )
    from bioetl.composition.bootstrap.cli.health import (
        HealthServerDependencies as HealthServerDependencies,
    )
    from bioetl.domain.ports import (
        MetricsPort,
        QuarantinePort,
    )

    from bioetl.composition.contracts.health import HealthListenerDependenciesProtocol

    def get_health_server_dependencies() -> HealthListenerDependenciesProtocol: ...

    def get_quarantine_runtime_service(
        pipeline: str,
    ) -> QuarantineRuntimeServiceProtocol: ...

    def get_health_service() -> HealthService: ...

    def get_quarantine_port() -> QuarantinePort: ...

    def get_quarantine_service() -> QuarantineService: ...

    def rehydrate_provider_health_gauges(metrics: MetricsPort) -> int: ...

    def get_runtime_settings() -> object: ...


__all__ = [
    "HealthServerDependencies",
    "get_health_server_dependencies",
    "get_health_service",
    "get_quarantine_port",
    "get_quarantine_runtime_service",
    "get_quarantine_service",
    "rehydrate_provider_health_gauges",
]

_SERVICES_MODULE = "bioetl.composition._services"
_BOOTSTRAP_HEALTH_MODULE = "bioetl.composition.bootstrap.cli.health"
_RESOURCE_MANAGEMENT_MODULE = "bioetl.composition._resource_management"
_PREFLIGHT_HEALTH_MODULE = (
    "bioetl.composition.factories.pipeline._preflight_health_monitor"
)
_CONFIG_ACCESS_MODULE = "bioetl.composition.runtime_builders.config_access"
_PUBLIC_EXPORTS = {
    "HealthServerDependencies": _BOOTSTRAP_HEALTH_MODULE,
    "get_health_server_dependencies": _SERVICES_MODULE,
    "get_health_service": _SERVICES_MODULE,
    "get_quarantine_port": _SERVICES_MODULE,
    "get_quarantine_runtime_service": _RESOURCE_MANAGEMENT_MODULE,
    "get_quarantine_service": _SERVICES_MODULE,
    "rehydrate_provider_health_gauges": _PREFLIGHT_HEALTH_MODULE,
}
_COMPATIBILITY_EXPORTS = {
    "get_runtime_settings": (_CONFIG_ACCESS_MODULE, "get_settings"),
}
_LAZY_EXPORTS: Mapping[str, LazyExportTarget] = {
    **_PUBLIC_EXPORTS,
    **_COMPATIBILITY_EXPORTS,
}


install_cached_public_exports(
    module_globals=globals(),
    public_exports=cast("Mapping[str, LazyExportTarget]", _LAZY_EXPORTS),
    module_name=__name__,
)
