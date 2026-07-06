"""Thin composition facade for service bootstrap entrypoints."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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
    from bioetl.application.services.control_plane.workflow.execution_service import (
        WorkflowExecutionService,
    )
    from bioetl.application.services.control_plane.workflow.inspection_service import (
        WorkflowInspectionService,
    )
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.application.services.health_service import HealthService
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
_BOOTSTRAP_CLI_MODULE = "bioetl.composition.bootstrap.cli"


@dataclass(frozen=True, slots=True)
class BootstrapExport:
    """Typed owner descriptor for one lazy bootstrap export."""

    module_name: str


def _bootstrap_export(module_name: str) -> BootstrapExport:
    return BootstrapExport(module_name=module_name)


_BOOTSTRAP_EXPORTS: dict[str, BootstrapExport] = {
    "bootstrap_adr_service": _bootstrap_export(_BOOTSTRAP_CLI_MODULE),
    "bootstrap_audit_inspection_service": _bootstrap_export(
        _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE
    ),
    "bootstrap_bronze_cleanup_service": _bootstrap_export(
        _BOOTSTRAP_STORAGE_EXPORT_MODULE
    ),
    "bootstrap_checkpoint_service": _bootstrap_export(
        _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE
    ),
    "bootstrap_config_service": _bootstrap_export(
        "bioetl.composition.bootstrap.cli.config"
    ),
    "bootstrap_contract_migration_service": _bootstrap_export(
        _BOOTSTRAP_STORAGE_EXPORT_MODULE
    ),
    "bootstrap_export_service": _bootstrap_export(_BOOTSTRAP_STORAGE_EXPORT_MODULE),
    "bootstrap_forensic_run_diff_service": _bootstrap_export(
        _BOOTSTRAP_RUN_MANIFEST_EXPORT_MODULE
    ),
    "bootstrap_historical_replay_corpus_service": _bootstrap_export(
        _BOOTSTRAP_RUN_MANIFEST_EXPORT_MODULE
    ),
    "bootstrap_historical_replay_closure_service": _bootstrap_export(
        _BOOTSTRAP_RUN_MANIFEST_EXPORT_MODULE
    ),
    "bootstrap_historical_replay_universe_service": _bootstrap_export(
        _BOOTSTRAP_RUN_MANIFEST_EXPORT_MODULE
    ),
    "bootstrap_health_server_dependencies": _bootstrap_export(
        "bioetl.composition.bootstrap.cli.health"
    ),
    "bootstrap_health_service": _bootstrap_export(
        "bioetl.composition.bootstrap.cli.health"
    ),
    "bootstrap_lineage_service": _bootstrap_export(_BOOTSTRAP_CHECKPOINT_EXPORT_MODULE),
    "bootstrap_lock_service": _bootstrap_export(
        "bioetl.composition.bootstrap.cli.lock"
    ),
    "bootstrap_metrics_service": _bootstrap_export(
        "bioetl.composition.bootstrap.cli.metrics"
    ),
    "bootstrap_observability_workflow_service": _bootstrap_export(
        "bioetl.composition.bootstrap.cli.checkpoint"
    ),
    "bootstrap_pipeline_runner_service": _bootstrap_export(
        "bioetl.composition.bootstrap.runtime.runner"
    ),
    "bootstrap_quarantine_adapter": _bootstrap_export(
        "bioetl.composition.bootstrap.assembly.checkpoint"
    ),
    "bootstrap_quarantine_service": _bootstrap_export(
        _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE
    ),
    "bootstrap_run_manifest_service": _bootstrap_export(
        _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE
    ),
    "bootstrap_vacuum_service": _bootstrap_export(_BOOTSTRAP_STORAGE_EXPORT_MODULE),
}


def resolve_bootstrap_attr(name: str) -> object:
    """Resolve one public bootstrap export lazily without invoking it."""
    export = _BOOTSTRAP_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"Unknown bootstrap export: {name!r}")
    return getattr(import_module(export.module_name), name)


def _invoke_bootstrap(name: str, *args: object, **kwargs: object) -> object:
    """Resolve one bootstrap owner lazily and invoke it as a callable."""
    bootstrap_fn = cast("Callable[..., object]", resolve_bootstrap_attr(name))
    return bootstrap_fn(*args, **kwargs)


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


def _ensure_pipeline_registrations(registry: PipelineRegistry | None = None) -> None:
    """Ensure full provider and pipeline factory registration."""
    _ensure_registrations(registry=registry, scope="pipelines")


def get_checkpoint_service() -> CheckpointService:
    """Get checkpoint administration service."""
    _ensure_provider_registrations()
    return cast("CheckpointService", _invoke_bootstrap("bootstrap_checkpoint_service"))


def get_audit_service() -> AuditInspectionService:
    """Get an audit inspection service for operator diagnostics operations."""
    _ensure_provider_registrations()
    return cast(
        "AuditInspectionService",
        _invoke_bootstrap("bootstrap_audit_inspection_service"),
    )


def get_quarantine_service() -> QuarantineService:
    """Get quarantine administration service without pipeline registration."""
    return cast("QuarantineService", _invoke_bootstrap("bootstrap_quarantine_service"))


def get_bronze_cleanup_service() -> BronzeCleanupService:
    """Get Bronze cleanup service."""
    _ensure_provider_registrations()
    return cast(
        "BronzeCleanupService", _invoke_bootstrap("bootstrap_bronze_cleanup_service")
    )


def get_vacuum_service() -> VacuumService:
    """Get batch vacuum service."""
    _ensure_provider_registrations()
    return cast("VacuumService", _invoke_bootstrap("bootstrap_vacuum_service"))


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


def get_contract_migration_service() -> object:
    """Get the contract migration planner service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_contract_migration_service")


def get_health_service() -> HealthService:
    """Get provider health service."""
    _ensure_provider_registrations()
    return cast("HealthService", _invoke_bootstrap("bootstrap_health_service"))


def get_observability_workflow_service() -> ObservabilityWorkflowService:
    """Get workflow-level observability diagnostics helpers."""
    _ensure_provider_registrations()
    return cast(
        "ObservabilityWorkflowService",
        _invoke_bootstrap("bootstrap_observability_workflow_service"),
    )


def get_health_server_dependencies() -> HealthServerDependenciesProtocol:
    """Get health-server dependencies without pipeline registration."""
    return cast(
        "HealthServerDependenciesProtocol",
        _invoke_bootstrap("bootstrap_health_server_dependencies"),
    )


def get_metrics_service() -> MetricsService:
    """Get metrics administration service."""
    _ensure_provider_registrations()
    return cast("MetricsService", _invoke_bootstrap("bootstrap_metrics_service"))


def get_quarantine_port() -> QuarantinePort:
    """Get the shared low-level quarantine port without pipeline registration."""
    return cast("QuarantinePort", _invoke_bootstrap("bootstrap_quarantine_adapter"))


def get_adr_service() -> object:
    """Get ADR management port."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_adr_service")

def get_config_service() -> object:
    """Get application configuration service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_config_service")

def get_export_service() -> object:
    """Get Delta export service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_export_service")

def get_forensic_run_diff_service() -> object:
    """Get forensic run diff service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_forensic_run_diff_service")

def get_historical_replay_closure_service() -> object:
    """Get historical replay closure service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_historical_replay_closure_service")

def get_historical_replay_corpus_service() -> object:
    """Get historical replay corpus service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_historical_replay_corpus_service")

def get_historical_replay_universe_service() -> object:
    """Get historical replay universe service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_historical_replay_universe_service")

def get_lineage_service() -> object:
    """Get lineage service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_lineage_service")

def get_lock_service() -> object:
    """Get administrative lock service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_lock_service")

def get_run_manifest_service() -> object:
    """Get run-manifest service without full pipeline registration."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_run_manifest_service")
