"""Public health-oriented composition API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.composition.lazy_exports import install_cached_public_exports

if TYPE_CHECKING:
    from bioetl.application.services.health_service import HealthService
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.composition._resource_management import (
        QuarantineRuntimeServiceProtocol,
    )
    from bioetl.composition.bootstrap.cli.health import (
        HealthServerDependencies as HealthServerDependencies,
    )
    from bioetl.domain.ports import (
        CheckpointPort,
        HealthMonitorPort,
        MetricsPort,
        QuarantinePort,
        RunLedgerPort,
        RunManifestPort,
    )

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
    checkpoint_port: CheckpointPort
    run_manifest_port: RunManifestPort
    run_ledger_port: RunLedgerPort


install_cached_public_exports(
    module_globals=globals(),
    public_exports=_PUBLIC_EXPORTS,
    module_name=__name__,
)


def get_runtime_settings() -> object:
    """Load runtime settings through the composition boundary."""
    from bioetl.composition.runtime_builders.config_access import get_settings

    return get_settings()
