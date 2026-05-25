"""Thin composition facade for service bootstrap entrypoints."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import TYPE_CHECKING, cast

from bioetl.composition._service_protocols import (
    BronzeCleanupServiceProtocol,
    HealthServerDependenciesProtocol,
)

if TYPE_CHECKING:
    from bioetl.application.services.audit_inspection_service import (
        AuditInspectionService,
    )
    from bioetl.application.services.bronze_cleanup_service import (
        BronzeCleanupResult,
        BronzeCleanupService,
    )
    from bioetl.application.services.checkpoint_service import CheckpointService
    from bioetl.application.services.control_plane.forensic_diff_service import (
        ForensicRunDiffService,
    )
    from bioetl.application.services.control_plane.historical_replay_closure_service import (
        HistoricalReplayClosureService,
    )
    from bioetl.application.services.control_plane.historical_replay_corpus_service import (
        HistoricalReplayCorpusService,
    )
    from bioetl.application.services.control_plane.historical_replay_universe_service import (
        HistoricalReplayUniverseService,
    )
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.application.services.control_plane.workflow_execution_service import (
        WorkflowExecutionService,
    )
    from bioetl.application.services.control_plane.workflow_inspection_service import (
        WorkflowInspectionService,
    )
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.application.services.export_service import ExportService
    from bioetl.application.services.health_service import HealthService
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )
    from bioetl.application.services.lock_service import LockService
    from bioetl.application.services.metrics_service import MetricsService
    from bioetl.application.services.observability_workflow_service import (
        ObservabilityWorkflowService,
    )
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.application.services.vacuum_service import VacuumService
    from bioetl.application.services.workflow_runner_service import (
        WorkflowRunnerService,
    )
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.domain.ports import LockPort, QuarantinePort
    from bioetl.domain.workflow import WorkflowConfig


_BOOTSTRAP_CHECKPOINT_EXPORT_MODULE = "bioetl.composition.bootstrap.cli.checkpoint"
_BOOTSTRAP_RUN_MANIFEST_EXPORT_MODULE = "bioetl.composition.bootstrap.cli.run_manifest"
_BOOTSTRAP_STORAGE_EXPORT_MODULE = "bioetl.composition.bootstrap.cli.storage"

_BOOTSTRAP_EXPORT_MODULES: dict[str, str] = {
    "bootstrap_adr_service": "bioetl.composition.bootstrap.cli.adr",
    "bootstrap_audit_inspection_service": _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE,
    "bootstrap_bronze_cleanup_service": _BOOTSTRAP_STORAGE_EXPORT_MODULE,
    "bootstrap_checkpoint_service": _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE,
    "bootstrap_config_service": "bioetl.composition.bootstrap.cli.config",
    "bootstrap_contract_migration_service": _BOOTSTRAP_STORAGE_EXPORT_MODULE,
    "bootstrap_export_service": _BOOTSTRAP_STORAGE_EXPORT_MODULE,
    "bootstrap_forensic_run_diff_service": _BOOTSTRAP_RUN_MANIFEST_EXPORT_MODULE,
    "bootstrap_historical_replay_corpus_service": _BOOTSTRAP_RUN_MANIFEST_EXPORT_MODULE,
    "bootstrap_historical_replay_closure_service": _BOOTSTRAP_RUN_MANIFEST_EXPORT_MODULE,
    "bootstrap_historical_replay_universe_service": _BOOTSTRAP_RUN_MANIFEST_EXPORT_MODULE,
    "bootstrap_health_server_dependencies": "bioetl.composition.bootstrap.cli.health",
    "bootstrap_health_service": "bioetl.composition.bootstrap.cli.health",
    "bootstrap_lineage_service": _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE,
    "bootstrap_lock_service": "bioetl.composition.bootstrap.cli.lock",
    "bootstrap_metrics_service": "bioetl.composition.bootstrap.cli.metrics",
    "bootstrap_observability_workflow_service": "bioetl.composition.bootstrap.cli.checkpoint",
    "bootstrap_pipeline_runner_service": "bioetl.composition.bootstrap.runtime.runner",
    "bootstrap_quarantine_adapter": (
        "bioetl.composition.bootstrap.assembly.checkpoint"
    ),
    "bootstrap_quarantine_service": _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE,
    "bootstrap_run_manifest_service": _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE,
    "bootstrap_vacuum_service": _BOOTSTRAP_STORAGE_EXPORT_MODULE,
}


def resolve_bootstrap_attr(name: str) -> object:
    """Resolve one public bootstrap export lazily without invoking it."""
    module_name = _BOOTSTRAP_EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"Unknown bootstrap export: {name!r}")
    return getattr(import_module(module_name), name)


def _invoke_bootstrap(name: str, *args: object, **kwargs: object) -> object:
    """Resolve one bootstrap owner lazily and invoke it as a callable."""
    bootstrap_fn = cast("Callable[..., object]", resolve_bootstrap_attr(name))
    return bootstrap_fn(*args, **kwargs)


def _resolve_bootstrap_callable(name: str) -> Callable[[], object]:
    """Resolve dynamically exported bootstrap hooks as zero-arg callables."""
    return cast("Callable[[], object]", resolve_bootstrap_attr(name))


def _ensure_registrations(
    registry: PipelineRegistry | None = None,
    *,
    scope: str = "pipelines",
) -> None:
    """Ensure the requested runtime registration scope lazily."""
    from bioetl.composition._registration import ensure_runtime_registrations

    ensure_runtime_registrations(registry=registry, scope=scope)


def _ensure_provider_registrations() -> None:
    """Ensure provider adapters only, without full pipeline factory registration."""
    _ensure_registrations(scope="providers")


def _ensure_pipeline_registrations(
    registry: PipelineRegistry | None = None,
) -> None:
    """Ensure full provider and pipeline factory registration."""
    _ensure_registrations(registry=registry, scope="pipelines")


def get_checkpoint_service() -> CheckpointService:
    """Get checkpoint administration service."""
    _ensure_provider_registrations()
    return cast(
        "CheckpointService",
        _invoke_bootstrap("bootstrap_checkpoint_service"),
    )


def get_audit_service() -> AuditInspectionService:
    """Get an audit inspection service for operator diagnostics operations."""
    _ensure_provider_registrations()
    bootstrap = _resolve_bootstrap_callable("bootstrap_audit_inspection_service")
    return cast("AuditInspectionService", bootstrap())


def get_quarantine_service() -> QuarantineService:
    """Get quarantine administration service.

    Quarantine admin/explorer operations read shared storage directly and do not
    require provider or pipeline registration before bootstrap.
    """
    return cast(
        "QuarantineService",
        _invoke_bootstrap("bootstrap_quarantine_service"),
    )


def get_bronze_cleanup_service() -> BronzeCleanupService:
    """Get Bronze cleanup service."""
    _ensure_provider_registrations()
    return cast(
        "BronzeCleanupService",
        _invoke_bootstrap("bootstrap_bronze_cleanup_service"),
    )


def get_vacuum_service() -> VacuumService:
    """Get batch vacuum service."""
    _ensure_provider_registrations()
    return cast("VacuumService", _invoke_bootstrap("bootstrap_vacuum_service"))


def get_export_service() -> ExportService:
    """Get Delta export service."""
    _ensure_provider_registrations()
    return cast("ExportService", _invoke_bootstrap("bootstrap_export_service"))


def get_lock_service() -> LockService:
    """Get administrative lock service."""
    _ensure_provider_registrations()
    return cast("LockService", _invoke_bootstrap("bootstrap_lock_service"))


async def cleanup_bronze(
    retention_days: int = 90,
    dry_run: bool = False,
) -> BronzeCleanupResult:
    """Clean up Bronze files based on retention policy."""
    service = cast(BronzeCleanupServiceProtocol, get_bronze_cleanup_service())
    return await service.cleanup(
        retention_days=retention_days,
        dry_run=dry_run,
    )


def get_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Get universal pipeline runner service."""
    _ensure_pipeline_registrations(registry=registry)
    return cast(
        "PipelineRunnerService",
        _invoke_bootstrap("bootstrap_pipeline_runner_service", registry=registry),
    )


def get_workflow_runner_service(
    registry: PipelineRegistry | None = None,
) -> WorkflowRunnerService:
    """Build workflow runner service via the canonical workflow seam."""
    from bioetl.composition import _workflow_services

    return _workflow_services.get_workflow_runner_service(registry=registry)


def get_workflow_execution_service(
    registry: PipelineRegistry | None = None,
    workflow_lock_port: LockPort | None = None,
) -> WorkflowExecutionService:
    """Build workflow execution service via the canonical workflow seam."""
    from bioetl.composition import _workflow_services

    return _workflow_services.get_workflow_execution_service(
        registry=registry,
        workflow_lock_port=workflow_lock_port,
    )


def get_workflow_inspection_service() -> WorkflowInspectionService:
    """Build workflow inspection service via the canonical workflow seam."""
    from bioetl.composition import _workflow_services

    return _workflow_services.get_workflow_inspection_service()


def load_workflow_config(name: str) -> WorkflowConfig:
    """Load workflow YAML through the canonical workflow seam."""
    from bioetl.composition import _workflow_services

    return _workflow_services.load_workflow_config(name)


def get_config_service() -> object:
    """Get application configuration service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_config_service")


def get_contract_migration_service() -> object:
    """Get the contract migration planner service."""
    _ensure_provider_registrations()
    bootstrap = cast(
        "Callable[[], object]",
        resolve_bootstrap_attr("bootstrap_contract_migration_service"),
    )
    return bootstrap()


def get_run_manifest_service() -> RunManifestInspectionService:
    """Get a run-manifest inspection service for control-plane operations."""
    _ensure_provider_registrations()
    bootstrap = _resolve_bootstrap_callable("bootstrap_run_manifest_service")
    return cast("RunManifestInspectionService", bootstrap())


def get_forensic_run_diff_service() -> ForensicRunDiffService:
    """Get a unified forensic run-diff service for control-plane diagnostics."""
    _ensure_provider_registrations()
    bootstrap = _resolve_bootstrap_callable("bootstrap_forensic_run_diff_service")
    return cast("ForensicRunDiffService", bootstrap())


def get_historical_replay_corpus_service() -> HistoricalReplayCorpusService:
    """Get retained-corpus historical replay workflows for CLI operations."""
    _ensure_provider_registrations()
    bootstrap = _resolve_bootstrap_callable(
        "bootstrap_historical_replay_corpus_service"
    )
    return cast("HistoricalReplayCorpusService", bootstrap())


def get_historical_replay_closure_service() -> HistoricalReplayClosureService:
    """Get retained-corpus closure reporting workflows for CLI operations."""
    _ensure_provider_registrations()
    bootstrap = _resolve_bootstrap_callable(
        "bootstrap_historical_replay_closure_service"
    )
    return cast("HistoricalReplayClosureService", bootstrap())


def get_historical_replay_universe_service() -> HistoricalReplayUniverseService:
    """Get full-universe historical replay workflows for CLI operations."""
    _ensure_provider_registrations()
    bootstrap = _resolve_bootstrap_callable(
        "bootstrap_historical_replay_universe_service"
    )
    return cast("HistoricalReplayUniverseService", bootstrap())


def get_lineage_service() -> LineageInspectionService:
    """Get a lineage inspection service for traceability operations."""
    _ensure_provider_registrations()
    bootstrap = _resolve_bootstrap_callable("bootstrap_lineage_service")
    return cast("LineageInspectionService", bootstrap())


def get_health_service() -> HealthService:
    """Get provider health service."""
    _ensure_provider_registrations()
    return cast("HealthService", _invoke_bootstrap("bootstrap_health_service"))


def get_observability_workflow_service() -> ObservabilityWorkflowService:
    """Get workflow-level observability diagnostics helpers."""
    _ensure_provider_registrations()
    bootstrap = _resolve_bootstrap_callable("bootstrap_observability_workflow_service")
    return cast("ObservabilityWorkflowService", bootstrap())


def get_health_server_dependencies() -> HealthServerDependenciesProtocol:
    """Get dependencies for the health server.

    Health listener startup must stay independent from pipeline registration so
    the server can bind quickly even when registration is slow or broken.
    """
    return cast(
        "HealthServerDependenciesProtocol",
        _invoke_bootstrap("bootstrap_health_server_dependencies"),
    )


def get_metrics_service() -> MetricsService:
    """Get metrics administration service."""
    _ensure_provider_registrations()
    return cast("MetricsService", _invoke_bootstrap("bootstrap_metrics_service"))


def get_adr_service() -> object:
    """Get ADR management port."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_adr_service")


def get_quarantine_port() -> QuarantinePort:
    """Get the shared low-level quarantine port.

    The shared quarantine table is configuration-backed and does not depend on
    runtime pipeline registration.
    """
    return cast("QuarantinePort", _invoke_bootstrap("bootstrap_quarantine_adapter"))
