"""Typed registry backing the public composition entrypoint functions."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import import_module
from typing import cast

from bioetl.composition.bootstrap.runtime_public_exports import (
    AdrServicePort,
    AuditInspectionServiceProtocol,
    BronzeCleanupServiceProtocol,
    CheckpointServiceProtocol,
    ConfigServiceProtocol,
    ContractMigrationServiceProtocol,
    ExportServiceProtocol,
    ForensicRunDiffServiceProtocol,
    HealthServerDependenciesFactoryProtocol,
    HealthServiceProtocol,
    HistoricalReplayClosureServiceProtocol,
    HistoricalReplayCorpusServiceProtocol,
    HistoricalReplayUniverseServiceProtocol,
    LineageInspectionServiceProtocol,
    LockServiceProtocol,
    MetricsService,
    ObservabilityWorkflowServiceProtocol,
    PipelineRunnerServiceFactoryProtocol,
    QuarantinePort,
    QuarantineServiceFactoryProtocol,
    RunManifestInspectionServiceProtocol,
    VacuumServiceProtocol,
    WorkflowInspectionServiceProtocol,
)

_REGISTRY: dict[type[object], Callable[[], object]] = {}
_CHECKPOINT_BOOTSTRAP_MODULE = "bioetl.composition.bootstrap.cli.checkpoint"
_STORAGE_BOOTSTRAP_MODULE = "bioetl.composition.bootstrap.cli.storage"
_RUN_MANIFEST_BOOTSTRAP_MODULE = "bioetl.composition.bootstrap.cli.run_manifest"


class _TypedPortSelector:
    """Select a Protocol type while preserving a runtime-callable registry key."""

    def __getitem__[T](self, port_type: object) -> Callable[[object], type[T]]:
        """Bind the selected Protocol type for one subsequent marker call."""
        del port_type
        return cast("Callable[[object], type[T]]", self)

    def __call__[T](self, port: object) -> type[T]:
        """Return a Protocol class as a registry key without instantiating it."""
        return cast("type[T]", port)


typed_port = _TypedPortSelector()


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
            raise TypeError(f"{self.module_name}.{self.attribute_name} is not callable")
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
    typed_port[HealthServiceProtocol](HealthServiceProtocol),
    "bioetl.composition.bootstrap.cli.health",
    "bootstrap_health_service",
)
_register_lazy_service(
    typed_port[CheckpointServiceProtocol](CheckpointServiceProtocol),
    _CHECKPOINT_BOOTSTRAP_MODULE,
    "bootstrap_checkpoint_service",
)
_register_lazy_service(
    typed_port[AuditInspectionServiceProtocol](AuditInspectionServiceProtocol),
    _CHECKPOINT_BOOTSTRAP_MODULE,
    "bootstrap_audit_inspection_service",
)
_register_lazy_service(
    typed_port[BronzeCleanupServiceProtocol](BronzeCleanupServiceProtocol),
    _STORAGE_BOOTSTRAP_MODULE,
    "bootstrap_bronze_cleanup_service",
)
_register_lazy_service(
    typed_port[VacuumServiceProtocol](VacuumServiceProtocol),
    _STORAGE_BOOTSTRAP_MODULE,
    "bootstrap_vacuum_service",
)
_register_lazy_service(
    typed_port[ContractMigrationServiceProtocol](ContractMigrationServiceProtocol),
    _STORAGE_BOOTSTRAP_MODULE,
    "bootstrap_contract_migration_service",
)
_register_lazy_service(
    typed_port[ObservabilityWorkflowServiceProtocol](
        ObservabilityWorkflowServiceProtocol
    ),
    _CHECKPOINT_BOOTSTRAP_MODULE,
    "bootstrap_observability_workflow_service",
)
_register_lazy_service(
    typed_port[MetricsService](MetricsService),
    "bioetl.composition.bootstrap.cli.metrics",
    "bootstrap_metrics_service",
)
_register_lazy_service(
    typed_port[QuarantinePort](QuarantinePort),
    "bioetl.composition.bootstrap.assembly.checkpoint",
    "bootstrap_quarantine_adapter",
)
_register_lazy_service(
    typed_port[AdrServicePort](AdrServicePort),
    "bioetl.composition.bootstrap.cli",
    "bootstrap_adr_service",
)
_register_lazy_service(
    typed_port[ConfigServiceProtocol](ConfigServiceProtocol),
    "bioetl.composition.bootstrap.cli.config",
    "bootstrap_config_service",
)
_register_lazy_service(
    typed_port[ExportServiceProtocol](ExportServiceProtocol),
    _STORAGE_BOOTSTRAP_MODULE,
    "bootstrap_export_service",
)
_register_lazy_service(
    typed_port[LockServiceProtocol](LockServiceProtocol),
    "bioetl.composition.bootstrap.cli.lock",
    "bootstrap_lock_service",
)
_register_lazy_service(
    typed_port[ForensicRunDiffServiceProtocol](ForensicRunDiffServiceProtocol),
    _RUN_MANIFEST_BOOTSTRAP_MODULE,
    "bootstrap_forensic_run_diff_service",
)
_register_lazy_service(
    typed_port[HistoricalReplayClosureServiceProtocol](
        HistoricalReplayClosureServiceProtocol
    ),
    _RUN_MANIFEST_BOOTSTRAP_MODULE,
    "bootstrap_historical_replay_closure_service",
)
_register_lazy_service(
    typed_port[HistoricalReplayCorpusServiceProtocol](
        HistoricalReplayCorpusServiceProtocol
    ),
    _RUN_MANIFEST_BOOTSTRAP_MODULE,
    "bootstrap_historical_replay_corpus_service",
)
_register_lazy_service(
    typed_port[HistoricalReplayUniverseServiceProtocol](
        HistoricalReplayUniverseServiceProtocol
    ),
    _RUN_MANIFEST_BOOTSTRAP_MODULE,
    "bootstrap_historical_replay_universe_service",
)
_register_lazy_service(
    typed_port[LineageInspectionServiceProtocol](LineageInspectionServiceProtocol),
    "bioetl.composition.bootstrap.cli.lineage",
    "bootstrap_lineage_service",
)
_register_lazy_service(
    typed_port[RunManifestInspectionServiceProtocol](
        RunManifestInspectionServiceProtocol
    ),
    _RUN_MANIFEST_BOOTSTRAP_MODULE,
    "bootstrap_run_manifest_service",
)
_register_lazy_service(
    typed_port[WorkflowInspectionServiceProtocol](WorkflowInspectionServiceProtocol),
    "bioetl.composition._workflow_services",
    "get_workflow_inspection_service",
)
_register_lazy_contextual_factory(
    typed_port[QuarantineServiceFactoryProtocol](QuarantineServiceFactoryProtocol),
    _CHECKPOINT_BOOTSTRAP_MODULE,
    "bootstrap_quarantine_service",
)
_register_lazy_contextual_factory(
    typed_port[PipelineRunnerServiceFactoryProtocol](
        PipelineRunnerServiceFactoryProtocol
    ),
    "bioetl.composition.bootstrap.runtime.runner",
    "bootstrap_pipeline_runner_service",
)
_register_lazy_contextual_factory(
    typed_port[HealthServerDependenciesFactoryProtocol](
        HealthServerDependenciesFactoryProtocol
    ),
    "bioetl.composition.bootstrap.cli.health",
    "bootstrap_health_server_dependencies",
)
