"""Public health-oriented composition API."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
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
    "get_health_service": _SERVICES_MODULE,
    "get_quarantine_runtime_service": _RESOURCE_MANAGEMENT_MODULE,
}


class HealthServerDependenciesProtocol(Protocol):
    """Typed view of health-server dependencies exposed through the facade."""

    health_monitor: HealthMonitorPort
    metrics: MetricsPort


@dataclass(frozen=True, slots=True)
class _DirectHealthServerDependencies:
    """Minimal dependency bundle for health listener startup."""

    health_monitor: object
    metrics: object


class _NoOpLogger:
    """Local no-op logger for lightweight health/quarantine bootstrap."""

    def bind(self, **_: object) -> "_NoOpLogger":
        return self

    def debug(self, *_: object, **__: object) -> None:
        return None

    def info(self, *_: object, **__: object) -> None:
        return None

    def warning(self, *_: object, **__: object) -> None:
        return None


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


def get_health_server_dependencies() -> object:
    """Bootstrap health-listener dependencies without heavy CLI bootstrap imports."""
    return _DirectHealthServerDependencies(
        health_monitor=None,
        metrics=None,
    )


def get_quarantine_port() -> object:
    """Bootstrap the shared quarantine adapter without service-graph imports."""
    from bioetl.infrastructure.config import get_settings
    from bioetl.infrastructure.quarantine.unified import UnifiedQuarantineAdapter

    settings = get_settings()
    return UnifiedQuarantineAdapter(base_path=str(settings.quarantine_path))


def get_quarantine_service() -> object:
    """Bootstrap quarantine admin service without heavy CLI bootstrap imports."""
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.infrastructure.config import get_settings
    from bioetl.infrastructure.control_plane import (
        FileEffectiveConfigArtifactStore,
        FileRunLedgerStore,
        FileRunManifestStore,
    )
    from bioetl.infrastructure.time import SystemClock

    settings = get_settings()
    output_root = Path(settings.data_dir) / "output" / "control"
    run_manifest_service = RunManifestInspectionService(
        manifest_port=FileRunManifestStore(
            base_path=output_root / "run_manifest",
            metrics=None,
        ),
        ledger_port=FileRunLedgerStore(
            base_path=output_root / "run_ledger",
            metrics=None,
        ),
        effective_config_artifact_port=FileEffectiveConfigArtifactStore(
            base_path=output_root / "effective_config",
        ),
    )
    return QuarantineService(
        quarantine_port=get_quarantine_port(),
        logger=_NoOpLogger(),
        clock=SystemClock(),
        metrics=None,
        tracer=None,
        run_manifest_service=run_manifest_service,
    )


def __dir__() -> list[str]:
    """Expose lazy exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
