"""Typed registry backing the public composition entrypoint functions."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING, cast

from bioetl.application.ports.control_plane import (
    ForensicRunDiffServiceProtocol,
    HistoricalReplayClosureServiceProtocol,
    HistoricalReplayCorpusServiceProtocol,
    HistoricalReplayUniverseServiceProtocol,
    LineageInspectionServiceProtocol,
    RunManifestInspectionServiceProtocol,
    WorkflowInspectionServiceProtocol,
)
from bioetl.application.ports.metrics import MetricsService
from bioetl.application.ports.operations import (
    AuditInspectionServiceProtocol,
    CheckpointServiceProtocol,
    ConfigServiceProtocol,
    ContractMigrationServiceProtocol,
    ExportServiceProtocol,
    LockServiceProtocol,
    ObservabilityWorkflowServiceProtocol,
    VacuumServiceProtocol,
)
from bioetl.composition.contracts.factories import (
    HealthServerDependenciesFactoryProtocol,
    PipelineRunnerServiceFactoryProtocol,
    QuarantineServiceFactoryProtocol,
)
from bioetl.composition.contracts.health import BronzeCleanupServiceProtocol
from bioetl.domain.ports.adr import AdrServicePort
from bioetl.domain.ports.quality.quarantine import QuarantinePort

if TYPE_CHECKING:
    from bioetl.application.ports.health import HealthServiceProtocol

_REGISTRY: dict[type[object], Callable[[], object]] = {}


def register[T](port: type[T], factory: Callable[[], T]) -> None:
    """Register a zero-argument factory for a port or protocol type."""
    _REGISTRY[cast(type[object], port)] = cast(Callable[[], object], factory)


def resolve[T](port: type[T]) -> T:
    """Resolve a registered port factory."""
    factory = _REGISTRY.get(cast(type[object], port))
    if factory is None:
        raise KeyError(f"no composition factory registered for {port!r}")
    return cast(T, factory())


def registered_ports() -> Mapping[type[object], Callable[[], object]]:
    """Return an isolated snapshot of registered composition factories."""
    return dict(_REGISTRY)


@dataclass(frozen=True, slots=True)
class _LazyServiceFactory[T]:
    """Zero-argument factory backed by explicit lazy import metadata."""

    module_name: str
    attribute_name: str

    def __call__(self) -> T:
        """Import and invoke one configured zero-argument bootstrap factory."""
        candidate = cast(
            object,
            getattr(import_module(self.module_name), self.attribute_name),
        )
        if not callable(candidate):
            raise TypeError(f"{self.module_name}.{self.attribute_name} is not callable")
        return cast(Callable[[], T], candidate)()


@dataclass(frozen=True, slots=True)
class _LazyContextualFactory[T]:
    """Zero-argument registry thunk returning one lazy contextual factory."""

    module_name: str
    attribute_name: str

    def __call__(self) -> T:
        """Import and return one configured callable without invoking it."""
        candidate = cast(
            object,
            getattr(import_module(self.module_name), self.attribute_name),
        )
        if not callable(candidate):
            raise TypeError(
                f"{self.module_name}.{self.attribute_name} is not callable"
            )
        return cast(T, candidate)


def _register_lazy_service[T](
    port: type[T],
    module_name: str,
    attribute_name: str,
) -> None:
    """Register a typed port against one lazy bootstrap target."""
    register(
        port,
        _LazyServiceFactory[T](
            module_name=module_name,
            attribute_name=attribute_name,
        ),
    )


def _register_lazy_contextual_factory[T](
    port: type[T],
    module_name: str,
    attribute_name: str,
) -> None:
    """Register a typed contextual factory through a zero-argument thunk."""
    register(
        port,
        _LazyContextualFactory[T](
            module_name=module_name,
            attribute_name=attribute_name,
        ),
    )


_register_lazy_service(
    cast(
        "type[HealthServiceProtocol]",
        import_module("bioetl.application.ports.health").HealthServiceProtocol,
    ),
    "bioetl.composition.bootstrap.cli.health",
    "bootstrap_health_service",
)
_register_lazy_service(
    CheckpointServiceProtocol,
    "bioetl.composition.bootstrap.cli.checkpoint",
    "bootstrap_checkpoint_service",
)
_register_lazy_service(
    AuditInspectionServiceProtocol,
    "bioetl.composition.bootstrap.cli.checkpoint",
    "bootstrap_audit_inspection_service",
)
_register_lazy_service(
    BronzeCleanupServiceProtocol,
    "bioetl.composition.bootstrap.cli.storage",
    "bootstrap_bronze_cleanup_service",
)
_register_lazy_service(
    VacuumServiceProtocol,
    "bioetl.composition.bootstrap.cli.storage",
    "bootstrap_vacuum_service",
)
_register_lazy_service(
    ContractMigrationServiceProtocol,
    "bioetl.composition.bootstrap.cli.storage",
    "bootstrap_contract_migration_service",
)
_register_lazy_service(
    ObservabilityWorkflowServiceProtocol,
    "bioetl.composition.bootstrap.cli.checkpoint",
    "bootstrap_observability_workflow_service",
)
_register_lazy_service(
    MetricsService,
    "bioetl.composition.bootstrap.cli.metrics",
    "bootstrap_metrics_service",
)
_register_lazy_service(
    QuarantinePort,
    "bioetl.composition.bootstrap.assembly.checkpoint",
    "bootstrap_quarantine_adapter",
)
_register_lazy_service(
    AdrServicePort,
    "bioetl.composition.bootstrap.cli",
    "bootstrap_adr_service",
)
_register_lazy_service(
    ConfigServiceProtocol,
    "bioetl.composition.bootstrap.cli.config",
    "bootstrap_config_service",
)
_register_lazy_service(
    ExportServiceProtocol,
    "bioetl.composition.bootstrap.cli.storage",
    "bootstrap_export_service",
)
_register_lazy_service(
    LockServiceProtocol,
    "bioetl.composition.bootstrap.cli.lock",
    "bootstrap_lock_service",
)
_register_lazy_service(
    ForensicRunDiffServiceProtocol,
    "bioetl.composition.bootstrap.cli.run_manifest",
    "bootstrap_forensic_run_diff_service",
)
_register_lazy_service(
    HistoricalReplayClosureServiceProtocol,
    "bioetl.composition.bootstrap.cli.run_manifest",
    "bootstrap_historical_replay_closure_service",
)
_register_lazy_service(
    HistoricalReplayCorpusServiceProtocol,
    "bioetl.composition.bootstrap.cli.run_manifest",
    "bootstrap_historical_replay_corpus_service",
)
_register_lazy_service(
    HistoricalReplayUniverseServiceProtocol,
    "bioetl.composition.bootstrap.cli.run_manifest",
    "bootstrap_historical_replay_universe_service",
)
_register_lazy_service(
    LineageInspectionServiceProtocol,
    "bioetl.composition.bootstrap.cli.lineage",
    "bootstrap_lineage_service",
)
_register_lazy_service(
    RunManifestInspectionServiceProtocol,
    "bioetl.composition.bootstrap.cli.run_manifest",
    "bootstrap_run_manifest_service",
)
_register_lazy_service(
    WorkflowInspectionServiceProtocol,
    "bioetl.composition._workflow_services",
    "get_workflow_inspection_service",
)
_register_lazy_contextual_factory(
    QuarantineServiceFactoryProtocol,
    "bioetl.composition.bootstrap.cli.checkpoint",
    "bootstrap_quarantine_service",
)
_register_lazy_contextual_factory(
    PipelineRunnerServiceFactoryProtocol,
    "bioetl.composition.bootstrap.runtime.runner",
    "bootstrap_pipeline_runner_service",
)
_register_lazy_contextual_factory(
    HealthServerDependenciesFactoryProtocol,
    "bioetl.composition.bootstrap.cli.health",
    "bootstrap_health_server_dependencies",
)
