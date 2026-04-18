================================================================================
File: __init__.py
Path: __init__.py
================================================================================
"""Composition Root for BioETL dependency injection.

This package contains the Composition Root - the single place where
all dependencies are composed and wired together according to the
Ports & Adapters architecture (RULES.md).

Components:
    bootstrap: Pipeline bootstrapping and factory functions.
    registry: Pipeline registry for dynamic pipeline discovery.
    builders: Builder classes for constructing pipelines.
    types: Type definitions for composition layer.
    observability: Observability setup (tracing, metrics, logging).
    entrypoints: CLI and API entrypoints.

The composition layer is the only layer allowed to import from
infrastructure and wire concrete implementations to domain ports.

See Also:
    docs/02-architecture/decisions/ADR-005-composition-layer-separation.md
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

from bioetl.composition.registry import (
    PipelineDefinition,
    PipelineRegistry,
    create_registry,
)
from bioetl.composition.registry_default import get_default_registry

_LAZY_MODULE_EXPORTS: dict[str, str] = {
    "bootstrap": "bioetl.composition.bootstrap",
    "composite_api": "bioetl.composition.composite_api",
    "control_plane_api": "bioetl.composition.control_plane_api",
    "entrypoints": "bioetl.composition.entrypoints",
    "execution_api": "bioetl.composition.execution_api",
    "health_api": "bioetl.composition.health_api",
    "maintenance_api": "bioetl.composition.maintenance_api",
    "observability_api": "bioetl.composition.observability_api",
    "registry_api": "bioetl.composition.registry_api",
    "resources_api": "bioetl.composition.resources_api",
    "resource_management_api": "bioetl.composition.resource_management_api",
    "services_api": "bioetl.composition.services_api",
    "types": "bioetl.composition.types",
}

__all__ = [
    "PipelineDefinition",
    "PipelineRegistry",
    "bootstrap",
    "composite_api",
    "control_plane_api",
    "create_registry",
    "entrypoints",
    "execution_api",
    "get_default_registry",
    "health_api",
    "maintenance_api",
    "observability_api",
    "registry_api",
    "resource_management_api",
    "resources_api",
    "services_api",
    "types",
]


def __getattr__(name: str) -> ModuleType:
    """Lazily expose composition public submodules for patch/import stability."""
    try:
        module_name = _LAZY_MODULE_EXPORTS[name]
    except KeyError as exc:  # pragma: no cover - standard attribute path
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_name)
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    """Return stable composition exports for help() and shell introspection."""
    return sorted(set(globals()) | set(__all__))

================================================================================
File: _pipeline_execution.py
Path: _pipeline_execution.py
================================================================================
"""Pipeline execution entrypoints.

Core functions for building, configuring, and running ETL pipelines.
Split from entrypoints.py per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from bioetl.application.runtime_timestamps import (
    capture_runtime_timing_anchor,
    derive_completion_timestamp,
)
from bioetl.application.services import PipelineRunResult, RunOptions, RunResult
from bioetl.composition import PipelineRegistry
from bioetl.composition.bootstrap import (
    bootstrap_pipeline_runner,
    maybe_start_metrics_server,
)
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.factories.pipeline.runner import create_metrics_extractor
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.domain.context import (
    CachedBronzeContext,
    InputFilterContext,
    PipelineRunContext,
    VacuumSettings,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.domain.types import ExecutionContext, RunID, RunType
from bioetl.infrastructure.config import get_settings

if TYPE_CHECKING:
    from bioetl.domain.ports import ExecutionMetricsRunnerPort


__all__ = [
    "ArchiveOptions",
    "VacuumOptions",
    "build_pipeline_context",
    "create_pipeline_runner",
    "ensure_metrics_server_started",
    "push_metrics_to_gateway",
    "run_pipeline",
]


def _ensure_registrations(registry: PipelineRegistry | None = None) -> None:
    """Ensure providers and pipelines are registered for shared entrypoints."""
    ensure_providers_loaded()
    if registry is None or not registry.list_pipelines():
        register_all_pipelines(registry=registry)


def _require_execution_metrics_runner(
    runner: object,
) -> ExecutionMetricsRunnerPort:
    """Validate that the created runner is runnable and metrics-readable."""
    from bioetl.domain.ports import ExecutionMetricsRunnerPort

    if not isinstance(runner, ExecutionMetricsRunnerPort):
        raise TypeError("Runner does not implement ExecutionMetricsRunnerPort")
    return runner


def push_metrics_to_gateway(
    run_label: str = "bioetl",
    pipeline_name: str | None = None,
    run_type: str | None = None,
) -> bool:
    """Push current metrics to Prometheus Pushgateway via composition.

    Args:
        run_label: Run label for pushed metrics.
        pipeline_name: Pipeline name for grouping (e.g. "chembl_molecule").
        run_type: Optional run type for grouping (e.g. "incremental").

    Returns:
        True if push succeeded, False otherwise.
    """
    from bioetl.composition.observability_api import (
        push_metrics_to_gateway as _push,
    )

    return bool(
        _push(
            run_label=run_label,
            pipeline_name=pipeline_name,
            run_type=run_type,
        )
    )


def ensure_metrics_server_started() -> bool:
    """Ensure metrics server is started if enabled in settings.

    This function should be called at the start of pipeline execution
    to start the Prometheus HTTP server. It's idempotent - calling it
    multiple times is safe.

    Returns:
        True if server was started or already running, False if disabled.

    Example:
        >>> ensure_metrics_server_started()
        True  # Server started on configured port
    """
    settings = get_settings()
    return bool(maybe_start_metrics_server(settings))


@dataclass(frozen=True)
class VacuumOptions:
    """Options for vacuum operation.

    Attributes:
        retention_days: Minimum age of files to remove (days).
        dry_run: Preview mode showing what would be removed.
    """

    retention_days: int = 7
    dry_run: bool = False


@dataclass(frozen=True)
class ArchiveOptions:
    """Options for archive operation.

    Attributes:
        target_path: Destination path for archive.
        remove_source: Remove source table after archiving.
    """

    target_path: str
    remove_source: bool = False


def _build_input_filter_context(options: RunOptions) -> InputFilterContext:
    """Build input filter context from CLI options.

    Args:
        options: User-facing run options containing filter configuration.

    Returns:
        InputFilterContext configured for multi-field, single-field, or CSV filtering.
    """
    if options.multi_filter_ids:
        return InputFilterContext.from_multi_ids(
            multi_filter_ids=options.multi_filter_ids,
        )
    if options.filter_ids:
        return InputFilterContext.from_ids(
            filter_ids=options.filter_ids,
            filter_field=options.filter_field or "doi",
            fallback_mapping=options.fallback_mapping,
        )
    if options.input_csv:
        return InputFilterContext(
            enabled=True,
            source_path=options.input_csv,
            column_name=options.filter_column or "",
            filter_field=options.filter_field or "",
        )
    return InputFilterContext.disabled()


def _build_vacuum_config(options: RunOptions) -> VacuumSettings:
    """Build vacuum config from CLI overrides (preserving tri-state).

    Args:
        options: User-facing run options containing vacuum configuration.

    Returns:
        VacuumSettings with enabled flag and retention_days.
    """
    return VacuumSettings(
        enabled=options.vacuum_after_run,
        retention_days=options.vacuum_retention_days or 7,
    )


def _build_cached_bronze_context(options: RunOptions) -> CachedBronzeContext:
    """Build cached bronze context from CLI options.

    Args:
        options: User-facing run options containing cached bronze settings.

    Returns:
        CachedBronzeContext enabled with path/date, or disabled if not requested.
    """
    if options.use_cached_bronze:
        return CachedBronzeContext.from_options(
            path=options.cached_bronze_path,
            date=options.cached_bronze_date,
        )
    if options.exact_replay:
        raise ValueError(
            "exact replay currently requires --use-cached-bronze with snapshot-backed Bronze inputs"
        )
    return CachedBronzeContext.disabled()


def build_pipeline_context(name: str, options: RunOptions) -> PipelineRunContext:
    """Build a PipelineRunContext from user-facing options.

    Args:
        name: Pipeline name (e.g., 'chembl_activity').
        options: User-facing run options.

    Returns:
        PipelineRunContext ready for bootstrap_pipeline_runner.
    """
    return PipelineRunContext(
        pipeline_name=name,
        run_id=cast(RunID, uuid4()),
        run_type=RunType(options.run_type),
        resume=options.resume,
        limit=options.limit,
        dry_run=options.dry_run,
        input_filter=_build_input_filter_context(options),
        vacuum=_build_vacuum_config(options),
        log_level=options.log_level,
        ignore_yaml_filter=options.ignore_yaml_filter,
        skip_gold=options.skip_gold,
        cached_bronze=_build_cached_bronze_context(options),
        exact_replay=options.exact_replay,
        execution_context=ExecutionContext(options.execution_context),
    )


def create_pipeline_runner(
    name: str,
    options: RunOptions,
) -> ExecutionMetricsRunnerPort:
    """Create a pipeline runner for the given pipeline and options.

    This is the main entrypoint for pipeline execution. It handles:
    - Registration of providers and pipelines
    - Building the pipeline context
    - Bootstrapping the runner with all dependencies

    Args:
        name: Pipeline name (e.g., 'chembl_activity').
        options: User-facing run options.

    Returns:
        ExecutionMetricsRunnerPort ready for execution via runner.run().

    Raises:
        ValueError: If pipeline name is unknown or options are invalid.
        FileNotFoundError: If pipeline config file is missing.

    Example:
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> runner = create_pipeline_runner("chembl_activity", options)
        >>> await runner.run()
    """
    run_context = build_pipeline_context(name, options)
    return _require_execution_metrics_runner(bootstrap_pipeline_runner(run_context))


async def run_pipeline(name: str, options: RunOptions) -> RunResult:
    """Run pipeline end-to-end and return structured execution result.

    Args:
        name: Pipeline name (e.g., 'chembl_activity').
        options: User-facing run options controlling execution behaviour.

    Returns:
        RunResult with execution status, record counts, and timing information.
    """
    # Start metrics server if enabled (side-effect in entrypoint, not bootstrap)
    settings = get_settings()
    maybe_start_metrics_server(settings)

    started_at, started_monotonic = capture_runtime_timing_anchor()
    runner = _require_execution_metrics_runner(create_pipeline_runner(name, options))

    # Extract run context for result
    run_id = runner.run_id
    run_type = options.run_type

    status = PipelineRunResult.SUCCESS
    error_message: str | None = None
    error_type: str | None = None

    try:
        await runner.run()
    except PipelineShutdownError:
        status = PipelineRunResult.SHUTDOWN
    except (BioETLError, OSError, RuntimeError, ValueError, TypeError) as e:
        status = PipelineRunResult.FAILED
        error_message = str(e)
        error_type = type(e).__name__

    completed_at, _ = derive_completion_timestamp(
        started_at=started_at,
        started_monotonic=started_monotonic,
    )

    metrics = create_metrics_extractor().extract_metrics(runner)
    result = RunResult(
        status=status,
        pipeline_name=name,
        run_id=run_id,
        run_type=run_type,
        records_fetched=int(metrics.get("records_fetched", 0)),
        records_bronze=int(metrics.get("records_bronze", 0)),
        records_silver=int(metrics.get("records_silver", 0)),
        records_gold=int(metrics.get("records_gold", 0)),
        records_quarantined=int(metrics.get("records_quarantined", 0)),
        records_filtered_out=int(metrics.get("records_filtered_out", 0)),
        started_at=started_at,
        completed_at=completed_at,
        error_message=error_message,
        error_type=error_type,
    )
    if settings.observability.metrics_enabled:
        push_metrics_to_gateway(
            run_label="bioetl",
            pipeline_name=name,
            run_type=run_type,
        )
    return result

================================================================================
File: _resource_management.py
Path: _resource_management.py
================================================================================
"""Resource management entrypoints.

Legacy managers, maintenance operations (vacuum, archive),
and inspection functions (quarantine, checkpoints).
Split from entrypoints.py per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, ParamSpec, Protocol, TypeVar

from bioetl.composition._pipeline_execution import (
    ArchiveOptions,
    VacuumOptions,
    _ensure_registrations,
)
from bioetl.composition.bootstrap import (
    bootstrap_checkpoint_manager,
    bootstrap_cleanup_service,
    bootstrap_lifecycle_service,
    bootstrap_quarantine_manager,
    load_pipeline_config,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from collections.abc import Awaitable


__all__ = [
    "archive_table",
    "get_checkpoint_manager",
    "get_lifecycle_service",
    "get_quarantine_manager",
    "inspect_quarantine",
    "list_checkpoints",
    "preview_cleanup",
    "vacuum_table",
]

_P = ParamSpec("_P")
_T = TypeVar("_T")


class QuarantineManagerProtocol(Protocol):
    """Minimal quarantine-manager contract exposed by resource management APIs."""

    def inspect(self, limit: int = 100) -> Awaitable[list[JsonDict]]:
        """Inspect quarantined records."""
        ...


class CheckpointManagerProtocol(Protocol):
    """Minimal checkpoint-manager contract exposed by resource management APIs."""

    def list_all(self) -> Awaitable[list[object]]:
        """List available checkpoints."""
        ...


class MedallionLifecycleServiceProtocol(Protocol):
    """Minimal lifecycle service contract used by maintenance entrypoints."""

    def vacuum(
        self,
        *,
        table: str,
        retention_days: int,
        dry_run: bool,
    ) -> Awaitable[int]:
        """Vacuum one table."""
        ...

    def archive(
        self,
        *,
        table: str,
        target_path: str,
        remove_source: bool,
    ) -> Awaitable[int]:
        """Archive one table."""
        ...


class CleanupPreviewProtocol(Protocol):
    """Minimal preview payload contract for cleanup dry-run operations."""

    total_files: int


def _bootstrap_registered_resource(
    bootstrap_fn: Callable[_P, _T],
    /,
    *args: _P.args,
    **kwargs: _P.kwargs,
) -> _T:
    """Run registration bootstrap before delegating to a resource builder."""
    _ensure_registrations()
    return bootstrap_fn(*args, **kwargs)


def get_quarantine_manager(pipeline: str) -> QuarantineManagerProtocol:
    """Get a quarantine manager for the given pipeline.

    Used for inspecting and managing quarantined (failed) records.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').

    Returns:
        QuarantineManagerService instance for the pipeline.

    Example:
        >>> manager = get_quarantine_manager("chembl_activity")
        >>> records = await manager.inspect(limit=100)
    """
    return _bootstrap_registered_resource(bootstrap_quarantine_manager, pipeline)


def get_checkpoint_manager(pipeline: str) -> CheckpointManagerProtocol:
    """Get a checkpoint manager for the given pipeline.

    Used for listing, loading, and managing pipeline checkpoints.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').

    Returns:
        CheckpointManagerService instance for the pipeline.

    Example:
        >>> manager = get_checkpoint_manager("chembl_activity")
        >>> checkpoints = await manager.list_all()
    """
    return _bootstrap_registered_resource(bootstrap_checkpoint_manager, pipeline)


def get_lifecycle_service() -> MedallionLifecycleServiceProtocol:
    """Get the lifecycle service for maintenance operations.

    Used for vacuum and archive operations on Delta tables.

    Returns:
        MedallionLifecycleService instance.

    Example:
        >>> service = get_lifecycle_service()
        >>> removed = await service.vacuum("chembl.activity", retention_days=7)
    """
    return _bootstrap_registered_resource(bootstrap_lifecycle_service)


async def vacuum_table(table: str, options: VacuumOptions) -> int:
    """Vacuum a Delta table to reclaim storage space.

    Args:
        table: Table name in format "provider.entity" (e.g., 'chembl.activity').
        options: Vacuum options including retention and dry_run.

    Returns:
        Number of files removed (or would be removed in dry_run mode).

    Example:
        >>> options = VacuumOptions(retention_days=30, dry_run=True)
        >>> files_removed = await vacuum_table("chembl.activity", options)
    """
    service = get_lifecycle_service()
    result: int = await service.vacuum(
        table=table,
        retention_days=options.retention_days,
        dry_run=options.dry_run,
    )
    return result


async def archive_table(table: str, options: ArchiveOptions) -> int:
    """Archive a Delta table to cold storage.

    Args:
        table: Table name to archive.
        options: Archive options including target path and remove_source.

    Returns:
        Number of files archived.

    Example:
        >>> options = ArchiveOptions(target_path="/archive/chembl", remove_source=False)
        >>> files_archived = await archive_table("chembl.activity", options)
    """
    service = get_lifecycle_service()
    result: int = await service.archive(
        table=table,
        target_path=options.target_path,
        remove_source=options.remove_source,
    )
    return result


async def preview_cleanup(pipeline: str) -> CleanupPreviewProtocol:
    """Preview what data would be cleared for a pipeline.

    Used for dry-run mode of rebuild/backfill operations.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').

    Returns:
        CleanupPreview with information about what would be cleared.

    Example:
        >>> preview = await preview_cleanup("chembl_activity")
        >>> preview.total_files  # Number of files to clear
        42
    """
    _ensure_registrations()
    pipeline_cfg = load_pipeline_config(pipeline)
    cleanup_service = bootstrap_cleanup_service()
    silver_table = (
        pipeline_cfg.silver_table
        or f"{pipeline_cfg.provider}.{pipeline_cfg.entity_type}"
    )
    gold_table = (
        pipeline_cfg.gold_table or f"{pipeline_cfg.provider}.{pipeline_cfg.entity_type}"
    )
    return await cleanup_service.preview(
        silver_table=silver_table,
        gold_table=gold_table,
    )


async def inspect_quarantine(
    pipeline: str, limit: int = 100
) -> list[JsonDict]:  # Any: quarantine record has heterogeneous values
    """Inspect quarantined records for a pipeline.

    Convenience function for quick quarantine inspection.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').
        limit: Maximum number of records to return.

    Returns:
        List of quarantine record dictionaries.

    Example:
        >>> records = await inspect_quarantine("chembl_activity", limit=50)
        >>> [rec['error_code'] for rec in records]  # List of error codes
        ['DQ_MISSING_FIELD', 'DQ_INVALID_SMILES']
    """
    manager = get_quarantine_manager(pipeline)
    records: list[
        JsonDict  # Any: factory wiring; concrete types resolved at runtime
    ] = await manager.inspect(  # Any: factory wiring; concrete types resolved at runtime
        limit=limit
    )  # Any: factory wiring; concrete types resolved at runtime
    return records


async def list_checkpoints(pipeline: str) -> list[str]:
    """List all checkpoints for a pipeline.

    Convenience function for quick checkpoint listing.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').

    Returns:
        List of checkpoint identifiers.

    Example:
        >>> checkpoints = await list_checkpoints("chembl_activity")
        >>> checkpoints  # List of checkpoint identifiers
        ['checkpoint_2024_01_15', 'checkpoint_2024_01_16']
    """
    manager = get_checkpoint_manager(pipeline)
    checkpoints: list[str] = await manager.list_all()
    return checkpoints

================================================================================
File: _services.py
Path: _services.py
================================================================================
"""Service factory entrypoints for CLI and other interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services import (
    BronzeCleanupResult,
    BronzeCleanupService,
    ConfigService,
    ContractMigrationService,
    ExportService,
    HealthService,
    LineageInspectionService,
    MetricsService,
    ObservabilityWorkflowService,
    PipelineRunnerService,
    QuarantineService,
    RunManifestInspectionService,
    VacuumService,
)
from bioetl.application.services.audit_inspection_service import AuditInspectionService
from bioetl.application.services.checkpoint_service import CheckpointService
from bioetl.application.services.lock_service import LockService
from bioetl.composition.bootstrap import (
    HealthServerDependencies,
    bootstrap_adr_service,
    bootstrap_audit_inspection_service,
    bootstrap_bronze_cleanup_service,
    bootstrap_checkpoint_service,
    bootstrap_config_service,
    bootstrap_contract_migration_service,
    bootstrap_health_server_dependencies,
    bootstrap_health_service,
    bootstrap_lineage_service,
    bootstrap_lock_service,
    bootstrap_metrics_service,
    bootstrap_observability_workflow_service,
    bootstrap_pipeline_runner_service,
    bootstrap_quarantine_port,
    bootstrap_quarantine_service,
    bootstrap_run_manifest_service,
    bootstrap_vacuum_service,
)
from bioetl.composition.bootstrap.cli.storage import bootstrap_export_service

if TYPE_CHECKING:
    from bioetl.composition import PipelineRegistry
    from bioetl.domain.ports import AdrServicePort, QuarantinePort
    from bioetl.domain.workflow import WorkflowConfig


__all__ = [
    "cleanup_bronze",
    "get_adr_service",
    "get_audit_service",
    "get_bronze_cleanup_service",
    "get_checkpoint_service",
    "get_config_service",
    "get_contract_migration_service",
    "get_export_service",
    "get_health_server_dependencies",
    "get_health_service",
    "get_lineage_service",
    "get_lock_service",
    "get_metrics_service",
    "get_observability_workflow_service",
    "get_pipeline_runner_service",
    "get_quarantine_port",
    "get_quarantine_service",
    "get_run_manifest_service",
    "get_vacuum_service",
    "load_workflow_config",
]


def _ensure_registrations(registry: PipelineRegistry | None = None) -> None:
    """Ensure providers and pipelines are registered lazily to avoid cycles."""
    from bioetl.composition._pipeline_execution import (
        _ensure_registrations as ensure_registrations_impl,
    )

    ensure_registrations_impl(registry=registry)


def get_checkpoint_service() -> CheckpointService:
    """Get a checkpoint service for administrative operations.

    Used for listing, deleting, and inspecting checkpoints across all pipelines.
    This is the recommended way to manage checkpoints from CLI or other interfaces.

    Returns:
        CheckpointService instance.
    """
    _ensure_registrations()
    return bootstrap_checkpoint_service()


def get_audit_service() -> AuditInspectionService:
    """Get an audit inspection service for operator diagnostics operations."""
    _ensure_registrations()
    return bootstrap_audit_inspection_service()


def get_quarantine_service() -> QuarantineService:
    """Get a quarantine service for administrative operations.

    Used for inspecting, replaying, and purging quarantine records.
    This is the recommended way to manage quarantine from CLI or other interfaces.

    Returns:
        QuarantineService instance.
    """
    _ensure_registrations()
    return bootstrap_quarantine_service()


def get_bronze_cleanup_service() -> BronzeCleanupService:
    """Get a bronze cleanup service for maintenance operations.

    Used for Bronze layer retention cleanup per RULES.md §2.1.
    This is the recommended way to manage Bronze cleanup from CLI.
    """
    _ensure_registrations()
    return bootstrap_bronze_cleanup_service()


def get_vacuum_service() -> VacuumService:
    """Get a vacuum service for batch vacuum operations.

    Used for vacuuming multiple Delta tables at once.
    This is the recommended way to vacuum tables from CLI.
    """
    _ensure_registrations()
    return bootstrap_vacuum_service()


def get_export_service() -> ExportService:
    """Get an export service for exporting Delta Lake tables.

    Used for exporting Silver/Gold Delta tables to CSV, XLSX, and TSV formats.
    This is the recommended way to export tables from CLI.
    """
    _ensure_registrations()
    return bootstrap_export_service()


def get_lock_service() -> LockService:
    """Get a lock service for administrative lock operations.

    Used for releasing stale locks and checking lock status.
    This is the recommended way to manage locks from CLI.

    Note: Uses in-memory locking which only affects the current process.
    Lock operations are local to this process instance.
    """
    _ensure_registrations()
    return bootstrap_lock_service()


async def cleanup_bronze(
    retention_days: int = 90,
    dry_run: bool = False,
) -> BronzeCleanupResult:
    """Clean up old Bronze files based on retention policy.

    Convenience function for Bronze cleanup operations.
    Removes files older than the specified retention period.
    """
    service = get_bronze_cleanup_service()
    result: BronzeCleanupResult = await service.cleanup(
        retention_days=retention_days,
        dry_run=dry_run,
    )
    return result


def get_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Get a pipeline runner service for universal pipeline execution.

    This is the recommended way to run pipelines programmatically from
    any interface (CLI, REST API, Airflow, etc.). The service provides
    a clean, stateless API for pipeline execution.

    Returns:
        PipelineRunnerService instance ready for use.

    Example:
        >>> from bioetl.application.services import RunOptions
        >>> service = get_pipeline_runner_service()
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> result = await service.run("chembl_activity", options=options)
        >>> if result.is_success:
        ...     logger.info("pipeline_success", records_silver=result.records_silver)
    """
    _ensure_registrations(registry=registry)
    return bootstrap_pipeline_runner_service(registry=registry)


def get_config_service() -> ConfigService:
    """Get a configuration service for accessing application configuration.

    Provides a clean interface for configuration access from CLI or other
    interfaces. Abstracts infrastructure configuration loading.

    Returns:
        ConfigService instance for configuration operations.

    Example:
        >>> service = get_config_service()
        >>> settings = service.get_settings()
        >>> logger.info("environment", env=settings.env)
        >>> config = service.load_pipeline_config("chembl_activity")
        >>> logger.info("pipeline", provider=config.provider)
    """
    _ensure_registrations()
    return bootstrap_config_service()


def load_workflow_config(name: str) -> WorkflowConfig:
    """Load workflow YAML through the canonical composition service seam."""
    from bioetl.infrastructure.config.workflow_config_api import (
        load_workflow_config as load_workflow_config_impl,
    )

    return load_workflow_config_impl(name)


def get_contract_migration_service() -> ContractMigrationService:
    """Get the contract migration planner service."""
    _ensure_registrations()
    return bootstrap_contract_migration_service()


def get_run_manifest_service() -> RunManifestInspectionService:
    """Get a run-manifest inspection service for control-plane operations."""
    _ensure_registrations()
    return bootstrap_run_manifest_service()


def get_lineage_service() -> LineageInspectionService:
    """Get a lineage inspection service for traceability operations."""
    _ensure_registrations()
    return bootstrap_lineage_service()


def get_health_service() -> HealthService:
    """Get a health service for checking provider health.

    Provides a clean interface for health checking from CLI or other
    interfaces. Abstracts data source factory and adapter creation.

    Returns:
        HealthService instance for health check operations.

    Example:
        >>> service = get_health_service()
        >>> summary = await service.check_providers()
        >>> if summary.all_healthy:
        ...     logger.info("All providers healthy")
        >>> else:
        ...     for name, result in summary.results.items():
        ...         if result.is_unhealthy:
        ...             logger.error("Provider unhealthy", provider=name, error=result.error)
    """
    _ensure_registrations()
    return bootstrap_health_service()


def get_observability_workflow_service() -> ObservabilityWorkflowService:
    """Get workflow-level observability diagnostics helpers."""
    _ensure_registrations()
    return bootstrap_observability_workflow_service()


def get_health_server_dependencies() -> HealthServerDependencies:
    """Get dependencies for HealthServer via composition root.

    Returns HealthServerDependencies with PrometheusMetrics and
    ProviderHealthMonitor. HealthServer is created in interfaces layer.

    Returns:
        Health server dependencies.
    """
    _ensure_registrations()
    return bootstrap_health_server_dependencies()


def get_metrics_service() -> MetricsService:
    """Get a metrics service for managing the Prometheus metrics server.

    Provides a clean interface for metrics server management from CLI or
    other interfaces. Abstracts infrastructure metrics server operations.

    Returns:
        MetricsService instance for metrics server operations.

    Example:
        >>> service = get_metrics_service()
        >>> result = service.start(port=8000)
        >>> if result.success:
        ...     logger.info("Metrics server started", port=result.port)
        >>> status = service.get_status()
        >>> logger.info("Server status", running=status.running)
    """
    _ensure_registrations()
    return bootstrap_metrics_service()


def get_adr_service() -> AdrServicePort:
    """Get ADR service (port) for ADR management operations.

    Provides read-only access to ADR documents and validation.

    Returns:
        AdrServicePort instance.
    """
    _ensure_registrations()
    return bootstrap_adr_service()


def get_quarantine_port() -> QuarantinePort:
    """Get the shared quarantine port for direct quarantine operations.

    This provides direct access to the QuarantinePort for low-level
    quarantine operations. For most use cases, prefer get_quarantine_service()
    which provides a higher-level interface.

    Returns:
        QuarantinePort instance for quarantine operations.

    Example:
        >>> port = get_quarantine_port()
        >>> records = await port.inspect("chembl_activity", limit=10)
    """
    _ensure_registrations()
    return bootstrap_quarantine_port()

================================================================================
File: __init__.py
Path: bootstrap\__init__.py
================================================================================
"""Bootstrap package for BioETL Composition Root.

Provides modular bootstrap functions organized by context:

- **assembly**: Shared infrastructure components (ports, storage adapters)
  without side-effects. Used by both CLI and runtime.
- **cli**: Bootstrap functions for CLI-only commands (inspect, list, maintenance,
  admin operations). These use NoOp observability implementations.
- **runtime**: Bootstrap functions for actual pipeline execution (pipeline run,
  composite pipelines). These use full observability stack.

Import Rules:
- runtime MUST NOT import from cli
- cli MAY import from runtime (for runner access)
- Both MUST import shared code from assembly

Public names are resolved lazily so light-weight imports, such as test fixtures
that only need a helper submodule, do not pay the cost of importing the entire
runtime bootstrap tree.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_BOOTSTRAP_CLI_MODULE = "bioetl.composition.bootstrap.cli"
_BOOTSTRAP_ASSEMBLY_MODULE = "bioetl.composition.bootstrap.assembly"
_BOOTSTRAP_RUNTIME_MODULE = "bioetl.composition.bootstrap.runtime"

__all__ = [
    "HealthServerDependencies",
    "bootstrap_adr_service",
    "bootstrap_audit_inspection_service",
    "bootstrap_bronze_cleanup_service",
    "bootstrap_checkpoint_manager",
    "bootstrap_checkpoint_service",
    "bootstrap_cleanup_service",
    "bootstrap_composite_checkpoint_port",
    "bootstrap_composite_runner",
    "bootstrap_config_service",
    "bootstrap_contract_migration_service",
    "bootstrap_export_service",
    "bootstrap_health_server_dependencies",
    "bootstrap_health_service",
    "bootstrap_lifecycle_service",
    "bootstrap_lineage_service",
    "bootstrap_lock_service",
    "bootstrap_logger_port",
    "bootstrap_metrics_port",
    "bootstrap_metrics_service",
    "bootstrap_observability_workflow_service",
    "bootstrap_pipeline_runner",
    "bootstrap_pipeline_runner_service",
    "bootstrap_quarantine_manager",
    "bootstrap_quarantine_port",
    "bootstrap_quarantine_service",
    "bootstrap_run_manifest_service",
    "bootstrap_vacuum_service",
    "load_composite_config",
    "load_pipeline_config",
    "maybe_start_metrics_server",
]

_PUBLIC_EXPORTS: dict[str, str] = {
    "HealthServerDependencies": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_adr_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_audit_inspection_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_bronze_cleanup_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_checkpoint_manager": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_checkpoint_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_cleanup_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_composite_checkpoint_port": _BOOTSTRAP_ASSEMBLY_MODULE,
    "bootstrap_composite_runner": _BOOTSTRAP_RUNTIME_MODULE,
    "bootstrap_config_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_contract_migration_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_export_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_health_server_dependencies": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_health_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_lifecycle_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_lineage_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_lock_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_logger_port": _BOOTSTRAP_RUNTIME_MODULE,
    "bootstrap_metrics_port": _BOOTSTRAP_RUNTIME_MODULE,
    "bootstrap_metrics_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_observability_workflow_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_pipeline_runner": _BOOTSTRAP_RUNTIME_MODULE,
    "bootstrap_pipeline_runner_service": _BOOTSTRAP_RUNTIME_MODULE,
    "bootstrap_quarantine_manager": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_quarantine_port": _BOOTSTRAP_ASSEMBLY_MODULE,
    "bootstrap_quarantine_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_run_manifest_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_vacuum_service": _BOOTSTRAP_CLI_MODULE,
    "load_composite_config": _BOOTSTRAP_RUNTIME_MODULE,
    "load_pipeline_config": "bioetl.infrastructure.config.pipeline_config_api",
    "maybe_start_metrics_server": _BOOTSTRAP_RUNTIME_MODULE,
}

# ``importlib.reload`` preserves the existing module dict. Clear any cached lazy
# exports so post-reload attribute access still flows through ``__getattr__``.
for _cached_export_name in tuple(_PUBLIC_EXPORTS):
    globals().pop(_cached_export_name, None)


def __getattr__(
    name: str,
) -> Any:  # Any: lazy re-export preserves the original symbol type at lookup time.
    """Resolve bootstrap re-exports lazily to avoid eager runtime imports."""
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from bioetl.infrastructure.compat.pandera_compat import (
        apply_pandera_typing_compat_if_needed,
    )

    apply_pandera_typing_compat_if_needed()
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy re-exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))

================================================================================
File: __init__.py
Path: bootstrap\assembly\__init__.py
================================================================================
"""Assembly module for shared bootstrap infrastructure.

Contains bootstrap functions for infrastructure components that are used by
both CLI and runtime contexts. These functions have no side-effects and
create pure infrastructure adapters.

Components:
- checkpoint: Checkpoint and quarantine port creation
- storage: Storage adapter assembly for I/O operations

Note:
    This module should NOT contain any NoOp implementations or CLI-specific
    logic. It provides neutral building blocks for higher-level bootstrap.
"""

from __future__ import annotations

from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_checkpoint_port,
    bootstrap_composite_checkpoint_port,
    bootstrap_quarantine_port,
)
from bioetl.composition.bootstrap.assembly.storage import (
    bootstrap_storage_adapter,
)

__all__ = [
    "bootstrap_checkpoint_port",
    "bootstrap_composite_checkpoint_port",
    "bootstrap_quarantine_port",
    "bootstrap_storage_adapter",
]

================================================================================
File: checkpoint.py
Path: bootstrap\assembly\checkpoint.py
================================================================================
"""Bootstrap functions for checkpoint and quarantine ports.

Provides basic port creation for checkpoint and quarantine infrastructure.
These are low-level building blocks used by both CLI and runtime.

Note:
    Higher-level managers and services are created in cli/ module
    since they require additional context (pipeline_name, run_id, etc.)
    and use NoOp observability for CLI operations.
"""

from __future__ import annotations

from bioetl.domain.ports import (
    CheckpointPort,
    CompositeCheckpointPort,
    LoggerPort,
    QuarantinePort,
)
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.quarantine import UnifiedQuarantineAdapter
from bioetl.infrastructure.storage.support.checkpoint_writer import (
    FileCompositeCheckpointWriter,
)

__all__ = [
    "bootstrap_checkpoint_compatibility_service",
    "bootstrap_checkpoint_port",
    "bootstrap_composite_checkpoint_port",
    "bootstrap_quarantine_port",
]


def bootstrap_quarantine_port() -> QuarantinePort:
    """Create a quarantine port implementation for record quarantine storage.

    Creates a UnifiedQuarantineAdapter adapter using centralized quarantine_path
    from settings (data_dir/quarantine) for unified quarantine storage
    independent of entity paths.

    Layer: Returns domain port implementation (QuarantinePort).

    Returns:
        QuarantinePort implementation for quarantine operations.
    """
    settings = get_settings()
    quarantine = UnifiedQuarantineAdapter(base_path=str(settings.quarantine_path))
    assert isinstance(quarantine, QuarantinePort), (
        f"UnifiedQuarantineAdapter must implement QuarantinePort, got {type(quarantine)}"
    )
    return quarantine


def bootstrap_checkpoint_port(pipeline_name: str) -> CheckpointPort:
    """Create a checkpoint port implementation for pipeline state persistence.

    Creates a LocalCheckpointAdapter adapter for the specified pipeline using
    the checkpoint_path from settings.

    Layer: Returns domain port implementation (CheckpointPort).

    Args:
        pipeline_name: Name of the pipeline for checkpoint scoping.

    Returns:
        CheckpointPort implementation for checkpoint operations.
    """
    settings = get_settings()
    checkpoint = LocalCheckpointAdapter(
        base_path=settings.checkpoint_path,
        pipeline_name=pipeline_name,
    )
    assert isinstance(checkpoint, CheckpointPort), (
        f"LocalCheckpointAdapter must implement CheckpointPort, got {type(checkpoint)}"
    )
    return checkpoint


def bootstrap_composite_checkpoint_port() -> CompositeCheckpointPort:
    """Create a composite checkpoint port implementation for runtime resume state.

    Composite checkpoints live under the canonical checkpoint root with a
    dedicated ``composite/`` subdirectory so runtime and operational tooling
    share one consistent storage layout.

    Returns:
        CompositeCheckpointPort implementation for composite checkpoint operations.
    """
    settings = get_settings()
    checkpoint = FileCompositeCheckpointWriter(
        checkpoint_dir=settings.checkpoint_path / "composite",
    )
    assert isinstance(checkpoint, CompositeCheckpointPort), (
        "FileCompositeCheckpointWriter must implement CompositeCheckpointPort, "
        f"got {type(checkpoint)}"
    )
    return checkpoint


def bootstrap_checkpoint_compatibility_service(logger: LoggerPort) -> object:
    """Create checkpoint compatibility service for DQ contract validation.

    Creates a CheckpointCompatibilityService for validating checkpoint compatibility
    based on Data Quality contract hashes and pipeline versions.

    Args:
        logger: Logger instance for observability.

    Returns:
        CheckpointCompatibilityService instance.
    """
    from bioetl.application.services.checkpoint_compatibility_service import (
        CheckpointCompatibilityService,
    )

    service = CheckpointCompatibilityService(logger=logger)
    return service

================================================================================
File: metrics_service.py
Path: bootstrap\assembly\metrics_service.py
================================================================================
"""Shared metrics-service assembly helpers for composition bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.metrics_service import MetricsService
from bioetl.infrastructure.observability.metrics_publisher_adapter import (
    MetricsPublisherAdapter,
)
from bioetl.infrastructure.observability.metrics_server_adapter import (
    MetricsServerAdapter,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, TracingPort

__all__ = ["create_metrics_service"]


def create_metrics_service(
    *,
    logger: LoggerPort | None = None,
    tracer: TracingPort | None = None,
) -> MetricsService:
    """Build a metrics service with a composition-owned server adapter."""
    resolved_logger = logger if logger is not None else NoOpLogger()
    return MetricsService(
        logger=resolved_logger,
        tracer=tracer,
        _server=MetricsServerAdapter(logger=resolved_logger),
        _publisher=MetricsPublisherAdapter(logger=resolved_logger),
    )

================================================================================
File: storage.py
Path: bootstrap\assembly\storage.py
================================================================================
"""Bootstrap functions for storage adapter assembly.

Provides storage adapter creation for both CLI preview operations and
composite pipeline execution. This is a shared building block.

Note:
    This function uses NoOpLogger internally as observability is not
    required for storage adapter assembly. The actual observability
    is provided at a higher level (BatchWriter, RecordProcessor).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.bootstrap.cli.noop import create_noop_observability_bundle
from bioetl.composition.factories.storage import StorageAdapter
from bioetl.composition.factories.storage.resilience import (
    create_silver_atomic_retry_policy,
    create_silver_merge_resilience_policy,
)
from bioetl.domain.types import RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.config import Settings, get_settings
from bioetl.infrastructure.control_plane import FileLineageStore
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta.resilience import SilverMergeResiliencePolicy
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort

__all__ = [
    "bootstrap_storage_adapter",
]


def _create_composite_metadata_services(
    *,
    settings: Settings,
    output_dir: Path,
    logger: LoggerPort,
    metrics: MetricsPort,
) -> tuple[
    MetadataWriter,
    FileLineageStore,
    MetadataCoordinator,
    SilverMergeResiliencePolicy,
]:
    """Create shared metadata services and resilience policy for storage bootstrap."""
    atomic_retry_policy = create_silver_atomic_retry_policy(settings)
    merge_resilience_policy = create_silver_merge_resilience_policy(settings)
    metadata_writer = MetadataWriter(
        logger=logger,
        atomic_replace_retry_policy=atomic_retry_policy,
        metrics=metrics,
    )
    lineage_store = FileLineageStore(base_path=output_dir / "control" / "lineage")
    run_context = RunContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime.now(UTC),
        pipeline_name="composite",
        provider="composite",
        entity="merged",
    )
    return (
        metadata_writer,
        lineage_store,
        MetadataCoordinator(run_context=run_context),
        merge_resilience_policy,
    )


def _create_csv_exporters(
    *,
    output_dir: Path,
    logger: LoggerPort,
    enable_csv_export: bool,
) -> tuple[CsvExporter | None, CsvExporter | None]:
    """Create optional CSV exporters for silver and gold layers."""
    if not enable_csv_export:
        return None, None
    return (
        CsvExporter(base_path=str(output_dir / "silver"), logger=logger),
        CsvExporter(base_path=str(output_dir / "gold"), logger=logger),
    )


def bootstrap_storage_adapter(*, enable_csv_export: bool = False) -> StorageAdapter:
    """Create a storage adapter for CLI and composite pipeline operations.

    Creates a StorageAdapter suitable for preview operations and composite
    pipelines. CSV export is disabled by default for read-only inspection
    but can be enabled for composite pipelines that need CSV output.

    Uses NoOpLogger since this is for CLI preview operations without observability.

    Layer: Returns infrastructure adapter (StorageAdapter) containing
    Bronze, Silver, and Gold writers.

    Note:
        Lock validation is performed at Application layer (BatchWriter)
        per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.

    Args:
        enable_csv_export: If True, creates CsvExporters for Silver and Gold
            layers. Used by composite pipelines that need CSV output.

    Returns:
        StorageAdapter configured for the current environment.
    """
    settings = get_settings()
    noop_logger, noop_metrics, noop_tracing = create_noop_observability_bundle()

    # ADR-025: Use data/output/ hierarchy for consistency with pipeline configs
    output_dir = Path(settings.data_dir) / "output"
    (
        metadata_writer,
        lineage_store,
        metadata_coordinator,
        merge_resilience_policy,
    ) = _create_composite_metadata_services(
        settings=settings,
        output_dir=output_dir,
        logger=noop_logger,
        metrics=noop_metrics,
    )
    silver_csv_exporter, gold_csv_exporter = _create_csv_exporters(
        output_dir=output_dir,
        logger=noop_logger,
        enable_csv_export=enable_csv_export,
    )

    return StorageAdapter(
        bronze_writer=BronzeWriter(
            base_path=output_dir / "bronze",  # data/output/bronze
            logger=noop_logger,
            metrics=noop_metrics,
            tracing=noop_tracing,
            save_json=False,
            json_path=None,
        ),
        silver_writer=SilverWriter(
            base_path=output_dir / "silver",  # data/output/silver
            logger=noop_logger,
            tracing=noop_tracing,
            csv_exporter=silver_csv_exporter,
            metadata_writer=metadata_writer,
            metadata_coordinator=metadata_coordinator,
            lineage_store=lineage_store,
            merge_resilience_policy=merge_resilience_policy,
        ),
        gold_writer=GoldWriter(
            base_path=output_dir / "gold",  # data/output/gold
            logger=noop_logger,
            tracing=noop_tracing,
            csv_exporter=gold_csv_exporter,
            metadata_writer=metadata_writer,
            metadata_coordinator=metadata_coordinator,
            lineage_store=lineage_store,
        ),
    )

================================================================================
File: __init__.py
Path: bootstrap\cli\__init__.py
================================================================================
"""CLI bootstrap module for administrative operations.

Contains bootstrap functions for CLI-only commands:
- Inspection: quarantine inspect, checkpoint list
- Maintenance: vacuum, archive, bronze cleanup
- Admin: lock management, health checks, metrics server
- Configuration: settings access, pipeline config loading

These functions use NoOp observability implementations since CLI operations
don't require full runtime observability (no run_id, no metrics collection).

IMPORTANT: This module MUST NOT be imported by bootstrap/runtime/.
CLI may import from runtime for runner access, but not vice versa.

Components:
- checkpoint: Manager and service bootstrap for checkpoint operations
- config: ConfigService bootstrap
- health: HealthService and health server dependencies
- lock: LockService bootstrap
- metrics: MetricsService for server management (not metrics collection)
- storage: Maintenance services (cleanup, vacuum, export, lifecycle)
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.composition.bootstrap.cli.health import (
        HealthServerDependencies,
        bootstrap_health_server_dependencies,
        bootstrap_health_service,
    )

_CLI_HEALTH_MODULE = "bioetl.composition.bootstrap.cli.health"
_CLI_CHECKPOINT_MODULE = "bioetl.composition.bootstrap.cli.checkpoint"
_CLI_STORAGE_MODULE = "bioetl.composition.bootstrap.cli.storage"
_CLI_NOOP_MODULE = "bioetl.composition.bootstrap.cli.noop"


_CLI_EXPORT_MODULES = {
    "HealthServerDependencies": _CLI_HEALTH_MODULE,
    "bootstrap_adr_service": "bioetl.composition.bootstrap.cli.adr",
    "bootstrap_audit_inspection_service": _CLI_CHECKPOINT_MODULE,
    "bootstrap_bronze_cleanup_service": _CLI_STORAGE_MODULE,
    "bootstrap_checkpoint_manager": _CLI_CHECKPOINT_MODULE,
    "bootstrap_checkpoint_service": _CLI_CHECKPOINT_MODULE,
    "bootstrap_cleanup_service": _CLI_STORAGE_MODULE,
    "bootstrap_config_service": "bioetl.composition.bootstrap.cli.config",
    "bootstrap_contract_migration_service": _CLI_STORAGE_MODULE,
    "bootstrap_export_service": _CLI_STORAGE_MODULE,
    "bootstrap_health_server_dependencies": _CLI_HEALTH_MODULE,
    "bootstrap_health_service": _CLI_HEALTH_MODULE,
    "bootstrap_lifecycle_service": _CLI_STORAGE_MODULE,
    "bootstrap_lineage_service": "bioetl.composition.bootstrap.cli.lineage",
    "bootstrap_lock_service": "bioetl.composition.bootstrap.cli.lock",
    "bootstrap_metrics_service": "bioetl.composition.bootstrap.cli.metrics",
    "bootstrap_observability_workflow_service": _CLI_CHECKPOINT_MODULE,
    "bootstrap_quarantine_manager": _CLI_CHECKPOINT_MODULE,
    "bootstrap_quarantine_service": _CLI_CHECKPOINT_MODULE,
    "bootstrap_run_manifest_service": "bioetl.composition.bootstrap.cli.run_manifest",
    "bootstrap_vacuum_service": _CLI_STORAGE_MODULE,
    "create_noop_logger": _CLI_NOOP_MODULE,
    "create_noop_metrics": _CLI_NOOP_MODULE,
    "create_noop_observability_bundle": _CLI_NOOP_MODULE,
    "create_noop_tracing": _CLI_NOOP_MODULE,
}


def __getattr__(name: str) -> object:
    """Load CLI bootstrap helpers on demand to avoid package import cycles."""
    module_name = _CLI_EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name)
    return getattr(module, name)


__all__ = [
    "HealthServerDependencies",
    "bootstrap_adr_service",
    "bootstrap_audit_inspection_service",
    "bootstrap_bronze_cleanup_service",
    "bootstrap_checkpoint_manager",
    "bootstrap_checkpoint_service",
    "bootstrap_cleanup_service",
    "bootstrap_config_service",
    "bootstrap_contract_migration_service",
    "bootstrap_export_service",
    "bootstrap_health_server_dependencies",
    "bootstrap_health_service",
    "bootstrap_lifecycle_service",
    "bootstrap_lineage_service",
    "bootstrap_lock_service",
    "bootstrap_metrics_service",
    "bootstrap_observability_workflow_service",
    "bootstrap_quarantine_manager",
    "bootstrap_quarantine_service",
    "bootstrap_run_manifest_service",
    "bootstrap_vacuum_service",
    "create_noop_logger",
    "create_noop_metrics",
    "create_noop_observability_bundle",
    "create_noop_tracing",
]

================================================================================
File: adr.py
Path: bootstrap\cli\adr.py
================================================================================
"""Bootstrap functions for ADR CLI operations.

Provides a factory for the ADR service port used by CLI commands and
other interfaces. Uses default repository-relative path for ADR docs.
"""

from __future__ import annotations

from typing import cast

from bioetl.domain.ports import AdrServicePort
from bioetl.infrastructure.adr.fs_adr_service import FsAdrService

__all__ = ["bootstrap_adr_service"]


def bootstrap_adr_service() -> AdrServicePort:
    """Bootstrap ADR service using default filesystem implementation.

    Returns:
        AdrServicePort wired to the repository docs folder.
    """

    # Default path is used inside FsAdrService; allow future injection via env
    service = FsAdrService()
    return cast(AdrServicePort, service)

================================================================================
File: checkpoint.py
Path: bootstrap\cli\checkpoint.py
================================================================================
"""Bootstrap functions for checkpoint and quarantine CLI operations.

Contains bootstrap functions for checkpoint manager, checkpoint service,
quarantine manager, and quarantine service. Used for CLI inspection
and administrative operations.

Note:
    CLI diagnostics use NoOp logging by default. Metrics and tracing are
    resolved through composition so operator workflows can publish bounded
    observability signals when those capabilities are enabled.
"""

from __future__ import annotations

from uuid import uuid4

from bioetl.application.core.lifecycle.checkpoint_manager import (
    CheckpointManagerService,
)
from bioetl.application.services.admin_runtime_api import QuarantineManagerService
from bioetl.application.services.audit_inspection_service import AuditInspectionService
from bioetl.application.services.checkpoint_service import CheckpointService
from bioetl.application.services.control_plane.run_manifest_inspection_service import (
    RunManifestInspectionService,
)
from bioetl.application.services.observability_workflow_service import (
    ObservabilityWorkflowService,
)
from bioetl.application.services.quarantine_service import QuarantineService
from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_checkpoint_compatibility_service,
    bootstrap_checkpoint_port,
    bootstrap_quarantine_port,
)
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.bootstrap.cli.run_manifest import (
    bootstrap_run_manifest_service,
)
from bioetl.composition.factories.storage.audit import create_audit_port
from bioetl.composition.observability_resolution import (
    resolve_metrics_port,
    resolve_tracing_port,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.infrastructure.config import get_settings

__all__ = [
    "bootstrap_audit_inspection_service",
    "bootstrap_checkpoint_manager",
    "bootstrap_checkpoint_service",
    "bootstrap_observability_workflow_service",
    "bootstrap_quarantine_manager",
    "bootstrap_quarantine_service",
]


def bootstrap_quarantine_manager(pipeline_name: str) -> QuarantineManagerService:
    """Bootstrap QuarantineManagerService for CLI inspection operations.

    Creates a QuarantineManagerService for quarantine inspection and reporting.
    Used by CLI for `quarantine inspect` and similar commands.

    Args:
        pipeline_name: Name of the pipeline to inspect.

    Returns:
        QuarantineManagerService configured for the specified pipeline.
    """
    quarantine_port = bootstrap_quarantine_port()
    return QuarantineManagerService(
        quarantine_port=quarantine_port,
        pipeline_name=pipeline_name,
    )


def bootstrap_checkpoint_manager(pipeline_name: str) -> CheckpointManagerService:
    """Bootstrap CheckpointManagerService for CLI inspection operations.

    Creates a minimal CheckpointManagerService for checkpoint listing and inspection.
    Uses NoOpLogger and dummy run_id since CLI operations don't need full
    pipeline execution context.

    Args:
        pipeline_name: Name of the pipeline (used for context, may be ignored
            for operations like list_all).

    Returns:
        CheckpointManagerService configured for CLI inspection.
    """
    checkpoint_port = bootstrap_checkpoint_port(pipeline_name)
    noop_logger = create_noop_logger()

    compatibility_service = bootstrap_checkpoint_compatibility_service(noop_logger)

    return CheckpointManagerService(
        checkpoint_port=checkpoint_port,
        logger=noop_logger,
        pipeline_name=pipeline_name,
        run_id=RunID(uuid4()),  # Dummy run_id for CLI inspection
        resume=False,
        checkpoint_compatibility_service=compatibility_service,
    )


def bootstrap_checkpoint_service() -> CheckpointService:
    """Bootstrap CheckpointService for CLI administrative operations.

    Creates a CheckpointService for checkpoint listing, deletion, and inspection.
    Uses a generic checkpoint port that can list all pipelines.

    Returns:
        CheckpointService configured for CLI operations.
    """
    settings = get_settings()
    # Use empty pipeline name for global operations
    checkpoint_port = LocalCheckpointAdapter(
        base_path=settings.checkpoint_path,
        pipeline_name="",
    )
    noop_logger = create_noop_logger()

    return CheckpointService(
        checkpoint_port=checkpoint_port,
        logger=noop_logger,
    )


def bootstrap_audit_inspection_service() -> AuditInspectionService:
    """Bootstrap AuditInspectionService for operator diagnostics workflows."""
    settings = get_settings()
    noop_logger = create_noop_logger()
    audit_port = create_audit_port(
        settings=settings,
        logger=noop_logger,
        metrics=resolve_metrics_port(metrics=None, settings=settings),
        tracing=resolve_tracing_port(
            tracer=None,
            settings=settings,
            service_name="bioetl.audit_admin",
        ),
    )
    return AuditInspectionService(audit_port=audit_port)


def bootstrap_observability_workflow_service() -> ObservabilityWorkflowService:
    """Bootstrap canonical audit/checkpoint diagnostics workflows."""
    settings = get_settings()
    checkpoint_service = bootstrap_checkpoint_service()
    audit_service = bootstrap_audit_inspection_service()
    run_manifest_service: RunManifestInspectionService = (
        bootstrap_run_manifest_service()
    )
    return ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=run_manifest_service,
        tracer=resolve_tracing_port(
            tracer=None,
            settings=settings,
            service_name="bioetl.diagnostics",
        ),
    )


def bootstrap_quarantine_service() -> QuarantineService:
    """Bootstrap QuarantineService for CLI administrative operations.

    Creates a QuarantineService for quarantine inspection, replay, and purge.

    Returns:
        QuarantineService configured for CLI operations.
    """
    settings = get_settings()
    quarantine_port = bootstrap_quarantine_port()
    noop_logger = create_noop_logger()
    metrics = resolve_metrics_port(metrics=None, settings=settings)

    return QuarantineService(
        quarantine_port=quarantine_port,
        logger=noop_logger,
        metrics=metrics,
        tracer=resolve_tracing_port(
            tracer=None,
            settings=settings,
            service_name="bioetl.quarantine_admin",
        ),
    )

================================================================================
File: config.py
Path: bootstrap\cli\config.py
================================================================================
"""Bootstrap `ConfigService` for CLI configuration commands."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, cast

from bioetl.application.services import ConfigService
from bioetl.application.services.config_dq_service import ConfigDQService
from bioetl.application.services.control_plane.effective_config_service import (
    create_effective_config_service,
)
from bioetl.composition import get_default_registry
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.domain.ports import DomainConfigMapperPort, SettingsLoaderPort
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.config.dq_contract_config_loader import (
    load_dq_config_for_pipeline,
)
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config

__all__ = ["bootstrap_config_service"]

if TYPE_CHECKING:
    from bioetl.composition import PipelineRegistry


def _pipeline_yaml_for_dq(pipeline_name: str) -> JsonDict:
    config = load_pipeline_config(pipeline_name)
    if hasattr(config, "model_dump"):
        pipeline_payload: JsonDict = config.model_dump()
        return pipeline_payload
    if isinstance(config, Mapping):
        return dict(config)
    raise TypeError("Pipeline YAML config must provide model_dump() or be a mapping")


def bootstrap_config_service(
    *,
    registry: PipelineRegistry | None = None,
) -> ConfigService:
    """Assemble the CLI-facing ConfigService with default composition wiring."""
    logger = create_noop_logger()
    effective_registry = registry
    if effective_registry is None:
        register_all_pipelines()
        effective_registry = get_default_registry()

    dq_service = ConfigDQService(
        logger=logger,
        _pipeline_yaml_getter=_pipeline_yaml_for_dq,
        _dq_config_loader=load_dq_config_for_pipeline,
        _effective_config_service=create_effective_config_service(),
    )
    return ConfigService(
        logger=logger,
        _settings_loader=cast(SettingsLoaderPort, get_settings),
        _pipeline_config_loader=load_pipeline_config,
        _domain_config_mapper=cast(DomainConfigMapperPort, yaml_config_to_domain),
        _registry_accessor=lambda: effective_registry,
        _dq_service=dq_service,
    )

================================================================================
File: health.py
Path: bootstrap\cli\health.py
================================================================================
"""Bootstrap functions for health CLI operations.

Contains bootstrap functions for HealthService and health server dependencies.
Used primarily by CLI health operations.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services import HealthService
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceFactory,
)
from bioetl.domain.ports import MetricsPort
from bioetl.infrastructure.adapters.http.health_monitor import ProviderHealthMonitor
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics

__all__ = [
    "HealthServerDependencies",
    "bootstrap_health_server_dependencies",
    "bootstrap_health_service",
]


@dataclass(frozen=True, slots=True)
class HealthServerDependencies:
    """Dependencies for HealthServer, provided by composition layer.

    This dataclass allows composition to provide dependencies without
    importing from interfaces layer (which would violate layer rules).

    Attributes:
        health_monitor: ProviderHealthMonitor for health state tracking.
        metrics: MetricsPort for observability.
    """

    health_monitor: ProviderHealthMonitor
    metrics: MetricsPort


def bootstrap_health_service() -> HealthService:
    """Bootstrap HealthService for CLI health operations.

    Creates a HealthService for checking provider health.
    Wires up DataSourceFactory for adapter creation.

    Returns:
        HealthService configured for CLI operations.

    Example:
        >>> service = bootstrap_health_service()
        >>> summary = await service.check_providers()
        >>> if summary.all_healthy:
        ...     logger.info("All providers healthy")
    """
    noop_logger = create_noop_logger()

    return HealthService(
        logger=noop_logger,
        _factory=DataSourceFactory,
    )


def bootstrap_health_server_dependencies() -> HealthServerDependencies:
    """Bootstrap dependencies for HealthServer via DI.

    Creates and wires up:
    - PrometheusMetrics for observability
    - ProviderHealthMonitor for health state tracking

    The actual HealthServer is created in the interfaces layer
    to maintain proper layer separation (composition cannot import interfaces).

    Returns:
        HealthServerDependencies with metrics and health_monitor.

    Example:
        >>> deps = bootstrap_health_server_dependencies()
        >>> server = HealthServer(host="127.0.0.1", port=9090,
        ...                       health_monitor=deps.health_monitor)
    """
    # Create metrics port for health monitor
    metrics = PrometheusMetrics()

    # Create health monitor with injected metrics
    health_monitor = ProviderHealthMonitor(metrics=metrics)

    return HealthServerDependencies(
        health_monitor=health_monitor,
        metrics=metrics,
    )

================================================================================
File: lineage.py
Path: bootstrap\cli\lineage.py
================================================================================
"""Bootstrap functions for lineage CLI operations."""

from __future__ import annotations

from pathlib import Path

from bioetl.application.services.lineage.lineage_inspection_service import (
    LineageInspectionService,
)
from bioetl.composition.factories.services.port_factories import create_metrics
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.control_plane import (
    FileLineageStore,
    FileRunManifestStore,
)

__all__ = ["bootstrap_lineage_service"]


def bootstrap_lineage_service() -> LineageInspectionService:
    """Bootstrap lineage inspection service for CLI commands."""
    settings = get_settings()
    metrics = create_metrics(settings)
    output_root = Path(settings.data_dir) / "output" / "control"
    return LineageInspectionService(
        lineage_store=FileLineageStore(
            base_path=output_root / "lineage",
            metrics=metrics,
        ),
        manifest_port=FileRunManifestStore(
            base_path=output_root / "run_manifest",
            metrics=metrics,
        ),
    )

================================================================================
File: lock.py
Path: bootstrap\cli\lock.py
================================================================================
"""Bootstrap functions for lock CLI operations.

Contains bootstrap functions for lock service used by CLI operations.
"""

from __future__ import annotations

from bioetl.application.services.lock_service import LockService
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.infrastructure.locking.memory_lock import MemoryLock

__all__ = ["bootstrap_lock_service"]


def bootstrap_lock_service() -> LockService:
    """Bootstrap LockService for CLI lock management commands.

    Creates a LockService for administrative lock operations.
    Used by CLI for `lock release` and `lock list` commands.

    Note: Uses MemoryLock which is the in-process lock implementation.
    Lock operations only affect the current process. For inter-process
    scenarios, an external coordinator adapter would be required.

    Returns:
        LockService configured for the current environment.
    """
    lock_port = MemoryLock()
    noop_logger = create_noop_logger()

    return LockService(lock_port=lock_port, logger=noop_logger)

================================================================================
File: metrics.py
Path: bootstrap\cli\metrics.py
================================================================================
"""Bootstrap functions for metrics CLI operations.

Contains bootstrap functions for MetricsService.
Used for metrics server management from CLI (start, stop, status).

Note:
    This is for managing the metrics server, not for metrics collection.
    Runtime metrics collection uses bootstrap/runtime/observability.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.metrics_service import MetricsService
from bioetl.composition.bootstrap.assembly.metrics_service import (
    create_metrics_service,
)
from bioetl.composition.observability_resolution import resolve_tracing_port
from bioetl.infrastructure.config import get_settings

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

__all__ = ["bootstrap_metrics_service"]


def bootstrap_metrics_service(
    *,
    logger: LoggerPort | None = None,
) -> MetricsService:
    """Bootstrap metrics service for administrative operations.

    Creates a MetricsService with infrastructure dependencies injected.
    Used by CLI and other interfaces for metrics server management.

    Returns:
        MetricsService instance ready for use.

    Example:
        >>> service = bootstrap_metrics_service()
        >>> result = service.start(port=8000)
        >>> # result.success is True if server started
    """
    settings = get_settings()
    tracer = resolve_tracing_port(
        tracer=None,
        settings=settings,
        service_name="bioetl.metrics_admin",
    )
    return create_metrics_service(logger=logger, tracer=tracer)

================================================================================
File: noop.py
Path: bootstrap\cli\noop.py
================================================================================
"""Centralized NoOp dependency factory functions for CLI bootstrap.

Contains pure factory functions for creating NoOp implementations used by
CLI-specific bootstrap functions. These provide silent/null implementations
for observability dependencies when full observability is not needed.

Usage:
    # In CLI bootstrap modules
    from bioetl.composition.bootstrap.cli.noop import create_noop_logger

    logger = create_noop_logger()

Design Decisions:
    - Pure functions, not singletons or factory objects
    - Each call creates a new instance (no hidden state sharing)
    - CLI-specific: warn_on_use=False for metrics (intentional opt-out)
    - MUST NOT be imported by runtime code

Note:
    This module centralizes NoOp creation to eliminate duplication across
    CLI bootstrap modules. Runtime observability uses different bootstrap
    functions from composition/bootstrap/runtime/observability.py.
"""

from __future__ import annotations

from bioetl.domain.ports import (
    MetricsPort,
    TracingPort,
)
from bioetl.domain.ports.noop import (
    NoOpMetrics,
    NoOpTracing,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

__all__ = [
    "create_noop_logger",
    "create_noop_metrics",
    "create_noop_observability_bundle",
    "create_noop_tracing",
]


def create_noop_logger() -> NoOpLogger:
    """Create a NoOpLogger instance for CLI operations.

    Returns a logger that silently ignores all logging calls.
    Used by CLI bootstrap functions that don't require full observability.

    Returns:
        NoOpLogger instance implementing LoggerPort interface.

    Example:
        >>> logger = create_noop_logger()
        >>> logger.info("This will be silently ignored")
    """
    return NoOpLogger()


def create_noop_metrics() -> MetricsPort:
    """Create a NoOpMetrics instance for CLI operations.

    Returns a metrics collector that silently ignores all metrics.
    Uses warn_on_use=False since CLI intentionally opts out of metrics.

    Returns:
        NoOpMetrics instance implementing MetricsPort interface.

    Example:
        >>> metrics = create_noop_metrics()
        >>> metrics.increment_counter("test", 1, {"label": "value"})
    """
    return NoOpMetrics(warn_on_use=False)


def create_noop_tracing() -> TracingPort:
    """Create a NoOpTracing instance for CLI operations.

    Returns a tracer that does nothing when spans are created.
    Used when distributed tracing is not needed for CLI commands.

    Returns:
        NoOpTracing instance implementing TracingPort interface.

    Example:
        >>> tracing = create_noop_tracing()
        >>> tracer = tracing.get_tracer("cli")
        >>> with tracer.start_as_current_span("operation"):
        ...     pass  # Span is silently ignored
    """
    return NoOpTracing()


def create_noop_observability_bundle() -> tuple[NoOpLogger, MetricsPort, TracingPort]:
    """Create a complete NoOp observability bundle for CLI operations.

    Convenience function that creates all three NoOp implementations
    in a single call. Useful when a CLI bootstrap function needs
    multiple observability dependencies.

    Returns:
        Tuple of (NoOpLogger, NoOpMetrics, NoOpTracing) instances.

    Example:
        >>> logger, metrics, tracing = create_noop_observability_bundle()
        >>> # Use in service construction
        >>> service = SomeService(logger=logger, metrics=metrics)
    """
    return (
        create_noop_logger(),
        create_noop_metrics(),
        create_noop_tracing(),
    )

================================================================================
File: run_manifest.py
Path: bootstrap\cli\run_manifest.py
================================================================================
"""Bootstrap functions for run-manifest CLI operations."""

from __future__ import annotations

from pathlib import Path

from bioetl.application.services.control_plane.run_manifest_inspection_service import (
    RunManifestInspectionService,
)
from bioetl.composition.factories.services.port_factories import create_metrics
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.control_plane import (
    FileRunLedgerStore,
    FileRunManifestStore,
)

__all__ = ["bootstrap_run_manifest_service"]


def bootstrap_run_manifest_service() -> RunManifestInspectionService:
    """Bootstrap manifest/ledger inspection service for CLI commands."""
    settings = get_settings()
    metrics = create_metrics(settings)
    output_root = Path(settings.data_dir) / "output" / "control"
    return RunManifestInspectionService(
        manifest_port=FileRunManifestStore(
            base_path=output_root / "run_manifest",
            metrics=metrics,
        ),
        ledger_port=FileRunLedgerStore(
            base_path=output_root / "run_ledger",
            metrics=metrics,
        ),
    )

================================================================================
File: storage.py
Path: bootstrap\cli\storage.py
================================================================================
"""Bootstrap functions for storage-related CLI operations.

Contains bootstrap functions for maintenance services:
- CleanupService: Preview and execute cleanup operations
- MedallionLifecycleService: Vacuum and archive Delta tables
- BronzeCleanupService: Bronze layer retention cleanup
- VacuumService: Batch vacuum operations
- ExportService: Export Delta tables to various formats

Note:
    Uses NoOp observability since these are CLI operations.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services import (
    BronzeCleanupService,
    ContractMigrationService,
    ExportService,
    VacuumService,
)
from bioetl.application.services.admin_runtime_api import CleanupService
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition import get_default_registry
from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage_adapter
from bioetl.composition.bootstrap.cli.config import bootstrap_config_service
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)
from bioetl.infrastructure.config.contract_policy_validation import (
    load_contract_registry_entries,
)
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
from bioetl.infrastructure.export import ExportCatalogAdapter, ExportWriterAdapter
from bioetl.infrastructure.storage.delta_reader import DeltaReader

__all__ = [
    "bootstrap_bronze_cleanup_service",
    "bootstrap_cleanup_service",
    "bootstrap_contract_migration_service",
    "bootstrap_export_service",
    "bootstrap_lifecycle_service",
    "bootstrap_vacuum_service",
]

if TYPE_CHECKING:
    from bioetl.composition import PipelineRegistry


def bootstrap_cleanup_service() -> CleanupService:
    """Create a cleanup service for CLI operations.

    Creates a CleanupService with storage and logger for cleanup operations.
    Used by CLI for --dry-run preview and actual cleanup.

    Layer: Returns application service (CleanupService).

    Returns:
        CleanupService configured for the current environment.
    """
    storage = bootstrap_storage_adapter()
    noop_logger = create_noop_logger()

    return CleanupService(storage=storage, logger=noop_logger)


def bootstrap_lifecycle_service() -> MedallionLifecycleService:
    """Bootstrap MedallionLifecycleService for CLI maintenance commands.

    Creates a MedallionLifecycleService for vacuum and archive operations.
    Used by CLI for `maintenance vacuum` and `maintenance archive` commands.

    Returns:
        MedallionLifecycleService configured for the current environment.
    """
    storage = bootstrap_storage_adapter()
    noop_logger = create_noop_logger()

    return MedallionLifecycleService(storage=storage, logger=noop_logger)


def bootstrap_bronze_cleanup_service() -> BronzeCleanupService:
    """Bootstrap BronzeCleanupService for CLI maintenance commands.

    Creates a BronzeCleanupService for Bronze layer retention cleanup.
    Used by CLI for `maintenance bronze-cleanup` command.

    Returns:
        BronzeCleanupService configured for the current environment.
    """
    storage = bootstrap_storage_adapter()
    noop_logger = create_noop_logger()

    return BronzeCleanupService(storage=storage, logger=noop_logger)


def bootstrap_contract_migration_service(
    *,
    registry: PipelineRegistry | None = None,
) -> ContractMigrationService:
    """Bootstrap ContractMigrationService for maintenance planner commands."""
    noop_logger = create_noop_logger()
    config_service = bootstrap_config_service(registry=registry)
    return ContractMigrationService(
        logger=noop_logger,
        _pipeline_info_loader=config_service.validate_pipeline_config,
        _contract_policy_loader=load_pipeline_contract_policy,
        _registry_entries_loader=load_contract_registry_entries,
    )


def bootstrap_vacuum_service(
    *,
    registry: PipelineRegistry | None = None,
) -> VacuumService:
    """Bootstrap VacuumService for CLI maintenance commands.

    Creates a VacuumService for batch vacuum operations.
    Used by CLI for `maintenance vacuum-all` command.

    Args:
        registry: Optional explicit registry. When omitted, a fresh registered
            registry is built for the table collector.

    Returns:
        VacuumService configured for the current environment.
    """
    lifecycle = bootstrap_lifecycle_service()
    noop_logger = create_noop_logger()

    # Create table collector that queries the registry (DI pattern)
    table_collector = _create_table_collector(registry=registry)

    return VacuumService(
        lifecycle=lifecycle,
        logger=noop_logger,
        table_collector=table_collector,
    )


def _create_table_collector(
    *,
    registry: PipelineRegistry | None = None,
) -> Callable[[str], list[tuple[str, str]]]:
    """Create a callable that gathers Silver/Gold table names from registry configs."""
    effective_registry = registry if registry is not None else get_default_registry()

    def collect_tables(layer: str) -> list[tuple[str, str]]:
        """Collect `(table_name, layer)` pairs for requested layer scope."""
        pipelines = effective_registry.list_pipelines()

        silver_tables: set[str] = set()
        gold_tables: set[str] = set()

        for pipeline_name in pipelines:
            pipeline_cfg = load_pipeline_config(pipeline_name)
            silver_table = (
                pipeline_cfg.silver_table
                or f"{pipeline_cfg.provider}.{pipeline_cfg.entity_type}"
            )
            gold_table = (
                pipeline_cfg.gold_table
                or f"{pipeline_cfg.provider}.{pipeline_cfg.entity_type}"
            )
            if silver_table:
                silver_tables.add(silver_table)
            if gold_table:
                gold_tables.add(gold_table)

        tables: list[tuple[str, str]] = []
        if layer in ("all", "silver"):
            tables.extend((t, "silver") for t in sorted(silver_tables))
        if layer in ("all", "gold"):
            tables.extend((t, "gold") for t in sorted(gold_tables))

        return tables

    return collect_tables


def bootstrap_export_service() -> ExportService:
    """Bootstrap ExportService for CLI export commands.

    Creates an ExportService for exporting Delta Lake tables to
    CSV, XLSX, and TSV formats.

    Returns:
        ExportService configured for the current environment.
    """
    settings = get_settings()
    noop_logger = create_noop_logger()

    # Use data/output/ subdirectory for actual data paths (matches pipeline configs)
    # The pipeline configs use data/output/silver, data/output/gold
    output_dir = Path(settings.data_dir) / "output"
    silver_path = output_dir / "silver"
    gold_path = output_dir / "gold"

    # Create Delta reader for Silver and Gold paths
    reader = DeltaReader(
        base_path=silver_path,  # Base path for relative paths
        logger=noop_logger,
    )

    return ExportService(
        reader=reader,
        catalog=ExportCatalogAdapter(),
        writer=ExportWriterAdapter(),
        logger=noop_logger,
        silver_path=silver_path,
        gold_path=gold_path,
        export_path=output_dir / "exports",
    )

================================================================================
File: composite_infrastructure_context.py
Path: bootstrap\composite_infrastructure_context.py
================================================================================
"""Shared context object for composite bootstrap infrastructure primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bioetl.domain.ports import LockPort, LoggerPort, MetricsPort, TracingPort
from bioetl.infrastructure.config import Settings


@dataclass(frozen=True, slots=True)
class CompositeInfrastructureContext:
    """Bundle of infrastructure primitives required by composite bootstrap."""

    run_id: str
    settings: Settings
    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracingPort
    storage: (
        Any  # Any: storage adapter is concrete infra object implementing StoragePort
    )
    lock: LockPort

================================================================================
File: __init__.py
Path: bootstrap\runtime\__init__.py
================================================================================
"""Runtime bootstrap module for pipeline execution.

Contains bootstrap functions for actual pipeline execution scenarios:
- Single pipeline runs (incremental, backfill, rebuild)
- Composite pipeline runs with enrichment coordination
- Full observability stack (logging, tracing, metrics, DQ monitoring)

IMPORTANT: This module MUST NOT import from bootstrap/cli/.
CLI modules may import from runtime for runner access, but not vice versa.

Public runtime helpers are re-exported lazily so importing one light-weight
submodule does not eagerly initialize the full runtime bootstrap graph.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "MetricsServerError",
    "assemble_filter_config",
    "assemble_runtime_config",
    "assemble_vacuum_settings",
    "bootstrap_composite_runner",
    "bootstrap_dq_monitor_port",
    "bootstrap_logger_port",
    "bootstrap_metrics_port",
    "bootstrap_observability_bundle",
    "bootstrap_pipeline_runner",
    "bootstrap_pipeline_runner_service",
    "bootstrap_tracer_port",
    "load_composite_config",
    "maybe_start_metrics_server",
    "validate_observability_preflight",
]

_PUBLIC_EXPORTS: dict[str, str] = {
    "MetricsServerError": "bioetl.composition.bootstrap.runtime.observability",
    "assemble_filter_config": "bioetl.composition.bootstrap.runtime.assembly",
    "assemble_runtime_config": "bioetl.composition.bootstrap.runtime.assembly",
    "assemble_vacuum_settings": "bioetl.composition.bootstrap.runtime.assembly",
    "bootstrap_composite_runner": "bioetl.composition.bootstrap.runtime.composite",
    "bootstrap_dq_monitor_port": "bioetl.composition.bootstrap.runtime.observability",
    "bootstrap_logger_port": "bioetl.composition.bootstrap.runtime.observability",
    "bootstrap_metrics_port": "bioetl.composition.bootstrap.runtime.observability",
    "bootstrap_observability_bundle": (
        "bioetl.composition.bootstrap.runtime.observability"
    ),
    "bootstrap_pipeline_runner": "bioetl.composition.bootstrap.runtime.pipeline",
    "bootstrap_pipeline_runner_service": (
        "bioetl.composition.bootstrap.runtime.pipeline_runner_service_bootstrap"
    ),
    "bootstrap_tracer_port": "bioetl.composition.bootstrap.runtime.observability",
    "load_composite_config": "bioetl.composition.bootstrap.runtime.composite",
    "maybe_start_metrics_server": "bioetl.composition.bootstrap.runtime.observability",
    "validate_observability_preflight": (
        "bioetl.composition.bootstrap.runtime.observability"
    ),
}


def __getattr__(
    name: str,
) -> (
    Any  # Any: lazy runtime re-export preserves the original symbol type at lookup time.
):  # Any: lazy runtime re-export preserves the original symbol type at lookup time.
    """Resolve runtime re-exports lazily to keep package import light-weight."""
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy re-exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))

================================================================================
File: _composite_config_runtime_compat.py
Path: bootstrap\runtime\_composite_config_runtime_compat.py
================================================================================
"""Helper for the composite runtime compatibility config-loading facade."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from bioetl.domain.composite.config import CompositeConfig

CompositeConfigPathResolver = Callable[[str], Path]
CompositeConfigValidator = Callable[[dict[str, object]], object]
CompositeConfigLoader = Callable[..., CompositeConfig]

__all__ = ["load_runtime_composite_config"]


def load_runtime_composite_config(
    name: str,
    *,
    resolve_config_path_fn: CompositeConfigPathResolver,
    load_config_fn: CompositeConfigLoader,
    validate_payload: CompositeConfigValidator,
    validation_error_cls: type[Exception],
) -> CompositeConfig:
    """Load composite config while preserving runtime facade patch points."""
    config_path = resolve_config_path_fn(name)
    try:
        return load_config_fn(
            config_path.stem,
            config_dir=config_path.parent,
            validate_payload=validate_payload,
        )
    except validation_error_cls as error:
        raise ValueError(f"Invalid composite config '{name}': {error}") from error

================================================================================
File: _composite_control_plane_payloads.py
Path: bootstrap\runtime\_composite_control_plane_payloads.py
================================================================================
"""Pure payload builders for composite control-plane bootstrap."""

from __future__ import annotations

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.runtime_builders.run_manifest_support import (
    to_serializable_mapping,
)
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.control_plane import RunArtifactRef, RunSourceRef
from bioetl.domain.types import RunType

__all__ = [
    "build_composite_launch_context_snapshot",
    "build_composite_planned_artifacts",
    "build_composite_resolved_config_snapshot",
    "build_composite_runtime_config_snapshot",
    "build_composite_source_refs",
]


def build_composite_launch_context_snapshot(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    *,
    required_persistence_profile: str,
) -> dict[str, object]:
    """Capture launch-time options that materially affect composite execution."""
    return {
        "pipeline_name": config.name,
        "run_type": RunType.INCREMENTAL.value,
        "resume": runtime.resume,
        "dry_run": runtime.dry_run,
        "required_only": runtime.required_only,
        "force_enricher": runtime.force_enricher,
        "seed_limit": runtime.seed_limit,
        "enrich_only": list(runtime.enrich_only or ()),
        "use_cached_bronze": runtime.use_cached_bronze,
        "cached_bronze_path": runtime.cached_bronze_path,
        "cached_bronze_date": runtime.cached_bronze_date,
        "cached_bronze_enrichers": runtime.cached_bronze_enrichers,
        "cached_bronze_dependencies": runtime.cached_bronze_dependencies,
        "execution_context": "composite",
        "exact_replay_support_boundary": "composite_execution_unsupported",
        "required_persistence_profile": required_persistence_profile,
    }


def build_composite_source_refs(
    config: CompositeConfig,
) -> tuple[RunSourceRef, ...]:
    """Capture seed, dependency, and enricher sources in manifest payload."""
    pipeline_names = [config.seed.pipeline]
    pipeline_names.extend(dep.pipeline for dep in config.dependencies)
    pipeline_names.extend(enricher.pipeline for enricher in config.enrichers)
    return tuple(
        RunSourceRef(
            provider=provider,
            entity=entity,
            pipeline_name=pipeline_name,
        )
        for pipeline_name in pipeline_names
        for provider, entity in [_resolve_provider_entity(pipeline_name)]
    )


def build_composite_planned_artifacts(
    config: CompositeConfig,
) -> tuple[RunArtifactRef, ...]:
    """Capture planned composite artifacts for final materialization stages."""
    return (
        RunArtifactRef(layer="silver", path=config.merge.output_silver_path),
        RunArtifactRef(layer="gold", path=config.merge.output_gold_path),
    )


def build_composite_runtime_config_snapshot(
    runtime: CompositeRuntimeConfig,
) -> dict[str, object]:
    """Normalize composite runtime config into manifest-safe mapping."""
    return to_serializable_mapping(runtime)


def build_composite_resolved_config_snapshot(
    config: CompositeConfig,
) -> dict[str, object]:
    """Normalize resolved composite config into manifest-safe mapping."""
    return to_serializable_mapping(config)


def _resolve_provider_entity(pipeline_name: str) -> tuple[str, str]:
    """Resolve provider/entity from a canonical pipeline name."""
    if "_" not in pipeline_name:
        return pipeline_name, pipeline_name
    provider, entity = pipeline_name.split("_", 1)
    return provider, entity

================================================================================
File: _composite_plan_support.py
Path: bootstrap\runtime\_composite_plan_support.py
================================================================================
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from bioetl.application.composite.runner_pkg import CompositePipelineRunner
from bioetl.composition.bootstrap.runtime._composite_config_runtime_compat import (
    load_runtime_composite_config as _load_runtime_composite_config_impl,
)
from bioetl.composition.bootstrap.runtime.composite_bootstrap_builders import (
    bootstrap_runtime_basics as _bootstrap_runtime_basics_builder_impl,
)
from bioetl.composition.bootstrap.runtime.composite_bootstrap_builders import (
    build_runner_factories as _build_runner_factories_builder_impl,
)
from bioetl.composition.bootstrap.runtime.composite_bootstrap_builders import (
    build_support_services as _build_support_services_builder_impl,
)
from bioetl.composition.bootstrap.runtime.composite_bootstrap_builders import (
    create_composite_runner as _create_composite_runner_builder_impl,
)
from bioetl.infrastructure.config.composite_config_api import (
    load_composite_config as _load_composite_config_impl,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import polars as pl

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.composition.bootstrap.composite_infrastructure_context import (
        CompositeInfrastructureContext,
    )
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LockPort, LoggerPort, MetricsPort, TracingPort
    from bioetl.infrastructure.config import Settings


@dataclass(frozen=True, slots=True)
class CompositeBootstrapPlan:
    run_id: str
    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracingPort
    lock: LockPort
    seed_runner_factory: Callable[[], PipelineRunner]
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    support_services: CompositeSupportServices


def load_composite_config_impl(
    name: str,
    *,
    resolve_config_path_fn: Callable[[str], Path],
    validate_payload: Callable[[object], object],
) -> CompositeConfig:
    return _load_runtime_composite_config_impl(
        name,
        resolve_config_path_fn=resolve_config_path_fn,
        load_config_fn=_load_composite_config_impl,
        validate_payload=validate_payload,
        validation_error_cls=ValidationError,
    )


def bootstrap_runtime_basics_impl(
    *,
    config: CompositeConfig,
    run_id: str | None,
    settings_provider: Callable[[], Settings],
    logger_bootstrapper: Callable[[str, str, str], LoggerPort],
    tracer_bootstrapper: Callable[[str, str, LoggerPort], TracingPort],
    storage_bootstrapper: Callable[..., object],
    lock_factory: type[object],
    uuid_factory: Callable[[], object],
) -> CompositeInfrastructureContext:
    return _bootstrap_runtime_basics_builder_impl(
        config=config,
        run_id=run_id,
        settings_provider=settings_provider,
        logger_bootstrapper=logger_bootstrapper,
        tracer_bootstrapper=tracer_bootstrapper,
        storage_bootstrapper=storage_bootstrapper,
        lock_factory=lock_factory,
        uuid_factory=uuid_factory,
    )


def build_runner_factories_impl(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    logger: LoggerPort,
    runner_factory_builder_cls: type[object],
    filter_extraction_service_cls: type[object],
    pipeline_runner_builder: Callable[..., PipelineRunner],
    resolve_bronze_opts_fn: Callable[..., dict[str, object]],
) -> tuple[
    Callable[[], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
]:
    return _build_runner_factories_builder_impl(
        config=config,
        runtime=runtime,
        logger=logger,
        runner_factory_builder_cls=runner_factory_builder_cls,
        filter_extraction_service_cls=filter_extraction_service_cls,
        pipeline_runner_builder=pipeline_runner_builder,
        resolve_bronze_opts_fn=resolve_bronze_opts_fn,
    )


def build_support_services_impl(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
    support_services_factory_cls: type[object],
    resolve_gold_schema_fn: Callable[[str], type | None],
    load_field_group_registry_fn: Callable[..., object],
    create_dq_report_service_fn: Callable[..., object],
) -> CompositeSupportServices:
    return _build_support_services_builder_impl(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
        support_services_factory_cls=support_services_factory_cls,
        resolve_gold_schema_fn=resolve_gold_schema_fn,
        load_field_group_registry_fn=load_field_group_registry_fn,
        create_dq_report_service_fn=create_dq_report_service_fn,
    )


def build_composite_bootstrap_plan_impl(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None,
    bootstrap_runtime_basics_fn: Callable[..., CompositeInfrastructureContext],
    build_runner_factories_fn: Callable[
        ...,
        tuple[
            Callable[[], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
        ],
    ],
    build_support_services_fn: Callable[..., CompositeSupportServices],
) -> CompositeBootstrapPlan:
    infra_context = bootstrap_runtime_basics_fn(config=config, run_id=run_id)
    seed_runner_factory, dependencies_runner_factory, enricher_runner_factory = (
        build_runner_factories_fn(
            config=config,
            runtime=runtime,
            logger=infra_context.logger,
        )
    )
    support_services = build_support_services_fn(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
    )
    return CompositeBootstrapPlan(
        run_id=infra_context.run_id,
        logger=infra_context.logger,
        metrics=infra_context.metrics,
        tracer=infra_context.tracer,
        lock=infra_context.lock,
        seed_runner_factory=seed_runner_factory,
        dependencies_runner_factory=dependencies_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        support_services=support_services,
    )


def create_composite_runner_from_plan_impl(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    plan: CompositeBootstrapPlan,
    runner_factory: Callable[..., CompositePipelineRunner],
) -> CompositePipelineRunner:
    return _create_composite_runner_builder_impl(
        config=config,
        runtime=runtime,
        run_id=plan.run_id,
        logger=plan.logger,
        metrics=plan.metrics,
        tracer=plan.tracer,
        lock=plan.lock,
        seed_runner_factory=plan.seed_runner_factory,
        dependencies_runner_factory=plan.dependencies_runner_factory,
        enricher_runner_factory=plan.enricher_runner_factory,
        support_services=plan.support_services,
        runner_factory=runner_factory,
    )

================================================================================
File: _dependency_runner_support.py
Path: bootstrap\runtime\_dependency_runner_support.py
================================================================================
"""Pure support helpers for dependency-runner factory assembly."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import DependencyConfig


__all__ = [
    "build_dependency_debug_context",
    "resolve_dependency_runner_limit",
]


def build_dependency_debug_context(
    *,
    pipeline_name: str,
    keys: pl.DataFrame,
    dep_cfg: DependencyConfig | None,
    filter_field: str | None,
    filter_ids: tuple[str, ...] | None,
    multi_filter_ids: dict[str, tuple[str, ...]] | None,
) -> dict[str, object]:
    """Build structured logging context for dependency-runner creation."""
    join_keys = [] if dep_cfg is None else list(dep_cfg.join_keys)
    filter_ids_sample = [] if filter_ids is None else list(filter_ids)[:5]
    multi_filter_fields = []
    multi_filter_counts: dict[str, int] = {}

    if multi_filter_ids is not None:
        multi_filter_fields = list(multi_filter_ids.keys())
        multi_filter_counts = {
            field: len(ids) for field, ids in multi_filter_ids.items()
        }

    return {
        "pipeline": pipeline_name,
        "keys_columns": list(keys.columns),
        "keys_count": len(keys),
        "join_keys": join_keys,
        "filter_field": filter_field,
        "filter_ids_count": 0 if filter_ids is None else len(filter_ids),
        "filter_ids_sample": filter_ids_sample,
        "multi_filter_fields": multi_filter_fields,
        "multi_filter_counts": multi_filter_counts,
        "is_chained": dep_cfg is not None and dep_cfg.key_source is not None,
        "key_source": None if dep_cfg is None else dep_cfg.key_source,
    }


def resolve_dependency_runner_limit(
    *,
    keys: pl.DataFrame,
    filter_ids: tuple[str, ...] | None,
    multi_filter_ids: dict[str, tuple[str, ...]] | None,
) -> int | None:
    """Return dependency-runner limit when filter inputs are present."""
    if filter_ids is None and multi_filter_ids is None:
        return None
    return len(keys)

================================================================================
File: _runner_assembly_support.py
Path: bootstrap\runtime\_runner_assembly_support.py
================================================================================
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from bioetl.application.composite.runner_pkg import CompositePipelineRunner
from bioetl.application.composite.runtime_wiring_api import (
    CompositeCheckpointService,
    CompositeLifecycleObserverService,
    CompositeRunnerDependencies,
    DependencyCoordinatorService,
    EnrichmentCoordinatorService,
)
from bioetl.application.composite.runtime_wiring_api import (
    KeyExtractorService as _KeyExtractorService,
)
from bioetl.application.composite.runtime_wiring_api import (
    MergeService as _MergeService,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_wiring_api import (
        CompositePreflightValidationService,
        FSMStateHelperService,
        PipelineRunner,
    )
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import (
        LockPort,
        LoggerPort,
        MetricsPort,
        QuarantinePort,
        TracingPort,
    )


CompositeRunnerFactory = Callable[..., CompositePipelineRunner]


@dataclass(frozen=True, slots=True)
class CompositeRunnerServiceInputs:
    config: CompositeConfig
    runtime: CompositeRuntimeConfig
    run_id: str
    logger: LoggerPort
    lock: LockPort
    seed_runner_factory: Callable[[], PipelineRunner]
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    key_extractor: _KeyExtractorService
    coordinator: EnrichmentCoordinatorService
    merger: _MergeService
    checkpoint_manager: CompositeCheckpointService
    fsm_state_helper: FSMStateHelperService
    dq_report_service: DQReportService | None
    preflight_validator: CompositePreflightValidationService | None
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner] | None
    dependency_coordinator: DependencyCoordinatorService | None
    quarantine_port: QuarantinePort | None
    metrics: MetricsPort | None
    tracer: TracingPort | None
    observer: CompositeLifecycleObserverService
    manifest_id: str | None
    run_ledger_service: RunLedgerService | None


def resolve_effective_run_id(run_id: str | None) -> str:
    return run_id or str(uuid4())


def build_composite_runner_dependencies(
    inputs: CompositeRunnerServiceInputs,
) -> CompositeRunnerDependencies:
    return CompositeRunnerDependencies(
        seed_runner_factory=inputs.seed_runner_factory,
        enricher_runner_factory=inputs.enricher_runner_factory,
        key_extractor=inputs.key_extractor,
        coordinator=inputs.coordinator,
        merger=inputs.merger,
        checkpoint_manager=inputs.checkpoint_manager,
        logger=inputs.logger,
        lock=inputs.lock,
        fsm_state_helper=inputs.fsm_state_helper,
        dq_report_service=inputs.dq_report_service,
        preflight_validator=inputs.preflight_validator,
        dependencies_runner_factory=inputs.dependencies_runner_factory,
        dependency_coordinator=inputs.dependency_coordinator,
        quarantine_port=inputs.quarantine_port,
        metrics=inputs.metrics,
        tracer=inputs.tracer,
        observer=inputs.observer,
        manifest_id=inputs.manifest_id,
        run_ledger_service=inputs.run_ledger_service,
    )


def build_composite_runner_service_inputs(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    tracer: TracingPort | None,
    lock: LockPort,
    seed_runner_factory: Callable[[], PipelineRunner],
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    support_services: CompositeSupportServices,
) -> CompositeRunnerServiceInputs:
    return CompositeRunnerServiceInputs(
        config=config,
        runtime=runtime,
        run_id=run_id,
        logger=logger,
        lock=lock,
        seed_runner_factory=seed_runner_factory,
        dependencies_runner_factory=dependencies_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        coordinator=support_services.coordinator,
        checkpoint_manager=support_services.checkpoint_manager,
        key_extractor=support_services.key_extractor,
        merger=support_services.merger,
        fsm_state_helper=support_services.fsm_state_helper,
        dq_report_service=support_services.dq_report_service,
        preflight_validator=None,
        dependency_coordinator=support_services.dependency_coordinator,
        quarantine_port=support_services.quarantine_port,
        metrics=metrics,
        tracer=tracer,
        observer=CompositeLifecycleObserverService(
            logger=logger,
            metrics=metrics,
            tracer=tracer,
        ),
        manifest_id=getattr(support_services, "manifest_id", None),
        run_ledger_service=getattr(support_services, "run_ledger_service", None),
    )


def invoke_composite_runner_factory(
    *,
    runner_factory: CompositeRunnerFactory,
    inputs: CompositeRunnerServiceInputs,
) -> CompositePipelineRunner:
    return runner_factory(
        config=inputs.config,
        runtime=inputs.runtime,
        seed_runner_factory=inputs.seed_runner_factory,
        enricher_runner_factory=inputs.enricher_runner_factory,
        key_extractor=inputs.key_extractor,
        coordinator=inputs.coordinator,
        merger=inputs.merger,
        checkpoint_manager=inputs.checkpoint_manager,
        logger=inputs.logger,
        lock=inputs.lock,
        fsm_state_helper=inputs.fsm_state_helper,
        run_id=inputs.run_id,
        dq_report_service=inputs.dq_report_service,
        preflight_validator=inputs.preflight_validator,
        dependencies_runner_factory=inputs.dependencies_runner_factory,
        dependency_coordinator=inputs.dependency_coordinator,
        quarantine_port=inputs.quarantine_port,
        metrics=inputs.metrics,
        tracer=inputs.tracer,
        observer=inputs.observer,
        manifest_id=inputs.manifest_id,
        run_ledger_service=inputs.run_ledger_service,
    )


def create_composite_runner_service_from_inputs(
    inputs: CompositeRunnerServiceInputs,
) -> CompositePipelineRunner:
    deps = build_composite_runner_dependencies(inputs)
    return CompositePipelineRunner(
        config=inputs.config,
        runtime=inputs.runtime,
        deps=deps,
        run_id=inputs.run_id,
    )

================================================================================
File: assembly.py
Path: bootstrap\runtime\assembly.py
================================================================================
"""Pure assembly helpers for pipeline bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.runtime_builders.inputs_resolver import ResolvedVacuumSettings
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.context import VacuumSettings as CliVacuumSettings
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterYamlConfig as YamlInputFilter,
    )
    from bioetl.infrastructure.schemas.pipeline_config import (
        MaintenanceConfig,
    )

__all__ = [
    "ResolvedVacuumSettings",
    "assemble_cached_bronze_context",
    "assemble_filter_config",
    "assemble_runtime_config",
    "assemble_vacuum_settings",
]


def assemble_vacuum_settings(
    *,
    cli_vacuum: CliVacuumSettings,
    yaml_maintenance: MaintenanceConfig,
) -> ResolvedVacuumSettings:
    """Merge CLI vacuum overrides with YAML defaults."""
    if cli_vacuum.enabled is not None:
        return ResolvedVacuumSettings(
            enabled=cli_vacuum.enabled,
            retention_days=cli_vacuum.retention_days,
        )

    return ResolvedVacuumSettings(
        enabled=yaml_maintenance.auto_vacuum,
        retention_days=yaml_maintenance.vacuum_retention_days,
    )


def assemble_runtime_config(
    *,
    run_type: RunType,
    resume: bool,
    limit: int | None,
    query: str | None,
    dry_run: bool,
    heartbeat_interval: int,
    vacuum: ResolvedVacuumSettings,
    skip_gold: bool = False,
    health_check_mode: Literal["strict", "probe"] = "strict",
) -> RuntimeConfig:
    """Build ``RuntimeConfig`` from already-resolved runtime inputs."""
    return RuntimeConfig(
        run_type=run_type,
        resume=resume,
        limit=limit,
        heartbeat_interval=heartbeat_interval,
        query=query,
        dry_run=dry_run,
        vacuum_after_run=vacuum.enabled,
        vacuum_retention_days=vacuum.retention_days,
        skip_gold=skip_gold,
        health_check_mode=health_check_mode,
    )


def assemble_filter_config(
    *,
    yaml_filter: YamlInputFilter,
    ctx: PipelineRunContext,
    test_mode: bool,
) -> InputFilterConfig | None:
    """Assemble filter config from YAML plus run-context overrides."""
    effective_test_mode = test_mode or ctx.ignore_yaml_filter

    return FilterConfigBuilder.build(
        yaml_filter=yaml_filter,
        cli_csv=ctx.input_filter.source_path if ctx.input_filter.enabled else None,
        cli_column=ctx.input_filter.column_name if ctx.input_filter.enabled else None,
        cli_field=ctx.input_filter.filter_field if ctx.input_filter.enabled else None,
        cli_fallback_column=(
            ctx.input_filter.fallback_column if ctx.input_filter.enabled else None
        ),
        test_mode=effective_test_mode,
        direct_filter_ids=ctx.input_filter.filter_ids,
        direct_fallback_mapping=ctx.input_filter.fallback_mapping,
        direct_multi_filter_ids=ctx.input_filter.multi_filter_ids,
        direct_valid_combinations=ctx.input_filter.valid_combinations,
    )


def assemble_cached_bronze_context(
    ctx: PipelineRunContext,
) -> CachedBronzeContext:
    """Return the cached-bronze context carried by the run context."""
    return ctx.cached_bronze

================================================================================
File: classification_init.py
Path: bootstrap\runtime\classification_init.py
================================================================================
"""Bootstrap initializer for publication type classification data.

Loads classification data from the JSON asset via infrastructure loader
and initializes the domain classification module.
"""

from __future__ import annotations

from pathlib import Path


def initialize_publication_type_classification(configs_root: Path) -> None:
    """Load classification data from JSON and initialize the domain module.

    Must be called once before any pipeline transformer uses
    ``classify_publication_type()``. Idempotent — repeated calls reload the
    data but do not cause errors.

    Args:
        configs_root: Root directory of the project configs tree (e.g., Path('configs')).
            The loader resolves the JSON asset path relative to this directory.
    """
    from bioetl.domain.mapping.publication_type_classification import (
        initialize_classification,
    )
    from bioetl.infrastructure.config.publication_type_classification_loader import (
        PublicationTypeClassificationLoader,
    )

    loader = PublicationTypeClassificationLoader(configs_root)
    data = loader.load()
    initialize_classification(data)

================================================================================
File: composite.py
Path: bootstrap\runtime\composite.py
================================================================================
"""Bootstrap facade for composite pipeline execution."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError as _ValidationError

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    CompositeBootstrapPlan as _CompositeBootstrapPlan,
)
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    bootstrap_runtime_basics_impl as _bootstrap_runtime_basics_impl,
)
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    build_composite_bootstrap_plan_impl as _build_composite_bootstrap_plan_impl,
)
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    build_runner_factories_impl as _build_runner_factories_impl,
)
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    build_support_services_impl as _build_support_services_impl,
)
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    create_composite_runner_from_plan_impl as _create_composite_runner_from_plan_impl,
)
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    load_composite_config_impl as _load_runtime_composite_config_impl,
)
from bioetl.composition.bootstrap.runtime.composite_support_helpers import (
    _create_dq_report_service,
    _load_field_group_registry,
)
from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
    CompositeSupportServices,
)
from bioetl.composition.bootstrap.runtime.runner_assembly import (
    create_composite_runner_service,
)
from bioetl.domain.composite.config import CompositeConfig
from bioetl.infrastructure.config.composite_config_api import (
    DEFAULT_COMPOSITE_CONFIG_DIR,
    DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY,
)
from bioetl.infrastructure.config.composite_config_api import (
    resolve_composite_config_path as _resolve_composite_config_path_impl,
)
from bioetl.infrastructure.config.composite_config_api import (
    resolve_composite_gold_schema as _resolve_composite_gold_schema_impl,
)
from bioetl.infrastructure.schemas.composite_config import (
    validate_composite_config_payload,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import polars as pl

    from bioetl.application.composite.runner_pkg import CompositePipelineRunner
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.composition.bootstrap.composite_infrastructure_context import (
        CompositeInfrastructureContext,
    )
    from bioetl.domain.ports import LoggerPort

__all__ = [
    "CompositeRuntimeConfig",
    "bootstrap_composite_runner",
    "load_composite_config",
]

ValidationError = _ValidationError


def _resolve_composite_gold_schema(composite_name: str) -> type | None:
    """Resolve composite Gold contract by composite pipeline name."""
    return _resolve_composite_gold_schema_impl(
        composite_name,
        schema_registry=DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY,
    )


def _resolve_composite_config_path(name: str) -> Path:
    """Resolve composite config path from canonical composites directory."""
    return _resolve_composite_config_path_impl(
        name,
        config_dir=DEFAULT_COMPOSITE_CONFIG_DIR,
    )


def load_composite_config(name: str) -> CompositeConfig:
    """Load and validate composite pipeline configuration from YAML."""
    return _load_runtime_composite_config_impl(
        name,
        resolve_config_path_fn=_resolve_composite_config_path,
        validate_payload=validate_composite_config_payload,
    )


def _bootstrap_runtime_basics(
    *,
    config: CompositeConfig,
    run_id: str | None,
) -> CompositeInfrastructureContext:
    """Build base runtime dependencies shared across composite bootstrap."""
    from uuid import uuid4

    from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage_adapter
    from bioetl.composition.bootstrap.runtime.observability import (
        bootstrap_logger_port,
    )
    from bioetl.composition.bootstrap.runtime.tracing_bootstrap import (
        bootstrap_tracer_port,
    )
    from bioetl.infrastructure.config import get_settings
    from bioetl.infrastructure.locking.memory_lock import MemoryLock

    return _bootstrap_runtime_basics_impl(
        config=config,
        run_id=run_id,
        settings_provider=get_settings,
        logger_bootstrapper=lambda pipeline_name, run_uuid, level: (
            bootstrap_logger_port(
                pipeline=pipeline_name,
                run_id=run_uuid,
                log_level=level,
            )
        ),
        tracer_bootstrapper=bootstrap_tracer_port,
        storage_bootstrapper=bootstrap_storage_adapter,
        lock_factory=MemoryLock,
        uuid_factory=uuid4,
    )


def _build_runner_factories(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    logger: LoggerPort,
) -> tuple[
    Callable[[], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
]:
    """Build seed/dependency/enricher runner factories for composite phases."""
    from bioetl.composition.bootstrap.runtime.composite_filter_extraction_service import (
        CompositeFilterExtractionService,
    )
    from bioetl.composition.bootstrap.runtime.pipeline import (
        bootstrap_pipeline_runner as bootstrap_pipeline_runner_impl,
    )
    from bioetl.composition.bootstrap.runtime.runner_factory_builder_service import (
        RunnerFactoryBuilderService,
        resolve_bronze_opts,
    )

    return _build_runner_factories_impl(
        config=config,
        runtime=runtime,
        logger=logger,
        runner_factory_builder_cls=RunnerFactoryBuilderService,
        filter_extraction_service_cls=CompositeFilterExtractionService,
        pipeline_runner_builder=bootstrap_pipeline_runner_impl,
        resolve_bronze_opts_fn=resolve_bronze_opts,
    )


def _build_support_services(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
) -> CompositeSupportServices:
    """Build composite support service bundle consumed by runner facade."""
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServicesFactory,
    )

    return _build_support_services_impl(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
        support_services_factory_cls=CompositeSupportServicesFactory,
        resolve_gold_schema_fn=_resolve_composite_gold_schema,
        load_field_group_registry_fn=_load_field_group_registry,
        create_dq_report_service_fn=_create_dq_report_service,
    )


def _build_composite_bootstrap_plan(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None,
) -> _CompositeBootstrapPlan:
    """Resolve declarative bootstrap plan for the composite runner."""
    return _build_composite_bootstrap_plan_impl(
        config=config,
        runtime=runtime,
        run_id=run_id,
        bootstrap_runtime_basics_fn=_bootstrap_runtime_basics,
        build_runner_factories_fn=_build_runner_factories,
        build_support_services_fn=_build_support_services,
    )


def _create_composite_runner_from_plan(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    plan: _CompositeBootstrapPlan,
) -> CompositePipelineRunner:
    """Create the final composite runner from the resolved bootstrap plan."""
    return _create_composite_runner_from_plan_impl(
        config=config,
        runtime=runtime,
        plan=plan,
        runner_factory=create_composite_runner_service,
    )


def bootstrap_composite_runner(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None = None,
) -> CompositePipelineRunner:
    """Create a ``CompositePipelineRunner`` with all dependencies."""
    plan = _build_composite_bootstrap_plan(
        config=config, runtime=runtime, run_id=run_id
    )
    return _create_composite_runner_from_plan(config=config, runtime=runtime, plan=plan)

================================================================================
File: composite_bootstrap_builders.py
Path: bootstrap\runtime\composite_bootstrap_builders.py
================================================================================
"""Internal builder helpers for composite runtime bootstrap.

This module holds orchestration internals so ``composite.py`` can remain
as a thin compatibility facade with stable patch points.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime.runner_assembly import (
    create_composite_runner as _create_composite_runner_impl,
)
from bioetl.composition.bootstrap.runtime.runtime_basics import (
    bootstrap_runtime_basics as _bootstrap_runtime_basics_impl,
)
from bioetl.composition.bootstrap.runtime.runtime_basics import (
    build_runner_factories,
    build_support_services,
)

__all__ = [
    "bootstrap_runtime_basics",
    "build_runner_factories",
    "build_support_services",
    "create_composite_runner",
]


def bootstrap_runtime_basics(
    *,
    config: CompositeConfig,
    run_id: str | None,
    settings_provider: Callable[[], Settings],
    logger_bootstrapper: Callable[[str, UUID, str], LoggerPort],
    tracer_bootstrapper: Callable[[Settings], TracingPort],
    storage_bootstrapper: Callable[..., object],
    lock_factory: Callable[[], LockPort],
    uuid_factory: Callable[[], UUID],
) -> CompositeInfrastructureContext:
    """Build base runtime dependencies shared across composite bootstrap.

    Args:
        config: Validated CompositeConfig used to derive the pipeline name.
        run_id: Optional run UUID string; a new UUID is generated when None.
        settings_provider: Callable returning global Settings.
        logger_bootstrapper: Callable accepting (pipeline_name, run_uuid, log_level)
            and returning a LoggerPort.
        storage_bootstrapper: Callable returning a storage adapter (any type).
        lock_factory: Callable returning a LockPort implementation.
        uuid_factory: Callable returning a new UUID (injectable for testing).

    Returns:
        Infrastructure context handoff for the composite run.
    """
    run_id_value, settings, logger, metrics, tracer, storage, lock = (
        _bootstrap_runtime_basics_impl(
            config=config,
            run_id=run_id,
            settings_provider=settings_provider,
            logger_bootstrapper=logger_bootstrapper,
            tracer_bootstrapper=tracer_bootstrapper,
            storage_bootstrapper=storage_bootstrapper,
            lock_factory=lock_factory,
            uuid_factory=uuid_factory,
        )
    )
    return CompositeInfrastructureContext(
        run_id=run_id_value,
        settings=settings,
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        storage=storage,
        lock=lock,
    )


if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    import polars as pl

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_wiring_api import (
        CompositePipelineRunner,
        PipelineRunner,
    )
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LockPort, LoggerPort, MetricsPort, TracingPort
    from bioetl.infrastructure.config import Settings


def create_composite_runner(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    tracer: TracingPort | None,
    lock: LockPort,
    seed_runner_factory: Callable[[], PipelineRunner],
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    support_services: CompositeSupportServices,
    runner_factory: Callable[..., CompositePipelineRunner],
) -> CompositePipelineRunner:
    """Create fully wired CompositePipelineRunner.

    Args:
        config: CompositeConfig for this composite run.
        runtime: Runtime options for the composite run.
        run_id: UUID string identifying this run.
        logger: Structured logger forwarded to the runner.
        lock: LockPort used for runtime execution safety.
        seed_runner_factory: Callable that creates a seed-phase PipelineRunner.
        dependencies_runner_factory: Callable that creates a dependency-phase
            PipelineRunner given a pipeline name and keys DataFrame.
        enricher_runner_factory: Callable that creates an enricher-phase
            PipelineRunner given a pipeline name and keys DataFrame.
        support_services: Bundle of support services (checkpoint, merger, etc.).
        runner_factory: Factory callable used to instantiate
            CompositePipelineRunner with all wired dependencies.

    Returns:
        Fully wired CompositePipelineRunner ready for execution.
    """
    return _create_composite_runner_impl(
        config=config,
        runtime=runtime,
        run_id=run_id,
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        lock=lock,
        seed_runner_factory=seed_runner_factory,
        dependencies_runner_factory=dependencies_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        support_services=support_services,
        runner_factory=runner_factory,
    )

================================================================================
File: composite_control_plane_builder.py
Path: bootstrap\runtime\composite_control_plane_builder.py
================================================================================
"""Control-plane builders for composite runtime bootstrap."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID

from bioetl.application.services.control_plane.run_ledger_service import (
    RunLedgerService,
)
from bioetl.application.services.control_plane.run_manifest_service import (
    RunManifestCreateSpec,
    RunManifestService,
)
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime._composite_control_plane_payloads import (
    build_composite_launch_context_snapshot,
    build_composite_planned_artifacts,
    build_composite_resolved_config_snapshot,
    build_composite_runtime_config_snapshot,
    build_composite_source_refs,
)
from bioetl.composition.bootstrap.runtime.composite_support_service_bundles import (
    CompositeControlPlaneBundle,
)
from bioetl.composition.runtime_builders.run_manifest_support import (
    control_plane_root as _shared_control_plane_root,
)
from bioetl.composition.runtime_builders.run_manifest_support import (
    to_serializable_mapping as _shared_to_serializable_mapping,
)
from bioetl.composition.runtime_builders.runner_builder_support import (
    validate_required_persistence_profile,
)
from bioetl.composition.services.versioning import compute_config_hash, get_git_commit
from bioetl.domain.control_plane import ReplayCapability
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane import FileRunLedgerStore, FileRunManifestStore

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.config import Settings

__all__ = [
    "bind_manifest_logger",
    "build_composite_control_plane_bundle",
    "resolve_composite_control_plane_flags",
]


def resolve_composite_control_plane_flags(settings: object) -> tuple[bool, bool]:
    """Resolve manifest/ledger feature flags for executable composite runs."""
    pipeline_settings = getattr(settings, "pipeline", None)
    control_plane = getattr(pipeline_settings, "control_plane", None)
    manifest_enabled = bool(getattr(control_plane, "run_manifest_enabled", True))
    ledger_enabled = bool(getattr(control_plane, "run_ledger_enabled", True))
    required_profile = getattr(
        control_plane,
        "required_persistence_profile",
        "degraded_observable",
    )
    if not manifest_enabled:
        raise RuntimeError(
            "Composite execution requires run manifests; set "
            "pipeline.control_plane.run_manifest_enabled=true"
        )
    validate_required_persistence_profile(
        manifest_enabled=manifest_enabled,
        ledger_enabled=ledger_enabled,
        required_profile=required_profile,
        execution_label="Composite execution",
        exact_replay_execution_context_supported=False,
    )
    return True, ledger_enabled


def bind_manifest_logger(logger: LoggerPort, manifest_id: str | None) -> LoggerPort:
    """Bind ``manifest_id`` into logger context when supported."""
    if manifest_id is None:
        return logger
    bind = getattr(logger, "bind", None)
    if not callable(bind):
        return logger
    rebound = bind(manifest_id=manifest_id)
    return cast("LoggerPort", rebound)


def build_composite_control_plane_bundle(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
) -> CompositeControlPlaneBundle:
    """Materialize manifest/ledger artifacts for one composite execution."""
    _manifest_enabled, ledger_enabled = resolve_composite_control_plane_flags(
        infra_context.settings
    )
    control_plane = getattr(
        getattr(infra_context.settings, "pipeline", None), "control_plane", None
    )
    required_profile = getattr(
        control_plane,
        "required_persistence_profile",
        "degraded_observable",
    )

    config_hash = _resolve_effective_config_hash(config)
    contract_ref = config.name
    contract_version = getattr(config, "version", "") or ""
    manifest_store = FileRunManifestStore(
        base_path=_control_plane_root(infra_context.settings, "run_manifest"),
        metrics=infra_context.metrics,
    )
    manifest = RunManifestService(manifest_port=manifest_store).create_manifest(
        _build_composite_manifest_create_request(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
            config_hash=config_hash,
            contract_ref=contract_ref,
            contract_version=contract_version,
            required_persistence_profile=str(required_profile),
        )
    )
    run_ledger_service = _build_run_ledger_service(
        manifest_id=manifest.manifest_id,
        ledger_enabled=ledger_enabled,
        infra_context=infra_context,
        pipeline_name=config.name,
        config_hash=config_hash,
        contract_ref=contract_ref,
        contract_version=contract_version,
    )
    if run_ledger_service is not None:
        run_ledger_service.record_manifest_created(manifest)
    return CompositeControlPlaneBundle(
        manifest_id=manifest.manifest_id,
        run_ledger_service=run_ledger_service,
        config_hash=config_hash or None,
        contract_ref=contract_ref,
        contract_version=contract_version or None,
    )


def _build_composite_manifest_create_request(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
    config_hash: str,
    contract_ref: str,
    contract_version: str,
    required_persistence_profile: str,
) -> RunManifestCreateSpec:
    """Build the manifest creation payload for one composite execution."""
    return RunManifestCreateSpec(
        run_id=_coerce_run_id(infra_context.run_id),
        run_type=RunType.INCREMENTAL,
        pipeline_name=config.name,
        provider="composite",
        entity=config.name,
        launch_context=build_composite_launch_context_snapshot(
            config,
            runtime,
            required_persistence_profile=required_persistence_profile,
        ),
        runtime_config=build_composite_runtime_config_snapshot(runtime),
        resolved_config=build_composite_resolved_config_snapshot(config),
        source_refs=build_composite_source_refs(config),
        planned_artifacts=build_composite_planned_artifacts(config),
        pipeline_version=contract_version or None,
        git_commit=get_git_commit(),
        config_hash=config_hash or None,
        contract_ref=contract_ref,
        contract_version=contract_version or None,
        replay_capability=ReplayCapability.REBUILD_ONLY,
    )


def _build_run_ledger_service(
    *,
    manifest_id: str,
    ledger_enabled: bool,
    infra_context: CompositeInfrastructureContext,
    pipeline_name: str,
    config_hash: str,
    contract_ref: str,
    contract_version: str,
) -> RunLedgerService | None:
    """Create composite run-ledger service when feature flag allows it."""
    if not ledger_enabled:
        return None
    return RunLedgerService(
        ledger_port=FileRunLedgerStore(
            base_path=_control_plane_root(infra_context.settings, "run_ledger"),
            metrics=infra_context.metrics,
        ),
        manifest_id=manifest_id,
        run_id=_coerce_run_id(infra_context.run_id),
        pipeline_name=pipeline_name,
        provider="composite",
        entity=pipeline_name,
        run_type=RunType.INCREMENTAL.value,
        effective_config_hash=config_hash or None,
        contract_ref=contract_ref,
        contract_version=contract_version or None,
        composite_run_id=infra_context.run_id,
    )


def _resolve_effective_config_hash(config: CompositeConfig) -> str:
    """Best-effort hash for checkpoint and manifest provenance anchors."""
    try:
        payload = config.to_dict()
    except (AttributeError, TypeError, ValueError):
        return ""
    if not isinstance(payload, dict):
        return ""
    try:
        payload_dict: dict[str, object] = payload
        return compute_config_hash(payload_dict)
    except (TypeError, ValueError):
        return ""


def _coerce_run_id(run_id: str) -> RunID:
    """Convert composite runtime run_id string into canonical RunID type."""
    return RunID(UUID(run_id))


def _control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return _shared_control_plane_root(settings, leaf)


def _normalize_object(value: object) -> dict[str, object]:
    """Convert dataclasses/models into stable JSON-safe mappings."""
    return _shared_to_serializable_mapping(value)

================================================================================
File: composite_execution_support_builder.py
Path: bootstrap\runtime\composite_execution_support_builder.py
================================================================================
"""Execution-support builders for composite runtime composition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.runtime_wiring_api import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    DependencyCoordinatorService,
    DependencyProgressService,
    DependencyResultService,
    EnrichmentCoordinatorService,
    KeyExtractorService,
    create_chained_key_resolver,
    create_seed_key_resolver,
    validate_join_key_normalization_policies,
)
from bioetl.composition.bootstrap.runtime.composite_support_service_bundles import (
    ExecutionSupportServicesBundle,
)

if TYPE_CHECKING:
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.storage.delta_reader import DeltaReader


def build_execution_support_services(
    *,
    config: CompositeConfig,
    logger: LoggerPort,
    delta_reader: DeltaReader,
) -> ExecutionSupportServicesBundle:
    """Build execution-facing support services shared across runtime stages."""
    validate_join_key_normalization_policies(config)
    return ExecutionSupportServicesBundle(
        key_extractor=KeyExtractorService(
            delta_reader=delta_reader,
            logger=logger,
            normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
        ),
        dependency_coordinator=DependencyCoordinatorService(
            logger=logger,
            seed_key_resolver=create_seed_key_resolver(
                logger,
                normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
            ),
            chained_key_resolver=create_chained_key_resolver(
                logger,
                normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
            ),
            progress_service=DependencyProgressService(logger),
            result_service=DependencyResultService(logger),
            delta_reader=delta_reader,
        ),
        coordinator=EnrichmentCoordinatorService(
            logger=logger,
            dq_config=config.dq,
            max_concurrency=config.execution.max_concurrency,
        ),
    )


__all__ = ["build_execution_support_services"]

================================================================================
File: composite_filter_extraction_service.py
Path: bootstrap\runtime\composite_filter_extraction_service.py
================================================================================
"""Filter extraction service for composite runtime runner factories."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import polars as pl

from bioetl.application.composite.runtime_wiring_api import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    JoinKeyNormalizationPolicy,
    stringify_join_key_value,
)

if TYPE_CHECKING:
    from bioetl.domain.composite.config import DependencyConfig, EnricherConfig
    from bioetl.domain.ports import LoggerPort


class CompositeFilterExtractionService:
    """Extract runner filter inputs from keys DataFrame."""

    def __init__(
        self,
        logger: LoggerPort | None = None,
        normalization_policies: Mapping[
            str, JoinKeyNormalizationPolicy
        ] = JOIN_KEY_NORMALIZATION_POLICIES,
    ) -> None:
        self._logger = logger
        self._normalization_policies = normalization_policies

    def to_id_str(self, value: object, *, key: str) -> str:
        """Convert a join key to a canonical filter ID string."""
        return str(
            stringify_join_key_value(
                value,
                key=key,
                normalization_policies=self._normalization_policies,
            )
        )

    def _deduplicate_filter_ids(
        self,
        values: list[object],
        *,
        key: str,
    ) -> tuple[str, ...]:
        """Normalize values and preserve first-seen order after deduplication."""
        return tuple(dict.fromkeys(self.to_id_str(value, key=key) for value in values))

    def build_fallback_mapping(
        self,
        keys: pl.DataFrame,
        filter_key: str,
        join_keys: tuple[str, ...],
    ) -> dict[str, str] | None:
        """Build ID-to-title mapping when title is part of the join keys."""
        if "title" not in join_keys or "title" not in keys.columns:
            return None
        pairs = keys.select([filter_key, "title"]).drop_nulls().iter_rows()
        mapping: dict[str, str] = {}
        for key, title in pairs:
            mapping.setdefault(self.to_id_str(key, key=filter_key), str(title))
        return mapping

    @staticmethod
    def find_filter_key(
        join_keys: tuple[str, ...],
        columns: list[str],
    ) -> str | None:
        """Find the first usable join key, preferring non-title keys."""
        for key in join_keys:
            if key == "title" and len(join_keys) > 1:
                continue
            if key in columns:
                return key
        return None

    def extract_enricher_filters(
        self,
        enricher_cfg: EnricherConfig,
        keys: pl.DataFrame | None,
    ) -> tuple[tuple[str, ...] | None, str | None, dict[str, str] | None]:
        """Extract single-field filters and fallback mapping for an enricher."""
        if keys is None or len(keys) == 0:
            self._debug(
                "No keys available for enricher", pipeline=enricher_cfg.pipeline
            )
            return None, None, None

        filter_key = self.find_filter_key(enricher_cfg.join_keys, keys.columns)
        if filter_key is None:
            self._warning(
                "Join key not found in keys columns",
                pipeline=enricher_cfg.pipeline,
                join_keys=list(enricher_cfg.join_keys),
                available_columns=list(keys.columns),
            )
            return None, None, None

        key_values = keys.select(filter_key).drop_nulls().to_series().to_list()
        if not key_values:
            return None, None, None

        filter_ids = self._deduplicate_filter_ids(key_values, key=filter_key)
        fallback_mapping = self.build_fallback_mapping(
            keys=keys,
            filter_key=filter_key,
            join_keys=enricher_cfg.join_keys,
        )
        return filter_ids, filter_key, fallback_mapping

    def extract_field_values(
        self,
        keys: pl.DataFrame,
        field: str,
    ) -> tuple[str, ...] | None:
        """Extract unique non-null values for a field from the keys frame."""
        if field not in keys.columns:
            return None
        values = keys.select(field).drop_nulls().to_series().to_list()
        if not values:
            return None
        return self._deduplicate_filter_ids(values, key=field)

    def extract_multi_filter_ids(
        self,
        dep_cfg: DependencyConfig,
        keys: pl.DataFrame | None,
    ) -> dict[str, tuple[str, ...]] | None:
        """Extract multi-field filter IDs for a dependency pipeline."""
        if keys is None or len(keys) == 0:
            return None

        result: dict[str, tuple[str, ...]] = {}
        for field in dep_cfg.effective_filter_fields:
            values = self.extract_field_values(keys, field)
            if values is None:
                self._warning(
                    "Multi-filter field missing or empty",
                    pipeline=dep_cfg.pipeline,
                    field=field,
                    available_columns=list(keys.columns),
                )
                return None
            result[field] = values

        self._info(
            "Extracted multi-field filter IDs",
            pipeline=dep_cfg.pipeline,
            fields=list(result.keys()),
            counts={field: len(ids) for field, ids in result.items()},
        )
        return result

    def resolve_dependency_filter_inputs(
        self,
        dep_cfg: DependencyConfig | None,
        keys: pl.DataFrame | None,
    ) -> tuple[tuple[str, ...] | None, str | None, dict[str, tuple[str, ...]] | None]:
        """Resolve single-field or multi-field dependency filter inputs."""
        filter_ids: tuple[str, ...] | None = None
        filter_field: str | None = None
        multi_filter_ids: dict[str, tuple[str, ...]] | None = None

        if dep_cfg is None or keys is None or len(keys) == 0:
            return filter_ids, filter_field, multi_filter_ids

        if dep_cfg.is_multi_field_filter:
            multi_filter_ids = self.extract_multi_filter_ids(dep_cfg, keys)
            return filter_ids, filter_field, multi_filter_ids

        for key in dep_cfg.join_keys:
            if key not in keys.columns:
                continue
            key_values = keys.select(key).drop_nulls().to_series().to_list()
            if not key_values:
                continue
            filter_ids = self._deduplicate_filter_ids(key_values, key=key)
            filter_field = dep_cfg.filter_field or key
            break

        return filter_ids, filter_field, multi_filter_ids

    def _debug(self, event: str, **kwargs: object) -> None:
        if self._logger is not None:
            self._logger.debug(event, **kwargs)

    def _info(self, event: str, **kwargs: object) -> None:
        if self._logger is not None:
            self._logger.info(event, **kwargs)

    def _warning(self, event: str, **kwargs: object) -> None:
        if self._logger is not None:
            self._logger.warning(event, **kwargs)


__all__ = ["CompositeFilterExtractionService"]

================================================================================
File: composite_infrastructure_context.py
Path: bootstrap\runtime\composite_infrastructure_context.py
================================================================================
"""Compatibility shim for the composite infrastructure context type."""

from __future__ import annotations

from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)

__all__ = ["CompositeInfrastructureContext"]

================================================================================
File: composite_merge_dependency_builder.py
Path: bootstrap\runtime\composite_merge_dependency_builder.py
================================================================================
"""Merge-dependency builders for composite runtime composition."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from bioetl.application.composite.helpers.resolver_helper import ResolverHelper
from bioetl.application.composite.join_execution import JoinExecutorService
from bioetl.application.composite.runtime_wiring_api import (
    CoalescePolicyService,
    ColumnOrderService,
    ColumnRenamer,
    ConflictResolverService,
    DependencyJoinerService,
    EnricherAggregator,
    EnricherDeduplicatorService,
    JoinHow,
    JoinKeyNormalizationPolicy,
    JoinKeyResolverService,
    JoinPlannerService,
    JoinPreparationCollaborators,
    parse_pipeline_name,
    resolve_field_aliases_from_registry,
)
from bioetl.composition.bootstrap.runtime.composite_support_service_bundles import (
    MergeDependenciesBundle,
)
from bioetl.composition.factories.services.polars_join_adapter import PolarsJoinAdapter
from bioetl.domain.composite.strategy import MergeStrategy

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LoggerPort


def build_merge_dependencies(
    *,
    config: CompositeConfig,
    logger: LoggerPort,
    resolve_join_how: Callable[[MergeStrategy], JoinHow],
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy],
    system_columns_to_drop: frozenset[str],
) -> MergeDependenciesBundle:
    """Assemble merge-specific collaborators used by MergeService."""
    merge_column_groups = getattr(config.merge, "column_groups", None)
    deduplicator = EnricherDeduplicatorService(logger)
    aggregator = EnricherAggregator(logger)
    renamer = ColumnRenamer(logger)
    order_service = ColumnOrderService(
        logger,
        column_groups=merge_column_groups if merge_column_groups else None,
    )
    coalesce_policy = CoalescePolicyService(logger, order_service=order_service)
    conflict_resolver = ConflictResolverService(
        config.merge,
        logger,
        coalesce_policy,
    )
    resolver_helper = ResolverHelper(
        logger=logger,
        normalization_policies=normalization_policies,
    )
    join_key_resolver = JoinKeyResolverService(
        resolver_helper=resolver_helper,
        parse_pipeline_name=parse_pipeline_name,
    )
    # Create the actual JoinExecutorService first
    join_service = JoinExecutorService(
        logger=logger,
        join_type_resolver=lambda: resolve_join_how(config.merge.strategy),
    )
    # Wrap it with the real adapter
    join_executor = PolarsJoinAdapter(join_service)
    dependency_joiner = DependencyJoinerService(
        logger=logger,
        deduplicator=deduplicator,
        renamer=renamer,
        conflict_resolver=conflict_resolver,
        field_alias_resolver=resolve_field_aliases_from_registry,
        join_key_resolver=join_key_resolver,
        join_executor=join_executor,
        system_columns_to_drop=system_columns_to_drop,
    )
    join_planner = JoinPlannerService(
        merge_config=config.merge,
        logger=logger,
        preparation=JoinPreparationCollaborators(
            deduplicator=deduplicator,
            aggregator=aggregator,
            renamer=renamer,
            conflict_resolver=conflict_resolver,
        ),
        field_alias_resolver=resolve_field_aliases_from_registry,
        join_key_resolver=join_key_resolver,
        join_executor=join_executor,
        dependency_joiner=dependency_joiner,
    )
    return MergeDependenciesBundle(
        deduplicator=deduplicator,
        aggregator=aggregator,
        renamer=renamer,
        orderer=order_service,
        priority_orderer=None,
        order_service=order_service,
        coalesce_policy=coalesce_policy,
        conflict_resolver=conflict_resolver,
        join_planner=join_planner,
    )


__all__ = ["build_merge_dependencies"]

================================================================================
File: composite_runtime_management_builder.py
Path: bootstrap\runtime\composite_runtime_management_builder.py
================================================================================
"""Runtime-management builders for composite runtime composition."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.composite.runtime_wiring_api import FSMStateHelperService
from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_composite_checkpoint_port,
    bootstrap_quarantine_port,
)
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime.composite_support_service_bundles import (
    CompositeControlPlaneBundle,
    RuntimeManagementServicesBundle,
)
from bioetl.composition.services.versioning import compute_config_hash
from bioetl.domain.normalization import (
    normalize_contract_ref,
    normalize_contract_version,
    normalize_control_plane_sha256,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_wiring_api import (
        CompositeCheckpointService,
    )
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import CompositeCheckpointPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.config import Settings


def build_runtime_management_services(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
    settings: Settings,
    logger: LoggerPort,
    run_id: str,
    checkpoint_manager_cls: type[CompositeCheckpointService],
    create_dq_report_service: Callable[
        [LoggerPort, Settings, MetricsPort],
        DQReportService,
    ],
    control_plane_bundle: CompositeControlPlaneBundle | None = None,
) -> RuntimeManagementServicesBundle:
    """Build checkpoint, FSM, DQ, and quarantine runtime services."""

    expected_effective_config_hash = _resolve_expected_effective_config_hash(config)
    checkpoint_storage: CompositeCheckpointPort = bootstrap_composite_checkpoint_port()
    quarantine_port = (
        bootstrap_quarantine_port() if config.cross_validation.enabled else None
    )
    return RuntimeManagementServicesBundle(
        checkpoint_manager=checkpoint_manager_cls(
            composite_name=config.name,
            run_id=run_id,
            storage=checkpoint_storage,
            logger=logger,
            resume=runtime.resume,
            expected_effective_config_hash=expected_effective_config_hash,
            expected_contract_ref=normalize_contract_ref(config.name),
            expected_contract_version=normalize_contract_version(
                getattr(config, "version", "")
            ),
            expected_manifest_id=(
                None
                if control_plane_bundle is None
                else control_plane_bundle.manifest_id
            ),
            run_ledger_port=(
                None
                if control_plane_bundle is None
                or control_plane_bundle.run_ledger_service is None
                else control_plane_bundle.run_ledger_service.ledger_port
            ),
        ),
        dq_report_service=create_dq_report_service(
            logger,
            settings,
            infra_context.metrics,
        ),
        fsm_state_helper=FSMStateHelperService(
            config=config,
            logger=logger,
            run_id=run_id,
        ),
        quarantine_port=quarantine_port,
    )


def _resolve_expected_effective_config_hash(config: CompositeConfig) -> str:
    """Best-effort hash for checkpoint compatibility anchors."""
    to_dict = getattr(config, "to_dict", None)
    if not callable(to_dict):
        return ""
    try:
        payload = to_dict()
    except (AttributeError, TypeError, ValueError):
        return ""
    if not isinstance(payload, dict):
        return ""
    try:
        return (
            normalize_control_plane_sha256(
                compute_config_hash(cast(dict[str, object], payload))
            )
            or ""
        )
    except (TypeError, ValueError):
        return ""


__all__ = ["build_runtime_management_services"]

================================================================================
File: composite_support_helpers.py
Path: bootstrap\runtime\composite_support_helpers.py
================================================================================
"""Helper factories for composite runtime support services."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.infrastructure.config.field_group_loader import (
    FieldGroupLoadError,
    load_field_groups,
)

if TYPE_CHECKING:
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.config import Settings

FIELD_GROUP_CONFIG_DIR = Path("configs/composites/field_groups")


def _load_field_group_registry(
    composite_name: str,
    logger: LoggerPort,
) -> FieldGroupRegistry | None:
    """Load field group registry for composite pipeline if config exists.

    Resolves the entity name from the composite pipeline name, looks for a
    YAML config file in the canonical field groups directory, and loads the
    registry. Returns None silently when no config is found so callers can
    treat missing field group configs as an opt-out.

    Args:
        composite_name: Composite pipeline name (e.g., 'composite_publication').
        logger: Structured logger used to emit debug/info/warning events.

    Returns:
        Populated FieldGroupRegistry if a config file exists, None otherwise.
    """
    entity = (
        composite_name.replace("composite_", "")
        if "_" in composite_name
        else composite_name
    )
    config_path = FIELD_GROUP_CONFIG_DIR / f"{entity}.yaml"
    if not config_path.exists():
        logger.debug(
            "No field group config found, skipping",
            config_path=str(config_path),
        )
        return None

    try:
        registry = load_field_groups(config_path)
        logger.info(
            "Loaded field group registry",
            config_path=str(config_path),
            groups=len(registry.groups),
            fields=registry.field_count,
            columns=registry.column_count,
        )
        return registry
    except (FieldGroupLoadError, FileNotFoundError) as error:
        logger.warning(
            "Failed to load field group config, continuing without it",
            error=str(error),
            config_path=str(config_path),
        )
        return None


def _create_dq_report_service(
    logger: LoggerPort,
    settings: Settings,
    metrics: MetricsPort,
) -> DQReportService:
    """Create DQ report service for composite pipelines.

    Builds a DQReportService wired with a DQReportWriter that writes reports
    to the canonical DQ output path under data_dir.

    Args:
        logger: Structured logger forwarded to both the writer and service.
        settings: Global settings providing data_dir for report output paths.
        metrics: Metrics port used for DQ lifecycle counters.

    Returns:
        DQReportService ready for composite pipeline DQ report generation.
    """
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.infrastructure.export.dq_report_writer import DQReportWriter

    reports_base_path = Path(settings.data_dir) / "output" / "reports" / "dq"
    report_writer = DQReportWriter(
        base_path=reports_base_path,
        logger=logger,
    )
    return DQReportService(
        logger=logger,
        report_writer=report_writer,
        metrics=metrics,
    )

================================================================================
File: composite_support_service_builders.py
Path: bootstrap\runtime\composite_support_service_builders.py
================================================================================
"""Facade exports for composite runtime support service builders."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig

from bioetl.composition.bootstrap.runtime.composite_execution_support_builder import (
    build_execution_support_services,
)
from bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder import (
    build_merge_dependencies,
)
from bioetl.composition.bootstrap.runtime.composite_runtime_management_builder import (
    build_runtime_management_services,
)
from bioetl.composition.bootstrap.runtime.composite_support_service_bundles import (
    ExecutionSupportServicesBundle,
    MergeDependenciesBundle,
    RuntimeManagementServicesBundle,
)

_RUNTIME_CONFIG_FACADE: type[CompositeRuntimeConfig] | None = None

__all__ = [
    "ExecutionSupportServicesBundle",
    "MergeDependenciesBundle",
    "RuntimeManagementServicesBundle",
    "build_execution_support_services",
    "build_merge_dependencies",
    "build_runtime_management_services",
]

================================================================================
File: composite_support_service_bundles.py
Path: bootstrap\runtime\composite_support_service_bundles.py
================================================================================
"""Dataclass bundles for composite runtime support assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_wiring_api import (
        CoalescePolicyService,
        ColumnOrderService,
        ColumnPriorityOrderer,
        ColumnRenamer,
        CompositeCheckpointService,
        ConflictResolverService,
        DependencyCoordinatorService,
        EnricherAggregator,
        EnricherDeduplicatorService,
        EnrichmentCoordinatorService,
        FSMStateHelperService,
        JoinPlannerService,
        KeyExtractorService,
    )
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.ports import QuarantinePort


@dataclass(slots=True)
class ExecutionSupportServicesBundle:
    """Execution-facing services shared across composite runtime phases."""

    key_extractor: KeyExtractorService
    dependency_coordinator: DependencyCoordinatorService
    coordinator: EnrichmentCoordinatorService


@dataclass(slots=True)
class RuntimeManagementServicesBundle:
    """Checkpoint, FSM, DQ, and quarantine services for runtime orchestration."""

    checkpoint_manager: CompositeCheckpointService
    dq_report_service: DQReportService
    fsm_state_helper: FSMStateHelperService
    quarantine_port: QuarantinePort | None


@dataclass(frozen=True, slots=True)
class CompositeControlPlaneBundle:
    """Optional control-plane artifacts materialized for one composite run."""

    manifest_id: str | None = None
    run_ledger_service: RunLedgerService | None = None
    config_hash: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None


@dataclass(slots=True)
class MergeDependenciesBundle:
    """Merge-specific collaborators assembled in composition."""

    deduplicator: EnricherDeduplicatorService
    aggregator: EnricherAggregator
    renamer: ColumnRenamer
    orderer: ColumnOrderService | None
    priority_orderer: ColumnPriorityOrderer | None
    order_service: ColumnOrderService
    coalesce_policy: CoalescePolicyService
    conflict_resolver: ConflictResolverService
    join_planner: JoinPlannerService


__all__ = [
    "CompositeControlPlaneBundle",
    "ExecutionSupportServicesBundle",
    "MergeDependenciesBundle",
    "RuntimeManagementServicesBundle",
]

================================================================================
File: composite_support_services_factory.py
Path: bootstrap\runtime\composite_support_services_factory.py
================================================================================
"""Factory for composite runtime support services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.application.composite.runtime_wiring_api import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    CompositeCheckpointService,
    DependencyCoordinatorService,
    EnrichmentCoordinatorService,
    EnrichmentCrossValidator,
    FSMStateHelperService,
    JoinHow,
    KeyExtractorService,
    MergeCollaboratorGroup,
    MergeService,
    validate_join_key_normalization_policies,
)
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime.composite_control_plane_builder import (
    bind_manifest_logger,
    build_composite_control_plane_bundle,
)
from bioetl.composition.bootstrap.runtime.composite_support_service_builders import (
    build_execution_support_services,
    build_merge_dependencies,
    build_runtime_management_services,
)
from bioetl.domain.composite.strategy import MergeStrategy
from bioetl.infrastructure.storage.delta_reader import DeltaReader

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import LoggerPort, MetricsPort, QuarantinePort
    from bioetl.infrastructure.config import Settings


@dataclass(slots=True)
class CompositeSupportServices:
    """Bundle of support services required by CompositePipelineRunner."""

    key_extractor: KeyExtractorService
    dependency_coordinator: DependencyCoordinatorService
    coordinator: EnrichmentCoordinatorService
    merger: MergeService
    checkpoint_manager: CompositeCheckpointService
    dq_report_service: DQReportService
    fsm_state_helper: FSMStateHelperService
    quarantine_port: QuarantinePort | None
    manifest_id: str | None = None
    run_ledger_service: RunLedgerService | None = None


class CompositeSupportServicesFactory:
    """Build support services used by composite runtime orchestration."""

    _JOIN_KEY_NORMALIZATION_POLICIES = JOIN_KEY_NORMALIZATION_POLICIES
    _SYSTEM_COLUMNS_TO_DROP: frozenset[str] = frozenset(
        {
            "_run_id",
            "_run_type",
            "_source_batch_id",
            "_ingestion_ts",
            "_dq_warn",
            "_dq_error",
            "_index",
            "_lookup_method",
            "_original_id",
            "_source",
        }
    )

    def __init__(
        self,
        *,
        config: CompositeConfig,
        runtime: CompositeRuntimeConfig,
        infra_context: CompositeInfrastructureContext,
        resolve_gold_schema: Callable[[str], type | None],
        load_field_group_registry: Callable[
            [str, LoggerPort], FieldGroupRegistry | None
        ],
        create_dq_report_service: Callable[
            [LoggerPort, Settings, MetricsPort],
            DQReportService,
        ],
        checkpoint_manager_cls: type[
            CompositeCheckpointService
        ] = CompositeCheckpointService,
    ) -> None:
        """Store composite runtime dependencies and validate normalization policies."""
        validate_join_key_normalization_policies(
            config,
            self._JOIN_KEY_NORMALIZATION_POLICIES,
        )
        self._config = config
        self._runtime = runtime
        self._infra = infra_context
        self._resolve_gold_schema = resolve_gold_schema
        self._load_field_group_registry = load_field_group_registry
        self._create_dq_report_service = create_dq_report_service
        self._checkpoint_manager_cls = checkpoint_manager_cls

    def build(self) -> CompositeSupportServices:
        """Build and return the support-service bundle."""
        control_plane_bundle = build_composite_control_plane_bundle(
            config=self._config,
            runtime=self._runtime,
            infra_context=self._infra,
        )
        logger = bind_manifest_logger(
            self._infra.logger,
            control_plane_bundle.manifest_id,
        )
        delta_reader = self._create_delta_reader(logger=logger)
        execution_services = build_execution_support_services(
            config=self._config,
            logger=logger,
            delta_reader=delta_reader,
        )
        field_group_registry = self._load_field_group_registry(
            self._config.name,
            logger,
        )
        cross_validator = self._create_cross_validator(logger=logger)
        merger = self._create_merge_service(
            delta_reader=delta_reader,
            field_group_registry=field_group_registry,
            cross_validator=cross_validator,
            logger=logger,
        )
        runtime_management_services = build_runtime_management_services(
            config=self._config,
            runtime=self._runtime,
            infra_context=self._infra,
            settings=self._infra.settings,
            logger=logger,
            run_id=self._infra.run_id,
            checkpoint_manager_cls=self._checkpoint_manager_cls,
            create_dq_report_service=self._create_dq_report_service,
            control_plane_bundle=control_plane_bundle,
        )

        return CompositeSupportServices(
            key_extractor=execution_services.key_extractor,
            dependency_coordinator=execution_services.dependency_coordinator,
            coordinator=execution_services.coordinator,
            merger=merger,
            checkpoint_manager=runtime_management_services.checkpoint_manager,
            dq_report_service=runtime_management_services.dq_report_service,
            fsm_state_helper=runtime_management_services.fsm_state_helper,
            quarantine_port=runtime_management_services.quarantine_port,
            manifest_id=control_plane_bundle.manifest_id,
            run_ledger_service=control_plane_bundle.run_ledger_service,
        )

    def _create_delta_reader(self, *, logger: LoggerPort) -> DeltaReader:
        silver_base_path = str(Path(self._infra.settings.data_dir) / "output")
        return DeltaReader(
            base_path=silver_base_path,
            logger=logger,
        )

    def _create_cross_validator(
        self,
        *,
        logger: LoggerPort,
    ) -> EnrichmentCrossValidator | None:
        if not self._config.cross_validation.enabled:
            return None
        return EnrichmentCrossValidator(
            config=self._config.cross_validation,
            logger=logger,
        )

    def _create_merge_service(
        self,
        *,
        delta_reader: DeltaReader,
        field_group_registry: FieldGroupRegistry | None,
        cross_validator: EnrichmentCrossValidator | None,
        logger: LoggerPort,
    ) -> MergeService:
        merge_dependencies = build_merge_dependencies(
            config=self._config,
            logger=logger,
            resolve_join_how=self._resolve_join_how,
            normalization_policies=self._JOIN_KEY_NORMALIZATION_POLICIES,
            system_columns_to_drop=self._SYSTEM_COLUMNS_TO_DROP,
        )
        return MergeService(
            merge_config=self._config.merge,
            storage=self._infra.storage,
            logger=logger,
            delta_reader=delta_reader,
            silver_reader=self._infra.storage,
            field_group_registry=field_group_registry,
            cross_validator=cross_validator,
            gold_schema=self._resolve_gold_schema(self._config.name),
            collaborators=MergeCollaboratorGroup(
                deduplicator=merge_dependencies.deduplicator,
                aggregator=merge_dependencies.aggregator,
                renamer=merge_dependencies.renamer,
                orderer=merge_dependencies.orderer,
                priority_orderer=merge_dependencies.priority_orderer,
                order_service=merge_dependencies.order_service,
                coalesce_policy=merge_dependencies.coalesce_policy,
                conflict_resolver=merge_dependencies.conflict_resolver,
                join_planner=merge_dependencies.join_planner,
            ),
        )

    @staticmethod
    def _resolve_join_how(strategy: MergeStrategy) -> JoinHow:
        match strategy:
            case MergeStrategy.LEFT_OUTER:
                return "left"
            case MergeStrategy.INNER:
                return "inner"
            case MergeStrategy.UNION:
                return "full"
            case _:
                return "left"


__all__ = ["CompositeSupportServices", "CompositeSupportServicesFactory"]

================================================================================
File: dq_bootstrap.py
Path: bootstrap\runtime\dq_bootstrap.py
================================================================================
"""DQ monitor bootstrap helpers for runtime observability wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

from bioetl.domain.ports import DQMonitorPort, LoggerPort
from bioetl.infrastructure.observability.anomaly import DataQualityMonitorService
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.infrastructure.config import Settings


class _ConfigurableDQMonitor(DQMonitorPort, Protocol):
    """DQ monitor contract with detector configuration support."""

    detector: _DQDetectorConfig


class _DQDetectorConfig(Protocol):
    """Configuration surface used by bootstrap when wiring DQ thresholds."""

    min_baseline_samples: int

    def set_threshold(
        self,
        metric_name: str,
        *,
        min_value: float,
        max_value: float,
    ) -> None: ...


__all__ = [
    "bootstrap_dq_monitor_port",
]


def bootstrap_dq_monitor_port(
    settings: Settings,
    logger: LoggerPort | None = None,
    monitor_factory: Callable[..., DQMonitorPort] = DataQualityMonitorService,
    noop_logger_factory: Callable[[], LoggerPort] = NoOpLogger,
) -> DQMonitorPort | None:
    """Create a data quality monitor port implementation.

    Args:
        settings: Application settings providing DQ monitoring flags, baseline window,
            Z-score threshold, error rate max, and quality score min.
        logger: Optional LoggerPort for structured DQ monitor logging; uses NoOpLogger
            when None.
        monitor_factory: Factory creating the DQ monitor implementation.
        noop_logger_factory: Factory used when no logger is provided.

    Returns:
        DQMonitorPort if DQ monitoring is enabled, None otherwise.
    """
    obs_settings = settings.observability

    if not obs_settings.dq_monitor_enabled:
        return None

    effective_logger = logger if logger is not None else noop_logger_factory()
    monitor = cast(
        _ConfigurableDQMonitor,
        monitor_factory(
            logger=effective_logger,
            baseline_window=obs_settings.dq_baseline_window,
            z_score_threshold=obs_settings.dq_z_score_threshold,
        ),
    )

    monitor.detector.min_baseline_samples = obs_settings.dq_min_baseline_samples
    monitor.detector.set_threshold(
        "error_rate",
        min_value=0.0,
        max_value=obs_settings.dq_error_rate_max,
    )
    monitor.detector.set_threshold(
        "quality_score",
        min_value=obs_settings.dq_quality_score_min,
        max_value=1.0,
    )

    return monitor

================================================================================
File: enum_loader_wiring.py
Path: bootstrap\runtime\enum_loader_wiring.py
================================================================================
"""Wiring for enum loader dependencies in composition layer."""

from __future__ import annotations

from bioetl.domain.config.enum_loader import EnumLoaderPort
from bioetl.infrastructure.config.enum_loader_adapter import FileSystemEnumLoader

__all__ = [
    "create_enum_loader_for_domain",
    "initialize_domain_enum_fields",
]


def create_enum_loader_for_domain() -> EnumLoaderPort:
    """Create enum loader instance for domain layer dependency injection.

    Returns:
        Configured EnumLoaderPort implementation
    """
    return FileSystemEnumLoader()


def initialize_domain_enum_fields() -> None:
    """Initialize domain layer enum fields using dependency injection.

    This function should be called during bootstrap to ensure domain layer
    enum configurations are properly loaded before any domain logic executes.

    Note: The actual enum loading happens lazily when domain functions are first called,
    but this function ensures the dependency injection wiring is available.
    """
    # Create the enum loader to ensure it's available for lazy initialization
    create_enum_loader_for_domain()
    # The enum loading is handled lazily by the domain layer when needed
    # This ensures the DI wiring is set up correctly

================================================================================
File: logger_bootstrap.py
Path: bootstrap\runtime\logger_bootstrap.py
================================================================================
"""Logger bootstrap helpers for runtime observability wiring."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.observability import UnifiedLogger

if TYPE_CHECKING:
    LoggerFactory = Callable[[str, UUID, str], LoggerPort]


__all__ = [
    "bootstrap_logger_port",
]


def _default_logger_factory(pipeline: str, run_id: UUID, log_level: str) -> LoggerPort:
    """Create a UnifiedLogger with standard runtime settings."""
    return UnifiedLogger(
        pipeline=pipeline,
        run_id=run_id,
        log_level=log_level,
        json_format=True,
    )


def bootstrap_logger_port(
    pipeline: str,
    run_id: UUID | None = None,
    log_level: str = "INFO",
    logger_factory: LoggerFactory | None = None,
) -> LoggerPort:
    """Create a logger port implementation for pipeline execution.

    Args:
        pipeline: Pipeline name used as a structured log field (e.g., 'chembl_activity').
        run_id: Run UUID for log correlation; a new UUID is generated if None.
        log_level: Minimum log level string (e.g., 'INFO', 'DEBUG').
        logger_factory: Optional factory callable for DI/testing; uses UnifiedLogger
            with JSON format when None.

    Returns:
        Configured LoggerPort for structured pipeline logging.
    """
    effective_run_id = run_id if run_id is not None else uuid4()
    factory = logger_factory or _default_logger_factory
    return factory(pipeline, effective_run_id, log_level)

================================================================================
File: metrics_bootstrap.py
Path: bootstrap\runtime\metrics_bootstrap.py
================================================================================
"""Metrics bootstrap helpers for runtime observability wiring."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.services.metrics_service import MetricsService
from bioetl.composition.bootstrap.assembly.metrics_service import (
    create_metrics_service,
)
from bioetl.domain.ports import MetricsPort
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.observability import PrometheusMetrics

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings

MetricsFactory = Callable[[], MetricsPort]
MetricsServiceFactory = Callable[..., MetricsService]

__all__ = [
    "bootstrap_metrics_port",
    "maybe_start_metrics_server",
]


def bootstrap_metrics_port(
    settings: Settings,
    metrics_factory: MetricsFactory | None = None,
) -> MetricsPort:
    """Create a metrics port implementation.

    Args:
        settings: Application settings used to check whether metrics are enabled.
        metrics_factory: Optional factory callable for DI/testing; uses PrometheusMetrics
            when None and metrics are enabled.

    Returns:
        Configured MetricsPort, or NoOpMetrics if metrics are disabled.
    """
    if not settings.observability.metrics_enabled:
        return NoOpMetrics(warn_on_use=False)

    factory = metrics_factory or PrometheusMetrics
    return factory()


def maybe_start_metrics_server(
    settings: Settings,
    metrics_service_factory: MetricsServiceFactory | None = None,
) -> bool:
    """Start metrics server if enabled in settings.

    Args:
        settings: Application settings providing metrics port, address, and flags.
        metrics_service_factory: Optional composition-owned service bootstrapper;
            uses the default shared ``create_metrics_service`` when None.

    Returns:
        True if the metrics server was started, False otherwise.
    """
    if not settings.observability.metrics_enabled:
        return False

    if not settings.observability.metrics_server_enabled:
        return False

    obs = settings.observability
    service_factory = metrics_service_factory or create_metrics_service
    service = service_factory()
    result = service.start(
        port=settings.metrics_port,
        addr=settings.metrics_addr,
        fail_fast=obs.metrics_fail_fast,
        retry_count=obs.metrics_retry_count,
        retry_delay=obs.metrics_retry_delay,
    )
    return bool(result.success)

================================================================================
File: observability.py
Path: bootstrap\runtime\observability.py
================================================================================
"""Bootstrap functions for runtime observability components."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING
from uuid import UUID

from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.exceptions import MetricsServerError
from bioetl.domain.ports import (
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.infrastructure.observability import (
    OpenTelemetryTracer,
    PrometheusMetrics,
    UnifiedLogger,
)
from bioetl.infrastructure.observability.anomaly import DataQualityMonitorService
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

from .dq_bootstrap import bootstrap_dq_monitor_port as _bootstrap_dq_monitor_port_impl
from .logger_bootstrap import bootstrap_logger_port as _bootstrap_logger_port_impl
from .metrics_bootstrap import bootstrap_metrics_port as _bootstrap_metrics_port_impl
from .metrics_bootstrap import (
    maybe_start_metrics_server as _maybe_start_metrics_server_impl,
)
from .observability_bundle import (
    bootstrap_observability_bundle_impl as _bootstrap_observability_bundle_impl,
)
from .observability_bundle import (
    validate_observability_preflight_impl as _validate_observability_preflight_impl,
)
from .tracing_bootstrap import bootstrap_tracer_port as _bootstrap_tracer_port_impl

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings

__all__ = [
    "MetricsServerError",
    "bootstrap_dq_monitor_port",
    "bootstrap_logger_port",
    "bootstrap_metrics_port",
    "bootstrap_observability_bundle",
    "bootstrap_tracer_port",
    "maybe_start_metrics_server",
    "validate_observability_preflight",
]


def validate_observability_preflight(
    tracer: TracingPort,
    metrics: MetricsPort,
    environment: str,
    logger: LoggerPort,
    allow_noop_in_prod: bool = False,
) -> None:
    """Validate observability components for production readiness.

    Args:
        tracer: TracingPort to validate; checked for NoOp in production.
        metrics: MetricsPort to validate; checked for NoOp in production.
        environment: Deployment environment name (e.g., 'prod', 'staging').
        logger: LoggerPort used to emit preflight validation warnings.
    """
    _validate_observability_preflight_impl(
        tracer=tracer,
        metrics=metrics,
        environment=environment,
        logger=logger,
        allow_noop_in_prod=allow_noop_in_prod,
    )


def bootstrap_logger_port(
    pipeline: str,
    run_id: UUID | None = None,
    log_level: str = "INFO",
) -> LoggerPort:
    """Create a logger port implementation for pipeline execution.

    Args:
        pipeline: Pipeline name used as a structured log field.
        run_id: Run UUID for log correlation; a new UUID is generated if None.
        log_level: Minimum log level string (e.g., 'INFO', 'DEBUG').

    Returns:
        Configured LoggerPort for structured pipeline logging.
    """

    def _logger_factory(
        logger_pipeline: str,
        logger_run_id: UUID,
        logger_level: str,
    ) -> LoggerPort:
        return UnifiedLogger(
            pipeline=logger_pipeline,
            run_id=logger_run_id,
            log_level=logger_level,
            json_format=True,
        )

    return _bootstrap_logger_port_impl(
        pipeline=pipeline,
        run_id=run_id,
        log_level=log_level,
        logger_factory=_logger_factory,
    )


def bootstrap_tracer_port(
    settings: Settings,
    service_name: str = "bioetl",
) -> TracingPort:
    """Create a tracing port implementation for distributed tracing.

    Args:
        settings: Application settings used to check whether tracing is enabled.
        service_name: OpenTelemetry service name for span identification.
            Defaults to 'bioetl'.

    Returns:
        Configured TracingPort for distributed tracing.
    """
    return _bootstrap_tracer_port_impl(
        settings=settings,
        service_name=service_name,
        tracer_factory=lambda trace_service_name: OpenTelemetryTracer(
            service_name=trace_service_name
        ),
    )


def bootstrap_metrics_port(settings: Settings) -> MetricsPort:
    """Create a metrics port implementation.

    Args:
        settings: Application settings used to determine if metrics are enabled.

    Returns:
        Configured MetricsPort for pipeline metrics collection.
    """
    return _bootstrap_metrics_port_impl(
        settings=settings,
        metrics_factory=PrometheusMetrics,
    )


def maybe_start_metrics_server(settings: Settings) -> bool:
    """Start metrics server if enabled in settings.

    Args:
        settings: Application settings providing metrics port, address, and feature flags.

    Returns:
        True if the metrics server was started, False otherwise.
    """
    return _maybe_start_metrics_server_impl(
        settings=settings,
    )


def start_metrics_server(
    port: int = 8000,
    addr: str = "0.0.0.0",
    *,
    fail_fast: bool = False,
    retry_count: int = 3,
    retry_delay: float = 1.0,
    logger: LoggerPort | None = None,
) -> bool:
    """Compatibility patch-point delegating to the composition observability seam."""
    observability_api = import_module("bioetl.composition.observability_api")
    return observability_api.start_metrics_server(
        port=port,
        addr=addr,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
        logger=logger,
    )


def bootstrap_dq_monitor_port(
    settings: Settings,
    logger: LoggerPort | None = None,
) -> DQMonitorPort | None:
    """Create a data quality monitor port implementation.

    Args:
        settings: Application settings used to check whether DQ monitoring is enabled.
        logger: Optional LoggerPort for structured DQ monitor logging; uses NoOpLogger
            if None.

    Returns:
        DQMonitorPort if DQ monitoring is enabled, None otherwise.
    """
    return _bootstrap_dq_monitor_port_impl(
        settings=settings,
        logger=logger,
        monitor_factory=DataQualityMonitorService,
        noop_logger_factory=NoOpLogger,
    )


def bootstrap_observability_bundle(
    pipeline: str,
    run_id: UUID,
    settings: Settings,
    log_level: str = "INFO",
) -> ObservabilityBundle:
    """Build validated logger/metrics/tracer/DQ-monitor bundle for a pipeline run.

    Args:
        pipeline: Pipeline name used for logger and tracer context.
        run_id: Run UUID used for log correlation across all observability components.
        settings: Application settings driving feature flags for each component.
        log_level: Minimum log level string (e.g., 'INFO', 'DEBUG').

    Returns:
        Validated ObservabilityBundle with logger, metrics, tracer, and DQ monitor.
    """
    return _bootstrap_observability_bundle_impl(
        pipeline=pipeline,
        run_id=run_id,
        settings=settings,
        log_level=log_level,
        logger_bootstrapper=bootstrap_logger_port,
        tracer_bootstrapper=bootstrap_tracer_port,
        metrics_bootstrapper=bootstrap_metrics_port,
        dq_monitor_bootstrapper=bootstrap_dq_monitor_port,
        preflight_validator=validate_observability_preflight,
    )

================================================================================
File: observability_bundle.py
Path: bootstrap\runtime\observability_bundle.py
================================================================================
"""Internal helpers for runtime observability bundle bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.observability import (
    ObservabilityBundle,
    ObservabilityContractError,
)
from bioetl.domain.ports import (
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.ports.noop import (
    NoOpMetrics,
    NoOpTracing,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from bioetl.domain.ports import DQMonitorPort
    from bioetl.infrastructure.config import Settings

__all__ = [
    "bootstrap_observability_bundle_impl",
    "validate_observability_preflight_impl",
]


def validate_observability_preflight_impl(
    tracer: TracingPort,
    metrics: MetricsPort,
    environment: str,
    logger: LoggerPort,
    allow_noop_in_prod: bool = False,
) -> None:
    """Validate observability components for production readiness.

    Emits structured warnings when NoOp implementations are used in production.
    By default, production fails closed unless explicit override is enabled.

    Args:
        tracer: TracingPort to validate; warns if NoOpTracing in production.
        metrics: MetricsPort to validate; warns if NoOpMetrics in production.
        environment: Deployment environment name (e.g., 'prod', 'staging').
        logger: LoggerPort used to emit structured preflight warning events.
    """
    if environment != "prod":
        return

    if isinstance(tracer, NoOpTracing):
        logger.warning(
            "noop_tracing_in_production",
            message="NoOpTracing in production - traces will be lost",
            recommendation="Set BIOETL_OBSERVABILITY__TRACING_ENABLED=true "
            "and configure OpenTelemetry endpoint",
        )
        if not allow_noop_in_prod:
            raise ObservabilityContractError(
                "NoOpTracing is not allowed in prod. "
                "Enable tracing or set "
                "BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD=true "
                "for an explicit override."
            )

    if isinstance(metrics, NoOpMetrics):
        logger.warning(
            "noop_metrics_in_production",
            message="NoOpMetrics in production - metrics will be lost",
            recommendation="Set BIOETL_OBSERVABILITY__METRICS_ENABLED=true "
            "to enable Prometheus metrics collection",
        )
        if not allow_noop_in_prod:
            raise ObservabilityContractError(
                "NoOpMetrics is not allowed in prod. "
                "Enable metrics or set "
                "BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD=true "
                "for an explicit override."
            )


def bootstrap_observability_bundle_impl(
    *,
    pipeline: str,
    run_id: UUID,
    settings: Settings,
    log_level: str,
    logger_bootstrapper: Callable[[str, UUID, str], LoggerPort],
    tracer_bootstrapper: Callable[[Settings], TracingPort],
    metrics_bootstrapper: Callable[[Settings], MetricsPort],
    dq_monitor_bootstrapper: Callable[
        [Settings, LoggerPort | None], DQMonitorPort | None
    ],
    preflight_validator: Callable[
        [TracingPort, MetricsPort, str, LoggerPort, bool], None
    ],
) -> ObservabilityBundle:
    """Build validated logger/metrics/tracer/DQ-monitor bundle for a pipeline run.

    Creates each observability component via the provided bootstrapper callables,
    logs initialization details, and runs preflight validation.

    Args:
        pipeline: Pipeline name passed to the logger bootstrapper for context.
        run_id: Run UUID used for log correlation across all components.
        settings: Application settings forwarded to tracer, metrics, and DQ bootstrappers.
        log_level: Minimum log level string forwarded to the logger bootstrapper.
        logger_bootstrapper: Callable that creates a LoggerPort from pipeline, run_id,
            and log_level.
        tracer_bootstrapper: Callable that creates a TracingPort from settings.
        metrics_bootstrapper: Callable that creates a MetricsPort from settings.
        dq_monitor_bootstrapper: Callable that creates an optional DQMonitorPort
            from settings and logger.
        preflight_validator: Callable that validates the assembled components and
            emits warnings for production misconfigurations.

    Returns:
        Validated ObservabilityBundle with logger, metrics, tracer, and DQ monitor.
    """
    logger = logger_bootstrapper(pipeline, run_id, log_level)
    tracer = tracer_bootstrapper(settings)
    metrics = metrics_bootstrapper(settings)
    dq_monitor = dq_monitor_bootstrapper(settings, logger)

    bundle = ObservabilityBundle(
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        dq_monitor=dq_monitor,
    )

    _log_observability_initialized(
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        dq_monitor=dq_monitor,
    )

    preflight_validator(
        tracer,
        metrics,
        settings.env,
        logger,
        settings.observability.allow_noop_observability_in_prod,
    )

    return bundle


def _log_observability_initialized(
    *,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracer: TracingPort,
    dq_monitor: DQMonitorPort | None,
) -> None:
    """Emit structured bootstrap observability event.

    Args:
        logger: LoggerPort used to emit the initialization event.
        metrics: MetricsPort whose type name is included in the event.
        tracer: TracingPort whose type name is included in the event.
        dq_monitor: Optional DQ monitor; presence is recorded in the event.
    """
    logger.info(
        "observability_initialized",
        stage="bootstrap",
        metrics_type=type(metrics).__name__,
        tracer_type=type(tracer).__name__,
        dq_monitor_enabled=dq_monitor is not None,
    )

================================================================================
File: pipeline.py
Path: bootstrap\runtime\pipeline.py
================================================================================
"""Bootstrap function for main pipeline execution.

Contains the primary Composition Root entry point for creating
a fully configured PipelineRunner ready for execution.

This is the main entry point for runtime pipeline execution.
CLI commands should use this via composition/entrypoints.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition import PipelineRegistry, create_registry
from bioetl.composition.bootstrap.runtime.assembly import assemble_filter_config
from bioetl.composition.bootstrap.runtime.classification_init import (
    initialize_publication_type_classification,
)
from bioetl.composition.bootstrap.runtime.observability import (
    bootstrap_observability_bundle,
)
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.runtime_builders.config_access import (
    get_settings,
    load_pipeline_config,
)
from bioetl.composition.runtime_builders.runner_builder import build_pipeline_runner

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.domain.context import PipelineRunContext

__all__ = [
    "bootstrap_pipeline_runner",
]


def bootstrap_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
) -> PipelineRunner:
    """Build a ready-to-run pipeline runner from runtime context and registry.

    Initializes publication type classification data, registers all providers
    and pipelines, then delegates to the runtime builder to wire all
    infrastructure dependencies.

    Args:
        ctx: Pipeline run context containing launch parameters such as pipeline
            name, run type, limit, filter settings, and observability options.
        registry: Optional PipelineRegistry to use instead of a fresh runtime
            registry; useful for test isolation.

    Returns:
        Fully configured PipelineRunner ready for execution.
    """
    # Classification data must be available before transformers run.
    initialize_publication_type_classification(Path("configs"))
    effective_registry = registry if registry is not None else create_registry()

    # Keep runtime bootstrap behind the registry facade while preserving
    # deterministic explicit registration in this composition root.
    ensure_providers_loaded()
    if not effective_registry.list_pipelines():
        register_all_pipelines(registry=effective_registry)

    return build_pipeline_runner(
        ctx=ctx,
        registry=effective_registry,
        ensure_providers_loaded_fn=lambda: None,
        register_all_pipelines_fn=lambda registry=None: None,
        get_settings_fn=get_settings,
        load_pipeline_config_fn=load_pipeline_config,
        build_observability_bundle_fn=bootstrap_observability_bundle,
        assemble_filter_config_fn=assemble_filter_config,
    )

================================================================================
File: pipeline_runner_service_bootstrap.py
Path: bootstrap\runtime\pipeline_runner_service_bootstrap.py
================================================================================
"""Canonical bootstrap entrypoint for PipelineRunnerService."""

from __future__ import annotations

from bioetl.composition.bootstrap.runtime.runner import (
    bootstrap_pipeline_runner_service,
)

__all__ = ["bootstrap_pipeline_runner_service"]

================================================================================
File: runner.py
Path: bootstrap\runtime\runner.py
================================================================================
"""Bootstrap functions for pipeline runner service.

Provides bootstrap functions for PipelineRunnerService assembly.
This service provides a unified interface for running pipelines
from any orchestration layer (CLI, REST API, etc.).
"""

from __future__ import annotations

from uuid import uuid4

from bioetl.application.services import PipelineRunnerService
from bioetl.application.services.execution.pipeline_run_context_service import (
    PipelineRunContextService,
)
from bioetl.application.services.execution.pipeline_run_execution_service import (
    PipelineRunExecutionService,
)
from bioetl.composition import PipelineRegistry
from bioetl.composition.bootstrap.runtime.observability import bootstrap_logger_port
from bioetl.composition.factories.pipeline.runner import (
    create_metrics_extractor,
    create_runner_factory,
)
from bioetl.infrastructure.time import SystemClock

__all__ = ["bootstrap_pipeline_runner_service"]


def bootstrap_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Bootstrap the PipelineRunnerService with all dependencies.

    Creates a fully configured PipelineRunnerService that can be used
    to run pipelines from any interface (CLI, REST API, etc.).

    Args:
        registry: Optional custom registry for test isolation.
            If None, creates a fresh runtime registry through the composition seam.

    Returns:
        PipelineRunnerService ready for use.

    Example:
        >>> service = bootstrap_pipeline_runner_service()
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> result = await service.run("chembl_activity", options=options)
    """
    # Bootstrap logger for the service (using a unique ID for service-level logging)
    logger = bootstrap_logger_port(
        pipeline="pipeline_runner_service",
        run_id=uuid4(),
        log_level="INFO",
    )

    # Create factory and extractor
    runner_factory = create_runner_factory(registry=registry)
    metrics_extractor = create_metrics_extractor()

    return PipelineRunnerService(
        runner_factory=runner_factory,
        metrics_extractor=metrics_extractor,
        logger=logger,
        clock=SystemClock(),
        _context_service=PipelineRunContextService(),
        _execution_service=PipelineRunExecutionService(),
    )

================================================================================
File: runner_assembly.py
Path: bootstrap\runtime\runner_assembly.py
================================================================================
"""Composite runner assembly facade."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.composite.runner_pkg import CompositePipelineRunner
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.application.composite.runtime_wiring_api import (
    CompositeCheckpointService,
    CompositeLifecycleObserverService,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    CompositeRunnerFactory,
    CompositeRunnerServiceInputs,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    build_composite_runner_service_inputs as _build_composite_runner_service_inputs_impl,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    create_composite_runner_service_from_inputs as _create_composite_runner_service_from_inputs_impl,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    invoke_composite_runner_factory as _invoke_composite_runner_factory_impl,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    resolve_effective_run_id as _resolve_effective_run_id_impl,
)
from bioetl.composition.bootstrap.runtime.runner_bootstrap_wiring import (
    bootstrap_composite_runner_via_wiring,
)
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.ports import LoggerPort

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_wiring_api import (
        CompositePreflightValidationService,
        DependencyCoordinatorService,
        EnrichmentCoordinatorService,
        FSMStateHelperService,
        PipelineRunner,
    )
    from bioetl.application.composite.runtime_wiring_api import (
        KeyExtractorService as _KeyExtractorService,
    )
    from bioetl.application.composite.runtime_wiring_api import (
        MergeService as _MergeService,
    )
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.ports import LockPort, MetricsPort, QuarantinePort, TracingPort
    from bioetl.infrastructure.config import Settings


__all__ = [
    "bootstrap_composite_runner",
    "create_composite_runner",
    "create_composite_runner_service",
]


def create_composite_runner_service(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    seed_runner_factory: Callable[[], PipelineRunner],
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    key_extractor: _KeyExtractorService,
    coordinator: EnrichmentCoordinatorService,
    merger: _MergeService,
    checkpoint_manager: CompositeCheckpointService,
    logger: LoggerPort,
    lock: LockPort,
    fsm_state_helper: FSMStateHelperService,
    run_id: str | None = None,
    dq_report_service: DQReportService | None = None,
    preflight_validator: CompositePreflightValidationService | None = None,
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    | None = None,
    dependency_coordinator: DependencyCoordinatorService | None = None,
    quarantine_port: QuarantinePort | None = None,
    metrics: MetricsPort | None = None,
    tracer: TracingPort | None = None,
    observer: CompositeLifecycleObserverService | None = None,
    manifest_id: str | None = None,
    run_ledger_service: RunLedgerService | None = None,
) -> CompositePipelineRunner:
    """Create a composite runner service from fully resolved dependencies."""
    if fsm_state_helper is None:
        raise AssertionError("Composite runner requires fsm_state_helper")
    inputs = CompositeRunnerServiceInputs(
        config=config,
        runtime=runtime,
        run_id=_resolve_effective_run_id_impl(run_id),
        logger=logger,
        lock=lock,
        seed_runner_factory=seed_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        key_extractor=key_extractor,
        coordinator=coordinator,
        merger=merger,
        checkpoint_manager=checkpoint_manager,
        fsm_state_helper=fsm_state_helper,
        dq_report_service=dq_report_service,
        preflight_validator=preflight_validator,
        dependencies_runner_factory=dependencies_runner_factory,
        dependency_coordinator=dependency_coordinator,
        quarantine_port=quarantine_port,
        metrics=metrics,
        tracer=tracer,
        observer=observer
        or CompositeLifecycleObserverService(
            logger=logger,
            metrics=metrics,
            tracer=tracer,
        ),
        manifest_id=manifest_id,
        run_ledger_service=run_ledger_service,
    )
    return _create_composite_runner_service_from_inputs_impl(inputs)


def create_composite_runner(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    tracer: TracingPort | None,
    lock: LockPort,
    seed_runner_factory: Callable[[], PipelineRunner],
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    support_services: CompositeSupportServices,
    runner_factory: CompositeRunnerFactory = create_composite_runner_service,
) -> CompositePipelineRunner:
    """Create a fully wired ``CompositePipelineRunner``."""
    service_inputs = _build_composite_runner_service_inputs_impl(
        config=config,
        runtime=runtime,
        run_id=run_id,
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        lock=lock,
        seed_runner_factory=seed_runner_factory,
        dependencies_runner_factory=dependencies_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        support_services=support_services,
    )
    return _invoke_composite_runner_factory_impl(
        runner_factory=runner_factory,
        inputs=service_inputs,
    )


def bootstrap_composite_runner(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None,
    bootstrap_runtime_basics_fn: Callable[
        ...,
        tuple[str, Settings, LoggerPort, MetricsPort, TracingPort, object, LockPort],
    ],
    build_runner_factories_fn: Callable[
        ...,
        tuple[
            Callable[[], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
        ],
    ],
    build_support_services_fn: Callable[..., CompositeSupportServices],
    create_composite_runner_fn: Callable[..., CompositePipelineRunner],
) -> CompositePipelineRunner:
    """Assemble and create a composite runner via injected dependency builders."""
    return bootstrap_composite_runner_via_wiring(
        config=config,
        runtime=runtime,
        run_id=run_id,
        bootstrap_runtime_basics_fn=bootstrap_runtime_basics_fn,
        build_runner_factories_fn=build_runner_factories_fn,
        build_support_services_fn=build_support_services_fn,
        create_composite_runner_fn=create_composite_runner_fn,
    )

================================================================================
File: runner_bootstrap_wiring.py
Path: bootstrap\runtime\runner_bootstrap_wiring.py
================================================================================
"""Internal wiring helpers for composite runner bootstrap assembly."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.composite.runner_pkg import CompositePipelineRunner
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.ports import LockPort
    from bioetl.infrastructure.config import Settings


@dataclass(frozen=True, slots=True)
class _BootstrapRuntimeBasics:
    """Resolved runtime-basics bundle used by bootstrap assembly."""

    run_id: str
    settings: Settings
    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracingPort
    storage: object
    lock: LockPort


@dataclass(frozen=True, slots=True)
class _BootstrapRunnerFactories:
    """Resolved phase runner factories used by composite bootstrap."""

    seed_factory: Callable[[], PipelineRunner]
    dependency_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    enricher_factory: Callable[[str, pl.DataFrame], PipelineRunner]


def _build_bootstrap_support_services(
    *,
    build_support_services_fn: Callable[..., CompositeSupportServices],
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    settings: Settings,
    logger: LoggerPort,
    storage: object,
    run_id: str,
) -> CompositeSupportServices:
    """Build support services from the runtime basics payload."""
    return build_support_services_fn(
        config=config,
        runtime=runtime,
        settings=settings,
        logger=logger,
        storage=storage,
        run_id=run_id,
    )


def _resolve_bootstrap_runtime_basics(
    *,
    bootstrap_runtime_basics_fn: Callable[
        ...,
        tuple[str, Settings, LoggerPort, MetricsPort, TracingPort, object, LockPort],
    ],
    config: CompositeConfig,
    run_id: str | None,
) -> _BootstrapRuntimeBasics:
    """Resolve the named runtime-basics bundle for bootstrap assembly."""
    effective_run_id, settings, logger, metrics, tracer, storage, lock = (
        bootstrap_runtime_basics_fn(
            config=config,
            run_id=run_id,
        )
    )
    return _BootstrapRuntimeBasics(
        run_id=effective_run_id,
        settings=settings,
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        storage=storage,
        lock=lock,
    )


def _resolve_bootstrap_runner_factories(
    *,
    build_runner_factories_fn: Callable[
        ...,
        tuple[
            Callable[[], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
        ],
    ],
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    logger: LoggerPort,
) -> _BootstrapRunnerFactories:
    """Resolve the named phase-factory bundle for composite bootstrap."""
    seed_factory, dependency_factory, enricher_factory = build_runner_factories_fn(
        config=config,
        runtime=runtime,
        logger=logger,
    )
    return _BootstrapRunnerFactories(
        seed_factory=seed_factory,
        dependency_factory=dependency_factory,
        enricher_factory=enricher_factory,
    )


def _create_bootstrapped_composite_runner(
    *,
    create_composite_runner_fn: Callable[..., CompositePipelineRunner],
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracer: TracingPort,
    lock: LockPort,
    seed_runner_factory: Callable[[], PipelineRunner],
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    support_services: CompositeSupportServices,
) -> CompositePipelineRunner:
    """Create the final runner from already-assembled bootstrap components."""
    return create_composite_runner_fn(
        config=config,
        runtime=runtime,
        run_id=run_id,
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        lock=lock,
        seed_runner_factory=seed_runner_factory,
        dependencies_runner_factory=dependencies_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        support_services=support_services,
    )


def bootstrap_composite_runner_via_wiring(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None,
    bootstrap_runtime_basics_fn: Callable[
        ...,
        tuple[str, Settings, LoggerPort, MetricsPort, TracingPort, object, LockPort],
    ],
    build_runner_factories_fn: Callable[
        ...,
        tuple[
            Callable[[], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
        ],
    ],
    build_support_services_fn: Callable[..., CompositeSupportServices],
    create_composite_runner_fn: Callable[..., CompositePipelineRunner],
) -> CompositePipelineRunner:
    """Assemble and create composite runner with injected dependency builders."""
    runtime_basics = _resolve_bootstrap_runtime_basics(
        bootstrap_runtime_basics_fn=bootstrap_runtime_basics_fn,
        config=config,
        run_id=run_id,
    )
    runner_factories = _resolve_bootstrap_runner_factories(
        build_runner_factories_fn=build_runner_factories_fn,
        config=config,
        runtime=runtime,
        logger=runtime_basics.logger,
    )
    support_services = _build_bootstrap_support_services(
        build_support_services_fn=build_support_services_fn,
        config=config,
        runtime=runtime,
        settings=runtime_basics.settings,
        logger=runtime_basics.logger,
        storage=runtime_basics.storage,
        run_id=runtime_basics.run_id,
    )
    return _create_bootstrapped_composite_runner(
        create_composite_runner_fn=create_composite_runner_fn,
        config=config,
        runtime=runtime,
        run_id=runtime_basics.run_id,
        logger=runtime_basics.logger,
        metrics=runtime_basics.metrics,
        tracer=runtime_basics.tracer,
        lock=runtime_basics.lock,
        seed_runner_factory=runner_factories.seed_factory,
        dependencies_runner_factory=runner_factories.dependency_factory,
        enricher_runner_factory=runner_factories.enricher_factory,
        support_services=support_services,
    )

================================================================================
File: runner_factory_builder_service.py
Path: bootstrap\runtime\runner_factory_builder_service.py
================================================================================
"""Builder service for composite runner factories."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, TypedDict, TypeVar

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.domain.composite.config import DependencyConfig, EnricherConfig
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import LoggerPort

from bioetl.composition.bootstrap.runtime._dependency_runner_support import (
    build_dependency_debug_context,
    resolve_dependency_runner_limit,
)
from bioetl.composition.bootstrap.runtime.composite_filter_extraction_service import (
    CompositeFilterExtractionService,
)


class BronzeRunOptions(TypedDict):
    """Cached bronze options passed to RunOptions constructor."""

    use_cached_bronze: bool
    cached_bronze_path: str | None
    cached_bronze_date: str | None


_RunOptionsT = TypeVar("_RunOptionsT")


def resolve_bronze_opts(
    runtime: CompositeRuntimeConfig,
    phase_override: bool | None,
) -> BronzeRunOptions:
    """Resolve per-phase cached bronze options using tri-state override.

    Returns:
        BronzeRunOptions with resolved cached bronze settings for the phase.
    """
    effective = (
        phase_override if phase_override is not None else runtime.use_cached_bronze
    )
    return BronzeRunOptions(
        use_cached_bronze=effective,
        cached_bronze_path=runtime.cached_bronze_path if effective else None,
        cached_bronze_date=runtime.cached_bronze_date if effective else None,
    )


class RunnerFactoryBuilderService(Generic[_RunOptionsT]):
    """Build seed/enricher/dependency runner factories."""

    def __init__(
        self,
        *,
        logger: LoggerPort,
        run_options_cls: Callable[..., _RunOptionsT],
        build_context: Callable[[str, _RunOptionsT], PipelineRunContext],
        pipeline_runner_builder: Callable[[PipelineRunContext], PipelineRunner],
        filter_extraction_service: CompositeFilterExtractionService,
    ) -> None:
        self._logger = logger
        self._run_options_cls = run_options_cls
        self._build_context = build_context
        self._pipeline_runner_builder = pipeline_runner_builder
        self._filter_extraction_service = filter_extraction_service

    def _create_runner(
        self,
        *,
        pipeline_name: str,
        **option_kwargs: object,
    ) -> PipelineRunner:
        """Build a runner from one resolved RunOptions payload."""
        options = self._run_options_cls(**option_kwargs)
        ctx = self._build_context(pipeline_name, options)
        return self._pipeline_runner_builder(ctx)

    def build_seed_factory(
        self,
        *,
        seed_pipeline: str,
        seed_limit: int | None,
        bronze_opts: BronzeRunOptions,
    ) -> Callable[[], PipelineRunner]:
        """Build seed phase runner factory.

        Returns:
            Callable that creates a configured PipelineRunner for the seed phase.
        """

        def seed_runner_factory() -> PipelineRunner:
            """Create a PipelineRunner configured for the seed phase."""
            return self._create_runner(
                pipeline_name=seed_pipeline,
                run_type="incremental",
                limit=seed_limit,
                skip_gold=True,
                **bronze_opts,
            )

        return seed_runner_factory

    def build_enricher_factory(
        self,
        *,
        enrichers: list[EnricherConfig],
        bronze_opts: BronzeRunOptions,
    ) -> Callable[[str, pl.DataFrame], PipelineRunner]:
        """Build enricher phase runner factory.

        Returns:
            Callable that creates a configured PipelineRunner for a named enricher.
        """
        enricher_configs = {enricher.pipeline: enricher for enricher in enrichers}

        def enricher_runner_factory(
            pipeline_name: str,
            keys: pl.DataFrame,
        ) -> PipelineRunner:
            """Create a PipelineRunner configured for the given enricher."""
            enricher_cfg = enricher_configs.get(pipeline_name)
            filter_ids: tuple[str, ...] | None = None
            filter_field: str | None = None
            fallback_mapping: dict[str, str] | None = None

            if enricher_cfg is not None:
                filter_ids, filter_field, fallback_mapping = (
                    self._filter_extraction_service.extract_enricher_filters(
                        enricher_cfg=enricher_cfg,
                        keys=keys,
                    )
                )

            self._logger.debug(
                "Creating enricher runner",
                pipeline=pipeline_name,
                keys_columns=list(keys.columns) if keys is not None else [],
                keys_count=len(keys) if keys is not None else 0,
                join_keys=list(enricher_cfg.join_keys) if enricher_cfg else [],
                filter_field=filter_field,
                filter_ids_count=len(filter_ids) if filter_ids else 0,
                filter_ids_sample=list(filter_ids)[:5] if filter_ids else [],
            )

            limit: int | None = None
            if enricher_cfg and not enricher_cfg.is_many_to_one and keys is not None:
                limit = len(keys)

            return self._create_runner(
                pipeline_name=pipeline_name,
                run_type="incremental",
                limit=limit,
                ignore_yaml_filter=True,
                skip_gold=True,
                filter_ids=filter_ids,
                filter_field=filter_field,
                fallback_mapping=fallback_mapping,
                execution_context="enricher",
                **bronze_opts,
            )

        return enricher_runner_factory

    def build_dependency_factory(
        self,
        *,
        dependencies: list[DependencyConfig],
        bronze_opts: BronzeRunOptions,
    ) -> Callable[[str, pl.DataFrame], PipelineRunner]:
        """Build dependency phase runner factory.

        Returns:
            Callable that creates a configured PipelineRunner for a named dependency.
        """
        dependency_configs = {
            dependency.pipeline: dependency for dependency in dependencies
        }

        def dependency_runner_factory(
            pipeline_name: str,
            keys: pl.DataFrame,
        ) -> PipelineRunner:
            """Create a PipelineRunner configured for the given dependency."""
            dep_cfg = dependency_configs.get(pipeline_name)
            filter_ids, filter_field, multi_filter_ids = (
                self._filter_extraction_service.resolve_dependency_filter_inputs(
                    dep_cfg=dep_cfg,
                    keys=keys,
                )
            )
            debug_context = build_dependency_debug_context(
                pipeline_name=pipeline_name,
                keys=keys,
                dep_cfg=dep_cfg,
                filter_field=filter_field,
                filter_ids=filter_ids,
                multi_filter_ids=multi_filter_ids,
            )
            limit = resolve_dependency_runner_limit(
                keys=keys,
                filter_ids=filter_ids,
                multi_filter_ids=multi_filter_ids,
            )

            self._logger.debug("Creating dependency runner", **debug_context)

            return self._create_runner(
                pipeline_name=pipeline_name,
                run_type="incremental",
                limit=limit,
                filter_ids=filter_ids,
                filter_field=filter_field,
                multi_filter_ids=multi_filter_ids,
                ignore_yaml_filter=True,
                skip_gold=True,
                execution_context="dependency",
                **bronze_opts,
            )

        return dependency_runner_factory


__all__ = ["BronzeRunOptions", "RunnerFactoryBuilderService", "resolve_bronze_opts"]

================================================================================
File: runtime_basics.py
Path: bootstrap\runtime\runtime_basics.py
================================================================================
"""Runtime dependency assembly helpers for composite bootstrap."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

from bioetl.application.composite.runtime_wiring_api import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    CompositeCheckpointService,
    validate_join_key_normalization_policies,
)
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.factories.services.port_factories import create_metrics

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.composition.bootstrap.runtime.composite_filter_extraction_service import (
        CompositeFilterExtractionService,
    )
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
        CompositeSupportServicesFactory,
    )
    from bioetl.composition.bootstrap.runtime.runner_factory_builder_service import (
        BronzeRunOptions,
        RunnerFactoryBuilderService,
    )
    from bioetl.composition.execution_api import RunOptions
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import LockPort, LoggerPort, MetricsPort, TracingPort
    from bioetl.infrastructure.config import Settings

__all__ = [
    "bootstrap_runtime_basics",
    "build_runner_factories",
    "build_support_services",
]


def bootstrap_runtime_basics(
    *,
    config: CompositeConfig,
    run_id: str | None,
    settings_provider: Callable[[], Settings],
    logger_bootstrapper: Callable[[str, UUID, str], LoggerPort],
    tracer_bootstrapper: Callable[[Settings], TracingPort],
    storage_bootstrapper: Callable[..., object],
    lock_factory: Callable[[], LockPort],
    uuid_factory: Callable[[], UUID],
) -> tuple[str, Settings, LoggerPort, MetricsPort, TracingPort, object, LockPort]:
    """Build base runtime dependencies shared across composite bootstrap.

    Args:
        config: CompositeConfig used to derive the pipeline name for logging.
        run_id: Optional UUID string; a new UUID is generated from uuid_factory
            when None.
        settings_provider: Zero-argument callable that returns global Settings.
        logger_bootstrapper: Callable accepting (pipeline_name, run_uuid, log_level)
            and returning a LoggerPort.
        storage_bootstrapper: Callable returning a storage adapter; called with
            ``enable_csv_export=True`` for composite pipelines.
        lock_factory: Zero-argument callable returning a LockPort.
        uuid_factory: Zero-argument callable returning a new UUID; injectable
            for deterministic testing.

    Returns:
        Tuple of (run_id, settings, logger, metrics, tracer, storage, lock) for the composite run.
    """
    effective_run_id = run_id or str(uuid_factory())
    settings = settings_provider()
    logger = logger_bootstrapper(config.name, UUID(effective_run_id), "INFO")

    # Initialize domain layer enum fields with proper dependency injection
    from bioetl.composition.bootstrap.runtime.enum_loader_wiring import (
        initialize_domain_enum_fields,
    )

    initialize_domain_enum_fields()

    metrics = create_metrics(settings)
    tracer = tracer_bootstrapper(settings)
    storage = storage_bootstrapper(enable_csv_export=True)
    lock = lock_factory()
    return effective_run_id, settings, logger, metrics, tracer, storage, lock


def build_runner_factories(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    logger: LoggerPort,
    runner_factory_builder_cls: type[RunnerFactoryBuilderService[RunOptions]],
    filter_extraction_service_cls: type[CompositeFilterExtractionService],
    pipeline_runner_builder: Callable[[PipelineRunContext], PipelineRunner],
    resolve_bronze_opts_fn: Callable[
        [CompositeRuntimeConfig, bool | None], BronzeRunOptions
    ],
) -> tuple[
    Callable[[], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
]:
    """Build seed/dependency/enricher runner factories for composite phases.

    Args:
        config: CompositeConfig describing seed, enrichers, and dependencies.
        runtime: Runtime options used to resolve per-phase Bronze cache settings.
        logger: Structured logger forwarded to the runner factory builder.
        runner_factory_builder_cls: Class implementing per-phase runner factory
            construction.
        filter_extraction_service_cls: Class used to extract filter IDs from
            keys DataFrames during enricher/dependency factory invocations.
        pipeline_runner_builder: Callable that accepts a PipelineRunContext and
            returns a configured PipelineRunner.
        resolve_bronze_opts_fn: Callable returning BronzeRunOptions for a given
            runtime config and optional phase-level override flag.

    Returns:
        Tuple of (seed_factory, dependency_factory, enricher_factory) callables.
    """
    # CIRCULAR-DEPENDENCY: kept local to avoid execution bootstrap cycle.
    from bioetl.composition.execution_api import RunOptions, build_pipeline_context

    validate_join_key_normalization_policies(config)
    filter_extraction_service = filter_extraction_service_cls(
        logger=logger,
        normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
    )
    runner_factory_builder = runner_factory_builder_cls(
        logger=logger,
        run_options_cls=RunOptions,
        build_context=build_pipeline_context,
        pipeline_runner_builder=pipeline_runner_builder,
        filter_extraction_service=filter_extraction_service,
    )
    seed_factory = runner_factory_builder.build_seed_factory(
        seed_pipeline=config.seed.pipeline,
        seed_limit=runtime.seed_limit,
        bronze_opts=resolve_bronze_opts_fn(runtime, None),
    )
    enricher_factory = runner_factory_builder.build_enricher_factory(
        enrichers=list(config.enrichers),
        bronze_opts=resolve_bronze_opts_fn(
            runtime,
            runtime.cached_bronze_enrichers,
        ),
    )
    dependency_factory = runner_factory_builder.build_dependency_factory(
        dependencies=list(config.dependencies),
        bronze_opts=resolve_bronze_opts_fn(
            runtime,
            runtime.cached_bronze_dependencies,
        ),
    )
    return seed_factory, dependency_factory, enricher_factory


def build_support_services(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
    support_services_factory_cls: type[CompositeSupportServicesFactory],
    resolve_gold_schema_fn: Callable[[str], type | None],
    load_field_group_registry_fn: Callable[
        [str, LoggerPort], FieldGroupRegistry | None
    ],
    create_dq_report_service_fn: Callable[
        [LoggerPort, Settings, MetricsPort],
        DQReportService,
    ],
) -> CompositeSupportServices:
    """Build composite support service bundle consumed by runner facade.

    Args:
        config: CompositeConfig for this composite run.
        runtime: Runtime options (resume, concurrency, etc.).
        infra_context: Bundle of infrastructure primitives.
        support_services_factory_cls: Factory class that assembles the bundle.
        resolve_gold_schema_fn: Callable returning the Gold Pandera schema for
            a composite pipeline name, or None if not registered.
        load_field_group_registry_fn: Callable returning the FieldGroupRegistry
            for a composite pipeline name, or None.
        create_dq_report_service_fn: Callable returning a DQReportService
            given a logger and settings.

    Returns:
        CompositeSupportServices bundle with all services required by the runner.
    """
    return support_services_factory_cls(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
        resolve_gold_schema=resolve_gold_schema_fn,
        load_field_group_registry=load_field_group_registry_fn,
        create_dq_report_service=create_dq_report_service_fn,
        checkpoint_manager_cls=CompositeCheckpointService,
    ).build()

================================================================================
File: tracing_bootstrap.py
Path: bootstrap\runtime\tracing_bootstrap.py
================================================================================
"""Tracing bootstrap helpers for runtime observability wiring."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.domain.ports import TracingPort
from bioetl.domain.ports.noop import NoOpTracing
from bioetl.infrastructure.observability import OpenTelemetryTracer

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings

TracerFactory = Callable[[str], TracingPort]

__all__ = [
    "bootstrap_tracer_port",
]


def _default_tracer_factory(service_name: str) -> TracingPort:
    """Create OpenTelemetry tracer for the given service name."""
    return OpenTelemetryTracer(service_name=service_name)


def bootstrap_tracer_port(
    settings: Settings,
    service_name: str = "bioetl",
    tracer_factory: TracerFactory | None = None,
) -> TracingPort:
    """Create a tracing port implementation for distributed tracing.

    Args:
        settings: Application settings used to check whether tracing is enabled.
        service_name: OpenTelemetry service name used for span identification.
            Defaults to 'bioetl'.
        tracer_factory: Optional factory callable for DI/testing; uses
            OpenTelemetryTracer when None and tracing is enabled.

    Returns:
        Configured TracingPort, or NoOpTracing if tracing is disabled.
    """
    observability = getattr(settings, "observability", None)
    tracing_enabled = bool(getattr(observability, "tracing_enabled", False))
    if tracing_enabled:
        factory = tracer_factory or _default_tracer_factory
        return factory(service_name)
    return NoOpTracing()

================================================================================
File: bootstrap_contexts.py
Path: bootstrap_contexts.py
================================================================================
"""Typed contexts for bootstrap functions returning multiple dependencies.

This module provides frozen dataclasses that replace untyped tuples
in bootstrap and factory functions, enabling IDE autocomplete and
type-safe access to returned dependencies.

All contexts are immutable (frozen=True) and contain only data, no logic.

Usage:
    >>> context = PipelineCallbacksContext(
    ...     transform=transform_fn,
    ...     gold_filter=filter_fn,
    ...     gold_transform=gold_transform_fn,
    ... )
    >>> context.transform  # IDE autocomplete works
"""

from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.context import PipelineContext
from bioetl.domain.resilience import CircuitBreakerConfig
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        SilverDQConfigPort,
    )


__all__ = [
    "CircuitBreakerConfig",
    "DQConfigsContext",
    "DQOutputPathsContext",
    "PipelineCallbacksContext",
    "RateLimitContext",
]


class TransformCallback(Protocol):
    """Bronze-to-Silver transformation callback contract for composition wiring."""

    def __call__(
        self,
        context: PipelineContext,
        record: JsonDict,
        index: int,
    ) -> Awaitable[object | None]:
        """Transform one bronze record."""
        ...


class GoldFilterCallback(Protocol):
    """Gold-write predicate callback contract for composition wiring."""

    def __call__(self, context: PipelineContext, record: JsonDict) -> bool:
        """Decide whether one silver record should flow to Gold."""
        ...


class GoldTransformCallback(Protocol):
    """Silver-to-Gold transformation callback contract for composition wiring."""

    def __call__(self, context: PipelineContext, record: JsonDict) -> JsonDict:
        """Transform one silver record for Gold output."""
        ...


@dataclass(frozen=True)
class PipelineCallbacksContext:
    """Typed context for pipeline transformation callbacks.

    Replaces untyped callback tuple from extract_pipeline_callbacks().

    Attributes:
        transform: Bronze to Silver transformation callback.
            Expected signature: (context, record, index) -> Awaitable[dict | None]
            Implements TransformCallback protocol.
        gold_filter: Callback to determine if record should be written to Gold.
            Expected signature: (context, record) -> bool
            Implements GoldFilterCallback protocol.
        gold_transform: Silver to Gold transformation callback.
            Expected signature: (context, silver_record) -> dict
            Implements GoldTransformCallback protocol.
    """

    transform: TransformCallback
    gold_filter: GoldFilterCallback
    gold_transform: GoldTransformCallback


@dataclass(frozen=True)
class DQConfigsContext:
    """Typed context for Data Quality report configurations.

    Replaces untyped tuple[BronzeDQConfigPort | None, SilverDQConfigPort | None,
    GoldDQConfigPort | None] from _extract_dq_configs().

    Attributes:
        bronze: DQ report configuration for Bronze layer (None if disabled).
        silver: DQ report configuration for Silver layer (None if disabled).
        gold: DQ report configuration for Gold layer (None if disabled).
    """

    bronze: BronzeDQConfigPort | None
    silver: SilverDQConfigPort | None
    gold: GoldDQConfigPort | None


@dataclass(frozen=True)
class DQOutputPathsContext:
    """Typed context for DQ report output paths.

    Replaces untyped tuple[str | None, str | None, str | None, bool]
    from _extract_dq_output_paths().

    Attributes:
        bronze_path: Output path for Bronze DQ reports (None if not configured).
        silver_path: Output path for Silver DQ reports (None if not configured).
        gold_path: Output path for Gold DQ reports (None if not configured).
        flat_structure: Whether to use flat directory structure for DQ reports.
    """

    bronze_path: str | None
    silver_path: str | None
    gold_path: str | None
    flat_structure: bool = False


@dataclass(frozen=True)
class RateLimitContext:
    """Typed context for rate limiting configuration.

    Replaces untyped tuple[float, int] from _get_rate_limit_from_config().

    Attributes:
        rate: Requests per second.
        capacity: Token bucket capacity (burst limit).
    """

    rate: float
    capacity: int


# CircuitBreakerConfig is imported from bioetl.domain.resilience (canonical definition)
# and re-exported via __all__ for backward compatibility.

================================================================================
File: bootstrap_logger.py
Path: bootstrap_logger.py
================================================================================
"""Bootstrap-phase structured logging for composition layer.

Provides structured logging for the composition layer during bootstrap,
before run_id is available. Uses structlog for consistent output format
with pipeline execution logs.

Key differences from pipeline LoggerPort:
- No run_id binding (uses "bootstrap" sentinel)
- stage is always "bootstrap"
- Intended for configuration/registration logging only

Usage:
    from bioetl.composition.bootstrap_logger import get_bootstrap_logger

    logger = get_bootstrap_logger()
    logger.debug("config_loaded", provider="chembl", source="yaml")

Requirements:
- SHOULD: Structured logging in composition layer (audit-2026-01-06)
- REQ-OBS-004: Structured JSON format
"""

from __future__ import annotations

import structlog  # Allowed: composition root configures logging before DI container

from bioetl.infrastructure.observability.logging_config import (
    configure_logging,
    is_logging_configured,
)

# Module-level cached logger instance
_bootstrap_logger: structlog.stdlib.BoundLogger | None = None


def get_bootstrap_logger() -> structlog.stdlib.BoundLogger:
    """Get a structured logger for bootstrap-phase logging.

    Returns a structlog logger pre-bound with bootstrap context:
    - run_id: "bootstrap" (sentinel value, no actual run_id yet)
    - stage: "bootstrap"

    The logger is cached at module level for efficiency.
    Ensures structlog is configured before use.

    Returns:
        Bound structlog logger with bootstrap context.

    Example:
        >>> logger = get_bootstrap_logger()
        >>> logger.debug("source_config_loaded", provider="chembl")
        >>> logger.warning("config_fallback", provider="pubchem", reason="yaml_not_found")
    """
    global _bootstrap_logger

    if _bootstrap_logger is not None:
        return _bootstrap_logger

    # Ensure structlog is configured (idempotent)
    if not is_logging_configured():
        configure_logging(json_format=True, log_level="INFO")

    # Create logger with bootstrap context
    base_logger = structlog.get_logger("bioetl.composition.bootstrap")
    _bootstrap_logger = base_logger.bind(
        run_id="bootstrap",
        stage="bootstrap",
    )

    return _bootstrap_logger


def reset_bootstrap_logger() -> None:
    """Reset the cached bootstrap logger (for testing only).

    Warning:
        This is intended for test fixtures only. Do not use in production code.
    """
    global _bootstrap_logger
    _bootstrap_logger = None


class BootstrapLogger:
    """Wrapper class providing LoggerPort-like interface for bootstrap phase.

    Provides familiar info/debug/warning/error methods while using
    structlog under the hood with bootstrap context pre-bound.

    Example:
        >>> logger = BootstrapLogger()
        >>> logger.debug("loading_config", provider="chembl")
        >>> logger.warning("fallback_defaults", provider="pubchem")
    """

    __slots__ = ("_logger",)

    def __init__(self) -> None:
        """Initialize with the bootstrap logger."""
        self._logger = get_bootstrap_logger()

    def debug(self, event: str, **kwargs: object) -> None:
        """Log a debug message.

        Args:
            event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        self._logger.debug(event, **kwargs)

    def info(self, event: str, **kwargs: object) -> None:
        """Log an informational message.

        Args:
            event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        self._logger.info(event, **kwargs)

    def warning(
        self,
        event: str,
        **kwargs: object,
    ) -> None:
        """Log a warning message.

        Args:
            event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        self._logger.warning(event, **kwargs)

    def error(self, event: str, **kwargs: object) -> None:
        """Log an error message.

        Args:
            event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        self._logger.error(event, **kwargs)


__all__ = [
    "BootstrapLogger",
    "get_bootstrap_logger",
    "reset_bootstrap_logger",
]

================================================================================
File: builders.py
Path: builders.py
================================================================================
"""Configuration builders for composition.

Encapsulates logic for constructing configuration objects from multiple sources
(e.g., merging YAML config with CLI arguments).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.filtering import FilterColumn, InputFilterConfig

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterYamlConfig as YamlInputFilter,
    )


__all__ = [
    "FilterConfigBuilder",
]


class FilterConfigBuilder:
    """Builder for InputFilterConfig."""

    @staticmethod
    def _is_filter_enabled(
        yaml_filter: YamlInputFilter, cli_csv: str | None, test_mode: bool
    ) -> bool:
        """Determine if filtering should be enabled.

        Args:
            yaml_filter: Filter configuration from pipeline YAML.
            cli_csv: CLI-provided CSV path; non-empty value activates filtering.
            test_mode: When True, YAML-based filters are ignored unless a CLI CSV
                is explicitly provided.

        Returns:
            True if input filtering should be applied for this run.
        """
        if test_mode:
            return bool(cli_csv)
        return bool(cli_csv) or yaml_filter.enabled

    @staticmethod
    def _build_multi_column_config(
        yaml_filter: YamlInputFilter, effective_csv: str
    ) -> InputFilterConfig:
        """Build config for multi-column filtering mode.

        Caller must ensure yaml_filter.columns is not None.

        Args:
            yaml_filter: Filter configuration from pipeline YAML providing column specs
                and batch size.
            effective_csv: Resolved path to the CSV file containing filter IDs.

        Returns:
            InputFilterConfig for multi-column filtering mode.
        """
        assert yaml_filter.columns is not None  # Guaranteed by caller check
        domain_columns = tuple(
            FilterColumn(
                column_name=col.column_name,
                filter_field=col.filter_field,
            )
            for col in yaml_filter.columns
        )
        return InputFilterConfig(
            enabled=True,
            source_path=effective_csv,
            columns=domain_columns,
            batch_size=yaml_filter.batch_size,
        )

    @staticmethod
    def _build_single_column_config(
        yaml_filter: YamlInputFilter,
        effective_csv: str,
        cli_column: str | None,
        cli_field: str | None,
        cli_fallback_column: str | None,
    ) -> InputFilterConfig:
        """Build config for single-column filtering mode.

        Args:
            yaml_filter: Filter configuration from pipeline YAML providing defaults.
            effective_csv: Resolved path to the CSV file containing filter IDs.
            cli_column: CLI-provided column name; overrides YAML column if non-None.
            cli_field: CLI-provided API filter field; overrides YAML field if non-None.
            cli_fallback_column: CLI-provided fallback column; overrides YAML if non-None.

        Returns:
            InputFilterConfig for single-column filtering mode.
        """
        effective_column = cli_column or yaml_filter.column_name
        effective_field = cli_field or yaml_filter.filter_field
        effective_fallback = cli_fallback_column or yaml_filter.fallback_column
        return InputFilterConfig(
            enabled=True,
            source_path=effective_csv,
            column_name=effective_column,
            filter_field=effective_field,
            batch_size=yaml_filter.batch_size,
            fallback_column=effective_fallback,
        )

    @staticmethod
    def from_direct_ids(
        filter_ids: tuple[str, ...],
        filter_field: str,
        batch_size: int = 100,
        fallback_mapping: dict[str, str] | None = None,
    ) -> InputFilterConfig:
        """Build config for direct filter IDs mode (no CSV file).

        Used for composite pipelines where IDs are passed programmatically.

        Args:
            filter_ids: List of identifiers to filter by.
            filter_field: Field name to apply filter on.
            batch_size: Number of records per batch.
            fallback_mapping: Fallback mapping.

        Returns:
            The InputFilterConfig result.
        """
        return InputFilterConfig(
            enabled=True,
            filter_field=filter_field,
            direct_filter_ids=filter_ids,
            direct_fallback_mapping=fallback_mapping,
            batch_size=batch_size,
        )

    @staticmethod
    def from_direct_multi_ids(
        multi_filter_ids: dict[str, tuple[str, ...]],
        valid_combinations: frozenset[tuple[str, ...]] | None = None,
        batch_size: int = 100,
    ) -> InputFilterConfig:
        """Build config for direct multi-field filter IDs mode.

        Used for composite dependencies that filter by multiple fields
        simultaneously (AND logic). E.g., compound_record filtered by both
        molecule_chembl_id and document_chembl_id.

        Args:
            multi_filter_ids: Mapping of field name to tuple of IDs.
            valid_combinations: Valid (field1, field2, ...) tuples for
                client-side combination filtering.
            batch_size: Number of IDs per API request.

        Returns:
            The InputFilterConfig result.
        """
        return InputFilterConfig(
            enabled=True,
            direct_multi_filter_ids=multi_filter_ids,
            direct_valid_combinations=valid_combinations,
            batch_size=batch_size,
        )

    @staticmethod
    def build(
        yaml_filter: YamlInputFilter,
        cli_csv: str | None = None,
        cli_column: str | None = None,
        cli_field: str | None = None,
        cli_fallback_column: str | None = None,
        *,
        test_mode: bool = False,
        direct_filter_ids: tuple[str, ...] | None = None,
        direct_fallback_mapping: dict[str, str] | None = None,
        direct_multi_filter_ids: dict[str, tuple[str, ...]] | None = None,
        direct_valid_combinations: frozenset[tuple[str, ...]] | None = None,
    ) -> InputFilterConfig | None:
        """Build `InputFilterConfig` from YAML settings and CLI overrides.

        Args:
            yaml_filter: Filter configuration from pipeline YAML providing defaults.
            cli_csv: CLI-provided CSV path override; defaults to None.
            cli_column: CLI-provided column name override; defaults to None.
            cli_field: CLI-provided API filter field override; defaults to None.
            cli_fallback_column: CLI-provided fallback column override; defaults to None.
            test_mode: If True, YAML filters are ignored unless CLI CSV is provided;
                defaults to False.
            direct_filter_ids: Programmatic filter IDs bypassing CSV; defaults to None.
            direct_fallback_mapping: Fallback mapping for direct filter IDs; defaults
                to None.
            direct_multi_filter_ids: Multi-field filter IDs for AND logic; defaults
                to None.
            direct_valid_combinations: Valid combination tuples for client-side
                filtering; defaults to None.

        Returns:
            Configured InputFilterConfig, or None if filtering is disabled.
        """
        if direct_multi_filter_ids is not None:
            return FilterConfigBuilder.from_direct_multi_ids(
                multi_filter_ids=direct_multi_filter_ids,
                valid_combinations=direct_valid_combinations,
                batch_size=yaml_filter.batch_size,
            )

        if direct_filter_ids is not None:
            return FilterConfigBuilder.from_direct_ids(
                filter_ids=direct_filter_ids,
                filter_field=cli_field or yaml_filter.filter_field or "doi",
                batch_size=yaml_filter.batch_size,
                fallback_mapping=direct_fallback_mapping,
            )

        if not FilterConfigBuilder._is_filter_enabled(yaml_filter, cli_csv, test_mode):
            return None

        effective_csv = cli_csv or yaml_filter.source_path
        if not effective_csv:
            return None

        if yaml_filter.columns and not cli_csv:
            return FilterConfigBuilder._build_multi_column_config(
                yaml_filter, effective_csv
            )

        return FilterConfigBuilder._build_single_column_config(
            yaml_filter, effective_csv, cli_column, cli_field, cli_fallback_column
        )

================================================================================
File: composite_api.py
Path: composite_api.py
================================================================================
"""Public composite-runtime composition API."""

from __future__ import annotations

from bioetl.composition.bootstrap import (
    bootstrap_composite_runner,
    load_composite_config,
    load_pipeline_config,
)

__all__ = [
    "bootstrap_composite_runner",
    "load_composite_config",
    "load_pipeline_config",
]

================================================================================
File: control_plane_api.py
Path: control_plane_api.py
================================================================================
"""Public control-plane composition API."""

from __future__ import annotations

from bioetl.composition._services import (
    get_adr_service,
    get_config_service,
    get_export_service,
    get_lineage_service,
    get_lock_service,
    get_run_manifest_service,
)

__all__ = [
    "get_adr_service",
    "get_config_service",
    "get_export_service",
    "get_lineage_service",
    "get_lock_service",
    "get_run_manifest_service",
]

================================================================================
File: entrypoints.py
Path: entrypoints.py
================================================================================
"""Public composition entrypoint focused on execution-oriented APIs.

`bioetl.composition.entrypoints` remains a stable import seam, but its explicit
public surface (`__all__`) is intentionally narrow and execution-focused.

Service and resource-management helpers remain available through compatibility
lookup in ``__getattr__`` and emit deprecation warnings with canonical import
targets (`services_api` / `resources_api`).
"""

from __future__ import annotations

import warnings
from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.composition.composite_api import (
        bootstrap_composite_runner,
        load_composite_config,
        load_pipeline_config,
    )
    from bioetl.composition.execution_api import (
        ArchiveOptions,
        PipelineRunResult,
        RunOptions,
        RunResult,
        VacuumOptions,
        build_pipeline_context,
        create_pipeline_runner,
        ensure_metrics_server_started,
        maybe_start_metrics_server,
        push_metrics_to_gateway,
        run_pipeline,
    )
    from bioetl.composition.observability_api import start_metrics_server

_COMPOSITION_EXECUTION_API_MODULE = "bioetl.composition.execution_api"
_COMPOSITION_COMPOSITE_API_MODULE = "bioetl.composition.composite_api"

__all__ = [
    "ArchiveOptions",
    "PipelineRunResult",
    "RunOptions",
    "RunResult",
    "VacuumOptions",
    "bootstrap_composite_runner",
    "build_pipeline_context",
    "create_pipeline_runner",
    "ensure_metrics_server_started",
    "load_composite_config",
    "load_pipeline_config",
    "maybe_start_metrics_server",
    "push_metrics_to_gateway",
    "run_pipeline",
    "start_metrics_server",
]

_PUBLIC_SYMBOL_TARGETS: dict[str, str] = {
    "ArchiveOptions": _COMPOSITION_EXECUTION_API_MODULE,
    "PipelineRunResult": _COMPOSITION_EXECUTION_API_MODULE,
    "RunOptions": _COMPOSITION_EXECUTION_API_MODULE,
    "RunResult": _COMPOSITION_EXECUTION_API_MODULE,
    "VacuumOptions": _COMPOSITION_EXECUTION_API_MODULE,
    "bootstrap_composite_runner": _COMPOSITION_COMPOSITE_API_MODULE,
    "build_pipeline_context": _COMPOSITION_EXECUTION_API_MODULE,
    "create_pipeline_runner": _COMPOSITION_EXECUTION_API_MODULE,
    "ensure_metrics_server_started": _COMPOSITION_EXECUTION_API_MODULE,
    "load_composite_config": _COMPOSITION_COMPOSITE_API_MODULE,
    "load_pipeline_config": _COMPOSITION_COMPOSITE_API_MODULE,
    "maybe_start_metrics_server": _COMPOSITION_EXECUTION_API_MODULE,
    "push_metrics_to_gateway": _COMPOSITION_EXECUTION_API_MODULE,
    "run_pipeline": _COMPOSITION_EXECUTION_API_MODULE,
    "start_metrics_server": "bioetl.composition.observability_api",
}

_LEGACY_SYMBOL_TARGETS: dict[str, str] = {
    # services_api
    "cleanup_bronze": "bioetl.composition.services_api",
    "get_adr_service": "bioetl.composition.services_api",
    "get_bronze_cleanup_service": "bioetl.composition.services_api",
    "get_checkpoint_service": "bioetl.composition.services_api",
    "get_config_service": "bioetl.composition.services_api",
    "get_export_service": "bioetl.composition.services_api",
    "get_health_server_dependencies": "bioetl.composition.services_api",
    "get_health_service": "bioetl.composition.services_api",
    "get_lock_service": "bioetl.composition.services_api",
    "get_metrics_service": "bioetl.composition.services_api",
    "get_pipeline_runner_service": "bioetl.composition.services_api",
    "get_quarantine_port": "bioetl.composition.services_api",
    "get_quarantine_service": "bioetl.composition.services_api",
    "get_vacuum_service": "bioetl.composition.services_api",
    # resources_api
    "archive_table": "bioetl.composition.resources_api",
    "get_checkpoint_manager": "bioetl.composition.resources_api",
    "get_lifecycle_service": "bioetl.composition.resources_api",
    "get_quarantine_manager": "bioetl.composition.resources_api",
    "inspect_quarantine": "bioetl.composition.resources_api",
    "list_checkpoints": "bioetl.composition.resources_api",
    "preview_cleanup": "bioetl.composition.resources_api",
    "vacuum_table": "bioetl.composition.resources_api",
}


def __getattr__(
    name: str,
) -> Any:  # Any: lazy compatibility exports resolve to heterogeneous symbol types.
    """Resolve public and deprecated entrypoint symbols lazily."""
    module_name = _PUBLIC_SYMBOL_TARGETS.get(name)
    if module_name is not None:
        module = import_module(module_name)
        value = getattr(module, name)
        globals()[name] = value
        return value

    module_name = _LEGACY_SYMBOL_TARGETS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    value = getattr(module, name)
    warnings.warn(
        (
            f"`bioetl.composition.entrypoints.{name}` is deprecated; "
            f"import `{name}` from `{module_name}` instead."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return stable introspection results including legacy compatibility names."""
    return sorted(
        set(globals())
        | set(__all__)
        | set(_PUBLIC_SYMBOL_TARGETS)
        | set(_LEGACY_SYMBOL_TARGETS)
    )

================================================================================
File: execution_api.py
Path: execution_api.py
================================================================================
"""Public execution-oriented composition API."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.application.services import PipelineRunResult, RunOptions, RunResult
    from bioetl.composition._pipeline_execution import (
        ArchiveOptions,
        VacuumOptions,
        build_pipeline_context,
        create_pipeline_runner,
        ensure_metrics_server_started,
        run_pipeline,
    )
    from bioetl.composition._services import get_pipeline_runner_service
    from bioetl.composition.bootstrap import maybe_start_metrics_server

_PIPELINE_EXECUTION_MODULE = "bioetl.composition._pipeline_execution"
_APPLICATION_SERVICES_MODULE = "bioetl.application.services"

__all__ = [
    "ArchiveOptions",
    "PipelineRunResult",
    "RunOptions",
    "RunResult",
    "VacuumOptions",
    "build_pipeline_context",
    "create_pipeline_runner",
    "ensure_metrics_server_started",
    "get_pipeline_runner_service",
    "maybe_start_metrics_server",
    "push_metrics_to_gateway",
    "run_pipeline",
]

_PUBLIC_EXPORTS: dict[str, str] = {
    "ArchiveOptions": _PIPELINE_EXECUTION_MODULE,
    "PipelineRunResult": _APPLICATION_SERVICES_MODULE,
    "RunOptions": _APPLICATION_SERVICES_MODULE,
    "RunResult": _APPLICATION_SERVICES_MODULE,
    "VacuumOptions": _PIPELINE_EXECUTION_MODULE,
    "build_pipeline_context": _PIPELINE_EXECUTION_MODULE,
    "create_pipeline_runner": _PIPELINE_EXECUTION_MODULE,
    "ensure_metrics_server_started": _PIPELINE_EXECUTION_MODULE,
    "get_pipeline_runner_service": "bioetl.composition._services",
    "maybe_start_metrics_server": "bioetl.composition.bootstrap",
    "run_pipeline": _PIPELINE_EXECUTION_MODULE,
}


def push_metrics_to_gateway(
    run_label: str = "bioetl",
    *,
    pipeline_name: str | None = None,
    run_type: str | None = None,
) -> bool:
    """Push metrics through the composition-owned observability seam."""
    from bioetl.composition.observability_api import (
        push_metrics_to_gateway as _impl,
    )

    return _impl(
        run_label=run_label,
        pipeline_name=pipeline_name,
        run_type=run_type,
    )


def __getattr__(
    name: str,
) -> Any:  # Any: lazy export returns either classes or callables from multiple modules.
    """Resolve execution-oriented public exports lazily."""
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy re-exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))

================================================================================
File: __init__.py
Path: factories\__init__.py
================================================================================
# src/bioetl/composition/factories/__init__.py
"""Pipeline factories module.

Provides the GenericPipelineFactory for creating pipeline instances declaratively.

Usage:
    >>> from bioetl.composition.factories import GenericPipelineFactory
    >>> factory = GenericPipelineFactory(...)

All pipeline factories are auto-registered when this module is imported.

Consolidated modules (v5.2):
- pipeline_factory: GenericPipelineFactory, runner assembly
- services_factory: BaseServicesFactory, ServicesBuilder
- data_source_factory: DataSourceFactory, DataSourceRegistry
- storage: StorageAdapter, StorageContext, StorageFactory
- dq_services_factory: DQServicesFactory for DQ report components
"""

from __future__ import annotations

# Data source factory and registry
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
    DataSourceFactory,
    DataSourceRegistry,
)

# DQ services factory
from bioetl.composition.factories.dq.factory import DQServicesFactory

# Services factory (DI for PipelineRunner)
from bioetl.composition.factories.services.factory import (
    BaseServicesFactory,
    ServicesBuilder,
    create_data_normalization_service,
)

# Storage factory
from bioetl.composition.factories.storage import (
    StorageAdapter,
    StorageContext,
    StorageFactory,
)

# Transformer factory (DI for transformers)
from bioetl.composition.factories.transformer_factory import (
    create_transformer,
    get_transformer_class,
    register_all_transformers,
    register_transformer,
)

# Backward-compatible package alias for tests/tools that patch
# `bioetl.composition.factories.datasource.*` via string import paths.
from . import datasource as datasource

_PIPELINE_FACTORY_EXPORTS = frozenset(
    {
        "chembl_activity_factory",
        "pubchem_compound_factory",
        "pubmed_publication_factory",
        "uniprot_protein_factory",
    }
)
# Compatibility alias retained for legacy imports; new code should use
# DataSourceCreatorProtocol directly.
import warnings


class DataSourceCreatorPort(DataSourceCreatorProtocol):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "DataSourceCreatorPort is deprecated and will be removed in v2.0. "
            "Use DataSourceCreatorProtocol instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


_PIPELINE_EXPORTS = frozenset(
    {
        "GenericPipelineFactory",
        "assemble_runner",
        "build_pipeline_services",
        "create_pipeline_factory",
    }
)


def __getattr__(name: str) -> object:
    """Lazily expose heavy pipeline exports to avoid import cycles."""
    if name in _PIPELINE_EXPORTS:
        from bioetl.composition.factories import pipeline as _pipeline

        return getattr(_pipeline, name)
    if name in _PIPELINE_FACTORY_EXPORTS:
        from bioetl.composition.factories.pipeline import registry as _registry

        return getattr(_registry, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseServicesFactory",
    "DQServicesFactory",
    "DataSourceCreatorProtocol",
    "DataSourceFactory",
    "DataSourceRegistry",
    "GenericPipelineFactory",
    "ServicesBuilder",
    "StorageAdapter",
    "StorageContext",
    "StorageFactory",
    "assemble_runner",
    "build_pipeline_services",
    "chembl_activity_factory",
    "create_data_normalization_service",
    "create_pipeline_factory",
    "create_transformer",
    "datasource",
    "get_transformer_class",
    "pubchem_compound_factory",
    "pubmed_publication_factory",
    "register_all_transformers",
    "register_transformer",
    "uniprot_protein_factory",
]

================================================================================
File: _observability_wiring.py
Path: factories\_observability_wiring.py
================================================================================
"""Observability/data-source wiring helpers for service bundle factory."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.observability_resolution import resolve_metrics_port

from .datasource.data_source_factory import DataSourceCreatorProtocol
from .services.factory import BaseServicesFactory

if TYPE_CHECKING:
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def create_shared_metrics(
    *,
    settings: Settings,
    base_services_factory: type[BaseServicesFactory],
) -> MetricsPort:
    """Create shared pipeline metrics via base services factory.

    Args:
        settings: Application settings used to configure the metrics backend.
        base_services_factory: Factory class providing the metrics creation method.

    Returns:
        Configured MetricsPort for shared use across pipeline components.
    """
    return base_services_factory._create_metrics(settings)


def _create_data_source(
    *,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None,
    metrics: MetricsPort | None,
    pipeline_name: str,
) -> DataSourcePort:
    """Create provider data source through factory callback."""
    return create_data_source_fn(
        settings,
        pipeline_config,
        logger,
        filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
    )


def _create_cached_bronze_data_source(
    *,
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    cached_bronze: CachedBronzeContext,
) -> DataSourcePort:
    """Create CachedBronzeDataSource for reading from Bronze cache."""
    from bioetl.infrastructure.adapters import CachedBronzeDataSource
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

    provider = pipeline_config.provider
    entity_type = pipeline_config.entity_type

    if cached_bronze.bronze_path:
        bronze_path = Path(cached_bronze.bronze_path)
    else:
        bronze_path = settings.bronze_path / provider / entity_type

    bronze_reader = BronzeWriter(
        base_path=bronze_path,
        logger=logger,
        metrics=resolve_metrics_port(metrics=None),
        flat_structure=True,
    )
    return CachedBronzeDataSource(
        bronze_reader=bronze_reader,
        provider=provider,
        entity_type=entity_type,
        logger=logger,
        bronze_date=cached_bronze.bronze_date,
    )


def create_data_source_with_observability(
    *,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None,
    shared_metrics: MetricsPort,
    pipeline_name: str,
    cached_bronze: CachedBronzeContext | None,
) -> DataSourcePort:
    """Create data source and emit cached-bronze observability logs.

    Args:
        create_data_source_fn: Factory callable producing a live DataSourcePort.
        settings: Application settings for data source configuration.
        pipeline_config: Pipeline YAML config providing provider and entity type.
        logger: LoggerPort for structured observability logging.
        filter_config: Optional input filter configuration for data source.
        shared_metrics: Shared MetricsPort passed to the live data source.
        pipeline_name: Pipeline name used in log events.
        cached_bronze: Optional cached Bronze context; if enabled, bypasses live API.

    Returns:
        DataSourcePort configured for live API or cached Bronze data.
    """
    if cached_bronze is not None and cached_bronze.enabled:
        data_source = _create_cached_bronze_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            cached_bronze=cached_bronze,
        )
        logger.info(
            "using_cached_bronze_mode",
            pipeline=pipeline_name,
            bronze_path=cached_bronze.bronze_path,
            bronze_date=cached_bronze.bronze_date,
        )
        return data_source

    return _create_data_source(
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        pipeline_config=pipeline_config,
        logger=logger,
        filter_config=filter_config,
        metrics=shared_metrics,
        pipeline_name=pipeline_name,
    )

================================================================================
File: _transformer_spec_rows.py
Path: factories\_transformer_spec_rows.py
================================================================================
from __future__ import annotations

from typing import Final

TransformerSpecRow = tuple[str, str, str, str]

BUILTIN_TRANSFORMER_SPEC_ROWS: Final[tuple[TransformerSpecRow, ...]] = (
    (
        "chembl",
        "activity",
        "bioetl.application.pipelines.chembl.activity_transformer",
        "ActivityTransformer",
    ),
    (
        "chembl",
        "assay",
        "bioetl.application.pipelines.chembl.assay_transformer",
        "AssayTransformer",
    ),
    (
        "chembl",
        "assay_parameters",
        "bioetl.application.pipelines.chembl.assay_parameters_transformer",
        "AssayParametersTransformer",
    ),
    (
        "chembl",
        "cell_line",
        "bioetl.application.pipelines.chembl.cell_line_transformer",
        "CellLineTransformer",
    ),
    (
        "chembl",
        "compound_record",
        "bioetl.application.pipelines.chembl.compound_record_transformer",
        "CompoundRecordTransformer",
    ),
    (
        "chembl",
        "document",
        "bioetl.application.pipelines.chembl.publication_transformer",
        "PublicationTransformer",
    ),
    (
        "chembl",
        "document_similarity",
        "bioetl.application.pipelines.chembl.publication_similarity_transformer",
        "PublicationSimilarityTransformer",
    ),
    (
        "chembl",
        "document_term",
        "bioetl.application.pipelines.chembl.publication_term_transformer",
        "PublicationTermTransformer",
    ),
    (
        "chembl",
        "molecule",
        "bioetl.application.pipelines.chembl.molecule_transformer",
        "MoleculeTransformer",
    ),
    (
        "chembl",
        "subcellular_fraction",
        "bioetl.application.pipelines.chembl.subcellular_fraction_transformer",
        "SubcellularFractionTransformer",
    ),
    (
        "chembl",
        "protein_class",
        "bioetl.application.pipelines.chembl.protein_class_transformer",
        "ProteinClassTransformer",
    ),
    (
        "chembl",
        "target",
        "bioetl.application.pipelines.chembl.target_transformer",
        "TargetTransformer",
    ),
    (
        "chembl",
        "target_component",
        "bioetl.application.pipelines.chembl.target_component_transformer",
        "TargetComponentTransformer",
    ),
    (
        "pubchem",
        "compound",
        "bioetl.application.pipelines.pubchem.transformer",
        "PubChemCompoundTransformer",
    ),
    (
        "uniprot",
        "protein",
        "bioetl.application.pipelines.uniprot.transformer",
        "UniProtProteinTransformer",
    ),
    (
        "uniprot",
        "idmapping",
        "bioetl.application.pipelines.uniprot.idmapping_transformer",
        "IDMappingTransformer",
    ),
    (
        "pubmed",
        "publication",
        "bioetl.application.pipelines.pubmed.transformer",
        "PubMedPublicationTransformer",
    ),
    (
        "crossref",
        "publication",
        "bioetl.application.pipelines.crossref.transformer",
        "CrossRefPublicationTransformer",
    ),
    (
        "openalex",
        "publication",
        "bioetl.application.pipelines.openalex.transformer",
        "OpenAlexPublicationTransformer",
    ),
    (
        "semanticscholar",
        "publication",
        "bioetl.application.pipelines.semanticscholar.transformer",
        "SemanticScholarPublicationTransformer",
    ),
)

================================================================================
File: batch_id_generator.py
Path: factories\batch_id_generator.py
================================================================================
"""Batch ID generator implementations for composition-layer wiring."""

from __future__ import annotations

from uuid import uuid4

from bioetl.domain.types import BatchID


class UuidBatchIdGenerator:
    """Default batch ID generator based on ``uuid4``."""

    def create(self) -> BatchID:
        """Create a UUID-backed batch identifier.

        Returns:
            New BatchID wrapping a freshly generated UUID4.
        """
        return BatchID(uuid4())


__all__ = ["UuidBatchIdGenerator"]

================================================================================
File: __init__.py
Path: factories\datasource\__init__.py
================================================================================
"""Data source factory subpackage."""

from __future__ import annotations

from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
    DataSourceFactory,
    DataSourceRegistry,
)

DataSourceCreatorPort = DataSourceCreatorProtocol

__all__ = ["DataSourceCreatorProtocol", "DataSourceFactory", "DataSourceRegistry"]

================================================================================
File: _crossref_inputs.py
Path: factories\datasource\_crossref_inputs.py
================================================================================
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings


def resolve_mailto(kwargs: dict[str, object], settings: Settings | None) -> str:
    mailto_raw = kwargs.get("mailto")
    mailto = mailto_raw if isinstance(mailto_raw, str) and mailto_raw else None
    if not mailto and settings:
        mailto = getattr(settings, "default_email", None)
    if not mailto:
        raise ValueError(
            "CrossRef adapter requires mailto. "
            "Provide via 'mailto' kwarg or settings.default_email"
        )
    return mailto


def require_dependencies(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
) -> tuple[UnifiedHTTPClient, LoggerPort]:
    if http_client is None:
        raise ValueError("CrossRef adapter requires http_client")
    if logger is None:
        raise ValueError("CrossRef adapter requires logger")
    return http_client, logger

================================================================================
File: _crossref_support.py
Path: factories\datasource\_crossref_support.py
================================================================================
from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from bioetl.composition.factories.datasource._crossref_inputs import resolve_mailto
from bioetl.composition.factories.datasource.adapter_helpers import (
    AdapterHelperServices,
    AdapterHelpersFactory,
)
from bioetl.domain.ports import ErrorHandlerPort
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common import FallbackFetchOrchestratorService
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.crossref import CROSSREF_API_BASE
from bioetl.infrastructure.adapters.crossref.client_builders import (
    _create_default_crossref_batch_fetcher,
    _create_default_crossref_query_builder,
    _create_default_crossref_response_mapper,
    _create_default_crossref_search_paginator,
    _create_default_crossref_title_fallback_handler,
)
from bioetl.infrastructure.adapters.crossref.fallback import (
    CrossRefTitleFallbackHandler,
)
from bioetl.infrastructure.adapters.crossref.query_builder import CrossRefQueryBuilder
from bioetl.infrastructure.adapters.crossref.response_mapper import (
    CrossRefResponseMapper,
)
from bioetl.infrastructure.adapters.crossref.types import (
    CrossRefBatchFetcher,
    CrossRefSearchPaginator,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings


@dataclass(frozen=True)
class CrossRefAdapterComponents:
    metrics: MetricsPort | None
    error_handler: ErrorHandlerPort
    adapter_metrics: AdapterMetricsRecorder
    request_collector: APIRequestCollector
    fallback_fetch_service: FallbackFetchOrchestratorService
    query_builder: CrossRefQueryBuilder
    response_mapper: CrossRefResponseMapper
    batch_fetcher: CrossRefBatchFetcher
    search_paginator: CrossRefSearchPaginator
    title_fallback_handler: CrossRefTitleFallbackHandler


def _create_helper_services(
    logger: LoggerPort, metrics: MetricsPort | None
) -> AdapterHelperServices:
    return AdapterHelpersFactory.create_http_helpers(
        provider="crossref",
        logger=logger,
        metrics=metrics,
    )


def _resolve_optional_components(
    kwargs: dict[str, object],
    helper_services: AdapterHelperServices,
) -> tuple[
    ErrorHandlerPort,
    AdapterMetricsRecorder,
    APIRequestCollector,
    FallbackFetchOrchestratorService,
]:
    error_handler = cast("ErrorHandlerPort | None", kwargs.get("error_handler"))
    adapter_metrics = cast(
        "AdapterMetricsRecorder | None",
        kwargs.get("adapter_metrics"),
    )
    request_collector = cast(
        "APIRequestCollector | None",
        kwargs.get("request_collector"),
    )
    fallback_fetch_service = cast(
        "FallbackFetchOrchestratorService | None",
        kwargs.get("fallback_fetch_service"),
    )
    return (
        error_handler or helper_services.error_handler,
        adapter_metrics or helper_services.adapter_metrics,
        request_collector or helper_services.request_collector,
        fallback_fetch_service or helper_services.fallback_fetch_service,
    )


def _create_query_builder(
    kwargs: dict[str, object],
    mailto: str,
) -> CrossRefQueryBuilder:
    query_builder = cast(
        "CrossRefQueryBuilder | None",
        kwargs.get("query_builder"),
    )
    if query_builder is None:
        query_builder = _create_default_crossref_query_builder(
            api_base=CROSSREF_API_BASE,
            mailto=mailto,
        )
    return query_builder


def _create_response_mapper(kwargs: dict[str, object]) -> CrossRefResponseMapper:
    response_mapper = cast(
        "CrossRefResponseMapper | None", kwargs.get("response_mapper")
    )
    if response_mapper is None:
        response_mapper = _create_default_crossref_response_mapper()
    return response_mapper


def _create_batch_fetcher(
    kwargs: dict[str, object],
    http_client: UnifiedHTTPClient,
    logger: LoggerPort,
    adapter_metrics: AdapterMetricsRecorder,
    mailto: str,
    headers_fn: Callable[[], dict[str, str]],
    request_collector: APIRequestCollector,
) -> CrossRefBatchFetcher:
    batch_fetcher = cast("CrossRefBatchFetcher | None", kwargs.get("batch_fetcher"))
    if batch_fetcher is None:
        batch_fetcher = _create_default_crossref_batch_fetcher(
            http=http_client,
            logger=logger,
            metrics=adapter_metrics,
            mailto=mailto,
            api_base=CROSSREF_API_BASE,
            headers_fn=headers_fn,
            request_collector=request_collector,
        )
    return batch_fetcher


def _create_search_paginator(
    kwargs: dict[str, object],
    http_client: UnifiedHTTPClient,
    logger: LoggerPort,
    adapter_metrics: AdapterMetricsRecorder,
    mailto: str,
    headers_fn: Callable[[], dict[str, str]],
    request_collector: APIRequestCollector,
) -> CrossRefSearchPaginator:
    search_paginator = cast(
        "CrossRefSearchPaginator | None",
        kwargs.get("search_paginator"),
    )
    if search_paginator is None:
        search_paginator = _create_default_crossref_search_paginator(
            http=http_client,
            logger=logger,
            metrics=adapter_metrics,
            mailto=mailto,
            api_base=CROSSREF_API_BASE,
            headers_fn=headers_fn,
            request_collector=request_collector,
        )
    return search_paginator


def _create_title_fallback_handler(
    kwargs: dict[str, object],
    logger: LoggerPort,
    search_fn: Callable[[str, int], AsyncIterator[JsonDict]],
) -> CrossRefTitleFallbackHandler:
    title_fallback_handler = cast(
        "CrossRefTitleFallbackHandler | None", kwargs.get("title_fallback_handler")
    )
    if title_fallback_handler is None:
        title_fallback_handler = _create_default_crossref_title_fallback_handler(
            logger=logger,
            search_fn=search_fn,
        )
    return title_fallback_handler


def build_crossref_components(
    *,
    kwargs: dict[str, object],
    http_client: UnifiedHTTPClient,
    logger: LoggerPort,
    settings: Settings | None,
) -> CrossRefAdapterComponents:
    mailto = resolve_mailto(kwargs, settings)
    metrics = cast("MetricsPort | None", kwargs.get("metrics"))
    helper_services = _create_helper_services(logger, metrics)
    error_handler, adapter_metrics, request_collector, fallback_fetch_service = (
        _resolve_optional_components(kwargs, helper_services)
    )
    query_builder = _create_query_builder(kwargs, mailto)
    headers_fn = query_builder.build_headers
    response_mapper = _create_response_mapper(kwargs)
    search_paginator = _create_search_paginator(
        kwargs,
        http_client,
        logger,
        adapter_metrics,
        mailto,
        headers_fn,
        request_collector,
    )
    return CrossRefAdapterComponents(
        metrics=metrics,
        error_handler=error_handler,
        adapter_metrics=adapter_metrics,
        request_collector=request_collector,
        fallback_fetch_service=fallback_fetch_service,
        query_builder=query_builder,
        response_mapper=response_mapper,
        batch_fetcher=_create_batch_fetcher(
            kwargs,
            http_client,
            logger,
            adapter_metrics,
            mailto,
            headers_fn,
            request_collector,
        ),
        search_paginator=search_paginator,
        title_fallback_handler=_create_title_fallback_handler(
            kwargs,
            logger,
            search_paginator.search,
        ),
    )

================================================================================
File: adapter_helpers.py
Path: factories\datasource\adapter_helpers.py
================================================================================
"""Factory for adapter helper services assembled at composition root."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.composition.observability_resolution import resolve_metrics_port
from bioetl.domain.ports import (
    ErrorHandlerPort,
    LoggerPort,
    MetricsPort,
)
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common import (
    FallbackFetchOrchestratorService,
    HttpAdapterDependencyContext,
    SyncAdapterDependencyContext,
)
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.error_handling import ErrorService

__all__ = [
    "AdapterHelperServices",
    "AdapterHelpersFactory",
    "SyncAdapterHelperServices",
]


@dataclass(frozen=True, slots=True)
class AdapterHelperServices:
    """Container with helper dependencies shared by HTTP adapters."""

    metrics: MetricsPort
    error_handler: ErrorHandlerPort
    adapter_metrics: AdapterMetricsRecorder
    request_collector: APIRequestCollector
    fallback_fetch_service: FallbackFetchOrchestratorService

    def build_dependency_context(self) -> HttpAdapterDependencyContext:
        """Return explicit constructor context for HTTP adapter runtime deps."""
        return HttpAdapterDependencyContext(
            metrics=self.metrics,
            error_handler=self.error_handler,
            adapter_metrics=self.adapter_metrics,
            request_collector=self.request_collector,
        )

    def as_injection_kwargs(self) -> dict[str, object]:
        """Return kwargs payload for adapter constructor injection.

        Returns:
            Dict of kwargs for injecting adapter helpers into constructor.
        """
        return {
            "dependency_context": self.build_dependency_context(),
            "error_handler": self.error_handler,
            "adapter_metrics": self.adapter_metrics,
            "request_collector": self.request_collector,
            "fallback_fetch_service": self.fallback_fetch_service,
        }


@dataclass(frozen=True, slots=True)
class SyncAdapterHelperServices:
    """Container with helper dependencies shared by sync-backed adapters."""

    metrics: MetricsPort
    error_handler: ErrorHandlerPort
    request_collector: APIRequestCollector

    def build_dependency_context(self) -> SyncAdapterDependencyContext:
        """Return explicit constructor context for sync adapter runtime deps."""
        return SyncAdapterDependencyContext(
            metrics=self.metrics,
            error_handler=self.error_handler,
            request_collector=self.request_collector,
        )

    def as_injection_kwargs(self) -> dict[str, object]:
        """Return kwargs payload for sync adapter constructor injection."""
        return {
            "dependency_context": self.build_dependency_context(),
            "error_handler": self.error_handler,
            "request_collector": self.request_collector,
        }


class AdapterHelpersFactory:
    """Build helper service bundles for adapter constructor injection."""

    _DI_TARGET_PROVIDERS = frozenset(
        {"openalex", "crossref", "pubmed", "semanticscholar", "uniprot", "chembl"}
    )

    @classmethod
    def supports_provider(cls, provider: str) -> bool:
        """Return True if provider uses helper-service DI profile.

        Args:
            provider: Provider name to check (e.g., 'chembl', 'pubmed').

        Returns:
            True if the provider is in the DI target set, False otherwise.
        """
        return provider in cls._DI_TARGET_PROVIDERS

    @classmethod
    def create_http_helpers(
        cls,
        *,
        provider: str,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
    ) -> AdapterHelperServices:
        """Create helper services for one HTTP-backed provider adapter.

        Args:
            provider: Provider name used as label in adapter metrics.
            logger: LoggerPort for structured error and request logging.
            metrics: Optional MetricsPort; uses NoOpMetrics if None.

        Returns:
            AdapterHelperServices bundle with error handler, metrics, request
            collector, and fallback fetch service.
        """
        metrics_port = resolve_metrics_port(metrics=metrics)
        adapter_metrics = AdapterMetricsRecorder(metrics_port, provider)
        request_collector = APIRequestCollector()
        error_handler = ErrorService(logger=logger, metrics=metrics_port)
        fallback_fetch_service = FallbackFetchOrchestratorService(adapter_metrics)
        return AdapterHelperServices(
            metrics=metrics_port,
            error_handler=error_handler,
            adapter_metrics=adapter_metrics,
            request_collector=request_collector,
            fallback_fetch_service=fallback_fetch_service,
        )

    @classmethod
    def create_sync_helpers(
        cls,
        *,
        provider: str,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
    ) -> SyncAdapterHelperServices:
        """Create helper services for one sync-backed provider adapter.

        Args:
            provider: Provider name kept for a symmetric factory signature.
            logger: LoggerPort for structured error and request logging.
            metrics: Optional MetricsPort; uses NoOpMetrics if None.

        Returns:
            SyncAdapterHelperServices bundle with error handler and request
            collector for sync-backed adapters.
        """
        del provider
        metrics_port = resolve_metrics_port(metrics=metrics)
        request_collector = APIRequestCollector()
        error_handler = ErrorService(logger=logger, metrics=metrics_port)
        return SyncAdapterHelperServices(
            metrics=metrics_port,
            error_handler=error_handler,
            request_collector=request_collector,
        )

================================================================================
File: crossref.py
Path: factories\datasource\crossref.py
================================================================================
"""CrossRef datasource factory facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.composition.factories.datasource._crossref_inputs import (
    require_dependencies,
    resolve_mailto,
)
from bioetl.composition.factories.datasource._crossref_support import (
    build_crossref_components,
)
from bioetl.infrastructure.adapters.crossref import CrossRefAdapter

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.common.dependency_context import (
        HttpAdapterDependencyContext,
    )
    from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings

__all__ = ["create_crossref_adapter"]


def create_crossref_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: object,
) -> CrossRefAdapter:
    """Create a configured CrossRef adapter."""
    http_client_resolved, logger_resolved = require_dependencies(http_client, logger)
    components = build_crossref_components(
        kwargs=kwargs,
        http_client=http_client_resolved,
        logger=logger_resolved,
        settings=settings,
    )
    batch_size = cast(int, kwargs.get("batch_size", 50))
    dependency_context = cast(
        "HttpAdapterDependencyContext | None",
        kwargs.get("dependency_context"),
    )
    fetch_flow = cast("CrossRefFetchFlow | None", kwargs.get("fetch_flow"))
    mailto = resolve_mailto(kwargs, settings)

    return CrossRefAdapter(
        http_client=http_client_resolved,
        logger=logger_resolved,
        mailto=mailto,
        batch_size=batch_size,
        metrics=components.metrics,
        dependency_context=dependency_context,
        error_handler=components.error_handler,
        adapter_metrics=components.adapter_metrics,
        request_collector=components.request_collector,
        fallback_fetch_service=components.fallback_fetch_service,
        query_builder=components.query_builder,
        response_mapper=components.response_mapper,
        batch_fetcher=components.batch_fetcher,
        search_paginator=components.search_paginator,
        title_fallback_handler=components.title_fallback_handler,
        fetch_flow=fetch_flow,
    )

================================================================================
File: data_source_factory.py
Path: factories\datasource\data_source_factory.py
================================================================================
"""Canonical data-source factory module with a retained legacy compat facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from bioetl.composition.factories.datasource.adapter_helpers import (
    AdapterHelpersFactory,
)
from bioetl.composition.factories.datasource.provider_registry_resolution import (
    resolve_datasource_provider_registry as _resolve_provider_registry,
)
from bioetl.composition.providers.provider_registry import (
    DataSourceCreatorProtocol,
    ProviderRegistry,
)
from bioetl.domain.ports import DataSourcePort

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings

DataSourceCreatorPort = DataSourceCreatorProtocol


def get_data_source_creator(
    provider: str,
    *,
    provider_registry: ProviderRegistry | None = None,
) -> DataSourceCreatorProtocol:
    """Return the canonical provider-bound data-source creator callback."""
    registry = _resolve_provider_registry(provider_registry)
    return registry.build_data_source_creator(provider)


class DataSourceRegistry:
    """Legacy compatibility facade over the canonical provider creator path."""

    # Retained for backward-compatible test fixtures that backup/restore this
    # dict.  Never populated in production — all delegation goes via
    # ProviderRegistry.
    _creators: ClassVar[dict[str, DataSourceCreatorProtocol]] = {}

    @classmethod
    def get(
        cls,
        provider: str,
        *,
        provider_registry: ProviderRegistry | None = None,
    ) -> DataSourceCreatorProtocol:
        """Get creator function for provider via the canonical creator path."""
        return get_data_source_creator(
            provider,
            provider_registry=provider_registry,
        )

    @classmethod
    def list_providers(
        cls,
        *,
        provider_registry: ProviderRegistry | None = None,
    ) -> list[str]:
        """List providers that expose data-source creators."""
        registry = _resolve_provider_registry(provider_registry)
        providers: list[str] = registry.list_providers()
        return providers

    @classmethod
    def list_keys(cls) -> list[str]:
        """Alias for list_providers()."""
        return cls.list_providers()

    @classmethod
    def contains(cls, key: str) -> bool:
        """Check if provider is registered and has a data-source creator."""
        registry = _resolve_provider_registry()
        contains_provider: bool = registry.has_data_source_creator(key)
        return contains_provider

    @classmethod
    def clear(cls) -> None:
        """Clear the local legacy facade cache used only by compatibility tests."""
        cls._creators.clear()


class DataSourceFactory:
    """Factory for creating data source adapters."""

    @classmethod
    def create(
        cls,
        provider: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: Settings | None = None,
        provider_registry: ProviderRegistry | None = None,
        **kwargs: object,
    ) -> DataSourcePort:
        """Create a data source adapter."""
        registry = _resolve_provider_registry(provider_registry)

        if not registry.is_registered(provider):
            available = ", ".join(registry.list_providers())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")

        adapter_kwargs = {k: v for k, v in kwargs.items() if k != "filter_config"}
        cls._inject_adapter_helpers(
            provider=provider,
            logger=logger,
            adapter_kwargs=adapter_kwargs,
        )

        adapter = registry.create_adapter(
            provider,
            http_client=http_client,
            logger=logger,
            settings=settings,
            **adapter_kwargs,
        )
        assert isinstance(adapter, DataSourcePort), (
            f"Adapter for provider '{provider}' must implement DataSourcePort, "
            f"got {type(adapter)}"
        )
        return adapter

    @staticmethod
    def _inject_adapter_helpers(
        *,
        provider: str,
        logger: LoggerPort | None,
        adapter_kwargs: dict[str, object],
    ) -> None:
        """Inject helper-service bundle for DI-target providers."""
        if not AdapterHelpersFactory.supports_provider(provider):
            return
        if logger is None:
            return

        required_keys = frozenset(
            {
                "error_handler",
                "adapter_metrics",
                "request_collector",
                "fallback_fetch_service",
            }
        )
        if required_keys.issubset(adapter_kwargs.keys()):
            return

        metrics = cast("MetricsPort | None", adapter_kwargs.get("metrics"))
        helpers = AdapterHelpersFactory.create_http_helpers(
            provider=provider,
            logger=logger,
            metrics=metrics,
        )
        for key, value in helpers.as_injection_kwargs().items():
            adapter_kwargs.setdefault(key, value)

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all available providers."""
        providers: list[str] = _resolve_provider_registry().list_providers()
        return providers


__all__ = [
    "DataSourceCreatorProtocol",
    "DataSourceFactory",
    "DataSourceRegistry",
    "get_data_source_creator",
]

================================================================================
File: http_client.py
Path: factories\datasource\http_client.py
================================================================================
"""Factory for provider-specific HTTP clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.factories.datasource.provider_registry_resolution import (
    resolve_datasource_provider_registry as _resolve_provider_registry,
)
from bioetl.composition.providers.provider_registry import (
    ProviderRegistry,
)
from bioetl.composition.source_config_access import load_source_config
from bioetl.domain.resilience import RetryConfig
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings

__all__ = [
    "HttpClientFactory",
    "ResolvedHttpConfig",
]


@dataclass(frozen=True)
class ResolvedHttpConfig:
    """Resolved HTTP scalar config."""

    rate: float
    capacity: int
    failure_threshold: int
    recovery_timeout: int
    timeout: float
    max_retries: int
    base_delay: float
    max_delay: float
    max_connections: int
    max_keepalive: int
    trust_env: bool


class HttpClientFactory:
    """Create HTTP clients from source config plus registry fallbacks."""

    @classmethod
    def create_for_provider(
        cls,
        provider: str,
        settings: Settings | None = None,
        *,
        run_id: RunID | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
        provider_registry: ProviderRegistry | None = None,
    ) -> UnifiedHTTPClient:
        """Create a configured client for ``provider``."""
        registry = _resolve_provider_registry(provider_registry)
        if not registry.is_registered(provider):
            available = ", ".join(registry.list_providers())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")

        return cls._create_from_registry(
            provider,
            settings,
            run_id=run_id,
            tracer=tracer,
            metrics=metrics,
            logger=logger,
            provider_registry=registry,
        )

    @classmethod
    def _resolve_config(
        cls,
        provider: str,
        settings: Settings | None,
        *,
        provider_registry: ProviderRegistry | None = None,
    ) -> ResolvedHttpConfig:
        """Resolve scalar config from source YAML, registry, and overrides."""
        registry = _resolve_provider_registry(provider_registry)
        try:
            source_config = load_source_config(provider)
        except ValueError:
            source_config = None

        if source_config is not None:
            rate = source_config.rate_limit.requests_per_second
            capacity = source_config.rate_limit.burst
            failure_threshold = source_config.circuit_breaker.failure_threshold
            recovery_timeout = source_config.circuit_breaker.recovery_timeout
            timeout = source_config.timeout_sec
            max_retries = source_config.max_retries
            base_delay = source_config.retry_base_delay
            max_delay = source_config.retry_max_delay
            max_connections = source_config.max_connections
            max_keepalive = source_config.max_keepalive_connections
            trust_env = source_config.trust_env
        else:
            _FALLBACK_TIMEOUT = 30.0
            _FALLBACK_MAX_RETRIES = 3
            _FALLBACK_CB_THRESHOLD = 5
            _FALLBACK_CB_RECOVERY = 300
            http_config = registry.get_http_config(provider)
            if http_config is None:
                rate, capacity = 5.0, 10
                failure_threshold, recovery_timeout = (
                    _FALLBACK_CB_THRESHOLD,
                    _FALLBACK_CB_RECOVERY,
                )
                timeout, max_retries = _FALLBACK_TIMEOUT, _FALLBACK_MAX_RETRIES
            else:
                rate, capacity = http_config.rate, http_config.capacity
                failure_threshold, recovery_timeout = (
                    _FALLBACK_CB_THRESHOLD,
                    _FALLBACK_CB_RECOVERY,
                )
                timeout, max_retries = _FALLBACK_TIMEOUT, _FALLBACK_MAX_RETRIES
            base_delay, max_delay = 1.0, 60.0
            max_connections, max_keepalive = 50, 10
            trust_env = True

        http_config = registry.get_http_config(provider)
        if settings and http_config and http_config.rate_overrides:
            for setting_name, override_rate in http_config.rate_overrides.items():
                if cls._check_setting(settings, setting_name):
                    rate = override_rate
                    capacity = int(override_rate * 2)
                    break

        return ResolvedHttpConfig(
            rate=rate,
            capacity=capacity,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            timeout=timeout,
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            max_connections=max_connections,
            max_keepalive=max_keepalive,
            trust_env=trust_env,
        )

    @classmethod
    def _create_from_registry(
        cls,
        provider: str,
        settings: Settings | None,
        *,
        run_id: RunID | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
        provider_registry: ProviderRegistry | None = None,
    ) -> UnifiedHTTPClient:
        """Resolve config and assemble a ``UnifiedHTTPClient``."""
        cfg = cls._resolve_config(
            provider,
            settings,
            provider_registry=provider_registry,
        )

        return UnifiedHTTPClient(
            rate_limiter=TokenBucketRateLimiter(
                rate=cfg.rate, capacity=cfg.capacity, provider=provider
            ),
            circuit_breaker=CircuitBreakerGuard(
                provider=provider,
                failure_threshold=cfg.failure_threshold,
                recovery_timeout=cfg.recovery_timeout,
                metrics=metrics,
            ),
            retry_config=RetryConfig(
                max_attempts=cfg.max_retries,
                base_delay=cfg.base_delay,
                max_delay=cfg.max_delay,
            ),
            timeout=cfg.timeout,
            provider=provider,
            run_id=run_id,
            max_connections=cfg.max_connections,
            max_keepalive_connections=cfg.max_keepalive,
            trust_env=cfg.trust_env,
            tracer=tracer,
            metrics=metrics,
            logger=logger,
        )

    @classmethod
    def _check_setting(cls, settings: Settings, setting_name: str) -> bool:
        """Return ``True`` when the setting exists and is truthy."""
        value = getattr(settings, setting_name, None)
        return value is not None and bool(value)

================================================================================
File: provider_registry_resolution.py
Path: factories\datasource\provider_registry_resolution.py
================================================================================
"""Shared provider-registry resolution helpers for datasource factories."""

from __future__ import annotations

from bioetl.composition.providers.provider_registry import (
    ProviderRegistry,
    resolve_provider_registry,
)


def resolve_datasource_provider_registry(
    provider_registry: ProviderRegistry | None = None,
) -> ProviderRegistry:
    """Resolve and initialize the registry used by datasource factory helpers."""
    resolved_registry = resolve_provider_registry(
        provider_registry,
        ensure_ready=True,
    )
    return resolved_registry


__all__ = ["resolve_datasource_provider_registry", "resolve_provider_registry"]

================================================================================
File: pubchem.py
Path: factories\datasource\pubchem.py
================================================================================
"""PubChem adapter factory for composition-layer wiring only."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import cast

from bioetl.composition.factories.datasource.adapter_helpers import (
    AdapterHelpersFactory,
)
from bioetl.composition.source_config_access import load_source_config
from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
from bioetl.infrastructure.adapters.common import SyncAdapterDependencyContext
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.pubchem import PubChemAdapter
from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper
from bioetl.infrastructure.adapters.pubchem.fetch_strategies import (
    PubChemFetchStrategies,
)

__all__ = ["PubChemRuntimeDependencies", "create_pubchem_adapter"]


@dataclass(frozen=True, slots=True)
class PubChemRuntimeDependencies:
    """Composition-owned runtime collaborators for the PubChem adapter."""

    error_handler: ErrorHandlerPort
    request_collector: APIRequestCollector
    entity_mapper: PubChemEntityMapper
    fetch_strategies: PubChemFetchStrategies
    dependency_context: SyncAdapterDependencyContext | None = None


def _resolve_rate_limit(provider: str) -> tuple[float, int]:
    """Resolve provider rate-limit config with stable defaults."""
    try:
        source_config = load_source_config(provider)
    except ValueError:
        return 5.0, 10
    return (
        source_config.rate_limit.requests_per_second,
        source_config.rate_limit.burst,
    )


def _resolve_circuit_breaker(provider: str) -> tuple[int, int]:
    """Resolve provider circuit-breaker config with stable defaults."""
    try:
        source_config = load_source_config(provider)
    except ValueError:
        return 5, 300
    return (
        source_config.circuit_breaker.failure_threshold,
        source_config.circuit_breaker.recovery_timeout,
    )


def _create_executor_runner(
    thread_pool: ThreadPoolExecutor,
) -> Callable[..., Awaitable[object]]:
    """Create an async executor bridge bound to one injected thread pool."""

    async def run_in_executor(
        func: Callable[..., object],
        *args: object,
    ) -> object:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(thread_pool, func, *args)

    return run_in_executor


def _build_runtime_dependencies(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    rate_limiter: TokenBucketRateLimiter,
    circuit_breaker: CircuitBreakerGuard,
    thread_pool: ThreadPoolExecutor,
    error_handler: ErrorHandlerPort | None,
    request_collector: APIRequestCollector | None,
    entity_mapper: PubChemEntityMapper | None,
    fetch_strategies: PubChemFetchStrategies | None,
) -> PubChemRuntimeDependencies:
    """Build PubChem runtime collaborators at the composition edge."""
    dependency_context: SyncAdapterDependencyContext | None = None
    if error_handler is None or request_collector is None:
        helper_services = AdapterHelpersFactory.create_sync_helpers(
            provider="pubchem",
            logger=logger,
            metrics=metrics,
        )
        error_handler = error_handler or helper_services.error_handler
        request_collector = request_collector or helper_services.request_collector
        dependency_context = SyncAdapterDependencyContext(
            metrics=helper_services.metrics,
            error_handler=error_handler,
            request_collector=request_collector,
        )

    mapper = entity_mapper or PubChemEntityMapper()
    strategies = fetch_strategies or PubChemFetchStrategies(
        logger=logger,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        mapper=mapper,
        run_in_executor=_create_executor_runner(thread_pool),
        provider_name=PubChemAdapter.provider_name,
        request_collector=request_collector,
    )
    return PubChemRuntimeDependencies(
        error_handler=error_handler,
        request_collector=request_collector,
        entity_mapper=mapper,
        fetch_strategies=strategies,
        dependency_context=dependency_context,
    )


def create_pubchem_adapter(
    http_client: object | None = None,
    logger: LoggerPort | None = None,
    settings: object | None = None,
    **kwargs: object,
) -> PubChemAdapter:
    """Create PubChem adapter with composition-owned runtime assembly."""
    if logger is None:
        raise ValueError("PubChem adapter requires logger")

    del http_client, settings
    default_rate, default_capacity = _resolve_rate_limit("pubchem")
    default_cb_threshold, default_cb_timeout = _resolve_circuit_breaker("pubchem")
    rate = cast(float, kwargs.pop("rate", default_rate))
    capacity = cast(int, kwargs.pop("capacity", default_capacity))
    cb_threshold = cast(
        int,
        kwargs.pop("circuit_breaker_threshold", default_cb_threshold),
    )
    cb_timeout = cast(
        int,
        kwargs.pop("circuit_breaker_timeout", default_cb_timeout),
    )
    max_workers = cast(int, kwargs.pop("max_workers", 4))
    strict_error_handling = cast(bool, kwargs.pop("strict_error_handling", False))
    metrics = cast("MetricsPort | None", kwargs.pop("metrics", None))
    error_handler = cast("ErrorHandlerPort | None", kwargs.pop("error_handler", None))
    request_collector = cast(
        "APIRequestCollector | None",
        kwargs.pop("request_collector", None),
    )
    entity_mapper = cast(
        "PubChemEntityMapper | None", kwargs.pop("entity_mapper", None)
    )
    fetch_strategies = cast(
        "PubChemFetchStrategies | None",
        kwargs.pop("fetch_strategies", None),
    )

    rate_limiter = TokenBucketRateLimiter(
        rate=rate,
        capacity=capacity,
        provider="pubchem",
    )
    circuit_breaker = CircuitBreakerGuard(
        provider="pubchem",
        failure_threshold=cb_threshold,
        recovery_timeout=cb_timeout,
        metrics=metrics,
    )
    thread_pool = ThreadPoolExecutor(max_workers=max_workers)
    runtime_dependencies = _build_runtime_dependencies(
        logger=logger,
        metrics=metrics,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        thread_pool=thread_pool,
        error_handler=error_handler,
        request_collector=request_collector,
        entity_mapper=entity_mapper,
        fetch_strategies=fetch_strategies,
    )

    return PubChemAdapter(
        logger=logger,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        thread_pool=thread_pool,
        owns_thread_pool=True,
        strict_error_handling=strict_error_handling,
        dependency_context=runtime_dependencies.dependency_context,
        error_handler=runtime_dependencies.error_handler,
        request_collector=runtime_dependencies.request_collector,
        entity_mapper=runtime_dependencies.entity_mapper,
        fetch_strategies=runtime_dependencies.fetch_strategies,
    )

================================================================================
File: __init__.py
Path: factories\dq\__init__.py
================================================================================
"""DQ (Data Quality) factory subpackage."""

from __future__ import annotations

from bioetl.composition.factories.dq.composite_validation import (
    create_composite_validation_service,
)
from bioetl.composition.factories.dq.factory import DQServicesFactory

__all__ = ["DQServicesFactory", "create_composite_validation_service"]

================================================================================
File: _context_resolver_support.py
Path: factories\dq\_context_resolver_support.py
================================================================================
from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.composition.bootstrap_contexts import DQConfigsContext, DQOutputPathsContext

if TYPE_CHECKING:
    from pydantic import BaseModel

    from bioetl.domain.ports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        LoggerPort,
        MetricsPort,
        SilverDQConfigPort,
    )
    from bioetl.domain.types import JsonDict
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class ModelDumpable(Protocol):
    def model_dump(self) -> dict[str, object]: ...


def extract_single_dq_config_impl(
    sink: Mapping[str, object],
    layer_name: str,
    config_class: type[BaseModel],
) -> BronzeDQConfigPort | SilverDQConfigPort | GoldDQConfigPort | None:
    sink_config = sink.get(layer_name)
    if not sink_config or not hasattr(sink_config, "model_dump"):
        return None
    validated = config_class.model_validate(
        cast(ModelDumpable, sink_config).model_dump()
    )
    dq_report = getattr(validated, "dq_report", None)
    if dq_report is not None and getattr(dq_report, "enabled", False):
        return cast(
            "BronzeDQConfigPort | SilverDQConfigPort | GoldDQConfigPort",
            dq_report,
        )
    return None


def extract_dq_configs_impl(
    yaml_config: PipelineYamlConfig | None,
    *,
    extract_single_dq_config_fn: Callable[..., object],
) -> DQConfigsContext:
    from bioetl.infrastructure.schemas.dq_report_config import (
        BronzeSinkConfig,
        GoldSinkConfig,
        SilverSinkConfig,
    )

    if yaml_config is None:
        return DQConfigsContext(bronze=None, silver=None, gold=None)

    sink = getattr(yaml_config, "sink", None)
    if sink is None or not isinstance(sink, Mapping):
        return DQConfigsContext(bronze=None, silver=None, gold=None)

    sink_mapping = cast(Mapping[str, object], sink)
    return DQConfigsContext(
        bronze=cast(
            "BronzeDQConfigPort | None",
            extract_single_dq_config_fn(sink_mapping, "bronze", BronzeSinkConfig),
        ),
        silver=cast(
            "SilverDQConfigPort | None",
            extract_single_dq_config_fn(sink_mapping, "silver", SilverSinkConfig),
        ),
        gold=cast(
            "GoldDQConfigPort | None",
            extract_single_dq_config_fn(sink_mapping, "gold", GoldSinkConfig),
        ),
    )


def get_layer_path_impl(config: object) -> str | None:
    return getattr(config, "path", None) if config else None


def has_flat_structure_impl(config: object) -> bool:
    return bool(config and getattr(config, "flat_structure", False))


def extract_dq_output_paths_impl(
    yaml_config: PipelineYamlConfig | None,
    *,
    get_layer_path_fn: Callable[[object], str | None],
    has_flat_structure_fn: Callable[[object], bool],
) -> DQOutputPathsContext:
    if yaml_config is None:
        return DQOutputPathsContext(
            bronze_path=None,
            silver_path=None,
            gold_path=None,
            flat_structure=False,
        )

    sink = getattr(yaml_config, "sink", None)
    if sink is None or not isinstance(sink, Mapping):
        return DQOutputPathsContext(
            bronze_path=None,
            silver_path=None,
            gold_path=None,
            flat_structure=False,
        )

    sink_mapping = cast(Mapping[str, object], sink)
    bronze_config = sink_mapping.get("bronze")
    silver_config = sink_mapping.get("silver")
    gold_config = sink_mapping.get("gold")
    return DQOutputPathsContext(
        bronze_path=get_layer_path_fn(bronze_config),
        silver_path=get_layer_path_fn(silver_config),
        gold_path=get_layer_path_fn(gold_config),
        flat_structure=has_flat_structure_fn(silver_config)
        or has_flat_structure_fn(gold_config),
    )


def is_dq_report_enabled_impl(config: PipelineYamlConfig) -> bool:
    sink = config.sink
    for layer_name in ("bronze", "silver", "gold"):
        layer_config = sink.get(layer_name)
        if layer_config and layer_config.dq_report.enabled:
            return True
    return False


def get_flat_structure_impl(config: PipelineYamlConfig) -> bool:
    sink = config.sink
    for layer_name in ("silver", "gold"):
        layer_config = sink.get(layer_name)
        if layer_config and getattr(layer_config, "flat_structure", False):
            return True
    return False


def get_output_root_impl(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
) -> Path:
    bronze_config = pipeline_config.sink.get("bronze")
    if not settings.test_mode and bronze_config and bronze_config.path:
        bronze_path = Path(bronze_config.path)
        return bronze_path.parent.parent.parent
    return settings.data_dir


def create_dq_services_impl(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    *,
    metrics: MetricsPort | None,
    create_bronze_analyzer_fn: Callable[[], object],
    create_silver_analyzer_fn: Callable[[], object],
    create_gold_analyzer_fn: Callable[[], object],
    create_report_writer_fn: Callable[..., object],
    dq_report_service_cls: type[object],
    is_dq_report_enabled_fn: Callable[[PipelineYamlConfig], bool],
    get_output_root_fn: Callable[[Settings, PipelineYamlConfig], Path],
    get_flat_structure_fn: Callable[[PipelineYamlConfig], bool],
) -> JsonDict:
    if not is_dq_report_enabled_fn(pipeline_config):
        return {}

    bronze_analyzer = create_bronze_analyzer_fn()
    silver_analyzer = create_silver_analyzer_fn()
    gold_analyzer = create_gold_analyzer_fn()
    report_writer = create_report_writer_fn(
        base_path=get_output_root_fn(settings, pipeline_config) / "reports" / "dq",
        logger=logger,
        flat_structure=get_flat_structure_fn(pipeline_config),
    )
    report_service = dq_report_service_cls(
        logger=logger,
        bronze_analyzer=bronze_analyzer,
        silver_analyzer=silver_analyzer,
        gold_analyzer=gold_analyzer,
        report_writer=report_writer,
        metrics=metrics,
    )
    return {
        "bronze_analyzer": bronze_analyzer,
        "silver_analyzer": silver_analyzer,
        "gold_analyzer": gold_analyzer,
        "report_writer": report_writer,
        "report_service": report_service,
    }

================================================================================
File: composite_validation.py
Path: factories\dq\composite_validation.py
================================================================================
"""Composition factory for composite validation services."""

from __future__ import annotations

from bioetl.domain.services.aggregation_validator import AggregationValidator
from bioetl.domain.services.composite_validation_layer import CompositeValidationService
from bioetl.domain.services.cross_validation_validator import CrossValidationValidator
from bioetl.domain.services.preflight_governance import PreflightGovernanceService


def create_composite_validation_service() -> CompositeValidationService:
    """Create the default composite validation service wiring."""
    return CompositeValidationService(
        aggregation_validator=AggregationValidator(),
        cross_validation_validator=CrossValidationValidator(),
        preflight_governance=PreflightGovernanceService(),
    )

================================================================================
File: context_resolver.py
Path: factories\dq\context_resolver.py
================================================================================
"""DQ Context Resolver.

Consolidated DQ config/path extraction and DQ services creation.
Merges pipeline_factory_dq_helpers.py + DQ methods from BaseServicesFactory.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.bootstrap_contexts import DQConfigsContext, DQOutputPathsContext
from bioetl.composition.factories.dq._context_resolver_support import (
    create_dq_services_impl,
    extract_dq_configs_impl,
    extract_dq_output_paths_impl,
    extract_single_dq_config_impl,
    get_flat_structure_impl,
    get_layer_path_impl,
    get_output_root_impl,
    has_flat_structure_impl,
    is_dq_report_enabled_impl,
)
from bioetl.composition.factories.dq.factory import DQServicesFactory

if TYPE_CHECKING:
    from pydantic import BaseModel

    from bioetl.domain.ports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        LoggerPort,
        MetricsPort,
        SilverDQConfigPort,
    )
    from bioetl.domain.types import JsonDict
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "create_dq_services",
    "extract_dq_configs",
    "extract_dq_output_paths",
    "extract_single_dq_config",
    "get_flat_structure",
    "get_layer_path",
    "get_output_root",
    "has_flat_structure",
    "is_dq_report_enabled",
]


# ---- Single-layer DQ config extraction ----


def extract_single_dq_config(
    sink: Mapping[str, object],
    layer_name: str,
    config_class: type[BaseModel],
) -> BronzeDQConfigPort | SilverDQConfigPort | GoldDQConfigPort | None:
    """Extract enabled DQ config for one layer."""
    return extract_single_dq_config_impl(sink, layer_name, config_class)


# ---- Multi-layer DQ config extraction ----


def extract_dq_configs(yaml_config: PipelineYamlConfig | None) -> DQConfigsContext:
    """Extract bronze/silver/gold DQ configs from YAML."""
    return extract_dq_configs_impl(
        yaml_config,
        extract_single_dq_config_fn=extract_single_dq_config,
    )


# ---- Path/structure helpers ----


def get_layer_path(config: object) -> str | None:
    """Extract path from a layer config when present."""
    return get_layer_path_impl(config)


def has_flat_structure(config: object) -> bool:
    """Return ``True`` when layer config enables flat structure."""
    return has_flat_structure_impl(config)


def extract_dq_output_paths(
    yaml_config: PipelineYamlConfig | None,
) -> DQOutputPathsContext:
    """Extract per-layer DQ output paths and flat-structure mode."""
    return extract_dq_output_paths_impl(
        yaml_config,
        get_layer_path_fn=get_layer_path,
        has_flat_structure_fn=has_flat_structure,
    )


# ---- DQ service enablement queries ----


def is_dq_report_enabled(config: PipelineYamlConfig) -> bool:
    """Return ``True`` when any layer enables DQ reporting."""
    return is_dq_report_enabled_impl(config)


def get_flat_structure(config: PipelineYamlConfig) -> bool:
    """Return ``True`` when any DQ sink uses flat structure."""
    return get_flat_structure_impl(config)


def get_output_root(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
) -> Path:
    """Resolve the output root for DQ report emission."""
    return get_output_root_impl(settings, pipeline_config)


# ---- DQ services factory ----


def create_dq_services(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    metrics: MetricsPort | None = None,
) -> JsonDict:  # Any: heterogeneous DQ service instances
    """Create DQ analyzers, report writer, and report service."""
    from bioetl.application.services.dq_report_service import DQReportService

    return create_dq_services_impl(
        settings,
        pipeline_config,
        logger,
        metrics=metrics,
        create_bronze_analyzer_fn=DQServicesFactory.create_bronze_analyzer,
        create_silver_analyzer_fn=DQServicesFactory.create_silver_analyzer,
        create_gold_analyzer_fn=DQServicesFactory.create_gold_analyzer,
        create_report_writer_fn=DQServicesFactory.create_report_writer,
        dq_report_service_cls=DQReportService,
        is_dq_report_enabled_fn=is_dq_report_enabled,
        get_output_root_fn=get_output_root,
        get_flat_structure_fn=get_flat_structure,
    )

================================================================================
File: factory.py
Path: factories\dq\factory.py
================================================================================
"""Factory for DQ report components.

Creates DQ analyzers and report writers following the DI pattern.
All components are created in the composition layer and injected
into pipeline services.

Usage:
    >>> from bioetl.composition.factories.dq.factory import DQServicesFactory
    >>> analyzer = DQServicesFactory.create_bronze_analyzer()
    >>> writer = DQServicesFactory.create_report_writer(base_path, logger)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.dq import (
    BronzeDQAnalyzer,
    GoldDQAnalyzer,
    SilverCheckExecutor,
    SilverDQAnalyzer,
    SilverStatisticsCalculator,
    SilverThresholdChecker,
)
from bioetl.infrastructure.export.dq_report_writer import DQReportWriter

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        BronzeDQAnalyzerPort,
        DQReportWriterPort,
        GoldDQAnalyzerPort,
        LoggerPort,
        SilverDQAnalyzerPort,
    )


class DQServicesFactory:
    """Factory for creating DQ analysis and reporting services.

    All methods are static factory methods following the composition pattern.
    Services are created lazily only when DQ reporting is enabled.

    Example:
        >>> factory = DQServicesFactory()
        >>> bronze_analyzer = DQServicesFactory.create_bronze_analyzer()
        >>> silver_analyzer = DQServicesFactory.create_silver_analyzer()
        >>> gold_analyzer = DQServicesFactory.create_gold_analyzer()
        >>> writer = DQServicesFactory.create_report_writer(Path("/data"), logger)
    """

    @staticmethod
    def create_bronze_analyzer() -> BronzeDQAnalyzerPort:
        """Create Bronze layer DQ analyzer.

        Returns:
            BronzeDQAnalyzerPort implementation for analyzing raw Bronze data.
        """
        return BronzeDQAnalyzer()

    @staticmethod
    def create_silver_analyzer() -> SilverDQAnalyzerPort:
        """Create Silver layer DQ analyzer.

        Returns:
            SilverDQAnalyzerPort implementation for analyzing normalized Silver data.
        """
        statistics = SilverStatisticsCalculator()
        threshold_checker = SilverThresholdChecker()
        check_executor = SilverCheckExecutor(
            statistics=statistics,
            threshold_checker=threshold_checker,
        )
        return SilverDQAnalyzer(
            statistics=statistics,
            threshold_checker=threshold_checker,
            check_executor=check_executor,
        )

    @staticmethod
    def create_gold_analyzer() -> GoldDQAnalyzerPort:
        """Create Gold layer DQ analyzer.

        Returns:
            GoldDQAnalyzerPort implementation for analyzing Gold data marts.
        """
        return GoldDQAnalyzer()

    @staticmethod
    def create_report_writer(
        base_path: str | Path,
        logger: LoggerPort,
        flat_structure: bool = False,
    ) -> DQReportWriterPort:
        """Create DQ report writer.

        Args:
            base_path: Base path for report storage.
            logger: Structured logger for observability.
            flat_structure: If True, write reports directly to base_path
                          with {layer}_{provider}_{entity}_dq_report{ext} naming.

        Returns:
            DQReportWriterPort implementation for writing reports to filesystem.
        """
        return DQReportWriter(
            base_path=base_path,
            logger=logger,
            flat_structure=flat_structure,
        )


__all__ = ["DQServicesFactory"]

================================================================================
File: observability_api.py
Path: factories\observability_api.py
================================================================================
"""Public observability wiring facade over private composition helpers."""

from __future__ import annotations

from bioetl.composition.factories._observability_wiring import (
    _create_cached_bronze_data_source,
    _create_data_source,
    create_shared_metrics,
)

__all__ = [
    "_create_cached_bronze_data_source",
    "_create_data_source",
    "create_shared_metrics",
]

================================================================================
File: __init__.py
Path: factories\pipeline\__init__.py
================================================================================
"""Pipeline factory subpackage.

Canonical import paths::

    GenericPipelineFactory : from bioetl.composition.factories.pipeline import GenericPipelineFactory
    PIPELINE_CONFIGS       : from bioetl.composition.factories.pipeline.registry_manifest import PIPELINE_CONFIGS
    register_all_pipelines : from bioetl.composition.factories.pipeline.registry import register_all_pipelines
    PipelineRegistry       : from bioetl.composition import PipelineRegistry
"""

from __future__ import annotations


def __getattr__(name: str) -> object:
    """Expose pipeline assembly helpers lazily to avoid package import cycles."""
    if name in {
        "GenericPipelineFactory",
        "assemble_runner",
        "create_pipeline_factory",
    }:
        from bioetl.composition.factories.pipeline import assembler as _assembler

        return getattr(_assembler, name)
    if name == "build_pipeline_services":
        from bioetl.composition.factories.services import bundle as _bundle

        return _bundle.build_pipeline_services
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "GenericPipelineFactory",
    "assemble_runner",
    "build_pipeline_services",
    "create_pipeline_factory",
]

================================================================================
File: _assembler_factory.py
Path: factories\pipeline\_assembler_factory.py
================================================================================
"""Implementation module for GenericPipelineFactory."""

from __future__ import annotations

from typing import Generic, TypeVar

import pyarrow as pa

from bioetl.application.core.wiring.factory import (
    BasePipeline,
    PipelineRunner,
    PipelineService,
)
from bioetl.application.core.wiring.transformer import (
    BaseTransformer,
    TransformerDependencyContext,
)
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
)
from bioetl.composition.factories.pipeline.assembler_helpers import (
    build_factory_context,
    create_runner_from_factory,
    create_with_services_from_factory,
)
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    _BuildFactoryServicesRequest,
    create_factory_data_source,
    create_transformer_instance,
    resolve_data_source_creator,
)
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    extract_entity_type as _extract_entity_type,
)
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers.provider_registry import ProviderRegistry
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.filtering import (
    GoldFilterConfig,
    InputFilterConfig,
    SilverFilterConfig,
)
from bioetl.domain.ports import (
    ContractPolicyPort,
    DataNormalizationPort,
    DataSourcePort,
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.services import IdentityService
from bioetl.domain.types import GoldSchemaType, RunID
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

TPipeline = TypeVar("TPipeline", bound="BasePipeline")


def _public_assembler_seam(name: str) -> object:
    from bioetl.composition.factories.pipeline import assembler as public_assembler

    return getattr(public_assembler, name)


class GenericPipelineFactory(Generic[TPipeline]):
    """Composition-layer factory for assembling pipelines and runners."""

    def __init__(
        self,
        pipeline_name: str,
        pipeline_class: type[TPipeline],
        provider: str,
        silver_schema: pa.Schema | None = None,
        gold_schema: GoldSchemaType | None = None,
        pandera_silver_schema: object | None = None,
        data_source_creator: DataSourceCreatorProtocol | None = None,
        transformer_class: type[BaseTransformer] | None = None,
        provider_registry: ProviderRegistry | None = None,
    ) -> None:
        if gold_schema is None:
            raise ValueError(
                f"gold_schema is required for pipeline '{pipeline_name}' "
                "to enforce Gold validation."
            )
        self.pipeline_name, self.pipeline_class, self.provider = (
            pipeline_name,
            pipeline_class,
            provider,
        )
        self.silver_schema, self.gold_schema, self.pandera_silver_schema = (
            silver_schema,
            gold_schema,
            pandera_silver_schema,
        )
        self.transformer_class, self.provider_registry = (
            transformer_class,
            provider_registry,
        )
        self._create_data_source = resolve_data_source_creator(
            provider=provider,
            provider_registry=provider_registry,
            data_source_creator=data_source_creator,
            get_data_source_creator_fn=_public_assembler_seam(
                "get_data_source_creator"
            ),
        )

    def create_transformer(
        self,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
        contract_policy: ContractPolicyPort | None = None,
        dependencies: TransformerDependencyContext | None = None,
    ) -> BaseTransformer | None:
        return create_transformer_instance(
            transformer_class=self.transformer_class,
            provider=self.provider,
            pipeline_name=self.pipeline_name,
            extract_entity_type=_extract_entity_type,
            tracer=tracer,
            metrics=metrics,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
            contract_policy=contract_policy,
            dependencies=dependencies,
        )

    def create_data_source(
        self,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        return create_factory_data_source(
            create_data_source_fn=self._create_data_source,
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            pipeline_name=self.pipeline_name,
            filter_config=filter_config,
        )

    def build_services(
        self,
        settings: Settings,
        logger: LoggerPort,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
    ) -> PipelineService:
        return _public_assembler_seam("build_factory_services")(
            factory_context=build_factory_context(self),
            request=_BuildFactoryServicesRequest(
                settings,
                logger,
                config,
                filter_config,
                tracer,
                dq_monitor,
            ),
        )

    def create_with_services(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        logger: LoggerPort,
        manifest_id: str | None = None,
        config_hash: str | None = None,
        dq_contract_compatibility_hash: str | None = None,
        effective_config_artifact_id: str | None = None,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metrics: MetricsPort | None = None,
        cached_bronze: CachedBronzeContext | None = None,
    ) -> TPipeline:
        return create_with_services_from_factory(
            self,
            run_id,
            runtime,
            settings,
            logger,
            manifest_id,
            config_hash,
            dq_contract_compatibility_hash,
            effective_config_artifact_id,
            config,
            filter_config,
            tracer,
            dq_monitor,
            metrics,
            cached_bronze,
            create_pipeline_instance_with_services_fn=_public_assembler_seam(
                "create_pipeline_instance_with_services"
            ),
        )

    def create_runner(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        observability: ObservabilityBundle,
        manifest_id: str | None = None,
        config_hash: str | None = None,
        dq_contract_compatibility_hash: str | None = None,
        effective_config_artifact_id: str | None = None,
        filter_config: InputFilterConfig | None = None,
        config: PipelineYamlConfig | None = None,
        cached_bronze: CachedBronzeContext | None = None,
    ) -> PipelineRunner:
        return create_runner_from_factory(
            self,
            run_id=run_id,
            runtime=runtime,
            settings=settings,
            observability=observability,
            silver_schema=self.silver_schema,
            gold_schema=self.gold_schema,
            manifest_id=manifest_id,
            config_hash=config_hash,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            effective_config_artifact_id=effective_config_artifact_id,
            filter_config=filter_config,
            config=config,
            cached_bronze=cached_bronze,
            assemble_runner_fn=_public_assembler_seam("assemble_runner"),
        )


__all__ = ["GenericPipelineFactory"]

================================================================================
File: _creation_wiring.py
Path: factories\pipeline\_creation_wiring.py
================================================================================
"""Internal pipeline creation wiring extracted from service bundle facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.application.core.wiring.factory import ShutdownSignal
from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.factories.pipeline.construction_types import (
    _SchemaBuilder,
)
from bioetl.composition.factories.pipeline.run_context_factory import (
    RunContextFactory,
)
from bioetl.composition.factories.pipeline.transformer_builder import (
    TransformerBuilder,
)
from bioetl.composition.services.versioning import get_git_commit, get_pipeline_version
from bioetl.infrastructure.config import load_pipeline_contract_policy
from bioetl.infrastructure.config.domain_config_resolver import (
    resolve_domain_pipeline_config,
)

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.wiring.factory import (
        BasePipeline,
        PipelineService,
    )
    from bioetl.application.core.wiring.transformer import BaseTransformer
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceCreatorProtocol,
    )
    from bioetl.composition.factories.pipeline.construction_types import (
        EntityTypeExtractor,
    )
    from bioetl.domain.config import DQConfig, PipelineConfig, RuntimeConfig
    from bioetl.domain.ports import (
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class _ServiceBundleDeps(Protocol):
    """Subset of dependencies required by pipeline creation internals."""

    def load_pipeline_config(self, pipeline_name: str) -> PipelineYamlConfig:
        """Load a pipeline YAML configuration by name."""
        ...

    def yaml_config_to_domain(
        self,
        yaml_config: PipelineYamlConfig,
        resolved_dq_config: DQConfig | None = None,
    ) -> PipelineConfig:
        """Convert a YAML pipeline config to a domain PipelineConfig."""
        ...

    def compute_config_hash(
        self, config: PipelineYamlConfig | dict[str, object]
    ) -> str:
        """Compute a deterministic hash of the pipeline configuration."""
        ...


class _BuildPipelineServicesFn(Protocol):
    """Typed callback for constructing the service bundle."""

    def __call__(
        self,
        pipeline_name: str,
        create_data_source_fn: DataSourceCreatorProtocol,
        settings: Settings,
        logger: LoggerPort,
        config: PipelineYamlConfig | None = None,
        filter_config: object | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        cached_bronze: object | None = None,
        silver_validator: SilverValidatorPort | None = None,
        _deps: object | None = None,
    ) -> PipelineService: ...


@dataclass(frozen=True, slots=True)
class _PipelineCreationRequest:
    """Shared runtime request bundle for pipeline creation helpers."""

    run_id: RunID
    runtime: RuntimeConfig
    settings: Settings
    logger: LoggerPort
    manifest_id: str | None = None
    config_hash: str | None = None
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None
    config: PipelineYamlConfig | None = None
    filter_config: object | None = None
    tracer: TracingPort | None = None
    dq_monitor: DQMonitorPort | None = None
    metrics: MetricsPort | None = None
    cached_bronze: object | None = None


@dataclass(frozen=True, slots=True)
class _PipelineCreationInputs:
    """Immutable input bundle for pipeline creation."""

    pipeline_name: str
    pipeline_class: type[BasePipeline]
    provider: str
    create_data_source_fn: DataSourceCreatorProtocol
    transformer_class: type[BaseTransformer] | None
    request: _PipelineCreationRequest
    pandera_silver_schema: object | None = None


def _create_pipeline_with_services_impl(
    inputs: _PipelineCreationInputs,
    *,
    deps: _ServiceBundleDeps,
    extract_entity_type: EntityTypeExtractor,
    build_pipeline_services_fn: _BuildPipelineServicesFn,
) -> BasePipeline:
    """Implement pipeline creation while keeping facade thin.

    Args:
        inputs: Immutable bundle of pipeline creation parameters.
        deps: Service bundle dependencies providing config loading and domain mapping.
        extract_entity_type: Callable deriving entity type from pipeline name.
        build_pipeline_services_fn: Callable assembling the PipelineService bundle.

    Returns:
        Configured BasePipeline instance ready for execution.
    """
    request = inputs.request
    yaml_config = request.config or deps.load_pipeline_config(inputs.pipeline_name)
    run_context_factory = RunContextFactory(
        pipeline_name=inputs.pipeline_name,
        provider=inputs.provider,
        entity_type_extractor=extract_entity_type,
        pipeline_version_getter=get_pipeline_version,
        git_commit_getter=get_git_commit,
        config_hash_getter=deps.compute_config_hash,
    )
    metadata_coordinator = MetadataCoordinator(
        run_context_factory.create(
            run_id=request.run_id,
            runtime=request.runtime,
            yaml_config=yaml_config,
            manifest_id=request.manifest_id,
            config_hash=request.config_hash,
            dq_contract_compatibility_hash=request.dq_contract_compatibility_hash,
            effective_config_artifact_id=request.effective_config_artifact_id,
        )
    )

    services = build_pipeline_services_fn(
        pipeline_name=inputs.pipeline_name,
        create_data_source_fn=inputs.create_data_source_fn,
        settings=request.settings,
        logger=request.logger,
        config=yaml_config,
        filter_config=request.filter_config,
        tracer=request.tracer,
        dq_monitor=request.dq_monitor,
        metadata_coordinator=metadata_coordinator,
        cached_bronze=request.cached_bronze,
        silver_validator=_create_silver_validator(inputs.pandera_silver_schema),
    )
    domain_config = resolve_domain_pipeline_config(
        yaml_config,
        relaxed_dq=request.settings.pipeline.relaxed_dq,
        domain_mapper=deps.yaml_config_to_domain,
    )
    transformer = TransformerBuilder(
        provider=inputs.provider,
        pipeline_name=inputs.pipeline_name,
        entity_type_extractor=extract_entity_type,
        contract_policy_loader=load_pipeline_contract_policy,
    ).build(
        transformer_class=inputs.transformer_class,
        yaml_config=yaml_config,
        domain_config=domain_config,
        pandera_silver_schema=inputs.pandera_silver_schema,
        tracer=request.tracer,
        metrics=request.metrics,
    )

    return inputs.pipeline_class.create(
        run_id=request.run_id,
        runtime=request.runtime,
        services=services,
        config=domain_config,
        shutdown_signal=ShutdownSignal(),
        transformer=transformer,
    )


def _create_silver_validator(
    pandera_silver_schema: object | None,
) -> SilverValidatorPort | None:
    """Create Pandera silver validator when schema is configured.

    Args:
        pandera_silver_schema: Optional Pandera DataFrameModel class with a
            to_schema() method; returns None when not provided.

    Returns:
        PanderaSilverValidator wrapping the schema, or None if schema is absent.
    """
    if pandera_silver_schema is None:
        return None

    from bioetl.infrastructure.validation.pandera_validator import (
        PanderaSilverValidator,
    )

    schema_builder = cast(_SchemaBuilder, pandera_silver_schema)
    typed_schema = cast("pa.DataFrameSchema | None", schema_builder.to_schema())
    return PanderaSilverValidator(typed_schema)

================================================================================
File: _factory_method_control_plane.py
Path: factories\pipeline\_factory_method_control_plane.py
================================================================================
"""Private control-plane helpers for pipeline factory methods."""

from __future__ import annotations

from bioetl.domain.config import RuntimeConfig
from bioetl.infrastructure.config import Settings


def apply_optional_control_plane_kwargs(
    kwargs: dict[str, object],
    *,
    manifest_id: str | None = None,
    config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
) -> None:
    """Attach only populated control-plane references to a kwargs bag."""
    for key, value in {
        "manifest_id": manifest_id,
        "config_hash": config_hash,
        "dq_contract_compatibility_hash": dq_contract_compatibility_hash,
        "effective_config_artifact_id": effective_config_artifact_id,
    }.items():
        if value is not None:
            kwargs[key] = value


def resolve_strict_gold_validation(
    *,
    runtime: RuntimeConfig,
    settings: Settings,
) -> bool:
    """Resolve production/default strict-gold validation policy."""
    return (
        settings.env == "prod" and not settings.test_mode
    ) or runtime.strict_gold_validation

================================================================================
File: _factory_method_runtime_support.py
Path: factories\pipeline\_factory_method_runtime_support.py
================================================================================
"""Private runtime helpers for pipeline factory method wrappers."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.composition.factories.pipeline._factory_method_types import (
        _CreatePipelineWithServicesRequest,
        _PipelineFactoryContext,
    )
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.types import GoldSchemaType, RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def create_pipeline_instance_from_request(
    *,
    factory_context: _PipelineFactoryContext,
    request: _CreatePipelineWithServicesRequest,
    create_pipeline_with_services_fn: Callable[..., BasePipeline],
    apply_optional_control_plane_kwargs_fn: Callable[..., None],
) -> BasePipeline:
    """Create a pipeline instance from typed factory/request objects."""
    if factory_context.pipeline_class is None or factory_context.provider is None:
        raise AssertionError(
            "factory_context must include pipeline_class and provider for pipeline creation"
        )
    create_pipeline_kwargs: dict[str, object] = {
        "pipeline_name": factory_context.pipeline_name,
        "pipeline_class": factory_context.pipeline_class,
        "provider": factory_context.provider,
        "create_data_source_fn": factory_context.create_data_source_fn,
        "transformer_class": factory_context.transformer_class,
        "pandera_silver_schema": factory_context.pandera_silver_schema,
        "run_id": request.run_id,
        "runtime": request.runtime,
        "settings": request.settings,
        "logger": request.logger,
        "config": request.config,
        "filter_config": cast("InputFilterConfig | None", request.filter_config),
        "tracer": request.tracer,
        "dq_monitor": request.dq_monitor,
        "metrics": request.metrics,
        "cached_bronze": cast("CachedBronzeContext | None", request.cached_bronze),
    }
    apply_optional_control_plane_kwargs_fn(
        create_pipeline_kwargs,
        manifest_id=request.manifest_id,
        config_hash=request.config_hash,
        dq_contract_compatibility_hash=request.dq_contract_compatibility_hash,
        effective_config_artifact_id=request.effective_config_artifact_id,
    )
    return cast(
        "BasePipeline",
        cast("Any", create_pipeline_with_services_fn)(  # Any: Dynamic factory function
            **cast("dict[str, Any]", create_pipeline_kwargs)  # Any: Dynamic kwargs dict
        ),
    )


def create_factory_runner_from_request(
    *,
    pipeline_name: str,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    run_id: RunID,
    runtime: RuntimeConfig,
    settings: Settings,
    observability: ObservabilityBundle,
    yaml_config: PipelineYamlConfig,
    manifest_id: str | None,
    config_hash: str | None,
    dq_contract_compatibility_hash: str | None,
    effective_config_artifact_id: str | None,
    create_with_services_fn: Callable[..., BasePipeline],
    assemble_runner_fn: Callable[..., PipelineRunner],
    filter_config: InputFilterConfig | None,
    cached_bronze: CachedBronzeContext | None,
    apply_optional_control_plane_kwargs_fn: Callable[..., None],
    resolve_strict_gold_validation_fn: Callable[..., bool],
) -> PipelineRunner:
    """Create a pipeline and assemble a runner from resolved runtime inputs."""
    create_with_services_kwargs: dict[str, object] = {
        "run_id": run_id,
        "runtime": runtime,
        "settings": settings,
        "logger": observability.logger,
        "config": yaml_config,
        "filter_config": filter_config,
        "tracer": observability.tracer,
        "dq_monitor": observability.dq_monitor,
        "metrics": observability.metrics,
        "cached_bronze": cached_bronze,
    }
    apply_optional_control_plane_kwargs_fn(
        create_with_services_kwargs,
        manifest_id=manifest_id,
        config_hash=config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
    )
    pipeline = cast(
        "Any",  # Any: Dynamic factory function
        create_with_services_fn,
    )(**cast("dict[str, Any]", create_with_services_kwargs))  # Any: Dynamic kwargs dict
    return assemble_runner_fn(
        pipeline=pipeline,
        observability=observability,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=resolve_strict_gold_validation_fn(
            runtime=runtime,
            settings=settings,
        ),
        yaml_config=yaml_config,
    )

================================================================================
File: _factory_method_types.py
Path: factories\pipeline\_factory_method_types.py
================================================================================
"""Private type/context helpers for pipeline factory method wrappers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
)
from bioetl.composition.factories.pipeline.creation_support import (
    _PipelineCreationRequest,
)
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.filtering import InputFilterConfig
from bioetl.domain.ports import (
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class _PipelineFactoryContext:
    pipeline_name: str
    create_data_source_fn: DataSourceCreatorProtocol
    pipeline_class: type[BasePipeline] | None = None
    provider: str | None = None
    transformer_class: type[BaseTransformer] | None = None
    pandera_silver_schema: object | None = None


@dataclass(frozen=True, slots=True)
class _BuildFactoryServicesRequest:
    settings: Settings
    logger: LoggerPort
    config: PipelineYamlConfig | None = None
    filter_config: InputFilterConfig | None = None
    tracer: TracingPort | None = None
    dq_monitor: DQMonitorPort | None = None


_CreatePipelineWithServicesRequest = _PipelineCreationRequest


def extract_entity_type(pipeline_name: str) -> str | None:
    """Extract trailing entity token from `<provider>_<entity>` pipeline names."""
    return pipeline_name.split("_")[-1] if "_" in pipeline_name else None


def resolve_data_source_creator(
    *,
    provider: str,
    provider_registry: object | None,
    data_source_creator: DataSourceCreatorProtocol | None,
    get_data_source_creator_fn: Callable[..., DataSourceCreatorProtocol],
) -> DataSourceCreatorProtocol:
    """Resolve explicit or registry-derived data-source creator callback."""
    if data_source_creator is not None:
        return data_source_creator
    return get_data_source_creator_fn(provider, provider_registry=provider_registry)


def build_pipeline_factory_context(
    *,
    pipeline_name: str,
    create_data_source_fn: DataSourceCreatorProtocol,
    pipeline_class: type[BasePipeline] | None = None,
    provider: str | None = None,
    transformer_class: type[BaseTransformer] | None = None,
    pandera_silver_schema: object | None = None,
) -> _PipelineFactoryContext:
    """Build immutable factory context consumed by helper orchestration flows."""
    return _PipelineFactoryContext(
        pipeline_name=pipeline_name,
        create_data_source_fn=create_data_source_fn,
        pipeline_class=pipeline_class,
        provider=provider,
        transformer_class=transformer_class,
        pandera_silver_schema=pandera_silver_schema,
    )


def build_create_pipeline_with_services_request(
    run_id: RunID,
    runtime: object,
    settings: Settings,
    logger: LoggerPort,
    manifest_id: str | None = None,
    config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
    metrics: MetricsPort | None = None,
    cached_bronze: CachedBronzeContext | None = None,
) -> _CreatePipelineWithServicesRequest:
    """Pack runtime pipeline-creation arguments into a typed request object."""
    return _CreatePipelineWithServicesRequest(
        run_id,
        runtime,
        settings,
        logger,
        manifest_id,
        config_hash,
        dq_contract_compatibility_hash,
        effective_config_artifact_id,
        config,
        filter_config,
        tracer,
        dq_monitor,
        metrics,
        cached_bronze,
    )


def create_factory_data_source(
    *,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    pipeline_name: str,
    filter_config: InputFilterConfig | None = None,
):
    """Create data-source adapter for one pipeline execution context."""
    return create_data_source_fn(
        settings, pipeline_config, logger, filter_config, pipeline_name=pipeline_name
    )

================================================================================
File: _registry_manifest_chembl.py
Path: factories\pipeline\_registry_manifest_chembl.py
================================================================================
"""Private ChEMBL entries for the canonical pipeline registry manifest."""

from __future__ import annotations

from bioetl.application.core.wiring.registry import (
    ActivityTransformer,
    AssayParametersTransformer,
    AssayTransformer,
    CellLineTransformer,
    CompoundRecordTransformer,
    MoleculeTransformer,
    ProteinClassTransformer,
    PublicationSimilarityTransformer,
    PublicationTermTransformer,
    PublicationTransformer,
    SubcellularFractionTransformer,
    TargetComponentTransformer,
    TargetTransformer,
    TissueTransformer,
)
from bioetl.composition.factories.pipeline.config_types import PipelineFactoryConfig
from bioetl.domain.contracts import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLAssayParametersGoldSchema,
    ChEMBLCellLineGoldSchema,
    ChEMBLCompoundRecordGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLProteinClassGoldSchema,
    ChEMBLPublicationGoldSchema,
    ChEMBLPublicationSimilarityGoldSchema,
    ChEMBLPublicationTermGoldSchema,
    ChEMBLSubcellularFractionGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
    ChEMBLTissueGoldSchema,
)
from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.assay_parameters import AssayParametersSchema
from bioetl.domain.schemas.chembl.cell_line import CellLineSchema
from bioetl.domain.schemas.chembl.compound_record import CompoundRecordSchema
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema
from bioetl.domain.schemas.chembl.protein_classification import (
    ProteinClassificationSchema,
)
from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema
from bioetl.domain.schemas.chembl.publication_similarity import (
    PublicationSimilaritySchema,
)
from bioetl.domain.schemas.chembl.publication_term import PublicationTermSchema
from bioetl.domain.schemas.chembl.subcellular_fraction import (
    SubcellularFractionSchema,
)
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.target_component import TargetComponentSchema
from bioetl.domain.schemas.chembl.tissue import TissueSchema
from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    CHEMBL_ASSAY_PARAMETERS_SCHEMA,
    CHEMBL_ASSAY_SCHEMA,
    CHEMBL_CELL_LINE_SCHEMA,
    CHEMBL_COMPOUND_RECORD_SCHEMA,
    CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
    CHEMBL_DOCUMENT_TERM_SCHEMA,
    CHEMBL_MOLECULE_SCHEMA,
    CHEMBL_PROTEIN_CLASS_SCHEMA,
    CHEMBL_PUBLICATION_SCHEMA,
    CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
    CHEMBL_TARGET_COMPONENT_SCHEMA,
    CHEMBL_TARGET_SCHEMA,
    CHEMBL_TISSUE_SCHEMA,
)

CHEMBL_PIPELINE_CONFIGS: tuple[PipelineFactoryConfig, ...] = (
    PipelineFactoryConfig(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type="activity",
        transformer_class=ActivityTransformer,
        silver_schema=CHEMBL_ACTIVITY_SCHEMA,
        gold_schema=ChEMBLActivityGoldSchema,
        pandera_silver_schema=ActivitySchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_assay",
        provider="chembl",
        entity_type="assay",
        transformer_class=AssayTransformer,
        silver_schema=CHEMBL_ASSAY_SCHEMA,
        gold_schema=ChEMBLAssayGoldSchema,
        pandera_silver_schema=AssaySchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_assay_parameters",
        provider="chembl",
        entity_type="assay_parameters",
        transformer_class=AssayParametersTransformer,
        silver_schema=CHEMBL_ASSAY_PARAMETERS_SCHEMA,
        gold_schema=ChEMBLAssayParametersGoldSchema,
        pandera_silver_schema=AssayParametersSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_cell_line",
        provider="chembl",
        entity_type="cell_line",
        transformer_class=CellLineTransformer,
        silver_schema=CHEMBL_CELL_LINE_SCHEMA,
        gold_schema=ChEMBLCellLineGoldSchema,
        pandera_silver_schema=CellLineSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_compound_record",
        provider="chembl",
        entity_type="compound_record",
        transformer_class=CompoundRecordTransformer,
        silver_schema=CHEMBL_COMPOUND_RECORD_SCHEMA,
        gold_schema=ChEMBLCompoundRecordGoldSchema,
        pandera_silver_schema=CompoundRecordSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_publication",
        provider="chembl",
        entity_type="publication",
        transformer_class=PublicationTransformer,
        silver_schema=CHEMBL_PUBLICATION_SCHEMA,
        gold_schema=ChEMBLPublicationGoldSchema,
        pandera_silver_schema=ChemblPublicationSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_publication_similarity",
        provider="chembl",
        entity_type="publication_similarity",
        transformer_class=PublicationSimilarityTransformer,
        silver_schema=CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
        gold_schema=ChEMBLPublicationSimilarityGoldSchema,
        pandera_silver_schema=PublicationSimilaritySchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_publication_term",
        provider="chembl",
        entity_type="publication_term",
        transformer_class=PublicationTermTransformer,
        silver_schema=CHEMBL_DOCUMENT_TERM_SCHEMA,
        gold_schema=ChEMBLPublicationTermGoldSchema,
        pandera_silver_schema=PublicationTermSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_molecule",
        provider="chembl",
        entity_type="molecule",
        transformer_class=MoleculeTransformer,
        silver_schema=CHEMBL_MOLECULE_SCHEMA,
        gold_schema=ChEMBLMoleculeGoldSchema,
        pandera_silver_schema=MoleculeSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_target",
        provider="chembl",
        entity_type="target",
        transformer_class=TargetTransformer,
        silver_schema=CHEMBL_TARGET_SCHEMA,
        gold_schema=ChEMBLTargetGoldSchema,
        pandera_silver_schema=TargetSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_target_component",
        provider="chembl",
        entity_type="target_component",
        transformer_class=TargetComponentTransformer,
        silver_schema=CHEMBL_TARGET_COMPONENT_SCHEMA,
        gold_schema=ChEMBLTargetComponentGoldSchema,
        pandera_silver_schema=TargetComponentSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_protein_class",
        provider="chembl",
        entity_type="protein_class",
        transformer_class=ProteinClassTransformer,
        silver_schema=CHEMBL_PROTEIN_CLASS_SCHEMA,
        gold_schema=ChEMBLProteinClassGoldSchema,
        pandera_silver_schema=ProteinClassificationSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_tissue",
        provider="chembl",
        entity_type="tissue",
        transformer_class=TissueTransformer,
        silver_schema=CHEMBL_TISSUE_SCHEMA,
        gold_schema=ChEMBLTissueGoldSchema,
        pandera_silver_schema=TissueSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_subcellular_fraction",
        provider="chembl",
        entity_type="subcellular_fraction",
        transformer_class=SubcellularFractionTransformer,
        silver_schema=CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
        gold_schema=ChEMBLSubcellularFractionGoldSchema,
        pandera_silver_schema=SubcellularFractionSchema,
    ),
)

__all__ = ["CHEMBL_PIPELINE_CONFIGS"]

================================================================================
File: _registry_manifest_non_chembl.py
Path: factories\pipeline\_registry_manifest_non_chembl.py
================================================================================
"""Private non-ChEMBL entries for the canonical pipeline registry manifest."""

from __future__ import annotations

from bioetl.application.core.wiring.registry import (
    CrossRefPublicationTransformer,
    IDMappingTransformer,
    OpenAlexPublicationTransformer,
    PubChemCompoundTransformer,
    PubMedPublicationTransformer,
    SemanticScholarPublicationTransformer,
    UniProtProteinTransformer,
)
from bioetl.composition.factories.pipeline.config_types import PipelineFactoryConfig
from bioetl.domain.contracts import (
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubChemCompoundGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
    UniProtIDMappingGoldSchema,
    UniProtProteinGoldSchema,
)
from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema
from bioetl.domain.schemas.openalex.publication import OpenAlexPublicationSchema
from bioetl.domain.schemas.pubchem.compound import PubchemMoleculeSchema
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema
from bioetl.domain.schemas.semanticscholar.publication import (
    SemanticScholarPublicationSchema,
)
from bioetl.domain.schemas.uniprot.idmapping import IDMappingSchema
from bioetl.domain.schemas.uniprot.protein import UniprotTargetSchema
from bioetl.infrastructure.schemas.silver import (
    CROSSREF_PUBLICATION_SCHEMA,
    OPENALEX_PUBLICATION_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    PUBMED_PUBLICATION_SCHEMA,
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
    UNIPROT_ID_MAPPING_SCHEMA,
    UNIPROT_PROTEIN_SCHEMA,
)

NON_CHEMBL_PIPELINE_CONFIGS: tuple[PipelineFactoryConfig, ...] = (
    PipelineFactoryConfig(
        pipeline_name="pubchem_compound",
        provider="pubchem",
        entity_type="compound",
        transformer_class=PubChemCompoundTransformer,
        silver_schema=PUBCHEM_COMPOUND_SCHEMA,
        gold_schema=PubChemCompoundGoldSchema,
        pandera_silver_schema=PubchemMoleculeSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="uniprot_protein",
        provider="uniprot",
        entity_type="protein",
        transformer_class=UniProtProteinTransformer,
        silver_schema=UNIPROT_PROTEIN_SCHEMA,
        gold_schema=UniProtProteinGoldSchema,
        pandera_silver_schema=UniprotTargetSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="uniprot_idmapping",
        provider="uniprot",
        entity_type="idmapping",
        transformer_class=IDMappingTransformer,
        silver_schema=UNIPROT_ID_MAPPING_SCHEMA,
        gold_schema=UniProtIDMappingGoldSchema,
        pandera_silver_schema=IDMappingSchema,
        data_source_provider="uniprot_idmapping",
    ),
    PipelineFactoryConfig(
        pipeline_name="pubmed_publication",
        provider="pubmed",
        entity_type="publication",
        transformer_class=PubMedPublicationTransformer,
        silver_schema=PUBMED_PUBLICATION_SCHEMA,
        gold_schema=PubMedPublicationGoldSchema,
        pandera_silver_schema=PubMedPublicationSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="crossref_publication",
        provider="crossref",
        entity_type="publication",
        transformer_class=CrossRefPublicationTransformer,
        silver_schema=CROSSREF_PUBLICATION_SCHEMA,
        gold_schema=CrossRefPublicationGoldSchema,
        pandera_silver_schema=PublicationEnrichedSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="openalex_publication",
        provider="openalex",
        entity_type="publication",
        transformer_class=OpenAlexPublicationTransformer,
        silver_schema=OPENALEX_PUBLICATION_SCHEMA,
        gold_schema=OpenAlexPublicationGoldSchema,
        pandera_silver_schema=OpenAlexPublicationSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="semanticscholar_publication",
        provider="semanticscholar",
        entity_type="publication",
        transformer_class=SemanticScholarPublicationTransformer,
        silver_schema=SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
        gold_schema=SemanticScholarPublicationGoldSchema,
        pandera_silver_schema=SemanticScholarPublicationSchema,
    ),
)

__all__ = ["NON_CHEMBL_PIPELINE_CONFIGS"]

================================================================================
File: _runner_assembly_support.py
Path: factories\pipeline\_runner_assembly_support.py
================================================================================
"""Private support helpers for pipeline runner assembly."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.lifecycle import LockCoordinator
from bioetl.application.core.preflight import (
    HealthAggregator,
    MedallionConfigValidator,
    PreflightService,
)
from bioetl.application.observability.observer import PipelineObserver
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.composition.factories.dq.context_resolver import extract_dq_output_paths
from bioetl.composition.factories.pipeline.postrun_assembly import build_postrun_service
from bioetl.composition.factories.pipeline.runner_constructor import (
    RunnerAssemblyParts,
    RunnerConstructorPayload,
)
from bioetl.composition.factories.services.factory import ServicesBuilder
from bioetl.domain.locking import LockContextHolder
from bioetl.domain.medallion import WriteModePolicy

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.lifecycle import CheckpointManagerService
    from bioetl.application.core.postrun import PostrunService
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import GoldSchemaType
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class RunnerAssemblyContext:
    """Typed seam carrying the inputs shared across runner assembly helpers."""

    pipeline: BasePipeline
    observability: ObservabilityBundle
    logger_port: LoggerPort
    yaml_config: PipelineYamlConfig | None
    silver_schema: pa.Schema | None
    gold_schema: GoldSchemaType
    strict_gold_validation: bool
    dq_configs_extractor: Callable[[PipelineYamlConfig | None], DQConfigsContext]


def build_lock_manager(
    context: RunnerAssemblyContext,
    *,
    checkpoint_manager: CheckpointManagerService,
    context_holder: LockContextHolder,
) -> LockCoordinator:
    """Build the lock coordinator for one assembled runner."""
    pipeline = context.pipeline
    return LockCoordinator.create(
        lock_port=pipeline.services.lock,
        run_id=pipeline.context.run_id,
        provider=pipeline.config.provider,
        entity_type=pipeline.config.entity_type,
        run_type=pipeline.runtime.run_type,
        lock_ttl=pipeline.runtime.effective_lock_ttl,
        wait_for_lock=pipeline.runtime.wait_for_lock,
        wait_timeout=pipeline.runtime.lock_wait_timeout,
        heartbeat_interval=pipeline.runtime.heartbeat_interval,
        logger=context.logger_port,
        shutdown_signal=pipeline.shutdown_signal,
        checkpoint_manager=checkpoint_manager,
        context_holder=context_holder,
    )


def build_preflight_service(context: RunnerAssemblyContext) -> PreflightService:
    """Build the preflight service for a pipeline runner."""
    pipeline = context.pipeline
    health_aggregator = HealthAggregator(
        logger=context.logger_port,
        health_check_mode=pipeline.runtime.health_check_mode,
    )
    medallion_validator = MedallionConfigValidator(
        config=pipeline.config,
        logger=context.logger_port,
        write_mode_policy=WriteModePolicy(),
    )
    return PreflightService(
        config=pipeline.config,
        context=pipeline.context,
        logger=context.logger_port,
        metrics=pipeline.services.metrics,
        health_aggregator=health_aggregator,
        medallion_validator=medallion_validator,
    )


def build_observer(context: RunnerAssemblyContext) -> PipelineObserver:
    """Build the pipeline observer bound to the current run context."""
    pipeline = context.pipeline
    pipeline_context = pipeline.context
    return PipelineObserver(
        pipeline_name=pipeline.config.pipeline_name,
        run_id=pipeline_context.run_id,
        run_type=pipeline.runtime.run_type,
        metrics=pipeline.services.metrics,
        logger=context.logger_port,
        tracer=context.observability.tracer,
        manifest_id=getattr(pipeline_context, "manifest_id", None),
        entity=getattr(pipeline_context, "entity", None),
        effective_config_hash=getattr(pipeline_context, "config_hash", None),
        contract_ref=getattr(pipeline_context, "contract_ref", None),
        contract_version=getattr(pipeline_context, "contract_version", None),
        composite_run_id=getattr(pipeline_context, "composite_run_id", None),
    )


def build_batch_executor(
    context: RunnerAssemblyContext,
    *,
    checkpoint_manager: CheckpointManagerService,
    lock_manager: LockCoordinator,
    observer: PipelineObserver,
) -> BatchExecutor:
    """Build the batch executor with YAML-derived DQ output paths."""
    dq_output_paths = extract_dq_output_paths(context.yaml_config)
    return ServicesBuilder.create_batch_executor_from_pipeline(
        pipeline=context.pipeline,
        silver_schema=context.silver_schema,
        gold_schema=context.gold_schema,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=context.pipeline.shutdown_signal,
        strict_gold_validation=context.strict_gold_validation,
        lock_validator=lock_manager.validate,
        tracer=context.observability.tracer,
        bronze_output_path=dq_output_paths.bronze_path,
        silver_output_path=dq_output_paths.silver_path,
        gold_output_path=dq_output_paths.gold_path,
        flat_structure=dq_output_paths.flat_structure,
        domain_event_emitter=observer,
    )


def build_postrun_service_for_pipeline(
    context: RunnerAssemblyContext,
    *,
    lifecycle_service: MedallionLifecycleService,
) -> PostrunService:
    """Build the postrun service from YAML-derived DQ config seams."""
    dq_configs = context.dq_configs_extractor(context.yaml_config)
    return build_postrun_service(
        pipeline=context.pipeline,
        logger_port=context.logger_port,
        lifecycle_service=lifecycle_service,
        dq_configs=dq_configs,
        tracer=context.observability.tracer,
    )


def build_runner_constructor_payload(
    *,
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    parts: RunnerAssemblyParts,
) -> RunnerConstructorPayload:
    """Package runner shell inputs into one typed constructor payload."""
    return RunnerConstructorPayload(
        pipeline=pipeline,
        observability=observability,
        parts=parts,
    )


def assemble_runner_parts(
    context: RunnerAssemblyContext,
    *,
    checkpoint_manager_builder: Callable[..., CheckpointManagerService],
    lock_manager_builder: Callable[..., LockCoordinator],
    preflight_service_builder: Callable[[RunnerAssemblyContext], PreflightService],
    observer_builder: Callable[[RunnerAssemblyContext], PipelineObserver],
    postrun_service_builder: Callable[..., PostrunService],
    batch_executor_builder: Callable[..., BatchExecutor],
) -> RunnerAssemblyParts:
    """Assemble runner collaborators before creating the PipelineRunner shell."""
    checkpoint_manager = checkpoint_manager_builder(
        pipeline=context.pipeline,
        logger_port=context.logger_port,
    )
    lifecycle_service = MedallionLifecycleService(
        storage=context.pipeline.services.storage,
        logger=context.logger_port,
    )
    lock_manager = lock_manager_builder(
        context,
        checkpoint_manager=checkpoint_manager,
        context_holder=LockContextHolder(),
    )
    preflight_service = preflight_service_builder(context)
    observer = observer_builder(context)
    postrun_service = postrun_service_builder(
        context,
        lifecycle_service=lifecycle_service,
    )
    batch_executor = batch_executor_builder(
        context,
        checkpoint_manager=checkpoint_manager,
        lock_manager=lock_manager,
        observer=observer,
    )
    return RunnerAssemblyParts(
        checkpoint_manager=checkpoint_manager,
        lifecycle_service=lifecycle_service,
        lock_manager=lock_manager,
        preflight_service=preflight_service,
        postrun_service=postrun_service,
        observer=observer,
        batch_executor=batch_executor,
    )

================================================================================
File: assembler.py
Path: factories\pipeline\assembler.py
================================================================================
"""Thin RF-014 façade for pipeline factory assembly."""

from __future__ import annotations

from typing import TypeVar

from bioetl.application.core.wiring.factory import BasePipeline
from bioetl.composition.factories.datasource.data_source_factory import (
    get_data_source_creator as _rf014_get_data_source_creator,
)
from bioetl.composition.factories.dq.context_resolver import (
    extract_dq_configs as _rf014_extract_dq_configs,
)
from bioetl.composition.factories.pipeline._assembler_factory import (
    GenericPipelineFactory as _GenericPipelineFactory,
)
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    build_factory_services as _rf014_build_factory_services,
)
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    create_pipeline_instance_with_services as _rf014_create_pipeline_instance_with_services,
)
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    extract_entity_type as _rf014_extract_entity_type,
)
from bioetl.composition.factories.pipeline.runner_assembly import (
    assemble_runner_impl as _rf014_assemble_runner_impl,
)

get_data_source_creator = _rf014_get_data_source_creator
build_factory_services = _rf014_build_factory_services
create_pipeline_instance_with_services = _rf014_create_pipeline_instance_with_services
_extract_entity_type = _rf014_extract_entity_type
_extract_dq_configs = _rf014_extract_dq_configs
_assemble_runner_impl = _rf014_assemble_runner_impl
TPipeline = TypeVar("TPipeline", bound=BasePipeline)


class GenericPipelineFactory(_GenericPipelineFactory[TPipeline]):
    def create_transformer(self, *args: object, **kwargs: object) -> object:
        return super().create_transformer(*args, **kwargs)

    def create_with_services(self, *args: object, **kwargs: object) -> object:
        # transformer_class=self.transformer_class stays delegated via helper owners.
        return super().create_with_services(*args, **kwargs)


def create_pipeline_factory(
    *args: object, **kwargs: object
) -> GenericPipelineFactory[object]:
    return GenericPipelineFactory(*args, **kwargs)


def assemble_runner(**kwargs: object) -> object:
    return _assemble_runner_impl(
        dq_configs_extractor=_extract_dq_configs,
        **kwargs,
    )


_RF014_HELPER_OWNERS = (
    get_data_source_creator,
    _extract_dq_configs,
    build_factory_services,
    _assemble_runner_impl,
)

__all__ = [
    "GenericPipelineFactory",
    "_extract_entity_type",
    "assemble_runner",
    "create_pipeline_factory",
]

================================================================================
File: assembler_helpers.py
Path: factories\pipeline\assembler_helpers.py
================================================================================
"""Helper implementations extracted from assembler to keep RF-014 seams thin."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, cast

from bioetl.application.core.wiring.factory import BasePipeline, PipelineRunner
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    _PipelineFactoryContext,
    build_create_pipeline_with_services_request,
    build_pipeline_factory_context,
    create_factory_runner,
)
from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.filtering import InputFilterConfig
from bioetl.domain.ports import DQMonitorPort, LoggerPort, MetricsPort, TracingPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.composition.factories.pipeline.assembler import GenericPipelineFactory
    from bioetl.domain.types import GoldSchemaType

TPipeline = TypeVar("TPipeline", bound=BasePipeline)


def build_factory_context(
    factory: GenericPipelineFactory[TPipeline],
) -> _PipelineFactoryContext:
    """Build typed factory context used by composition helper methods."""
    return build_pipeline_factory_context(
        pipeline_name=factory.pipeline_name,
        create_data_source_fn=factory._create_data_source,
        pipeline_class=cast(type[BasePipeline] | None, factory.pipeline_class),
        provider=factory.provider,
        transformer_class=factory.transformer_class,
        pandera_silver_schema=factory.pandera_silver_schema,
    )


def create_with_services_from_factory(
    factory: GenericPipelineFactory[TPipeline],
    run_id: RunID,
    runtime: RuntimeConfig,
    settings: Settings,
    logger: LoggerPort,
    manifest_id: str | None = None,
    config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
    metrics: MetricsPort | None = None,
    cached_bronze: CachedBronzeContext | None = None,
    *,
    create_pipeline_instance_with_services_fn: object,
) -> TPipeline:
    """Create a typed pipeline instance using shared factory helper plumbing."""
    return cast(
        TPipeline,
        create_pipeline_instance_with_services_fn(
            factory_context=build_factory_context(factory),
            request=build_create_pipeline_with_services_request(
                run_id,
                runtime,
                settings,
                logger,
                manifest_id,
                config_hash,
                dq_contract_compatibility_hash,
                effective_config_artifact_id,
                config,
                filter_config,
                tracer,
                dq_monitor,
                metrics,
                cached_bronze,
            ),
        ),
    )


def create_runner_from_factory(
    factory: GenericPipelineFactory[TPipeline],
    run_id: RunID,
    runtime: RuntimeConfig,
    settings: Settings,
    observability: ObservabilityBundle,
    *,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    manifest_id: str | None = None,
    config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    filter_config: InputFilterConfig | None = None,
    config: PipelineYamlConfig | None = None,
    cached_bronze: CachedBronzeContext | None = None,
    assemble_runner_fn: object,
) -> PipelineRunner:
    """Create a runner using the factory's current bound service constructor."""
    return create_factory_runner(
        pipeline_name=factory.pipeline_name,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        run_id=run_id,
        runtime=runtime,
        settings=settings,
        observability=observability,
        manifest_id=manifest_id,
        config_hash=config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        create_with_services_fn=factory.create_with_services,
        assemble_runner_fn=assemble_runner_fn,
        filter_config=filter_config,
        config=config,
        cached_bronze=cached_bronze,
    )

================================================================================
File: checkpoint_metadata_helpers.py
Path: factories\pipeline\checkpoint_metadata_helpers.py
================================================================================
"""Checkpoint metadata assembly helpers for pipeline runner composition."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders.cached_bronze_snapshot_support import (
    build_cached_bronze_input_snapshot_refs,
)
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
    compute_input_snapshot_identity_fingerprint,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.infrastructure.config import get_settings

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline


def _resolve_run_context_payload(pipeline: BasePipeline) -> object | None:
    """Resolve metadata run_context from pipeline services when available."""
    metadata_coordinator = getattr(pipeline.services, "metadata_coordinator", None)
    if metadata_coordinator is None:
        return None
    return getattr(metadata_coordinator, "run_context", None)


def _coerce_optional_str(value: object | None) -> str | None:
    """Return a string value when present, otherwise None."""
    if value is None:
        return None
    text = str(value)
    return text or None


def _normalize_execution_identity_payload(
    *,
    pipeline_name: str,
    run_type: str,
    pipeline_version: str | None,
    effective_config_hash: str | None,
    dq_contract_compatibility_hash: str | None,
    manifest_id: str | None,
    contract_ref: str | None,
    contract_version: str | None,
    effective_config_artifact_id: str | None,
    exact_replay: bool,
    input_snapshot_fingerprint: str | None,
) -> dict[str, str | None]:
    """Return the canonical checkpoint execution-identity payload."""
    return build_execution_identity_payload(
        pipeline_name=pipeline_name,
        run_type=run_type,
        pipeline_version=pipeline_version,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        contract_ref=contract_ref,
        contract_version=contract_version,
        effective_config_artifact_id=effective_config_artifact_id,
        exact_replay=exact_replay,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
    )


def _resolve_input_snapshot_ids(pipeline: BasePipeline) -> tuple[str, ...]:
    """Resolve cached-Bronze snapshot identities for replay-safe checkpoints."""
    runtime = getattr(pipeline, "runtime", None)
    cached_bronze = None if runtime is None else getattr(runtime, "cached_bronze", None)
    if cached_bronze is None or not getattr(cached_bronze, "enabled", False):
        return ()

    config = getattr(pipeline, "config", None)
    provider = _coerce_optional_str(getattr(config, "provider", None))
    entity = _coerce_optional_str(getattr(config, "entity_type", None))
    if provider is None or entity is None:
        return ()

    settings = get_settings()
    bronze_root = (
        Path(cached_bronze.bronze_path)
        if getattr(cached_bronze, "bronze_path", None)
        else settings.bronze_path / provider / entity
    )
    bronze_date = _coerce_optional_str(getattr(cached_bronze, "bronze_date", None))
    snapshot_refs = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date=bronze_date,
        pipeline_name=pipeline.config.pipeline_name,
    )
    return tuple(snapshot.snapshot_id for snapshot in snapshot_refs)


def build_current_checkpoint_metadata(pipeline: BasePipeline) -> CheckpointMetadata:
    """Build current execution identity metadata for checkpoint compatibility."""
    run_context = _resolve_run_context_payload(pipeline)
    pipeline_version = (
        _coerce_optional_str(getattr(run_context, "pipeline_version", None))
        if run_context is not None
        else None
    )
    effective_config_hash = (
        _coerce_optional_str(getattr(run_context, "config_hash", None))
        if run_context is not None
        else None
    )
    dq_contract_compatibility_hash = (
        _coerce_optional_str(
            getattr(run_context, "dq_contract_compatibility_hash", None)
        )
        if run_context is not None
        else None
    )
    manifest_id = (
        _coerce_optional_str(getattr(run_context, "manifest_id", None))
        if run_context is not None
        else None
    )
    contract_ref = (
        _coerce_optional_str(getattr(run_context, "contract_ref", None))
        if run_context is not None
        else None
    )
    contract_version = (
        _coerce_optional_str(getattr(run_context, "contract_version", None))
        if run_context is not None
        else None
    )
    effective_config_artifact_id = (
        _coerce_optional_str(getattr(run_context, "effective_config_artifact_id", None))
        if run_context is not None
        else None
    )
    composite_run_identity = (
        _coerce_optional_str(getattr(run_context, "composite_run_identity", None))
        if run_context is not None
        else None
    )
    exact_replay = bool(getattr(pipeline.runtime, "exact_replay", False))
    input_snapshot_ids = _resolve_input_snapshot_ids(pipeline)
    input_snapshot_fingerprint = compute_input_snapshot_identity_fingerprint(
        list(input_snapshot_ids)
    )

    run_type = pipeline.runtime.run_type
    run_type_value = run_type.value if hasattr(run_type, "value") else str(run_type)
    identity_payload = _normalize_execution_identity_payload(
        pipeline_name=pipeline.config.pipeline_name,
        run_type=run_type_value,
        pipeline_version=pipeline_version,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        manifest_id=manifest_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        effective_config_artifact_id=effective_config_artifact_id,
        exact_replay=exact_replay,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
    )
    execution_fingerprint = compute_execution_identity_fingerprint(identity_payload)

    return CheckpointMetadata(
        records_processed=0,
        pipeline_name=pipeline.config.pipeline_name,
        run_type=run_type_value,
        dq_contract_compatibility_hash=identity_payload[
            "dq_contract_compatibility_hash"
        ],
        pipeline_version=identity_payload["pipeline_version"],
        effective_config_hash=identity_payload["effective_config_hash"],
        effective_config_artifact_id=effective_config_artifact_id,
        execution_fingerprint=execution_fingerprint,
        composite_run_identity=composite_run_identity,
        manifest_id=manifest_id,
        contract_ref=identity_payload["contract_ref"],
        contract_version=identity_payload["contract_version"],
        exact_replay=exact_replay,
        input_snapshot_ids=input_snapshot_ids,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        run_context={
            "pipeline_name": pipeline.config.pipeline_name,
            "manifest_id": manifest_id,
        },
    )

================================================================================
File: checkpoint_policy_helpers.py
Path: factories\pipeline\checkpoint_policy_helpers.py
================================================================================
"""Helpers for resolving checkpoint compatibility policy in composition."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.domain.ports import LoggerPort

CheckpointCompatibilityPolicy = Literal["observe", "soft_fail", "hard_fail"]
_DEFAULT_CHECKPOINT_COMPATIBILITY_POLICY: CheckpointCompatibilityPolicy = "soft_fail"
_ALLOWED_CHECKPOINT_COMPATIBILITY_POLICIES: tuple[
    CheckpointCompatibilityPolicy, ...
] = (
    "observe",
    "soft_fail",
    "hard_fail",
)


def _resolve_requested_checkpoint_compatibility_policy(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
) -> CheckpointCompatibilityPolicy:
    """Resolve the operator-selected policy before strict replay coercion."""
    settings = getattr(pipeline, "settings", None)
    pipeline_settings = getattr(settings, "pipeline", None)
    control_plane = getattr(pipeline_settings, "control_plane", None)
    raw_policy = getattr(control_plane, "checkpoint_compatibility_policy", None)
    if (
        isinstance(raw_policy, str)
        and raw_policy in _ALLOWED_CHECKPOINT_COMPATIBILITY_POLICIES
    ):
        return cast(CheckpointCompatibilityPolicy, raw_policy)
    if raw_policy is not None:
        logger_port.warning(
            "Unsupported checkpoint compatibility policy in settings; "
            "falling back to soft_fail.",
            pipeline=pipeline.config.pipeline_name,
            policy=raw_policy,
            default=_DEFAULT_CHECKPOINT_COMPATIBILITY_POLICY,
        )
    return _DEFAULT_CHECKPOINT_COMPATIBILITY_POLICY


def resolve_checkpoint_compatibility_policy(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
) -> CheckpointCompatibilityPolicy:
    """Resolve compatibility policy from pipeline runtime settings."""
    requested_policy = _resolve_requested_checkpoint_compatibility_policy(
        pipeline=pipeline,
        logger_port=logger_port,
    )
    runtime = getattr(pipeline, "runtime", None)
    exact_replay = bool(getattr(runtime, "exact_replay", False))
    if exact_replay and requested_policy != "hard_fail":
        logger_port.warning(
            "Exact replay requires hard_fail checkpoint compatibility policy; "
            "coercing requested policy.",
            pipeline=pipeline.config.pipeline_name,
            exact_replay=True,
            requested_policy=requested_policy,
            applied_policy="hard_fail",
        )
        return "hard_fail"
    return requested_policy

================================================================================
File: config_types.py
Path: factories\pipeline\config_types.py
================================================================================
"""Type definitions for pipeline factory registry entries."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base_transformer import BaseTransformer


__all__ = ["PipelineFactoryConfig"]


class PipelineFactoryConfig(NamedTuple):
    """Value object describing one pipeline factory registration."""

    pipeline_name: str
    provider: str
    entity_type: str
    transformer_class: type[BaseTransformer]
    silver_schema: pa.Schema | None
    gold_schema: object
    pandera_silver_schema: object | None = None
    data_source_provider: str | None = None

================================================================================
File: construction.py
Path: factories\pipeline\construction.py
================================================================================
"""Public pipeline-construction helper exports.

Transformer instantiation lives in ``TransformerBuilder.build``, while this
module remains the sanctioned aggregate seam for construction helpers.
"""

from __future__ import annotations

from bioetl.composition.factories.pipeline.construction_types import (
    ContractPolicyLoader,
    DomainConfigMapper,
    EntityTypeExtractor,
)
from bioetl.composition.factories.pipeline.run_context_factory import (
    RunContextFactory,
)
from bioetl.composition.factories.pipeline.transformer_builder import (
    TransformerBuilder,
)
from bioetl.infrastructure.config.domain_config_resolver import (
    DomainConfigResolver,
    resolve_domain_pipeline_config,
)

# Architecture marker: the construction path ultimately instantiates
# ``transformer_class(...)`` inside ``TransformerBuilder.build``.

__all__ = [
    "ContractPolicyLoader",
    "DomainConfigMapper",
    "DomainConfigResolver",
    "EntityTypeExtractor",
    "RunContextFactory",
    "TransformerBuilder",
    "resolve_domain_pipeline_config",
]

================================================================================
File: construction_types.py
Path: factories\pipeline\construction_types.py
================================================================================
"""Typed protocol contracts for pipeline-construction helper modules."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.domain.config import DQConfig, PipelineConfig
    from bioetl.domain.ports import ContractPolicyPort
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class EntityTypeExtractor(Protocol):
    """Callable contract for deriving entity type from pipeline name."""

    def __call__(self, pipeline_name: str) -> str | None:
        """Resolve entity type from pipeline name."""
        ...


class DomainConfigMapper(Protocol):
    """Callable contract for mapping YAML config to domain config."""

    def __call__(
        self,
        yaml_config: PipelineYamlConfig,
        resolved_dq_config: DQConfig | None = None,
    ) -> PipelineConfig:
        """Map YAML config to domain PipelineConfig."""
        ...


class ContractPolicyLoader(Protocol):
    """Callable contract for loading pipeline contract policy."""

    def __call__(self, provider: str, entity: str) -> ContractPolicyPort:
        """Load contract policy for provider/entity."""
        ...


class _SchemaBuilder(Protocol):
    """Protocol for schema classes that can materialize a runtime schema."""

    @classmethod
    def to_schema(cls) -> object:
        """Materialize schema representation."""
        ...

================================================================================
File: contract_validator.py
Path: factories\pipeline\contract_validator.py
================================================================================
"""Assembly wrapper for pipeline contract preflight and factory creation."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.wiring.registry import GenericPipeline
from bioetl.composition.factories.datasource.data_source_factory import (
    get_data_source_creator,
)
from bioetl.composition.factories.pipeline.registry_manifest import (
    PipelineFactoryConfig,
)
from bioetl.composition.providers.provider_registry import ProviderRegistry
from bioetl.domain.types import GoldSchemaType
from bioetl.infrastructure.config import load_pipeline_contract_policy
from bioetl.infrastructure.config.contract_policy_validation import (
    resolve_silver_columns as _resolve_silver_columns_impl,
)
from bioetl.infrastructure.config.contract_policy_validation import (
    schema_columns as _schema_columns_impl,
)
from bioetl.infrastructure.config.contract_policy_validation import (
    validate_pipeline_contract_policy as _validate_pipeline_contract_policy_impl,
)

if TYPE_CHECKING:
    from bioetl.composition.factories.pipeline.assembler import GenericPipelineFactory


def _schema_columns(
    schema_class: object,
) -> set[str]:
    """Compatibility wrapper over canonical schema-column extraction helper."""
    return _schema_columns_impl(schema_class)


def _resolve_silver_columns(config: PipelineFactoryConfig) -> set[str]:
    """Compatibility wrapper over canonical Silver schema resolution helper."""
    return _resolve_silver_columns_impl(
        provider=config.provider,
        entity_type=config.entity_type,
        pandera_silver_schema=config.pandera_silver_schema,
        silver_schema=config.silver_schema,
    )


def _validate_contract_policy(config: PipelineFactoryConfig) -> None:
    """Assembly-scoped wrapper over canonical contract-policy validation."""
    _validate_pipeline_contract_policy_impl(
        provider=config.provider,
        entity_type=config.entity_type,
        pandera_silver_schema=config.pandera_silver_schema,
        silver_schema=config.silver_schema,
        gold_schema=config.gold_schema,
        load_policy=load_pipeline_contract_policy,
    )


def create_factory(
    config: PipelineFactoryConfig,
    *,
    provider_registry: ProviderRegistry | None = None,
) -> GenericPipelineFactory[GenericPipeline]:
    """Create a GenericPipelineFactory from configuration.

    Args:
        config: Pipeline factory configuration

    Returns:
        Configured GenericPipelineFactory instance
    """
    _validate_contract_policy(config)
    from bioetl.composition.factories.pipeline.assembler import (
        GenericPipelineFactory,
    )

    # Resolve data source creator: use data_source_provider override if set
    data_source_creator = (
        get_data_source_creator(
            config.data_source_provider,
            provider_registry=provider_registry,
        )
        if config.data_source_provider
        else None
    )

    return GenericPipelineFactory(
        pipeline_name=config.pipeline_name,
        pipeline_class=GenericPipeline,
        provider=config.provider,
        silver_schema=config.silver_schema,
        gold_schema=cast("GoldSchemaType", config.gold_schema),
        pandera_silver_schema=config.pandera_silver_schema,
        transformer_class=config.transformer_class,
        data_source_creator=data_source_creator,
        provider_registry=provider_registry,
    )


__all__ = [
    "create_factory",
]

================================================================================
File: creation_support.py
Path: factories\pipeline\creation_support.py
================================================================================
"""Public cross-owner support exports for pipeline creation wiring.

This module is the canonical non-private seam for first-party packages that
need creation-wiring contracts and the delegated implementation hook without
importing the private ``_creation_wiring`` module directly.
"""

from __future__ import annotations

from bioetl.composition.factories.pipeline._creation_wiring import (
    _BuildPipelineServicesFn,
    _create_pipeline_with_services_impl,
    _PipelineCreationInputs,
    _PipelineCreationRequest,
    _ServiceBundleDeps,
)

__all__ = [
    "_BuildPipelineServicesFn",
    "_PipelineCreationInputs",
    "_PipelineCreationRequest",
    "_ServiceBundleDeps",
    "_create_pipeline_with_services_impl",
]

================================================================================
File: factory_method_helpers.py
Path: factories\pipeline\factory_method_helpers.py
================================================================================
"""Internal helpers for GenericPipelineFactory orchestration."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import pyarrow as pa

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.core.base_transformer.types import (
    TransformerDependencyContext,
)
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.core.runner import PipelineRunner
from bioetl.composition.factories.pipeline._factory_method_control_plane import (
    apply_optional_control_plane_kwargs as _apply_optional_control_plane_kwargs,
)
from bioetl.composition.factories.pipeline._factory_method_control_plane import (
    resolve_strict_gold_validation as _resolve_strict_gold_validation,
)
from bioetl.composition.factories.pipeline._factory_method_runtime_support import (
    create_factory_runner_from_request,
    create_pipeline_instance_from_request,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    _BuildFactoryServicesRequest,
    _CreatePipelineWithServicesRequest,
    _PipelineFactoryContext,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    build_create_pipeline_with_services_request as _build_create_pipeline_with_services_request,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    build_pipeline_factory_context as _build_pipeline_factory_context,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    create_factory_data_source as _create_factory_data_source,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    extract_entity_type as _extract_entity_type_helper,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    resolve_data_source_creator as _resolve_data_source_creator,
)
from bioetl.composition.factories.pipeline.transformer_dependencies import (
    build_transformer_dependencies,
)
from bioetl.composition.factories.services.bundle import (
    build_pipeline_services,
    create_pipeline_with_services,
)
from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.filtering import (
    GoldFilterConfig,
    InputFilterConfig,
    SilverFilterConfig,
)
from bioetl.domain.ports import (
    ContractPolicyPort,
    DataNormalizationPort,
    MetricsPort,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.services import IdentityService
from bioetl.domain.types import GoldSchemaType, RunID
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

TPipeline = TypeVar("TPipeline", bound="BasePipeline")
build_create_pipeline_with_services_request = (
    _build_create_pipeline_with_services_request
)
build_pipeline_factory_context = _build_pipeline_factory_context
create_factory_data_source = _create_factory_data_source
extract_entity_type = _extract_entity_type_helper
resolve_data_source_creator = _resolve_data_source_creator


def create_transformer_instance(
    *,
    transformer_class: type[BaseTransformer] | None,
    provider: str,
    pipeline_name: str,
    extract_entity_type: Callable[[str], str | None],
    tracer: TracingPort | None = None,
    metrics: MetricsPort | None = None,
    silver_filters: SilverFilterConfig | None = None,
    gold_filters: GoldFilterConfig | None = None,
    identity_service: IdentityService | None = None,
    pii_hasher: PiiHasherPort | None = None,
    data_normalizer: DataNormalizationPort | None = None,
    contract_policy: ContractPolicyPort | None = None,
    dependencies: TransformerDependencyContext | None = None,
) -> BaseTransformer | None:
    """Create transformer instance with resolved dependency context."""
    if transformer_class is None:
        return None

    resolved_entity_type = extract_entity_type(pipeline_name)
    resolved_dependencies = (
        dependencies
        if dependencies is not None
        else build_transformer_dependencies(
            provider=provider,
            entity_type=resolved_entity_type,
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
            contract_policy=contract_policy,
        )
    )
    return transformer_class(
        provider=provider,
        entity_type=resolved_entity_type,
        silver_filters=silver_filters,
        gold_filters=gold_filters,
        dependencies=resolved_dependencies,
    )


def build_factory_services(
    *,
    factory_context: _PipelineFactoryContext,
    request: _BuildFactoryServicesRequest,
) -> PipelineService:
    """Build shared pipeline services from context and runtime request values."""
    return build_pipeline_services(
        pipeline_name=factory_context.pipeline_name,
        create_data_source_fn=factory_context.create_data_source_fn,
        settings=request.settings,
        logger=request.logger,
        config=request.config,
        filter_config=request.filter_config,
        tracer=request.tracer,
        dq_monitor=request.dq_monitor,
    )


def create_pipeline_instance_with_services(
    *,
    factory_context: _PipelineFactoryContext,
    request: _CreatePipelineWithServicesRequest,
) -> BasePipeline:
    return create_pipeline_instance_from_request(
        factory_context=factory_context,
        request=request,
        create_pipeline_with_services_fn=create_pipeline_with_services,
        apply_optional_control_plane_kwargs_fn=_apply_optional_control_plane_kwargs,
    )


def create_factory_runner(
    *,
    pipeline_name: str,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    run_id: RunID,
    runtime: RuntimeConfig,
    settings: Settings,
    observability: ObservabilityBundle,
    manifest_id: str | None = None,
    config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    create_with_services_fn: Callable[..., TPipeline],
    assemble_runner_fn: Callable[..., PipelineRunner],
    filter_config: InputFilterConfig | None = None,
    config: PipelineYamlConfig | None = None,
    cached_bronze: CachedBronzeContext | None = None,
) -> PipelineRunner:
    yaml_config = config or load_pipeline_config(pipeline_name)
    return create_factory_runner_from_request(
        pipeline_name=pipeline_name,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        run_id=run_id,
        runtime=runtime,
        settings=settings,
        observability=observability,
        yaml_config=yaml_config,
        manifest_id=manifest_id,
        config_hash=config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        create_with_services_fn=create_with_services_fn,
        assemble_runner_fn=assemble_runner_fn,
        filter_config=filter_config,
        cached_bronze=cached_bronze,
        apply_optional_control_plane_kwargs_fn=_apply_optional_control_plane_kwargs,
        resolve_strict_gold_validation_fn=_resolve_strict_gold_validation,
    )

================================================================================
File: postrun_assembly.py
Path: factories\pipeline\postrun_assembly.py
================================================================================
"""Postrun assembly helpers for pipeline factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.postrun import (
    PostrunCleanupService,
    PostrunCompactService,
    PostrunDependencyContext,
    PostrunDQReportService,
    PostrunMetadataVersionResolver,
    PostrunMetadataWriteService,
    PostrunService,
)
from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.composition.factories.services.common_service_wiring import resolve_tracer
from bioetl.domain.context import PipelineContext
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.ports import MetadataCoordinatorPort, MetadataWriterPort

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.ports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        LoggerPort,
        SilverDQConfigPort,
        StorageMaintenancePort,
        TracingPort,
    )


_POSTRUN_WARNING_ALLOWLIST = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
)
_METADATA_VERSION_ALLOWLIST = (
    FileNotFoundError,
    OSError,
    RuntimeError,
    ValueError,
)


def build_postrun_dependency_context(
    *,
    config: PipelineConfig,
    runtime: RuntimeConfig,
    context: PipelineContext,
    storage: StorageMaintenancePort,
    logger_port: LoggerPort,
    dq_report_service: DQReportService | None = None,
    bronze_dq_config: BronzeDQConfigPort | None = None,
    silver_dq_config: SilverDQConfigPort | None = None,
    gold_dq_config: GoldDQConfigPort | None = None,
    metadata_coordinator: MetadataCoordinatorPort | None = None,
    metadata_writer: MetadataWriterPort | None = None,
) -> PostrunDependencyContext:
    """Build the shared postrun collaborator graph for production and tests."""
    metadata_version_resolver = PostrunMetadataVersionResolver(
        logger=logger_port,
        runtime=runtime,
        storage=storage,
        warning_allowlist=_METADATA_VERSION_ALLOWLIST,
    )
    return PostrunDependencyContext(
        cleanup_orchestrator=PostrunCleanupService(
            logger=logger_port,
            warning_allowlist=_POSTRUN_WARNING_ALLOWLIST,
        ),
        dq_report_orchestrator=PostrunDQReportService(
            logger=logger_port,
            runtime=runtime,
            dq_report_service=dq_report_service,
            bronze_dq_config=bronze_dq_config,
            silver_dq_config=silver_dq_config,
            gold_dq_config=gold_dq_config,
            warning_allowlist=_POSTRUN_WARNING_ALLOWLIST,
        ),
        metadata_write_orchestrator=PostrunMetadataWriteService(
            config=config,
            runtime=runtime,
            context=context,
            storage=storage,
            metadata_coordinator=metadata_coordinator,
            metadata_writer=metadata_writer,
            metadata_version_resolver=metadata_version_resolver,
        ),
        compact_orchestrator=PostrunCompactService(
            config=config,
            storage=storage,
            logger=logger_port,
            warning_allowlist=_POSTRUN_WARNING_ALLOWLIST,
        ),
    )


def _build_pipeline_dq_service(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
) -> DataQualityService:
    """Build the pipeline-scoped DataQualityService from outer wiring."""
    return DataQualityService(
        dq_monitor=pipeline.services.dq_monitor,
        config=pipeline.config.dq,
        logger=logger_port,
        metrics=pipeline.services.metrics,
        pipeline_name=pipeline.config.pipeline_name,
        entity_type=pipeline.config.entity_type,
    )


def _build_pipeline_postrun_dependencies(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
    dq_configs: DQConfigsContext,
) -> PostrunDependencyContext:
    """Build postrun dependencies from pipeline services and DQ config seams."""
    return build_postrun_dependency_context(
        config=pipeline.config,
        runtime=pipeline.runtime,
        context=pipeline.context,
        storage=pipeline.services.storage,
        logger_port=logger_port,
        dq_report_service=pipeline.services.dq_report_service,
        bronze_dq_config=dq_configs.bronze,
        silver_dq_config=dq_configs.silver,
        gold_dq_config=dq_configs.gold,
        metadata_coordinator=pipeline.services.metadata_coordinator,
        metadata_writer=pipeline.services.metadata_writer,
    )


def build_postrun_service(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
    lifecycle_service: MedallionLifecycleService,
    dq_configs: DQConfigsContext,
    tracer: TracingPort | None = None,
) -> PostrunService:
    """Build the postrun service and its collaborators in the composition layer."""
    resolved_tracer = resolve_tracer(tracer)
    dq_service = _build_pipeline_dq_service(
        pipeline=pipeline,
        logger_port=logger_port,
    )
    dependencies = _build_pipeline_postrun_dependencies(
        pipeline=pipeline,
        logger_port=logger_port,
        dq_configs=dq_configs,
    )
    return PostrunService(
        config=pipeline.config,
        runtime=pipeline.runtime,
        context=pipeline.context,
        dq_service=dq_service,
        lifecycle_service=lifecycle_service,
        dependencies=dependencies,
        tracer=resolved_tracer,
        storage=pipeline.services.storage,
        metrics=pipeline.services.metrics,
        logger=logger_port,
    )

================================================================================
File: registry.py
Path: factories\pipeline\registry.py
================================================================================
"""Consolidated pipeline factory definitions and registration helpers."""

from __future__ import annotations

import threading
from types import MappingProxyType
from typing import cast

from bioetl.application.core.wiring.registry import GenericPipeline
from bioetl.composition import PipelineRegistry, get_default_registry
from bioetl.composition.factories.pipeline.assembler import (
    GenericPipelineFactory,
)
from bioetl.composition.factories.pipeline.contract_validator import create_factory
from bioetl.composition.factories.pipeline.registry_manifest import (
    PIPELINE_CONFIGS,
)
from bioetl.domain.ports import PipelineFactoryPort


def _build_factories() -> dict[str, GenericPipelineFactory[GenericPipeline]]:
    """Build factory instances from the canonical pipeline config table."""
    return {config.pipeline_name: create_factory(config) for config in PIPELINE_CONFIGS}


# Backward-compatible module surface kept for tests/importers, but frozen to
# avoid additional module-level mutable registry state.
_factories = MappingProxyType(_build_factories())

# Export individual factories for backward compatibility
chembl_activity_factory = _factories["chembl_activity"]
chembl_assay_factory = _factories["chembl_assay"]
chembl_assay_parameters_factory = _factories["chembl_assay_parameters"]
chembl_cell_line_factory = _factories["chembl_cell_line"]
chembl_compound_record_factory = _factories["chembl_compound_record"]
chembl_publication_factory = _factories["chembl_publication"]
chembl_publication_similarity_factory = _factories["chembl_publication_similarity"]
chembl_publication_term_factory = _factories["chembl_publication_term"]
chembl_molecule_factory = _factories["chembl_molecule"]
chembl_target_factory = _factories["chembl_target"]
chembl_target_component_factory = _factories["chembl_target_component"]
chembl_tissue_factory = _factories["chembl_tissue"]
chembl_subcellular_fraction_factory = _factories["chembl_subcellular_fraction"]
chembl_protein_class_factory = _factories["chembl_protein_class"]
pubchem_compound_factory = _factories["pubchem_compound"]
uniprot_protein_factory = _factories["uniprot_protein"]
uniprot_idmapping_factory = _factories["uniprot_idmapping"]
pubmed_publication_factory = _factories["pubmed_publication"]
crossref_publication_factory = _factories["crossref_publication"]
openalex_publication_factory = _factories["openalex_publication"]
semanticscholar_publication_factory = _factories["semanticscholar_publication"]


class _PipelineFactoryRegistrationState:
    """Thread-safe default-registration state holder.

    This keeps mutable registration state instance-scoped and lazily created,
    mirroring the project-wide registry hardening pattern without changing the
    existing module-level helper API.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._registered = False


_default_registration_state: _PipelineFactoryRegistrationState | None = None


def _get_default_registration_state() -> _PipelineFactoryRegistrationState:
    """Get the lazy default registration-state singleton."""
    global _default_registration_state
    if _default_registration_state is None:
        _default_registration_state = _PipelineFactoryRegistrationState()
    return _default_registration_state


def _register_to_explicit_registry(registry: PipelineRegistry) -> None:
    """Register factories into an explicit registry instance."""
    _register_factories_to(registry)


def _register_default_registry_once(
    registration_state: _PipelineFactoryRegistrationState,
) -> None:
    """Register factories into the default registry exactly once."""
    if registration_state._registered:
        return
    with registration_state._lock:
        if registration_state._registered:
            return
        _register_factories_to(get_default_registry())
        registration_state._registered = True


def register_all_pipelines(registry: PipelineRegistry | None = None) -> None:
    """Explicitly register all pipeline factories with PipelineRegistry.

    This function is idempotent and thread-safe - calling it multiple times
    or from multiple threads has no effect after the first successful call.

    Uses double-checked locking pattern to minimize lock contention while
    ensuring thread-safe initialization.

    When called with a custom registry, registration is still safe to repeat:
    already-registered pipeline names are skipped and only missing factories
    are added.

    Args:
        registry: Optional PipelineRegistry instance. If None, uses the
            default global registry. Pass a custom registry for test isolation.

    Should be called once at application startup (e.g., in cli.py or bootstrap.py).
    """
    if registry is not None:
        _register_to_explicit_registry(registry)
        return

    _register_default_registry_once(_get_default_registration_state())


def _register_factories_to(registry: PipelineRegistry) -> None:
    """Register all factory instances to the given registry.

    Internal helper for register_all_pipelines().
    Uses loop over _factories dict for DRY registration.

    Args:
        registry: Target registry instance.
    """
    registered_pipelines = set(registry.list_pipelines())
    for pipeline_name, factory in _factories.items():
        if pipeline_name in registered_pipelines:
            continue
        registry.register_factory(cast("PipelineFactoryPort", factory))


def _list_pipeline_names() -> list[str]:
    """Return available pipeline names in canonical sorted order."""
    return sorted(_factories.keys())


def is_registered() -> bool:
    """Check if factories have been registered.

    Thread-safe check of registration state.

    Returns:
        True if register_all_pipelines() has been called.
    """
    return _get_default_registration_state()._registered


def reset_registration() -> None:
    """Reset registration state (for testing only).

    Thread-safe reset of registration flag. Also clears the default PipelineRegistry.
    WARNING: Only use in tests. Not for production.

    Note: For isolated tests, prefer creating a new registry instance with
    create_registry() rather than using reset_registration().
    """
    registration_state = _get_default_registration_state()
    with registration_state._lock:
        get_default_registry().clear()
        registration_state._registered = False


def get_factory(pipeline_name: str) -> GenericPipelineFactory[GenericPipeline]:
    """Get a pipeline factory by name.

    Convenience function for accessing factories without going through registry.

    Args:
        pipeline_name: Name of the pipeline (e.g., "chembl_activity")

    Returns:
        GenericPipelineFactory instance

    Raises:
        KeyError: If pipeline_name is not found
    """
    if pipeline_name not in _factories:
        available = _list_pipeline_names()
        raise KeyError(f"Unknown pipeline: {pipeline_name}. Available: {available}")
    return _factories[pipeline_name]


def list_available_pipelines() -> list[str]:
    """List all available pipeline names.

    Returns:
        Sorted list of pipeline names
    """
    return _list_pipeline_names()


_PIPELINE_FACTORY_API = (
    get_factory,
    list_available_pipelines,
    reset_registration,
)

__all__ = [
    "chembl_activity_factory",
    "chembl_assay_factory",
    "chembl_assay_parameters_factory",
    "chembl_cell_line_factory",
    "chembl_compound_record_factory",
    "chembl_molecule_factory",
    "chembl_protein_class_factory",
    "chembl_publication_factory",
    "chembl_publication_similarity_factory",
    "chembl_publication_term_factory",
    "chembl_subcellular_fraction_factory",
    "chembl_target_component_factory",
    "chembl_target_factory",
    "chembl_tissue_factory",
    "crossref_publication_factory",
    "get_factory",
    "is_registered",
    "list_available_pipelines",
    "openalex_publication_factory",
    "pubchem_compound_factory",
    "pubmed_publication_factory",
    "register_all_pipelines",
    "reset_registration",
    "semanticscholar_publication_factory",
    "uniprot_idmapping_factory",
    "uniprot_protein_factory",
]

================================================================================
File: registry_manifest.py
Path: factories\pipeline\registry_manifest.py
================================================================================
"""Canonical pipeline registry manifest for composition-layer assembly."""

from __future__ import annotations

from bioetl.composition.factories.pipeline._registry_manifest_chembl import (
    CHEMBL_PIPELINE_CONFIGS,
)
from bioetl.composition.factories.pipeline._registry_manifest_non_chembl import (
    NON_CHEMBL_PIPELINE_CONFIGS,
)
from bioetl.composition.factories.pipeline.config_types import PipelineFactoryConfig

PIPELINE_CONFIGS: tuple[PipelineFactoryConfig, ...] = (
    *CHEMBL_PIPELINE_CONFIGS,
    *NON_CHEMBL_PIPELINE_CONFIGS,
)

__all__ = [
    "PIPELINE_CONFIGS",
    "PipelineFactoryConfig",
]

================================================================================
File: run_context_factory.py
Path: factories\pipeline\run_context_factory.py
================================================================================
"""Run-context assembly helpers for pipeline construction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from bioetl.composition.factories.pipeline.construction_types import (
    EntityTypeExtractor,
)
from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_git_commit,
    get_pipeline_version,
)
from bioetl.domain.value_objects.run_context import RunContext

if TYPE_CHECKING:
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _get_transform_version(yaml_config: PipelineYamlConfig) -> str | None:
    """Extract transform version from resolved pipeline YAML config."""
    transform = getattr(yaml_config, "transform", None)
    version = getattr(transform, "version", None)
    return str(version) if version is not None else None


def _get_transform_steps(yaml_config: PipelineYamlConfig) -> tuple[str, ...]:
    """Extract transform steps from resolved pipeline YAML config."""
    transform = getattr(yaml_config, "transform", None)
    steps = getattr(transform, "steps", ())
    return tuple(str(step) for step in (steps or ()))


def _coerce_optional_text(value: object) -> str | None:
    """Return normalized non-empty text when available."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_contract_identity_snapshot(
    provider: str,
    entity: str,
) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Resolve contract identity fields from the canonical registry."""
    contract_ref = f"{provider}.{entity}"
    registry_path = Path("configs/base/contract_registry.yaml")
    if not registry_path.exists():
        return contract_ref, None, None, None, None
    try:
        payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return contract_ref, None, None, None, None
    if not isinstance(payload, dict):
        return contract_ref, None, None, None, None
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        return contract_ref, None, None, None, None
    entry = entries.get(contract_ref)
    if not isinstance(entry, dict):
        return contract_ref, None, None, None, None
    identity = entry.get("identity")
    identity_payload = identity if isinstance(identity, dict) else {}
    contract_version = _coerce_optional_text(identity_payload.get("contract_version"))
    contract_schema_hash = _coerce_optional_text(identity_payload.get("schema_hash"))
    dq_policy_ref = _coerce_optional_text(
        identity_payload.get("dq_policy_ref") or entry.get("dq_policy_ref")
    )
    rule_bundle_version = _coerce_optional_text(
        identity_payload.get("rule_bundle_version") or entry.get("rule_bundle_version")
    )
    return (
        contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    )


@dataclass(frozen=True, slots=True)
class RunContextFactory:
    """Build ``RunContext`` for metadata coordinator wiring."""

    pipeline_name: str
    provider: str
    entity_type_extractor: EntityTypeExtractor
    pipeline_version_getter: Callable[[PipelineYamlConfig], str] = get_pipeline_version
    git_commit_getter: Callable[[], str | None] = get_git_commit
    config_hash_getter: Callable[[PipelineYamlConfig], str] = compute_config_hash
    transform_version_getter: Callable[[PipelineYamlConfig], str | None] = (
        _get_transform_version
    )
    transform_steps_getter: Callable[[PipelineYamlConfig], tuple[str, ...]] = (
        _get_transform_steps
    )
    contract_identity_resolver: Callable[
        [str, str], tuple[str, str | None, str | None, str | None, str | None]
    ] = _resolve_contract_identity_snapshot

    def create(
        self,
        *,
        run_id: RunID,
        runtime: RuntimeConfig,
        yaml_config: PipelineYamlConfig,
        manifest_id: str | None = None,
        config_hash: str | None = None,
        dq_contract_compatibility_hash: str | None = None,
        effective_config_artifact_id: str | None = None,
    ) -> RunContext:
        """Create metadata ``RunContext`` from runtime and resolved YAML."""
        entity = self.entity_type_extractor(self.pipeline_name) or self.pipeline_name
        (
            contract_ref,
            contract_version,
            contract_schema_hash,
            dq_policy_ref,
            rule_bundle_version,
        ) = self.contract_identity_resolver(self.provider, entity)
        resolved_config_hash = (
            self.config_hash_getter(yaml_config) if config_hash is None else config_hash
        )
        return RunContext.create(
            run_id=run_id,
            run_type=runtime.run_type,
            started_at=datetime.now(UTC),
            provider=self.provider,
            entity=entity,
            transform_version=self.transform_version_getter(yaml_config),
            transform_steps=self.transform_steps_getter(yaml_config),
            pipeline_version=self.pipeline_version_getter(yaml_config),
            git_commit=self.git_commit_getter(),
            config_hash=resolved_config_hash,
            manifest_id=manifest_id,
            contract_ref=contract_ref,
            contract_version=contract_version,
            contract_schema_hash=contract_schema_hash,
            dq_policy_ref=dq_policy_ref,
            rule_bundle_version=rule_bundle_version,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            effective_config_artifact_id=effective_config_artifact_id,
        )

================================================================================
File: runner.py
Path: factories\pipeline\runner.py
================================================================================
"""Runner factory implementation for composition layer.

Implements RunnerFactoryPort and MetricsExtractorPort protocols
for the PipelineRunnerService.

This module provides the composition-layer implementation of runner
creation, allowing the application layer to remain independent of
bootstrap details.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.composition import PipelineRegistry, create_registry
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.runtime_builders.runner_builder import build_pipeline_runner

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import (
        ExecutionMetricsReadablePort,
        ExecutionMetricsRunnerPort,
    )


__all__ = [
    "MetricsExtractor",
    "RunnerFactory",
    "create_metrics_extractor",
    "create_runner_factory",
]


def _require_execution_metrics_runner(
    runner: object,
) -> ExecutionMetricsRunnerPort:
    """Validate that a producer returned a metrics-readable runnable."""
    from bioetl.domain.ports import ExecutionMetricsRunnerPort

    if not isinstance(runner, ExecutionMetricsRunnerPort):
        raise TypeError("Runner does not implement ExecutionMetricsRunnerPort")
    return runner


class RunnerFactory:
    """Factory for creating pipeline runners.

    Implements RunnerFactoryPort protocol for PipelineRunnerService.
    Delegates to build_pipeline_runner() for actual runner creation.

    Attributes:
        registry: Optional custom registry for test isolation.
    """

    def __init__(
        self,
        registry: PipelineRegistry | None = None,
        registry_factory: Callable[[], PipelineRegistry] | None = None,
        runner_builder: Callable[..., ExecutionMetricsRunnerPort] | None = None,
        ensure_providers_loaded_fn: Callable[[], None] = ensure_providers_loaded,
    ) -> None:
        """Initialize the factory.

        Args:
            registry: Optional custom registry. If None, a fresh registry is
                created lazily for this factory instance.
            registry_factory: Optional registry factory for DI/testing when no
                explicit registry is supplied.
            runner_builder: Optional runner assembly function for DI/testing.
        """
        self._registry = registry
        self._registry_factory = registry_factory or create_registry
        self._runner_builder = runner_builder
        self._ensure_providers_loaded_fn = ensure_providers_loaded_fn
        self._registrations_done = False

    def _ensure_registrations(self) -> None:
        """Ensure all providers and pipelines are registered.

        Idempotent - safe to call multiple times.
        """
        if not self._registrations_done:
            self._ensure_providers_loaded_fn()
            if not self._effective_registry.list_pipelines():
                register_all_pipelines(registry=self._effective_registry)
            self._registrations_done = True

    @property
    def _effective_registry(self) -> PipelineRegistry:
        """Get the effective registry instance."""
        if self._registry is None:
            self._registry = self._registry_factory()
        return self._registry

    def create(self, context: PipelineRunContext) -> ExecutionMetricsRunnerPort:
        """Create a configured pipeline runner.

        Args:
            context: Pipeline run context containing all execution parameters.

        Returns:
            PipelineRunner ready for execution.

        Raises:
            ValueError: If pipeline name is unknown or config is invalid.
            FileNotFoundError: If pipeline config file is missing.
        """
        self._ensure_registrations()
        runner_builder = self._runner_builder or build_pipeline_runner
        runner = runner_builder(context, registry=self._effective_registry)
        return _require_execution_metrics_runner(runner)

    def list_pipelines(self) -> list[str]:
        """List all available pipeline names.

        Returns:
            Sorted list of registered pipeline names.
        """
        self._ensure_registrations()
        return self._effective_registry.list_pipelines()

    def contains(self, pipeline_name: str) -> bool:
        """Check if a pipeline is registered.

        Args:
            pipeline_name: Name of the pipeline to check.

        Returns:
            True if pipeline exists, False otherwise.
        """
        self._ensure_registrations()
        return bool(self._effective_registry.contains(pipeline_name))


class MetricsExtractor:
    """Extractor for pipeline execution metrics.

    Implements MetricsExtractorPort protocol for PipelineRunnerService.
    Extracts metrics from the runner's public execution-metrics contract.
    """

    def extract_metrics(self, runner: ExecutionMetricsReadablePort) -> dict[str, int]:
        """Extract execution metrics from a runner.

        Args:
            runner: Runner to extract metrics from.

        Returns:
            Dictionary with metric names and values.
        """
        try:
            metrics = runner.execution_metrics
        except AttributeError as error:
            raise TypeError(
                "Runner does not expose a valid execution_metrics mapping"
            ) from error
        if not isinstance(metrics, dict):
            raise TypeError("Runner does not expose a valid execution_metrics mapping")

        return {
            "records_fetched": int(metrics["records_fetched"]),
            "records_bronze": int(metrics["records_bronze"]),
            "records_silver": int(metrics["records_silver"]),
            "records_gold": int(metrics["records_gold"]),
            "records_quarantined": int(metrics["records_quarantined"]),
            "records_filtered_out": int(metrics.get("records_filtered_out", 0)),
        }


def create_runner_factory(
    registry: PipelineRegistry | None = None,
    registry_factory: Callable[[], PipelineRegistry] | None = None,
    runner_builder: Callable[..., ExecutionMetricsRunnerPort] | None = None,
    ensure_providers_loaded_fn: Callable[[], None] = ensure_providers_loaded,
) -> RunnerFactory:
    """Create a new RunnerFactory instance.

    Args:
        registry: Optional custom registry for test isolation.
        registry_factory: Optional registry factory used when ``registry`` is not
            provided.
        runner_builder: Optional runner assembly function for DI/testing.
        ensure_providers_loaded_fn: Optional runtime provider bootstrap callable.

    Returns:
        RunnerFactory instance.
    """
    return RunnerFactory(
        registry=registry,
        registry_factory=registry_factory,
        runner_builder=runner_builder,
        ensure_providers_loaded_fn=ensure_providers_loaded_fn,
    )


def create_metrics_extractor() -> MetricsExtractor:
    """Create a new MetricsExtractor instance.

    Returns:
        MetricsExtractor instance.
    """
    return MetricsExtractor()

================================================================================
File: runner_assembly.py
Path: factories\pipeline\runner_assembly.py
================================================================================
"""Runner assembly helper for pipeline factory."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from bioetl.application.services.checkpoint_compatibility_service import (
    CheckpointCompatibilityService,
)
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.composition.factories.pipeline._runner_assembly_support import (
    RunnerAssemblyContext as _RunnerAssemblyContext,
)
from bioetl.composition.factories.pipeline._runner_assembly_support import (
    build_batch_executor as _build_batch_executor_impl,
)
from bioetl.composition.factories.pipeline._runner_assembly_support import (
    build_lock_manager as _build_lock_manager_impl,
)
from bioetl.composition.factories.pipeline._runner_assembly_support import (
    build_observer as _build_observer_impl,
)
from bioetl.composition.factories.pipeline._runner_assembly_support import (
    build_preflight_service as _build_preflight_service_impl,
)
from bioetl.composition.factories.pipeline._runner_assembly_support import (
    build_runner_constructor_payload as _build_runner_constructor_payload_impl,
)
from bioetl.composition.factories.pipeline.checkpoint_metadata_helpers import (
    build_current_checkpoint_metadata,
)
from bioetl.composition.factories.pipeline.checkpoint_policy_helpers import (
    resolve_checkpoint_compatibility_policy,
)
from bioetl.composition.factories.pipeline.postrun_assembly import build_postrun_service
from bioetl.composition.factories.pipeline.runner_constructor import (
    RunnerAssemblyParts,
    create_pipeline_runner_from_payload,
)
from bioetl.composition.factories.services.factory import ServicesBuilder
from bioetl.domain.locking import LockContextHolder
from bioetl.domain.medallion import LoadingStrategy
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.lifecycle import (
        CheckpointManagerService,
        LockCoordinator,
    )
    from bioetl.application.core.postrun import PostrunService
    from bioetl.application.core.preflight import PreflightService
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.observability.observer import PipelineObserver
    from bioetl.composition.factories.pipeline.runner_constructor import (
        RunnerConstructorPayload,
    )
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import GoldSchemaType
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = ["assemble_runner_impl"]


def _build_checkpoint_manager(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
) -> CheckpointManagerService:
    current_metadata = _build_current_checkpoint_metadata(pipeline)
    compatibility_service = CheckpointCompatibilityService(
        logger=logger_port,
        metrics=pipeline.services.metrics,
        pipeline_name=pipeline.config.pipeline_name,
    )
    compatibility_policy = resolve_checkpoint_compatibility_policy(
        pipeline=pipeline,
        logger_port=logger_port,
    )
    return ServicesBuilder.create_checkpoint_manager(
        checkpoint_port=pipeline.services.checkpoint,
        logger=logger_port,
        pipeline_name=pipeline.config.pipeline_name,
        run_id=pipeline.run_id,
        resume=pipeline.runtime.resume,
        loading_strategy=cast(LoadingStrategy | None, pipeline.config.loading_strategy),
        metrics=pipeline.services.metrics,
        checkpoint_compatibility_service=compatibility_service,
        current_metadata=current_metadata,
        compatibility_policy=compatibility_policy,
    )


def _build_current_checkpoint_metadata(pipeline: BasePipeline) -> CheckpointMetadata:
    return build_current_checkpoint_metadata(pipeline)


def _build_lock_manager(
    context: _RunnerAssemblyContext,
    *,
    checkpoint_manager: CheckpointManagerService,
    context_holder: LockContextHolder,
) -> LockCoordinator:
    return _build_lock_manager_impl(
        context,
        checkpoint_manager=checkpoint_manager,
        context_holder=context_holder,
    )


def _build_preflight_service(
    context: _RunnerAssemblyContext,
) -> PreflightService:
    return _build_preflight_service_impl(context)


def _build_observer(
    context: _RunnerAssemblyContext,
) -> PipelineObserver:
    return _build_observer_impl(context)


def _build_batch_executor(
    context: _RunnerAssemblyContext,
    *,
    checkpoint_manager: CheckpointManagerService,
    lock_manager: LockCoordinator,
    observer: PipelineObserver,
) -> BatchExecutor:
    return _build_batch_executor_impl(
        context,
        checkpoint_manager=checkpoint_manager,
        lock_manager=lock_manager,
        observer=observer,
    )


def _build_postrun_service_for_pipeline(
    context: _RunnerAssemblyContext,
    *,
    lifecycle_service: MedallionLifecycleService,
) -> PostrunService:
    dq_configs = context.dq_configs_extractor(context.yaml_config)
    return build_postrun_service(
        pipeline=context.pipeline,
        logger_port=context.logger_port,
        lifecycle_service=lifecycle_service,
        dq_configs=dq_configs,
        tracer=context.observability.tracer,
    )


def _create_pipeline_runner(
    payload: RunnerConstructorPayload,
) -> PipelineRunner:
    return create_pipeline_runner_from_payload(payload)


def _build_runner_constructor_payload(
    *,
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    parts: RunnerAssemblyParts,
) -> RunnerConstructorPayload:
    return _build_runner_constructor_payload_impl(
        pipeline=pipeline,
        observability=observability,
        parts=parts,
    )


def _assemble_runner_parts(
    context: _RunnerAssemblyContext,
) -> RunnerAssemblyParts:
    checkpoint_manager = _build_checkpoint_manager(
        pipeline=context.pipeline,
        logger_port=context.logger_port,
    )
    lifecycle_service = MedallionLifecycleService(
        storage=context.pipeline.services.storage,
        logger=context.logger_port,
    )
    lock_manager = _build_lock_manager(
        context,
        checkpoint_manager=checkpoint_manager,
        context_holder=LockContextHolder(),
    )
    preflight_service = _build_preflight_service(context)
    observer = _build_observer(context)
    postrun_service = _build_postrun_service_for_pipeline(
        context,
        lifecycle_service=lifecycle_service,
    )
    batch_executor = _build_batch_executor(
        context,
        checkpoint_manager=checkpoint_manager,
        lock_manager=lock_manager,
        observer=observer,
    )
    return RunnerAssemblyParts(
        checkpoint_manager=checkpoint_manager,
        lifecycle_service=lifecycle_service,
        lock_manager=lock_manager,
        preflight_service=preflight_service,
        postrun_service=postrun_service,
        observer=observer,
        batch_executor=batch_executor,
    )


def assemble_runner_impl(
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    strict_gold_validation: bool,
    dq_configs_extractor: Callable[
        [PipelineYamlConfig | None],
        DQConfigsContext,
    ],
    yaml_config: PipelineYamlConfig | None = None,
) -> PipelineRunner:
    """Assemble the fully wired PipelineRunner for one configured pipeline."""
    assembly_context = _RunnerAssemblyContext(
        pipeline=pipeline,
        observability=observability,
        logger_port=observability.logger,
        yaml_config=yaml_config,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=strict_gold_validation,
        dq_configs_extractor=dq_configs_extractor,
    )
    assembly_parts = _assemble_runner_parts(assembly_context)
    constructor_payload = _build_runner_constructor_payload(
        pipeline=pipeline,
        observability=observability,
        parts=assembly_parts,
    )
    return _create_pipeline_runner(constructor_payload)

================================================================================
File: runner_constructor.py
Path: factories\pipeline\runner_constructor.py
================================================================================
# mypy: disable-error-code="attr-defined"
"""Runner construction helpers for pipeline factory assembly."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.core.wiring.factory import (
    BasePipeline,
    BatchExecutor,
    CheckpointManagerService,
    LockCoordinator,
    PipelineRunner,
    PipelineRunnerDependencies,
    PostrunService,
    PreflightService,
)
from bioetl.application.observability.observer import PipelineObserver
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.factories.services.common_service_wiring import resolve_tracer
from bioetl.composition.observability import ObservabilityBundle


@dataclass(frozen=True, slots=True)
class RunnerAssemblyParts:
    """Concrete runner collaborators assembled before PipelineRunner creation."""

    checkpoint_manager: CheckpointManagerService
    lifecycle_service: MedallionLifecycleService
    lock_manager: LockCoordinator
    preflight_service: PreflightService
    postrun_service: PostrunService
    observer: PipelineObserver
    batch_executor: BatchExecutor


@dataclass(frozen=True, slots=True)
class RunnerConstructorPayload:
    """Typed payload passed from assembly seams into final runner construction."""

    pipeline: BasePipeline
    observability: ObservabilityBundle
    parts: RunnerAssemblyParts


def create_pipeline_runner(
    *,
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    executor: BatchExecutor,
    checkpoint_manager: CheckpointManagerService,
    lock_manager: LockCoordinator,
    preflight_service: PreflightService,
    postrun_service: PostrunService,
    lifecycle_service: MedallionLifecycleService,
    observer: PipelineObserver,
) -> PipelineRunner:
    """Build the fully wired runtime PipelineRunner instance."""
    resolved_tracer = resolve_tracer(observability.tracer)
    dependencies = PipelineRunnerDependencies(
        executor=executor,
        checkpoint_manager=checkpoint_manager,
        lock_manager=lock_manager,
        preflight=preflight_service,
        postrun=postrun_service,
        lifecycle_service=lifecycle_service,
        observer=observer,
        shutdown_signal=pipeline.shutdown_signal,
    )
    return PipelineRunner(
        config=pipeline.config,
        runtime=pipeline.runtime,
        services=pipeline.services,
        context=pipeline.context,
        dependencies=dependencies,
        pipeline=pipeline,
        tracer=resolved_tracer,
    )


def create_pipeline_runner_from_payload(
    payload: RunnerConstructorPayload,
) -> PipelineRunner:
    """Build a PipelineRunner from a pre-assembled constructor payload."""
    return create_pipeline_runner(
        pipeline=payload.pipeline,
        observability=payload.observability,
        executor=payload.parts.batch_executor,
        checkpoint_manager=payload.parts.checkpoint_manager,
        lock_manager=payload.parts.lock_manager,
        preflight_service=payload.parts.preflight_service,
        postrun_service=payload.parts.postrun_service,
        lifecycle_service=payload.parts.lifecycle_service,
        observer=payload.parts.observer,
    )

================================================================================
File: transformer_builder.py
Path: factories\pipeline\transformer_builder.py
================================================================================
"""Transformer-construction helpers for pipeline factory wiring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.wiring.transformer import build_structural_policy
from bioetl.composition.factories.pipeline.construction_types import (
    ContractPolicyLoader,
    EntityTypeExtractor,
)
from bioetl.composition.factories.transformer_dependencies import (
    build_transformer_dependencies,
)
from bioetl.domain.services import IdentityService
from bioetl.infrastructure.config import load_pipeline_contract_policy

if TYPE_CHECKING:
    from bioetl.application.core.wiring.transformer import BaseTransformer
    from bioetl.domain.config import PipelineConfig
    from bioetl.domain.ports import ContractPolicyPort, MetricsPort, TracingPort
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class TransformerBuilder:
    """Construct transformer instances with policy/config dependencies."""

    provider: str
    pipeline_name: str
    entity_type_extractor: EntityTypeExtractor
    contract_policy_loader: ContractPolicyLoader = load_pipeline_contract_policy

    def build(
        self,
        *,
        transformer_class: type[BaseTransformer] | None,
        yaml_config: PipelineYamlConfig,
        domain_config: PipelineConfig,
        pandera_silver_schema: object | None,
        tracer: TracingPort | None,
        metrics: MetricsPort | None,
    ) -> BaseTransformer | None:
        """Build transformer instance or return ``None`` when class is absent."""
        if transformer_class is None:
            return None

        identity_service = IdentityService(
            content_hash_include_fields=set(yaml_config.content_hash.include) or None,
            content_hash_exclude_fields=set(yaml_config.content_hash.exclude),
        )
        entity_type = self.entity_type_extractor(self.pipeline_name)
        contract_policy = self._load_contract_policy(entity_type)
        structural_policy = build_structural_policy(
            domain_config=domain_config,
            pandera_silver_schema=pandera_silver_schema,
        )
        dependencies = build_transformer_dependencies(
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            contract_policy=contract_policy,
            structural_policy=structural_policy,
        )
        return transformer_class(
            provider=self.provider,
            entity_type=entity_type,
            silver_filters=domain_config.silver_filters,
            gold_filters=domain_config.gold_filters,
            dependencies=dependencies,
        )

    def _load_contract_policy(
        self, entity_type: str | None
    ) -> ContractPolicyPort | None:
        """Load policy for provider/entity and degrade gracefully when missing."""
        if entity_type is None:
            return None
        try:
            return self.contract_policy_loader(self.provider, entity_type)
        except ValueError:
            return None

================================================================================
File: transformer_dependencies.py
Path: factories\pipeline\transformer_dependencies.py
================================================================================
"""Canonical composition-side builders for explicit transformer dependencies."""

from __future__ import annotations

from collections.abc import Collection
from typing import Protocol

from bioetl.application.core.wiring.transformer import (
    DefaultContractPolicy,
    NoOpStructuralPolicy,
    StructuralPolicyProtocol,
    TransformerDependencyContext,
)
from bioetl.composition.observability_resolution import (
    resolve_metrics_port,
    resolve_tracing_port,
)
from bioetl.domain.ports import (
    ContractPolicyPort,
    DataNormalizationPort,
    MetricsPort,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.ports.noop import NoOpPiiHasher
from bioetl.domain.services import DataNormalizationService, IdentityService


class ContractPolicyLoader(Protocol):
    """Callable contract for loading pipeline contract policy."""

    def __call__(self, provider: str, entity: str) -> ContractPolicyPort:
        """Load contract policy for provider/entity."""
        ...


def build_transformer_dependencies(
    *,
    provider: str,
    entity_type: str | None,
    tracer: TracingPort | None = None,
    metrics: MetricsPort | None = None,
    identity_service: IdentityService | None = None,
    pii_hasher: PiiHasherPort | None = None,
    data_normalizer: DataNormalizationPort | None = None,
    contract_policy: ContractPolicyPort | None = None,
    content_hash_include_fields: Collection[str] | None = None,
    content_hash_exclude_fields: Collection[str] | None = None,
    contract_policy_loader: ContractPolicyLoader | None = None,
    structural_policy: StructuralPolicyProtocol | None = None,
) -> TransformerDependencyContext:
    """Build explicit collaborator bundle for transformer construction in composition."""

    resolved_contract_policy = contract_policy
    if resolved_contract_policy is None:
        resolved_contract_policy = _load_contract_policy(
            provider=provider,
            entity_type=entity_type,
            contract_policy_loader=contract_policy_loader,
        )

    return TransformerDependencyContext(
        tracer=resolve_tracing_port(tracer=tracer),
        metrics=resolve_metrics_port(metrics=metrics),
        identity_service=(
            identity_service
            if identity_service is not None
            else IdentityService(
                content_hash_include_fields=(
                    set(content_hash_include_fields)
                    if content_hash_include_fields
                    else None
                ),
                content_hash_exclude_fields=set(content_hash_exclude_fields or ()),
            )
        ),
        pii_hasher=pii_hasher if pii_hasher is not None else NoOpPiiHasher(),
        data_normalizer=(
            data_normalizer
            if data_normalizer is not None
            else DataNormalizationService()
        ),
        contract_policy=resolved_contract_policy,
        structural_policy=(
            structural_policy
            if structural_policy is not None
            else NoOpStructuralPolicy()
        ),
    )


def _load_contract_policy(
    *,
    provider: str,
    entity_type: str | None,
    contract_policy_loader: ContractPolicyLoader | None,
) -> ContractPolicyPort:
    """Load configured contract policy or degrade to the canonical fallback."""

    if entity_type is None or contract_policy_loader is None:
        return DefaultContractPolicy()
    try:
        return contract_policy_loader(provider, entity_type)
    except ValueError:
        return DefaultContractPolicy()

================================================================================
File: __init__.py
Path: factories\services\__init__.py
================================================================================
"""Services factory subpackage (DI for PipelineRunner)."""

from __future__ import annotations

from bioetl.composition.factories.pipeline.creation_support import (
    _BuildPipelineServicesFn,
    _create_pipeline_with_services_impl,
    _PipelineCreationInputs,
    _ServiceBundleDeps,
)
from bioetl.composition.factories.services.factory import (
    BaseServicesFactory,
    ServicesBuilder,
    create_data_normalization_service,
)
from bioetl.composition.factories.services.observability_api import (
    _create_cached_bronze_data_source,
    _create_data_source,
    create_shared_metrics,
)

__all__ = [
    "BaseServicesFactory",
    "ServicesBuilder",
    "_BuildPipelineServicesFn",
    "_PipelineCreationInputs",
    "_ServiceBundleDeps",
    "_create_cached_bronze_data_source",
    "_create_data_source",
    "_create_pipeline_with_services_impl",
    "create_data_normalization_service",
    "create_shared_metrics",
]

================================================================================
File: _builder_record_processor_support.py
Path: factories\services\_builder_record_processor_support.py
================================================================================
"""Injected helper for ServicesBuilder record-processor assembly."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.wiring.runtime import RecordProcessor
from bioetl.domain.config import TableConfig
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    import pandera as pdr
    import pyarrow as pa

    from bioetl.application.core.wiring.runtime import (
        ContentHashPolicyByVersion,
        GoldFilterCallback,
        GoldTransformCallback,
        PipelineService,
        RecordProcessorConfig,
        TransformCallback,
    )
    from bioetl.composition.factories.services.builder import ServicesBuilder
    from bioetl.domain.composite.config import ColumnGroupConfig
    from bioetl.domain.config import DQConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        GoldValidatorPort,
        TracingPort,
    )
    from bioetl.domain.types import (
        GoldSchemaPolicyByVersion,
        GoldSchemaType,
        ScdConfig,
    )


def create_record_processor_impl(
    *,
    services_builder: type[ServicesBuilder],
    services: PipelineService,
    context: PipelineContext,
    pipeline_name: str,
    provider: str,
    entity_type: str,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    dq_config: DQConfig | None,
    primary_keys: tuple[str, ...] | list[str],
    silver_table: str,
    gold_table: str | None,
    silver_write_mode: str,
    gold_write_mode: str,
    on_schema_mismatch: str,
    transform_callback: TransformCallback,
    gold_filter_callback: GoldFilterCallback,
    gold_transform_callback: GoldTransformCallback,
    tracer: TracingPort | None,
    strict_gold_validation: bool,
    lock_validator,
    column_groups: tuple[ColumnGroupConfig, ...],
    scd_config: ScdConfig | None,
    content_hash_include_fields: frozenset[str],
    content_hash_exclude_fields: frozenset[str],
    content_hash_policy_by_version: ContentHashPolicyByVersion | None,
    gold_schema_policy_by_version: GoldSchemaPolicyByVersion | None,
    record_processor_config_cls: type[RecordProcessorConfig],
    table_config_cls: type[TableConfig],
    gold_validator_factory: type[GoldValidatorPort] | type[PanderaGoldValidator],
    record_processor_cls: type[RecordProcessor],
) -> RecordProcessor:
    """Build a RecordProcessor using constructors injected from the public module."""
    effective_tracer = tracer or services.tracing
    active_gold_schema = (
        gold_schema_policy_by_version.active_schema
        if gold_schema_policy_by_version is not None
        else gold_schema
    )
    processor_config = record_processor_config_cls(
        pipeline_name=pipeline_name,
        provider=provider,
        entity_type=entity_type,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        dq_config=dq_config,
        table_config=table_config_cls(
            primary_keys=tuple(primary_keys),
            silver_table=silver_table,
            gold_table=gold_table,
            silver_write_mode=silver_write_mode,
            gold_write_mode=gold_write_mode,
            on_schema_mismatch=on_schema_mismatch,
        ),
        column_groups=column_groups,
        scd_config=scd_config,
        content_hash_include_fields=content_hash_include_fields,
        content_hash_exclude_fields=content_hash_exclude_fields,
        content_hash_policy_by_version=content_hash_policy_by_version,
        gold_schema_policy_by_version=gold_schema_policy_by_version,
    )
    components = services_builder.create_batch_processing_components(
        services=services,
        context=context,
        config=processor_config,
        error_classifier=ErrorClassifier(),
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
        gold_validator=gold_validator_factory(
            cast("pdr.DataFrameSchema | None", active_gold_schema),
            strict=strict_gold_validation,
        ),
        tracer=effective_tracer,
        lock_validator=lock_validator,
    )
    return record_processor_cls(
        context=context,
        batch_metrics=components.batch_metrics,
        transformer=components.transformer,
        writer=components.writer,
        config=processor_config,
        tracer=effective_tracer,
    )

================================================================================
File: _bundle_support.py
Path: factories\services\_bundle_support.py
================================================================================
"""Private support helpers for service-bundle wiring."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.factories.pipeline.creation_support import (
    _PipelineCreationInputs,
    _PipelineCreationRequest,
)

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceCreatorProtocol,
    )
    from bioetl.composition.factories.services.factory import BaseServicesFactory
    from bioetl.domain.config import DQConfig, PipelineConfig, RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import (
        DataSourcePort,
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class ServiceBundleDependencies:
    """Explicit dependency set for service-bundle wiring."""

    load_pipeline_config: Callable[[str], PipelineYamlConfig]
    yaml_config_to_domain: Callable[
        [PipelineYamlConfig, DQConfig | None], PipelineConfig
    ]
    compute_config_hash: Callable[[PipelineYamlConfig | dict[str, object]], str]
    base_services_factory: type[BaseServicesFactory]


def resolve_service_bundle_dependencies(
    *,
    override: ServiceBundleDependencies | None,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
    yaml_config_to_domain_fn: Callable[
        [PipelineYamlConfig, DQConfig | None], PipelineConfig
    ],
    compute_config_hash_fn: Callable[[PipelineYamlConfig | dict[str, object]], str],
    base_services_factory: type[BaseServicesFactory],
) -> ServiceBundleDependencies:
    """Resolve runtime dependencies with an optional test override."""
    if override is not None:
        return override
    return ServiceBundleDependencies(
        load_pipeline_config=load_pipeline_config_fn,
        yaml_config_to_domain=yaml_config_to_domain_fn,
        compute_config_hash=compute_config_hash_fn,
        base_services_factory=base_services_factory,
    )


def create_pipeline_data_source(
    *,
    pipeline_name: str,
    pipeline_config: PipelineYamlConfig,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None,
    metrics: MetricsPort,
    cached_bronze: CachedBronzeContext | None,
    create_cached_bronze_data_source_fn: Callable[..., DataSourcePort],
    create_data_source_impl_fn: Callable[..., DataSourcePort],
) -> DataSourcePort:
    """Resolve live-vs-cached data source construction for one pipeline run."""
    if cached_bronze is not None and cached_bronze.enabled:
        data_source = create_cached_bronze_data_source_fn(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            cached_bronze=cached_bronze,
        )
        logger.info(
            "using_cached_bronze_mode",
            pipeline=pipeline_name,
            bronze_path=cached_bronze.bronze_path,
            bronze_date=cached_bronze.bronze_date,
        )
        return data_source
    return create_data_source_impl_fn(
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        pipeline_config=pipeline_config,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
    )


def build_pipeline_creation_inputs(
    *,
    pipeline_name: str,
    pipeline_class: type[BasePipeline],
    provider: str,
    create_data_source_fn: DataSourceCreatorProtocol,
    transformer_class: type[BaseTransformer] | None,
    run_id: RunID,
    runtime: RuntimeConfig,
    settings: Settings,
    logger: LoggerPort,
    manifest_id: str | None,
    config_hash: str | None,
    dq_contract_compatibility_hash: str | None,
    effective_config_artifact_id: str | None,
    config: PipelineYamlConfig | None,
    filter_config: InputFilterConfig | None,
    tracer: TracingPort | None,
    dq_monitor: DQMonitorPort | None,
    metrics: MetricsPort | None,
    cached_bronze: CachedBronzeContext | None,
    pandera_silver_schema: object | None,
) -> _PipelineCreationInputs:
    """Build the delegated pipeline-creation envelope."""
    return _PipelineCreationInputs(
        pipeline_name=pipeline_name,
        pipeline_class=pipeline_class,
        provider=provider,
        create_data_source_fn=create_data_source_fn,
        transformer_class=transformer_class,
        request=_PipelineCreationRequest(
            run_id=run_id,
            runtime=runtime,
            settings=settings,
            logger=logger,
            manifest_id=manifest_id,
            config_hash=config_hash,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            effective_config_artifact_id=effective_config_artifact_id,
            config=config,
            filter_config=filter_config,
            tracer=tracer,
            dq_monitor=dq_monitor,
            metrics=metrics,
            cached_bronze=cached_bronze,
        ),
        pandera_silver_schema=pandera_silver_schema,
    )

================================================================================
File: _record_processor_policy_support.py
Path: factories\services\_record_processor_policy_support.py
================================================================================
"""Hash/schema policy helpers for record-processor assembly."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from itertools import chain
from typing import TYPE_CHECKING

from bioetl.application.core.wiring.runtime import (
    BasePipeline,
    ContentHashPolicyByVersion,
    ContentHashVersionPolicy,
)
from bioetl.domain.types import (
    GoldSchemaPolicyByVersion,
    GoldSchemaVersionPolicy,
)

if TYPE_CHECKING:
    from bioetl.domain.types import GoldSchemaType


def coerce_string_frozenset(value: object | None) -> frozenset[str]:
    """Coerce list/set-like string collections to an immutable set."""
    if value is None or isinstance(value, str | bytes):
        return frozenset()
    if not isinstance(value, Iterable):
        return frozenset()
    return frozenset(item for item in value if isinstance(item, str))


def extract_hash_policy(
    pipeline: BasePipeline,
) -> tuple[frozenset[str], frozenset[str]]:
    """Extract effective content-hash field policy from transformer wiring."""
    transformer = getattr(pipeline, "transformer", None)
    identity = getattr(transformer, "_identity", None)
    contract_policy = getattr(transformer, "_contract_policy", None)

    identity_include = coerce_string_frozenset(
        getattr(identity, "_content_hash_include_fields", None)
    )
    identity_exclude = coerce_string_frozenset(
        getattr(identity, "_content_hash_exclude_fields", None)
    )
    contract_include = coerce_string_frozenset(
        getattr(contract_policy, "hash_include", None)
    )
    contract_exclude = coerce_string_frozenset(
        getattr(contract_policy, "hash_exclude", None)
    )

    include_fields = (
        frozenset(contract_include & identity_include)
        if contract_include and identity_include
        else (contract_include or identity_include)
    )
    exclude_fields = frozenset(
        chain(identity_exclude, contract_exclude, ("entity_id", "content_hash"))
    )
    return include_fields, exclude_fields


def extract_hash_policy_by_version(
    pipeline: BasePipeline,
    *,
    include_fields: frozenset[str],
    exclude_fields: frozenset[str],
) -> ContentHashPolicyByVersion | None:
    """Build ordered per-version hash policies from rollout-aware contract policy."""
    transformer = getattr(pipeline, "transformer", None)
    contract_policy = getattr(transformer, "_contract_policy", None)
    active_version = getattr(contract_policy, "active_version", None)
    rollout = getattr(contract_policy, "rollout", None)
    write_versions = getattr(rollout, "write_versions", None)
    affects_hash = bool(getattr(rollout, "affects_hash", False))

    normalized_active_version = (
        str(active_version).strip() if active_version is not None else ""
    )
    if not normalized_active_version:
        return None

    if write_versions is None:
        versions: tuple[str, ...] = (normalized_active_version,)
    else:
        versions = tuple(
            str(version).strip() for version in write_versions if str(version).strip()
        ) or (normalized_active_version,)

    if normalized_active_version not in versions:
        versions = (normalized_active_version, *versions)

    return ContentHashPolicyByVersion(
        active_version=normalized_active_version,
        affects_hash=affects_hash,
        policies=tuple(
            ContentHashVersionPolicy(
                version=version,
                include_fields=include_fields,
                exclude_fields=exclude_fields,
            )
            for version in versions
        ),
    )


def extract_gold_schema_policy_by_version(
    pipeline: BasePipeline,
    *,
    gold_schema: GoldSchemaType,
) -> GoldSchemaPolicyByVersion | None:
    """Build ordered per-version Gold schema routing from rollout-aware policy."""
    transformer = getattr(pipeline, "transformer", None)
    contract_policy = getattr(transformer, "_contract_policy", None)
    active_version = getattr(contract_policy, "active_version", None)
    rollout = getattr(contract_policy, "rollout", None)
    write_versions = getattr(rollout, "write_versions", None)
    configured_mapping = getattr(pipeline, "gold_schema_by_version", None)

    normalized_active_version = (
        str(active_version).strip() if active_version is not None else ""
    )
    if not normalized_active_version:
        return None

    if write_versions is None:
        versions: tuple[str, ...] = (normalized_active_version,)
    else:
        versions = tuple(
            str(version).strip() for version in write_versions if str(version).strip()
        ) or (normalized_active_version,)

    if normalized_active_version not in versions:
        versions = (normalized_active_version, *versions)

    schema_mapping: dict[str, object] = {}
    if isinstance(configured_mapping, Mapping):
        schema_mapping = {
            str(version).strip(): schema
            for version, schema in configured_mapping.items()
            if str(version).strip() and schema is not None
        }

    for version in versions:
        schema_mapping.setdefault(version, gold_schema)

    return GoldSchemaPolicyByVersion(
        active_version=normalized_active_version,
        policies=tuple(
            GoldSchemaVersionPolicy(
                version=version,
                schema=schema_mapping[version],
            )
            for version in versions
        ),
    )

================================================================================
File: builder.py
Path: factories\services\builder.py
================================================================================
from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import TYPE_CHECKING, Literal

from bioetl.application.core.wiring.runtime import (
    BatchExecutor,
    BatchProcessingComponents,
    CheckpointManagerService,
    ContentHashPolicyByVersion,
    GoldFilterCallback,
    GoldTransformCallback,
    PipelineService,
    RecordProcessor,
    RecordProcessorConfig,
    ShutdownSignal,
    TransformCallback,
)
from bioetl.composition.factories.services._builder_record_processor_support import (
    create_record_processor_impl,
)
from bioetl.composition.factories.services.callbacks import (
    create_data_normalization_service,
    extract_pipeline_callbacks,
)
from bioetl.composition.factories.services.pipeline_builder import (
    create_batch_executor_from_pipeline,
    create_batch_processing_components,
    create_checkpoint_manager,
    create_record_processor_from_pipeline,
)
from bioetl.domain.composite.config import ColumnGroupConfig
from bioetl.domain.config import TableConfig
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.medallion import GoldWriteMode, LoadingStrategy, SilverWriteMode
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.wiring.runtime import BasePipeline
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterPort,
    )
    from bioetl.domain.config import DQConfig, MemoryConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        BatchIdGeneratorPort,
        CheckpointPort,
        GoldValidatorPort,
        LoggerPort,
        MemoryMonitorPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.domain.types import (
        GoldSchemaPolicyByVersion,
        GoldSchemaType,
        RunID,
        ScdConfig,
    )
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
__all__ = [
    "ServicesBuilder",
    "create_data_normalization_service",
    "extract_pipeline_callbacks",
]


class ServicesBuilder:
    @staticmethod
    def create_batch_processing_components(
        *,
        services: PipelineService,
        context: PipelineContext,
        config: RecordProcessorConfig,
        error_classifier: ErrorClassifier,
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
        gold_transform_callback: GoldTransformCallback,
        gold_validator: GoldValidatorPort,
        tracer: TracingPort | None = None,
        domain_event_emitter: DomainEventEmitterPort | None = None,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
    ) -> BatchProcessingComponents:
        return create_batch_processing_components(
            services=services,
            context=context,
            config=config,
            error_classifier=error_classifier,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            gold_validator=gold_validator,
            tracer=tracer,
            domain_event_emitter=domain_event_emitter,
            lock_validator=lock_validator,
        )

    @staticmethod
    def create_checkpoint_manager(
        checkpoint_port: CheckpointPort,
        logger: LoggerPort,
        pipeline_name: str,
        run_id: RunID,
        resume: bool,
        *,
        loading_strategy: LoadingStrategy | None = None,
        metrics: MetricsPort | None = None,
        checkpoint_compatibility_service: object | None = None,
        current_metadata: CheckpointMetadata | None = None,
        compatibility_policy: Literal[
            "observe", "soft_fail", "hard_fail"
        ] = "soft_fail",
    ) -> CheckpointManagerService:
        return create_checkpoint_manager(
            checkpoint_port=checkpoint_port,
            logger=logger,
            pipeline_name=pipeline_name,
            run_id=run_id,
            resume=resume,
            loading_strategy=loading_strategy,
            metrics=metrics,
            checkpoint_compatibility_service=checkpoint_compatibility_service,
            current_metadata=current_metadata,
            compatibility_policy=compatibility_policy,
        )

    @staticmethod
    def create_record_processor(
        services: PipelineService,
        context: PipelineContext,
        pipeline_name: str,
        provider: str,
        entity_type: str,
        silver_schema: pa.Schema | None,
        gold_schema: GoldSchemaType,
        dq_config: DQConfig | None,
        primary_keys: Sequence[str],
        silver_table: str,
        gold_table: str | None,
        silver_write_mode: SilverWriteMode,
        gold_write_mode: GoldWriteMode,
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
        gold_transform_callback: GoldTransformCallback,
        tracer: TracingPort | None = None,
        *,
        strict_gold_validation: bool = True,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
        column_groups: tuple[ColumnGroupConfig, ...] = (),
        scd_config: ScdConfig | None = None,
        content_hash_include_fields: frozenset[str] = frozenset(),
        content_hash_exclude_fields: frozenset[str] = frozenset(),
        content_hash_policy_by_version: ContentHashPolicyByVersion | None = None,
        gold_schema_policy_by_version: GoldSchemaPolicyByVersion | None = None,
    ) -> RecordProcessor:
        return create_record_processor_impl(
            services_builder=ServicesBuilder,
            services=services,
            context=context,
            pipeline_name=pipeline_name,
            provider=provider,
            entity_type=entity_type,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            dq_config=dq_config,
            primary_keys=primary_keys,
            silver_table=silver_table,
            gold_table=gold_table,
            silver_write_mode=silver_write_mode,
            gold_write_mode=gold_write_mode,
            on_schema_mismatch=on_schema_mismatch,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            tracer=tracer,
            strict_gold_validation=strict_gold_validation,
            lock_validator=lock_validator,
            column_groups=column_groups,
            scd_config=scd_config,
            content_hash_include_fields=content_hash_include_fields,
            content_hash_exclude_fields=content_hash_exclude_fields,
            content_hash_policy_by_version=content_hash_policy_by_version,
            gold_schema_policy_by_version=gold_schema_policy_by_version,
            record_processor_config_cls=RecordProcessorConfig,
            table_config_cls=TableConfig,
            gold_validator_factory=PanderaGoldValidator,
            record_processor_cls=RecordProcessor,
        )

    @staticmethod
    def create_record_processor_from_pipeline(
        pipeline: BasePipeline,
        silver_schema: pa.Schema | None,
        gold_schema: GoldSchemaType,
        *,
        strict_gold_validation: bool = True,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
    ) -> RecordProcessor:
        callbacks = extract_pipeline_callbacks(pipeline)
        return create_record_processor_from_pipeline(
            pipeline=pipeline,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            callbacks=callbacks,
            create_record_processor_fn=ServicesBuilder.create_record_processor,
            strict_gold_validation=strict_gold_validation,
            lock_validator=lock_validator,
            tracer=pipeline.services.tracing,
        )

    @staticmethod
    def create_batch_executor_from_pipeline(
        pipeline: BasePipeline,
        silver_schema: pa.Schema | None,
        gold_schema: GoldSchemaType,
        checkpoint_manager: CheckpointManagerService,
        shutdown_signal: ShutdownSignal,
        *,
        strict_gold_validation: bool = True,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
        tracer: TracingPort | None = None,
        memory_monitor: MemoryMonitorPort | None = None,
        memory_config: MemoryConfig | None = None,
        bronze_output_path: str | None = None,
        silver_output_path: str | None = None,
        gold_output_path: str | None = None,
        flat_structure: bool = False,
        batch_id_factory: BatchIdGeneratorPort | None = None,
        domain_event_emitter: DomainEventEmitterPort | None = None,
    ) -> BatchExecutor:
        callbacks = extract_pipeline_callbacks(pipeline)
        return create_batch_executor_from_pipeline(
            pipeline=pipeline,
            callbacks=callbacks,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            checkpoint_manager=checkpoint_manager,
            shutdown_signal=shutdown_signal,
            create_batch_processing_components_fn=(
                ServicesBuilder.create_batch_processing_components
            ),
            strict_gold_validation=strict_gold_validation,
            lock_validator=lock_validator,
            tracer=tracer,
            memory_monitor=memory_monitor,
            memory_config=memory_config,
            bronze_output_path=bronze_output_path,
            silver_output_path=silver_output_path,
            gold_output_path=gold_output_path,
            flat_structure=flat_structure,
            batch_id_factory=batch_id_factory,
            domain_event_emitter=domain_event_emitter,
        )

================================================================================
File: bundle.py
Path: factories\services\bundle.py
================================================================================
"""Service bundle facade for pipeline wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
)
from bioetl.composition.factories.pipeline.creation_support import (
    _BuildPipelineServicesFn,
    _create_pipeline_with_services_impl,
    _ServiceBundleDeps,
)
from bioetl.composition.factories.services._bundle_support import (
    ServiceBundleDependencies,
    build_pipeline_creation_inputs,
    resolve_service_bundle_dependencies,
)
from bioetl.composition.factories.services._bundle_support import (
    create_pipeline_data_source as _create_pipeline_data_source_impl,
)
from bioetl.composition.factories.services.factory import BaseServicesFactory
from bioetl.composition.factories.services.observability_api import (
    _create_cached_bronze_data_source as _create_cached_bronze_data_source_impl,
)
from bioetl.composition.factories.services.observability_api import (
    _create_data_source as _create_data_source_impl,
)
from bioetl.composition.factories.services.observability_api import (
    create_shared_metrics,
)
from bioetl.composition.services.versioning import (
    compute_config_hash as _compute_config_hash_direct,
)
from bioetl.infrastructure.config.converters import (
    yaml_config_to_domain as _yaml_config_to_domain_direct,
)
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config as _load_pipeline_config_direct,
)

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.domain.config import DQConfig, PipelineConfig, RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import (
        DataSourcePort,
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "ServiceBundleDependencies",
    "_create_cached_bronze_data_source",
    "_create_data_source",
    "build_pipeline_services",
    "create_pipeline_with_services",
]


def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    """Load pipeline YAML configuration using the canonical config API seam."""
    return _load_pipeline_config_direct(pipeline_name)


def yaml_config_to_domain(
    yaml_config: PipelineYamlConfig,
    resolved_dq_config: DQConfig | None = None,
) -> PipelineConfig:
    """Convert YAML pipeline config to domain config with optional DQ overrides."""
    return _yaml_config_to_domain_direct(
        yaml_config=yaml_config,
        resolved_dq_config=resolved_dq_config,
    )


def compute_config_hash(config: PipelineYamlConfig | dict[str, object]) -> str:
    """Compute deterministic config hash for run-manifest and cache identity."""
    config_hash: str = _compute_config_hash_direct(config)
    return config_hash


def _resolve_service_bundle_dependencies(
    override: ServiceBundleDependencies | None = None,
) -> ServiceBundleDependencies:
    return resolve_service_bundle_dependencies(
        override=override,
        load_pipeline_config_fn=load_pipeline_config,
        yaml_config_to_domain_fn=yaml_config_to_domain,
        compute_config_hash_fn=compute_config_hash,
        base_services_factory=BaseServicesFactory,
    )


def _extract_entity_type(pipeline_name: str) -> str | None:
    """Extract the trailing entity from `<provider>_<entity>` pipeline names."""
    return pipeline_name.split("_")[-1] if "_" in pipeline_name else None


_create_data_source = _create_data_source_impl
_create_cached_bronze_data_source = _create_cached_bronze_data_source_impl


def _create_pipeline_data_source(
    *,
    pipeline_name: str,
    pipeline_config: PipelineYamlConfig,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None,
    metrics: MetricsPort,
    cached_bronze: CachedBronzeContext | None,
) -> DataSourcePort:
    return _create_pipeline_data_source_impl(
        pipeline_name=pipeline_name,
        pipeline_config=pipeline_config,
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        cached_bronze=cached_bronze,
        create_cached_bronze_data_source_fn=_create_cached_bronze_data_source,
        create_data_source_impl_fn=_create_data_source,
    )


def build_pipeline_services(
    pipeline_name: str,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    logger: LoggerPort,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
    metadata_coordinator: MetadataCoordinator | None = None,
    cached_bronze: CachedBronzeContext | None = None,
    silver_validator: SilverValidatorPort | None = None,
    _deps: ServiceBundleDependencies | None = None,
) -> PipelineService:
    """Build the shared pipeline service bundle for one pipeline run."""
    deps = _resolve_service_bundle_dependencies(_deps)
    pipeline_config = config or deps.load_pipeline_config(pipeline_name)
    shared_metrics = create_shared_metrics(
        settings=settings,
        base_services_factory=deps.base_services_factory,
    )
    data_source = _create_pipeline_data_source(
        pipeline_name=pipeline_name,
        pipeline_config=pipeline_config,
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=shared_metrics,
        cached_bronze=cached_bronze,
    )
    return deps.base_services_factory.create_common_services(
        settings=settings,
        logger=logger,
        data_source=data_source,
        pipeline_config=pipeline_config,
        pipeline_name=pipeline_name,
        metrics=shared_metrics,
        tracer=tracer,
        dq_monitor=dq_monitor,
        metadata_coordinator=metadata_coordinator,
        silver_validator=silver_validator,
    )


def create_pipeline_with_services(
    pipeline_name: str,
    pipeline_class: type[BasePipeline],
    provider: str,
    create_data_source_fn: DataSourceCreatorProtocol,
    transformer_class: type[BaseTransformer] | None,
    run_id: RunID,
    runtime: RuntimeConfig,
    settings: Settings,
    logger: LoggerPort,
    manifest_id: str | None = None,
    config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
    metrics: MetricsPort | None = None,
    cached_bronze: CachedBronzeContext | None = None,
    pandera_silver_schema: object | None = None,
    _deps: ServiceBundleDependencies | None = None,
) -> BasePipeline:
    """Create a pipeline instance with its resolved service bundle."""
    # Compatibility markers for architecture static checks:
    # transformer_class(...) happens inside the delegated builder path.
    # transformer=transformer is preserved at the pipeline constructor boundary.
    resolved_deps = cast(
        _ServiceBundleDeps,
        _resolve_service_bundle_dependencies(_deps),
    )
    return _create_pipeline_with_services_impl(
        build_pipeline_creation_inputs(
            pipeline_name=pipeline_name,
            pipeline_class=pipeline_class,
            provider=provider,
            create_data_source_fn=create_data_source_fn,
            transformer_class=transformer_class,
            run_id=run_id,
            runtime=runtime,
            settings=settings,
            logger=logger,
            manifest_id=manifest_id,
            config_hash=config_hash,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            effective_config_artifact_id=effective_config_artifact_id,
            config=config,
            filter_config=filter_config,
            tracer=tracer,
            dq_monitor=dq_monitor,
            metrics=metrics,
            cached_bronze=cached_bronze,
            pandera_silver_schema=pandera_silver_schema,
        ),
        deps=resolved_deps,
        extract_entity_type=_extract_entity_type,
        build_pipeline_services_fn=cast(
            _BuildPipelineServicesFn,
            build_pipeline_services,
        ),
    )

================================================================================
File: callbacks.py
Path: factories\services\callbacks.py
================================================================================
"""Pipeline callback extraction and normalization service factory.

Extracted from builder.py to keep it within LOC limits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.wiring.runtime import (
    BasePipeline,
    GoldFilterCallback,
    GoldTransformCallback,
    TransformCallback,
)
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext

if TYPE_CHECKING:
    from bioetl.domain.ports import DataNormalizationPort
    from bioetl.domain.services import DataNormalizationConfig

__all__ = ["create_data_normalization_service", "extract_pipeline_callbacks"]


def extract_pipeline_callbacks(pipeline: BasePipeline) -> PipelineCallbacksContext:
    """Extract transformation callbacks from transformer or legacy methods.

    Returns:
        PipelineCallbacksContext with transform, gold filter, and gold transform callbacks.
    """
    transformer = pipeline.transformer
    if transformer is not None:
        transform_callback = cast(
            TransformCallback,
            getattr(transformer, "transform_pre_silver", transformer.transform),
        )
        return PipelineCallbacksContext(
            transform=transform_callback,
            gold_filter=cast(GoldFilterCallback, transformer.should_write_gold),
            gold_transform=cast(GoldTransformCallback, transformer.transform_for_gold),
        )

    # Fallback for pipelines without explicit transformer (legacy)
    return PipelineCallbacksContext(
        transform=cast(TransformCallback, pipeline.transform_bronze_to_silver),
        gold_filter=cast(
            GoldFilterCallback,
            getattr(pipeline, "should_write_gold", lambda _context, record: True),
        ),
        gold_transform=cast(
            GoldTransformCallback,
            getattr(
                pipeline,
                "transform_for_gold",
                lambda _context, silver_record: silver_record,
            ),
        ),
    )


def create_data_normalization_service(
    config: DataNormalizationConfig | None = None,
) -> DataNormalizationPort:
    """Create DataNormalizationService with optional configuration."""
    from bioetl.domain.services import (
        DataNormalizationConfig,
        DefaultDataNormalizationService,
    )

    return DefaultDataNormalizationService(config=config or DataNormalizationConfig())

================================================================================
File: common_service_wiring.py
Path: factories\services\common_service_wiring.py
================================================================================
"""Internal wiring helpers for common pipeline service ports."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.wiring.runtime import PipelineService
from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.factories.services.port_factories import (
    create_checkpoint,
    create_lock,
    create_metrics,
    create_quarantine,
)
from bioetl.composition.factories.storage import StorageContext, StorageFactory
from bioetl.composition.observability_resolution import (
    resolve_tracing_port as _resolve_tracing_port,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        CheckpointPort,
        DataSourcePort,
        DQMonitorPort,
        LockPort,
        LoggerPort,
        MetricsPort,
        QuarantinePort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class CommonServicePorts:
    """Resolved common ports required to assemble a ``PipelineService``."""

    storage_ctx: StorageContext
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics_port: MetricsPort
    tracer: TracingPort
    dq_services: JsonDict


@dataclass(frozen=True, slots=True)
class CommonServicePortsRequest:
    """Inputs required to resolve the shared ports for one pipeline service."""

    settings: Settings
    logger: LoggerPort
    pipeline_config: PipelineYamlConfig
    pipeline_name: str
    create_dq_services_fn: Callable[
        [Settings, PipelineYamlConfig, LoggerPort, MetricsPort | None],
        JsonDict,
    ]
    metrics: MetricsPort | None = None
    tracer: TracingPort | None = None
    metadata_coordinator: MetadataCoordinator | None = None
    silver_validator: SilverValidatorPort | None = None
    create_metrics_fn: Callable[[Settings], MetricsPort] = create_metrics
    storage_factory: type[StorageFactory] = StorageFactory
    create_lock_fn: Callable[[], LockPort] = create_lock
    create_checkpoint_fn: Callable[[StorageContext], CheckpointPort] = create_checkpoint
    create_quarantine_fn: Callable[[Settings], QuarantinePort] = create_quarantine


def resolve_tracer(tracer: TracingPort | None) -> TracingPort:
    """Return the provided tracer or a NoOpTracing fallback."""
    return _resolve_tracing_port(tracer=tracer)


def build_common_service_ports(
    request: CommonServicePortsRequest,
) -> CommonServicePorts:
    """Create the reusable common ports shared by pipeline services."""
    metrics_port = (
        request.metrics
        if request.metrics is not None
        else request.create_metrics_fn(request.settings)
    )
    storage_ctx = request.storage_factory.create(
        request.settings,
        request.pipeline_config,
        request.logger,
        metrics=metrics_port,
        metadata_coordinator=request.metadata_coordinator,
        silver_validator=request.silver_validator,
        pipeline_name=request.pipeline_name,
    )
    return CommonServicePorts(
        storage_ctx=storage_ctx,
        lock=request.create_lock_fn(),
        checkpoint=request.create_checkpoint_fn(storage_ctx),
        quarantine=request.create_quarantine_fn(request.settings),
        metrics_port=metrics_port,
        tracer=resolve_tracer(request.tracer),
        dq_services=request.create_dq_services_fn(
            request.settings,
            request.pipeline_config,
            request.logger,
            metrics_port,
        ),
    )


def assemble_pipeline_service(
    *,
    data_source: DataSourcePort,
    logger: LoggerPort,
    dq_monitor: DQMonitorPort | None,
    metadata_coordinator: MetadataCoordinator | None,
    common_ports: CommonServicePorts,
) -> PipelineService:
    """Assemble ``PipelineService`` from pre-built common ports."""
    from bioetl.infrastructure.storage.metadata_writer import MetadataWriter

    metadata_writer = MetadataWriter(logger=logger)
    return PipelineService(
        data_source=data_source,
        storage=common_ports.storage_ctx.adapter,
        lock=common_ports.lock,
        checkpoint=common_ports.checkpoint,
        quarantine=common_ports.quarantine,
        metrics=common_ports.metrics_port,
        tracing=common_ports.tracer,
        logger=logger,
        dq_monitor=dq_monitor,
        metadata_coordinator=metadata_coordinator,
        metadata_writer=metadata_writer,
        bronze_dq_analyzer=common_ports.dq_services.get("bronze_analyzer"),
        silver_dq_analyzer=common_ports.dq_services.get("silver_analyzer"),
        gold_dq_analyzer=common_ports.dq_services.get("gold_analyzer"),
        dq_report_writer=common_ports.dq_services.get("report_writer"),
        dq_report_service=common_ports.dq_services.get("report_service"),
    )

================================================================================
File: factory.py
Path: factories\services\factory.py
================================================================================
"""Services factory façade for pipeline service wiring."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.core.wiring.factory import PipelineService
from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.factories.dq.context_resolver import (
    create_dq_services as _create_dq_services_impl,
)
from bioetl.composition.factories.dq.context_resolver import (
    get_flat_structure as _get_flat_structure_impl,
)
from bioetl.composition.factories.dq.context_resolver import (
    get_output_root as _get_output_root_impl,
)
from bioetl.composition.factories.dq.context_resolver import (
    is_dq_report_enabled as _is_dq_report_enabled_impl,
)
from bioetl.composition.factories.dq.factory import DQServicesFactory
from bioetl.composition.factories.services.builder import ServicesBuilder
from bioetl.composition.factories.services.callbacks import (
    create_data_normalization_service,
    extract_pipeline_callbacks,
)
from bioetl.composition.factories.services.common_service_wiring import (
    CommonServicePorts,
    CommonServicePortsRequest,
    assemble_pipeline_service,
    build_common_service_ports,
    resolve_tracer,
)
from bioetl.composition.factories.services.port_factories import (
    create_checkpoint,
    create_lock,
    create_metrics,
    create_quarantine,
)
from bioetl.composition.factories.storage import StorageFactory
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.composition.factories.storage import StorageContext
    from bioetl.domain.ports import (
        CheckpointPort,
        DataSourcePort,
        DQMonitorPort,
        LockPort,
        LoggerPort,
        MetricsPort,
        QuarantinePort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "BaseServicesFactory",
    "DQServicesFactory",
    "ServicesBuilder",
    "create_data_normalization_service",
    "extract_pipeline_callbacks",
]


class BaseServicesFactory:
    """Reusable factory for common services (local deployment)."""

    @staticmethod
    def _create_metrics(settings: Settings) -> MetricsPort:
        """Compatibility wrapper delegating metrics creation to port factories."""
        return create_metrics(settings)

    @classmethod
    def create_common_services(
        cls,
        settings: Settings,
        logger: LoggerPort,
        data_source: DataSourcePort,
        pipeline_config: PipelineYamlConfig,
        pipeline_name: str,
        metrics: MetricsPort | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        silver_validator: SilverValidatorPort | None = None,
    ) -> PipelineService:
        """Create a fully wired `PipelineService` bundle for one pipeline run."""
        cls._ensure_prod_silver_validator(settings, pipeline_config, silver_validator)
        common_ports = build_common_service_ports(
            CommonServicePortsRequest(
                settings=settings,
                logger=logger,
                pipeline_config=pipeline_config,
                pipeline_name=pipeline_name,
                metrics=metrics,
                tracer=tracer,
                metadata_coordinator=metadata_coordinator,
                silver_validator=silver_validator,
                create_dq_services_fn=cls._create_dq_services,
                create_metrics_fn=create_metrics,
                storage_factory=StorageFactory,
                create_lock_fn=create_lock,
                create_checkpoint_fn=create_checkpoint,
                create_quarantine_fn=create_quarantine,
            )
        )
        return assemble_pipeline_service(
            data_source=data_source,
            logger=logger,
            dq_monitor=dq_monitor,
            metadata_coordinator=metadata_coordinator,
            common_ports=common_ports,
        )

    @staticmethod
    def _ensure_prod_silver_validator(
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        silver_validator: SilverValidatorPort | None,
    ) -> None:
        """Enforce validator requirement in production mode."""
        if (
            settings.env == "prod"
            and not settings.test_mode
            and silver_validator is None
        ):
            raise ValueError(
                "Silver validator is required for production pipelines "
                f"(pipeline={pipeline_config.pipeline_name})"
            )

    @staticmethod
    def _resolve_tracer(tracer: TracingPort | None) -> TracingPort:
        """Return tracer or fallback to NoOpTracing."""
        return resolve_tracer(tracer)

    @staticmethod
    def _build_pipeline_services(
        *,
        data_source: DataSourcePort,
        storage_ctx: StorageContext,
        lock: LockPort,
        checkpoint: CheckpointPort,
        quarantine: QuarantinePort,
        metrics_port: MetricsPort,
        tracer: TracingPort,
        logger: LoggerPort,
        dq_monitor: DQMonitorPort | None,
        metadata_coordinator: MetadataCoordinator | None,
        dq_services: JsonDict,  # Any: heterogeneous DQ service instances
    ) -> PipelineService:
        """Assemble PipelineService from pre-built dependencies."""
        return assemble_pipeline_service(
            data_source=data_source,
            logger=logger,
            dq_monitor=dq_monitor,
            metadata_coordinator=metadata_coordinator,
            common_ports=CommonServicePorts(
                storage_ctx=storage_ctx,
                lock=lock,
                checkpoint=checkpoint,
                quarantine=quarantine,
                metrics_port=metrics_port,
                tracer=tracer,
                dq_services=dq_services,
            ),
        )

    @staticmethod
    def _get_output_root(
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
    ) -> Path:
        """Derive output root from pipeline config or fall back to settings."""
        return _get_output_root_impl(settings, pipeline_config)

    @classmethod
    def _create_dq_services(
        cls,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
    ) -> JsonDict:  # Any: heterogeneous DQ service instances
        """Create DQ analyzers/writer/services when DQ reporting is enabled."""
        return _create_dq_services_impl(
            settings,
            pipeline_config,
            logger,
            metrics,
        )

    @staticmethod
    def _is_dq_report_enabled(config: PipelineYamlConfig) -> bool:
        """Check if any DQ report is enabled in pipeline config."""
        return _is_dq_report_enabled_impl(config)

    @staticmethod
    def _get_flat_structure(config: PipelineYamlConfig) -> bool:
        """Get flat_structure setting from pipeline config."""
        return _get_flat_structure_impl(config)

================================================================================
File: observability_api.py
Path: factories\services\observability_api.py
================================================================================
"""Public observability wiring facade for services bundle assembly."""

from __future__ import annotations

from bioetl.composition.factories.observability_api import (
    _create_cached_bronze_data_source,
    _create_data_source,
    create_shared_metrics,
)

__all__ = [
    "_create_cached_bronze_data_source",
    "_create_data_source",
    "create_shared_metrics",
]

================================================================================
File: pipeline_batch_executor_builder.py
Path: factories\services\pipeline_batch_executor_builder.py
================================================================================
"""Batch-executor assembly helpers for pipeline builder facade."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

from bioetl.application.core.wiring.runtime import (
    BatchExecutionFSM,
    BatchExecutionStateService,
    BatchExecutor,
    BatchExecutorDependencies,
    BatchExtractionLoopService,
    BatchProcessingComponents,
    CheckpointManagerService,
    GoldFilterCallback,
)
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
from bioetl.composition.factories.services.pipeline_processing import (
    build_components_and_processing_service,
)
from bioetl.composition.factories.services.pipeline_record_processor_builder import (
    build_record_processor_config_and_validator,
)
from bioetl.composition.factories.services.runtime_managers import (
    build_runtime_managers,
)
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.wiring.runtime import (
        BasePipeline,
        BatchCheckpointRecoveryService,
        BatchExecutionRunService,
        BatchMemoryManagerService,
        BatchProcessingService,
        BatchProgressService,
        ShutdownSignal,
    )
    from bioetl.domain.config import MemoryConfig
    from bioetl.domain.ports import (
        BatchIdGeneratorPort,
        MemoryMonitorPort,
        TracingPort,
    )
    from bioetl.domain.types import GoldSchemaType


def create_batch_executor_from_pipeline(
    *,
    pipeline: BasePipeline,
    callbacks: PipelineCallbacksContext,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    checkpoint_manager: CheckpointManagerService,
    shutdown_signal: ShutdownSignal,
    create_batch_processing_components_fn: Callable[..., BatchProcessingComponents],
    strict_gold_validation: bool = True,
    lock_validator: Callable[[], Awaitable[bool]] | None = None,
    tracer: TracingPort | None = None,
    memory_monitor: MemoryMonitorPort | None = None,
    memory_config: MemoryConfig | None = None,
    bronze_output_path: str | None = None,
    silver_output_path: str | None = None,
    gold_output_path: str | None = None,
    flat_structure: bool = False,
    batch_id_factory: BatchIdGeneratorPort | None = None,
    domain_event_emitter: DomainEventEmitter | None = None,
) -> BatchExecutor:
    """Create BatchExecutor from pipeline using delegated component factories."""
    gold_filter = _resolve_gold_filter(pipeline=pipeline, callbacks=callbacks)
    processor_config, gold_validator = build_record_processor_config_and_validator(
        pipeline=pipeline,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=strict_gold_validation,
        bronze_output_path=bronze_output_path,
        silver_output_path=silver_output_path,
        gold_output_path=gold_output_path,
        flat_structure=flat_structure,
        gold_validator_factory=PanderaGoldValidator,
    )
    runtime_managers = build_runtime_managers(
        pipeline=pipeline,
        processor_config=processor_config,
        checkpoint_manager=checkpoint_manager,
        memory_monitor=memory_monitor,
        memory_config=memory_config,
        tracer=tracer,
        batch_id_factory=batch_id_factory,
    )
    (
        memory_manager,
        tracing_manager,
        effective_batch_id_factory,
        progress_service,
        checkpoint_recovery_service,
        execution_run_service,
    ) = runtime_managers
    _, batch_processing_service = build_components_and_processing_service(
        pipeline=pipeline,
        processor_config=processor_config,
        error_classifier=ErrorClassifier(),
        callbacks=callbacks,
        gold_filter=gold_filter,
        gold_validator=gold_validator,
        tracer=tracer,
        domain_event_emitter=domain_event_emitter,
        lock_validator=lock_validator,
        tracing_manager=tracing_manager,
        batch_id_factory=effective_batch_id_factory,
        create_batch_processing_components_fn=create_batch_processing_components_fn,
    )
    deps = _build_batch_executor_dependencies(
        pipeline=pipeline,
        shutdown_signal=shutdown_signal,
        memory_manager=memory_manager,
        progress_service=progress_service,
        checkpoint_recovery_service=checkpoint_recovery_service,
        execution_run_service=execution_run_service,
        batch_processing_service=batch_processing_service,
    )
    return BatchExecutor(
        services=pipeline.services,
        context=pipeline.context,
        config=processor_config,
        dependencies=deps,
        batch_size=pipeline.config.batch_size,
        checkpoint_interval=pipeline.config.checkpoint_interval,
    )


def _resolve_gold_filter(
    *,
    pipeline: BasePipeline,
    callbacks: PipelineCallbacksContext,
) -> GoldFilterCallback:
    """Resolve the effective gold filter based on runtime skip configuration."""
    if pipeline.runtime.skip_gold:
        return cast(GoldFilterCallback, lambda _context, _record: False)
    return callbacks.gold_filter


def _build_batch_executor_dependencies(
    *,
    pipeline: BasePipeline,
    shutdown_signal: ShutdownSignal,
    memory_manager: BatchMemoryManagerService,
    progress_service: BatchProgressService,
    checkpoint_recovery_service: BatchCheckpointRecoveryService,
    execution_run_service: BatchExecutionRunService,
    batch_processing_service: BatchProcessingService,
) -> BatchExecutorDependencies:
    """Create the runtime dependency bundle for BatchExecutor."""
    execution_state_service = BatchExecutionStateService()
    extraction_loop_service = BatchExtractionLoopService(
        batch_processing_service=batch_processing_service,
        shutdown_signal=shutdown_signal,
        memory_manager=memory_manager,
        progress_service=progress_service,
        checkpoint_recovery_service=checkpoint_recovery_service,
        checkpoint_interval=pipeline.config.checkpoint_interval
        or BatchExecutor.DEFAULT_CHECKPOINT_INTERVAL,
    )
    return BatchExecutorDependencies(
        memory_manager=memory_manager,
        execution_run_service=execution_run_service,
        extraction_loop_service=extraction_loop_service,
        execution_state_service=execution_state_service,
        processing_port=batch_processing_service,
        fsm=BatchExecutionFSM(),
    )


__all__ = ["create_batch_executor_from_pipeline"]

================================================================================
File: pipeline_builder.py
Path: factories\services\pipeline_builder.py
================================================================================
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Literal

from bioetl.application.core.wiring.runtime import (
    BatchProcessingComponents,
    CheckpointManagerService,
)
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
from bioetl.composition.factories.services.pipeline_batch_executor_builder import (
    create_batch_executor_from_pipeline as build_batch_executor_from_pipeline,
)
from bioetl.composition.factories.services.pipeline_processing_components_builder import (
    create_batch_processing_components as build_batch_processing_components,
)
from bioetl.composition.factories.services.pipeline_record_processor_builder import (
    create_record_processor_from_pipeline as build_record_processor_from_pipeline,
)

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.wiring.runtime import (
        BasePipeline,
        BatchExecutor,
        GoldFilterCallback,
        GoldTransformCallback,
        PipelineService,
        RecordProcessor,
        RecordProcessorConfig,
        ShutdownSignal,
        TransformCallback,
    )
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterPort,
    )
    from bioetl.domain.config import MemoryConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.medallion import LoadingStrategy
    from bioetl.domain.ports import (
        BatchIdGeneratorPort,
        CheckpointPort,
        GoldValidatorPort,
        LoggerPort,
        MemoryMonitorPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.domain.types import GoldSchemaType, RunID
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


def create_batch_processing_components(
    *,
    services: PipelineService,
    context: PipelineContext,
    config: RecordProcessorConfig,
    error_classifier: ErrorClassifier,
    transform_callback: TransformCallback,
    gold_filter_callback: GoldFilterCallback,
    gold_transform_callback: GoldTransformCallback,
    gold_validator: GoldValidatorPort,
    tracer: TracingPort | None = None,
    domain_event_emitter: DomainEventEmitterPort | None = None,
    lock_validator: Callable[[], Awaitable[bool]] | None = None,
) -> BatchProcessingComponents:
    return build_batch_processing_components(
        services=services,
        context=context,
        config=config,
        error_classifier=error_classifier,
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
        gold_validator=gold_validator,
        tracer=tracer,
        domain_event_emitter=domain_event_emitter,
        lock_validator=lock_validator,
    )


def create_checkpoint_manager(
    checkpoint_port: CheckpointPort,
    logger: LoggerPort,
    pipeline_name: str,
    run_id: RunID,
    resume: bool,
    *,
    loading_strategy: LoadingStrategy | None = None,
    metrics: MetricsPort | None = None,
    checkpoint_compatibility_service: object | None = None,
    current_metadata: CheckpointMetadata | None = None,
    compatibility_policy: Literal["observe", "soft_fail", "hard_fail"] = "soft_fail",
) -> CheckpointManagerService:
    return CheckpointManagerService(
        checkpoint_port=checkpoint_port,
        logger=logger,
        pipeline_name=pipeline_name,
        run_id=run_id,
        resume=resume,
        loading_strategy=loading_strategy,
        metrics=metrics,
        checkpoint_compatibility_service=checkpoint_compatibility_service,
        current_metadata=current_metadata,
        compatibility_policy=compatibility_policy,
    )


def create_record_processor_from_pipeline(
    *,
    pipeline: BasePipeline,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    callbacks: PipelineCallbacksContext,
    create_record_processor_fn: Callable[..., RecordProcessor],
    strict_gold_validation: bool = True,
    lock_validator: Callable[[], Awaitable[bool]] | None = None,
    tracer: TracingPort | None = None,
) -> RecordProcessor:
    return build_record_processor_from_pipeline(
        pipeline=pipeline,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        callbacks=callbacks,
        create_record_processor_fn=create_record_processor_fn,
        strict_gold_validation=strict_gold_validation,
        lock_validator=lock_validator,
        tracer=tracer,
    )


def create_batch_executor_from_pipeline(
    *,
    pipeline: BasePipeline,
    callbacks: PipelineCallbacksContext,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    checkpoint_manager: CheckpointManagerService,
    shutdown_signal: ShutdownSignal,
    create_batch_processing_components_fn: Callable[..., BatchProcessingComponents],
    strict_gold_validation: bool = True,
    lock_validator: Callable[[], Awaitable[bool]] | None = None,
    tracer: TracingPort | None = None,
    memory_monitor: MemoryMonitorPort | None = None,
    memory_config: MemoryConfig | None = None,
    bronze_output_path: str | None = None,
    silver_output_path: str | None = None,
    gold_output_path: str | None = None,
    flat_structure: bool = False,
    batch_id_factory: BatchIdGeneratorPort | None = None,
    domain_event_emitter: DomainEventEmitterPort | None = None,
) -> BatchExecutor:
    return build_batch_executor_from_pipeline(
        pipeline=pipeline,
        callbacks=callbacks,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=shutdown_signal,
        create_batch_processing_components_fn=create_batch_processing_components_fn,
        strict_gold_validation=strict_gold_validation,
        lock_validator=lock_validator,
        tracer=tracer,
        memory_monitor=memory_monitor,
        memory_config=memory_config,
        bronze_output_path=bronze_output_path,
        silver_output_path=silver_output_path,
        gold_output_path=gold_output_path,
        flat_structure=flat_structure,
        batch_id_factory=batch_id_factory,
        domain_event_emitter=domain_event_emitter,
    )


__all__ = [
    "BatchProcessingComponents",
    "create_batch_executor_from_pipeline",
    "create_batch_processing_components",
    "create_checkpoint_manager",
    "create_record_processor_from_pipeline",
]

================================================================================
File: pipeline_processing.py
Path: factories\services\pipeline_processing.py
================================================================================
"""Helpers for assembling batch processing services in composition layer."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from bioetl.application.core.wiring.runtime import (
    BasePipeline,
    BatchProcessingComponents,
    BatchProcessingService,
    BatchProcessingSupportService,
    BatchTracingManagerService,
    GoldFilterCallback,
    QuarantineManagerService,
    RecordProcessorConfig,
)
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.ports import (
    BatchIdGeneratorPort,
    GoldValidatorPort,
    TracingPort,
)

if TYPE_CHECKING:
    pass


def build_components_and_processing_service(
    *,
    pipeline: BasePipeline,
    processor_config: RecordProcessorConfig,
    error_classifier: ErrorClassifier,
    callbacks: PipelineCallbacksContext,
    gold_filter: GoldFilterCallback,
    gold_validator: GoldValidatorPort,
    tracer: TracingPort | None,
    domain_event_emitter: DomainEventEmitter | None = None,
    lock_validator: Callable[[], Awaitable[bool]] | None,
    tracing_manager: BatchTracingManagerService,
    batch_id_factory: BatchIdGeneratorPort,
    create_batch_processing_components_fn: Callable[..., BatchProcessingComponents],
) -> tuple[BatchProcessingComponents, BatchProcessingService]:
    """Build component stack and BatchProcessingService.

    Args:
        pipeline: Configured pipeline instance providing services and context.
        processor_config: Record processor configuration (table names, schemas, keys).
        error_classifier: Classifier for categorizing processing errors.
        callbacks: Pipeline transformation callbacks (transform, gold_filter, gold_transform).
        gold_filter: Predicate determining if a Silver record writes to Gold.
        gold_validator: Gold-layer validator port applied to processed records.
        tracer: Optional TracingPort for distributed tracing.
        lock_validator: Optional async callable for lock validation before writes.
        tracing_manager: Batch-level tracing manager for span lifecycle.
        batch_id_factory: Generator for unique batch identifiers.
        create_batch_processing_components_fn: Injectable callable for creating
            BatchProcessingComponents (allows test substitution).

    Returns:
        Tuple of (BatchProcessingComponents, BatchProcessingService).
    """
    components = create_batch_processing_components_fn(
        services=pipeline.services,
        context=pipeline.context,
        config=processor_config,
        error_classifier=error_classifier,
        transform_callback=callbacks.transform,
        gold_filter_callback=gold_filter,
        gold_transform_callback=callbacks.gold_transform,
        gold_validator=gold_validator,
        tracer=tracer,
        domain_event_emitter=domain_event_emitter,
        lock_validator=lock_validator,
    )
    quarantine_manager = QuarantineManagerService(
        quarantine_port=pipeline.services.quarantine,
        pipeline_name=processor_config.pipeline_name,
        metrics=pipeline.services.metrics,
        domain_event_emitter=domain_event_emitter,
    )
    support_service = BatchProcessingSupportService(
        services=pipeline.services,
        logger=pipeline.context.logger,
        batch_metrics=components.batch_metrics,
        transformer=components.transformer,
        writer=components.writer,
        tracing=tracing_manager,
        quarantine_manager=quarantine_manager,
        run_id=pipeline.context.run_id,
        domain_event_emitter=domain_event_emitter,
    )
    batch_processing_service = BatchProcessingService(
        services=pipeline.services,
        context=pipeline.context,
        config=processor_config,
        components=components,
        tracing_manager=tracing_manager,
        batch_id_factory=batch_id_factory,
        support_service=support_service,
    )
    return components, batch_processing_service

================================================================================
File: pipeline_processing_components_builder.py
Path: factories\services\pipeline_processing_components_builder.py
================================================================================
"""Assembly helpers for batch processing components."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.core.wiring.runtime import (
    BatchMetricsRecorderService,
    BatchProcessingComponents,
    BatchTransformer,
    BatchWriter,
    BatchWriterOptions,
    GoldFilterCallback,
    GoldTransformCallback,
    PipelineService,
    QuarantineManagerService,
    RecordNormalizationProcessor,
    RecordProcessorConfig,
    TransformCallback,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.ports import GoldValidatorPort, TracingPort


def create_batch_processing_components(
    *,
    services: PipelineService,
    context: PipelineContext,
    config: RecordProcessorConfig,
    error_classifier: ErrorClassifier,
    transform_callback: TransformCallback,
    gold_filter_callback: GoldFilterCallback,
    gold_transform_callback: GoldTransformCallback,
    gold_validator: GoldValidatorPort,
    tracer: TracingPort | None = None,
    domain_event_emitter: DomainEventEmitter | None = None,
    lock_validator: Callable[[], Awaitable[bool]] | None = None,
) -> BatchProcessingComponents:
    """Create batch metrics, transformer, and writer via composition DI."""
    batch_metrics = BatchMetricsRecorderService(
        services.metrics,
        f"{config.provider}_{config.entity_type}",
        context.run_type.value,
    )
    quarantine_manager = QuarantineManagerService(
        quarantine_port=services.quarantine,
        pipeline_name=config.pipeline_name,
        metrics=services.metrics,
        domain_event_emitter=domain_event_emitter,
    )
    normalization_processor = (
        RecordNormalizationProcessor(
            provider=config.provider,
            entity_type=config.entity_type,
            rule_set=config.normalization_rule_set,
            allow_compatibility_fallback=config.allow_compatibility_fallback,
            content_hash_include_fields=config.content_hash_include_fields,
            content_hash_exclude_fields=config.content_hash_exclude_fields,
            content_hash_policy_by_version=config.content_hash_policy_by_version,
        )
        if config.normalization_enabled
        else None
    )
    transformer = BatchTransformer(
        context=context,
        config=config,
        error_classifier=error_classifier,
        quarantine_manager=quarantine_manager,
        batch_metrics=batch_metrics,
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
        normalization_processor=normalization_processor,
    )
    column_orderer = (
        ColumnOrderService(context.logger, column_groups=config.column_groups)
        if config.column_groups
        else None
    )
    writer = BatchWriter(
        storage=services.storage,
        context=context,
        config=config,
        gold_validator=gold_validator,
        error_classifier=error_classifier,
        batch_metrics=batch_metrics,
        options=BatchWriterOptions(
            tracer=tracer,
            lock_validator=lock_validator,
            column_orderer=column_orderer,
        ),
    )
    return BatchProcessingComponents(
        batch_metrics=batch_metrics,
        transformer=transformer,
        writer=writer,
    )


__all__ = ["create_batch_processing_components"]

================================================================================
File: pipeline_record_processor_builder.py
Path: factories\services\pipeline_record_processor_builder.py
================================================================================
"""Record-processor assembly helpers for pipeline_builder facade."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

from bioetl.application.core.wiring.runtime import (
    BasePipeline,
    RecordProcessor,
    RecordProcessorConfig,
)
from bioetl.composition.factories.services._record_processor_policy_support import (
    extract_gold_schema_policy_by_version,
    extract_hash_policy,
    extract_hash_policy_by_version,
)
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    import pandera as pdr
    import pyarrow as pa

    from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
    from bioetl.domain.config import DQConfig
    from bioetl.domain.ports import GoldValidatorPort, TracingPort
    from bioetl.domain.types import GoldSchemaType


def build_record_processor_config_and_validator(
    *,
    pipeline: BasePipeline,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    strict_gold_validation: bool,
    bronze_output_path: str | None,
    silver_output_path: str | None,
    gold_output_path: str | None,
    flat_structure: bool,
    gold_validator_factory: Callable[..., GoldValidatorPort] = PanderaGoldValidator,
) -> tuple[RecordProcessorConfig, GoldValidatorPort]:
    """Build RecordProcessorConfig plus Gold validator from pipeline state."""
    include_fields, exclude_fields = extract_hash_policy(pipeline)
    hash_policy_by_version = extract_hash_policy_by_version(
        pipeline,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    )
    gold_schema_policy_by_version = extract_gold_schema_policy_by_version(
        pipeline,
        gold_schema=gold_schema,
    )
    active_gold_schema = (
        gold_schema_policy_by_version.active_schema
        if gold_schema_policy_by_version is not None
        else gold_schema
    )
    processor_config = RecordProcessorConfig(
        pipeline_name=pipeline.config.pipeline_name,
        provider=pipeline.config.provider,
        entity_type=pipeline.config.entity_type,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        dq_config=cast("DQConfig | None", pipeline.config.dq),
        table_config=pipeline.config.table,
        bronze_output_path=bronze_output_path,
        silver_output_path=silver_output_path,
        gold_output_path=gold_output_path,
        flat_structure=flat_structure,
        column_groups=pipeline.config.column_groups,
        scd_config=pipeline.config.scd_config,
        content_hash_include_fields=include_fields,
        content_hash_exclude_fields=exclude_fields,
        content_hash_policy_by_version=hash_policy_by_version,
        gold_schema_policy_by_version=gold_schema_policy_by_version,
    )
    gold_validator = gold_validator_factory(
        cast("pdr.DataFrameSchema | None", active_gold_schema),
        strict=strict_gold_validation,
    )
    return processor_config, gold_validator


def create_record_processor_from_pipeline(
    *,
    pipeline: BasePipeline,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    callbacks: PipelineCallbacksContext,
    create_record_processor_fn: Callable[..., RecordProcessor],
    strict_gold_validation: bool = True,
    lock_validator: Callable[[], Awaitable[bool]] | None = None,
    tracer: TracingPort | None = None,
) -> RecordProcessor:
    """Project pipeline fields into the injected record-processor factory."""
    include_fields, exclude_fields = extract_hash_policy(pipeline)
    hash_policy_by_version = extract_hash_policy_by_version(
        pipeline,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    )
    gold_schema_policy_by_version = extract_gold_schema_policy_by_version(
        pipeline,
        gold_schema=gold_schema,
    )
    return create_record_processor_fn(
        services=pipeline.services,
        context=pipeline.context,
        pipeline_name=pipeline.config.pipeline_name,
        provider=pipeline.config.provider,
        entity_type=pipeline.config.entity_type,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        dq_config=pipeline.config.dq,
        primary_keys=pipeline.config.table.primary_keys,
        silver_table=pipeline.config.effective_silver_table,
        gold_table=pipeline.config.effective_gold_table,
        silver_write_mode=pipeline.config.table.silver_write_mode,
        gold_write_mode=pipeline.config.table.gold_write_mode,
        on_schema_mismatch=pipeline.config.table.on_schema_mismatch,
        transform_callback=callbacks.transform,
        gold_filter_callback=callbacks.gold_filter,
        gold_transform_callback=callbacks.gold_transform,
        strict_gold_validation=strict_gold_validation,
        lock_validator=lock_validator,
        tracer=tracer,
        column_groups=tuple(pipeline.config.column_groups),
        scd_config=pipeline.config.scd_config,
        content_hash_include_fields=include_fields,
        content_hash_exclude_fields=exclude_fields,
        content_hash_policy_by_version=hash_policy_by_version,
        gold_schema_policy_by_version=gold_schema_policy_by_version,
    )

================================================================================
File: polars_join_adapter.py
Path: factories\services\polars_join_adapter.py
================================================================================
"""Composition-facing adapter for composite Polars join execution."""

from __future__ import annotations

from bioetl.application.composite.join_execution import JoinExecutorService


class PolarsJoinAdapter:
    """Adapter wrapper for JoinExecutorService in composition layer.

    This real adapter provides composition-specific interface and behavior
    while delegating to the underlying JoinExecutorService.
    """

    def __init__(self, join_service: JoinExecutorService) -> None:
        """Initialize adapter with underlying join service.

        Args:
            join_service: The JoinExecutorService to adapt
        """
        self._join_service = join_service

    def get_polars_join_type(self):
        """Get current join type from adapted service."""
        return self._join_service.get_polars_join_type()

    def execute_polars_join(self, *args, **kwargs):
        """Execute join through adapted service."""
        return self._join_service.execute_polars_join(*args, **kwargs)


__all__ = ["PolarsJoinAdapter"]

================================================================================
File: port_factories.py
Path: factories\services\port_factories.py
================================================================================
"""Port factory functions for local deployment adapters.

Extracted from BaseServicesFactory to keep factory.py within LOC limits.
"""

from __future__ import annotations

from typing import cast

from bioetl.composition.observability_resolution import resolve_metrics_port
from bioetl.domain.ports import (
    CheckpointPort,
    LockPort,
    MetricsPort,
    QuarantinePort,
)
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.observability import PrometheusMetrics
from bioetl.infrastructure.quarantine import UnifiedQuarantineAdapter

__all__ = [
    "create_checkpoint",
    "create_lock",
    "create_metrics",
    "create_quarantine",
    "is_metrics_port_like",
]


def create_lock() -> LockPort:
    """Create in-memory lock for local deployment."""
    lock = MemoryLock()
    assert isinstance(lock, LockPort), (
        f"MemoryLock must implement LockPort, got {type(lock)}"
    )
    return lock


def create_checkpoint(storage_ctx: object) -> CheckpointPort:
    """Create local filesystem checkpoint."""
    checkpoint = LocalCheckpointAdapter(base_path=storage_ctx.checkpoints_path)
    assert isinstance(checkpoint, CheckpointPort), (
        f"LocalCheckpointAdapter must implement CheckpointPort, got {type(checkpoint)}"
    )
    return checkpoint


def create_quarantine(settings: object) -> QuarantinePort:
    """Create unified quarantine storage."""
    quarantine = UnifiedQuarantineAdapter(base_path=str(settings.quarantine_path))
    assert isinstance(quarantine, QuarantinePort), (
        f"UnifiedQuarantineAdapter must implement QuarantinePort, got {type(quarantine)}"
    )
    return quarantine


def create_metrics(settings: object) -> MetricsPort:
    """Create metrics port based on settings."""
    if not _metrics_enabled(settings):
        return NoOpMetrics(warn_on_use=False)

    observability = getattr(settings, "observability", None)
    if observability is None:
        metrics: object = PrometheusMetrics()
    else:
        metrics = resolve_metrics_port(metrics=None, settings=settings)

    if isinstance(metrics, MetricsPort):
        assert isinstance(metrics, MetricsPort), (
            f"Metrics adapter must implement MetricsPort, got {type(metrics)}"
        )
        return metrics
    if is_metrics_port_like(metrics):
        return cast("MetricsPort", metrics)
    raise TypeError(f"Metrics adapter must implement MetricsPort, got {type(metrics)}")


def is_metrics_port_like(candidate: object) -> bool:
    """Duck-typed fallback for patched test doubles."""
    required_methods = (
        "observe_histogram",
        "increment_counter",
        "set_gauge",
        "close",
    )
    return all(
        callable(getattr(candidate, method_name, None))
        for method_name in required_methods
    )


def _metrics_enabled(settings: object) -> bool:
    """Support both legacy flat settings and current nested observability config."""
    observability = getattr(settings, "observability", None)
    if observability is not None and hasattr(observability, "metrics_enabled"):
        return bool(observability.metrics_enabled)
    return bool(getattr(settings, "metrics_enabled", False))

================================================================================
File: runtime_managers.py
Path: factories\services\runtime_managers.py
================================================================================
"""Runtime manager builders for BatchExecutor.

Extracted from pipeline_builder.py to keep it within LOC limits.
"""

from __future__ import annotations

from bioetl.application.core.wiring.runtime import (
    BasePipeline,
    BatchCheckpointRecoveryService,
    BatchExecutionLifecycleService,
    BatchExecutionRunService,
    BatchExecutor,
    BatchMemoryManagerService,
    BatchProgressService,
    BatchTracingManagerService,
    CheckpointManagerService,
    RecordProcessorConfig,
)
from bioetl.composition.factories.batch_id_generator import UuidBatchIdGenerator
from bioetl.composition.factories.services.common_service_wiring import resolve_tracer
from bioetl.domain.config import MemoryConfig
from bioetl.domain.ports import (
    BatchIdGeneratorPort,
    MemoryMonitorPort,
    TracingPort,
)

__all__ = ["build_runtime_managers"]


def build_runtime_managers(
    *,
    pipeline: BasePipeline,
    processor_config: RecordProcessorConfig,
    checkpoint_manager: CheckpointManagerService,
    memory_monitor: MemoryMonitorPort | None,
    memory_config: MemoryConfig | None,
    tracer: TracingPort | None,
    batch_id_factory: BatchIdGeneratorPort | None,
) -> tuple[
    BatchMemoryManagerService,
    BatchTracingManagerService,
    BatchIdGeneratorPort,
    BatchProgressService,
    BatchCheckpointRecoveryService,
    BatchExecutionRunService,
]:
    """Build runtime manager instances for BatchExecutor."""
    initial_batch_size = pipeline.config.batch_size or BatchExecutor.DEFAULT_BATCH_SIZE
    memory_manager = BatchMemoryManagerService(
        initial_batch_size=initial_batch_size,
        memory_monitor=memory_monitor,
        memory_config=memory_config,
        logger=pipeline.services.logger,
    )
    resolved_tracer = resolve_tracer(tracer)
    tracing_manager = BatchTracingManagerService(
        tracer=resolved_tracer,
        context=pipeline.context,
        config=processor_config,
        initial_batch_size=initial_batch_size,
        adaptive_sizing_enabled=memory_manager.enabled,
    )
    progress_service = BatchProgressService(
        logger=pipeline.services.logger, data_source=pipeline.services.data_source
    )
    checkpoint_recovery_service = BatchCheckpointRecoveryService(
        checkpoint_manager=checkpoint_manager,
        logger=pipeline.services.logger,
        metrics=pipeline.services.metrics,
        tracer=resolved_tracer,
        pipeline_name=pipeline.pipeline_name,
    )
    execution_lifecycle_service = BatchExecutionLifecycleService(
        progress_service=progress_service,
        tracing_manager=tracing_manager,
        checkpoint_recovery_service=checkpoint_recovery_service,
    )
    execution_run_service = BatchExecutionRunService(
        execution_lifecycle_service=execution_lifecycle_service
    )
    return (
        memory_manager,
        tracing_manager,
        batch_id_factory or UuidBatchIdGenerator(),
        progress_service,
        checkpoint_recovery_service,
        execution_run_service,
    )

================================================================================
File: __init__.py
Path: factories\storage\__init__.py
================================================================================
"""Storage factory subpackage."""

from __future__ import annotations

from bioetl.composition.factories.storage.adapter import StorageAdapter
from bioetl.composition.factories.storage.factory import StorageContext, StorageFactory
from bioetl.composition.factories.storage.resilience import (
    create_silver_atomic_retry_policy,
    create_silver_merge_resilience_policy,
)

__all__ = [
    "StorageAdapter",
    "StorageContext",
    "StorageFactory",
    "create_silver_atomic_retry_policy",
    "create_silver_merge_resilience_policy",
]

================================================================================
File: _audit.py
Path: factories\storage\_audit.py
================================================================================
"""Audit wiring helpers for canonical storage factory assembly."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports import AuditPort
from bioetl.domain.ports.noop import NoOpAudit
from bioetl.infrastructure.audit.file_audit import FileAuditAdapter

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.infrastructure.config import Settings

__all__ = ["create_audit_port"]


def create_audit_port(
    *,
    settings: Settings,
    logger: LoggerPort,
    metrics: MetricsPort | None = None,
    tracing: TracingPort | None = None,
) -> AuditPort:
    """Create the canonical audit port for storage runtime wiring.

    Returns a concrete file-backed audit adapter when audit logging is enabled,
    otherwise returns an explicit ``NoOpAudit``.
    """
    observability = settings.observability
    if not observability.audit_enabled:
        return NoOpAudit()

    base_path = observability.audit_base_path
    resolved_path = (
        Path(base_path)
        if base_path is not None
        else _default_audit_path(settings=settings)
    )
    return FileAuditAdapter(
        base_path=resolved_path,
        logger=logger,
        metrics=metrics,
        tracing=tracing,
    )


def _default_audit_path(*, settings: Settings) -> Path:
    """Return the default audit directory under the managed output root."""
    return settings.data_dir / "output" / "audit"

================================================================================
File: _bronze.py
Path: factories\storage\_bronze.py
================================================================================
"""Bronze writer factory helpers for StorageFactory."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.infrastructure.control_plane import FileLineageStore
from bioetl.infrastructure.storage.bronze_writer import BronzeWriterRuntimeServices
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter

if TYPE_CHECKING:
    from bioetl.application.services.lineage.metadata_coordinator import (
        MetadataCoordinator,
    )
    from bioetl.domain.ports import AuditPort, LoggerPort, MetricsPort, TracingPort
    from bioetl.infrastructure.schemas.pipeline_config import SinkLayerConfig
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter


def create_bronze_writer(
    *,
    writer_cls: type[BronzeWriter],
    base_path: Path,
    config: SinkLayerConfig | None,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracing: TracingPort | None,
    metadata_coordinator: MetadataCoordinator | None,
    audit: AuditPort,
    flat_structure: bool,
) -> BronzeWriter:
    """Create configured Bronze writer.

    Args:
        writer_cls: BronzeWriter class to instantiate.
        base_path: Root directory for Bronze layer storage.
        config: Optional sink layer config providing save_json and save_metadata flags.
        logger: LoggerPort for structured logging.
        metrics: MetricsPort for recording storage metrics.
        tracing: TracingPort resolved by composition bootstrap.
        metadata_coordinator: Optional coordinator for metadata side-effects.
        flat_structure: If True, writes files without provider/entity subdirectories.

    Returns:
        Configured BronzeWriter instance for the Bronze storage layer.
    """
    save_json = config.save_json if config else False
    save_metadata = config.save_metadata if config else False
    if save_metadata and metadata_coordinator is None:
        raise RuntimeError(
            "Bronze metadata publication requires MetadataCoordinator when "
            "save_metadata is enabled."
        )
    lineage_store = (
        FileLineageStore(base_path=base_path.parent / "control" / "lineage")
        if save_metadata
        else None
    )
    metadata_writer = (
        MetadataWriter(logger=logger) if save_metadata else NoOpMetadataWriter()
    )
    if tracing is None:
        raise TypeError(
            "BronzeWriter requires explicit tracing injection. "
            "Build NoOpTracing in composition when tracing is disabled."
        )
    return writer_cls(
        base_path=base_path,
        logger=logger,
        metrics=metrics,
        save_json=save_json,
        json_path=None,
        runtime_services=BronzeWriterRuntimeServices(
            tracing=tracing,
            audit=audit,
            metadata_writer=metadata_writer,
            save_metadata=save_metadata,
            metadata_coordinator=metadata_coordinator,
            lineage_store=lineage_store,
        ),
        flat_structure=flat_structure,
    )

================================================================================
File: _context_resolution.py
Path: factories\storage\_context_resolution.py
================================================================================
"""Context and path resolution helpers for StorageFactory assembly flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.infrastructure.export.csv_exporter import CsvExporter

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        PipelineYamlConfig,
        SinkLayerConfig,
    )


@dataclass(frozen=True, slots=True)
class StorageCreationContext:
    """Resolved per-layer configuration for storage adapter creation (RF-005a)."""

    bronze_config: SinkLayerConfig | None
    silver_config: SinkLayerConfig | None
    gold_config: SinkLayerConfig | None
    bronze_path: Path
    silver_path: Path
    gold_path: Path
    bronze_flat: bool
    silver_flat: bool
    gold_flat: bool
    silver_csv_exporter: CsvExporter | None
    gold_csv_exporter: CsvExporter | None
    pipeline_name: str


def create_csv_exporter_from_config(
    csv_cfg: object | None,
    logger: LoggerPort,
    override_path: Path | None = None,
) -> CsvExporter | None:
    """Create CsvExporter from config, or None if disabled/unconfigured."""
    if not (csv_cfg and getattr(csv_cfg, "enabled", False)):
        return None
    path = override_path or getattr(csv_cfg, "path", None)
    if path is None:
        return None
    return CsvExporter(
        base_path=str(path),
        logger=logger,
        delimiter=str(getattr(csv_cfg, "delimiter", ",")),
        header=bool(getattr(csv_cfg, "header", True)),
        encoding=str(getattr(csv_cfg, "encoding", "utf-8")),
    )


def resolve_layer_path(
    layer_config: SinkLayerConfig | None,
    default_path: Path,
    use_yaml_paths: bool,
) -> Path:
    """Resolve storage path from sink config or fall back to default."""
    if use_yaml_paths and layer_config and layer_config.path:
        return Path(layer_config.path)
    return default_path


def get_layer_configs(
    config: PipelineYamlConfig,
) -> tuple[SinkLayerConfig | None, SinkLayerConfig | None, SinkLayerConfig | None]:
    """Extract per-layer sink configs: (bronze, silver, gold), each may be None."""
    return config.sink.get("bronze"), config.sink.get("silver"), config.sink.get("gold")


def resolve_storage_paths(
    settings: Settings,
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
) -> tuple[bool, Path, Path, Path]:
    """Resolve storage paths; returns (use_yaml_paths, bronze, silver, gold)."""
    use_yaml_paths = not settings.test_mode
    return (
        use_yaml_paths,
        resolve_layer_path(bronze_config, settings.bronze_path, use_yaml_paths),
        resolve_layer_path(silver_config, settings.silver_path, use_yaml_paths),
        resolve_layer_path(gold_config, settings.gold_path, use_yaml_paths),
    )


def create_layer_exporters(
    *,
    settings: Settings,
    logger: LoggerPort,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
    silver_path: Path,
    gold_path: Path,
) -> tuple[CsvExporter | None, CsvExporter | None]:
    """Create optional CSV exporters for Silver and Gold layers."""
    override = silver_path if settings.test_mode else None
    silver_csv = create_csv_exporter_from_config(
        silver_config.csv_export if silver_config else None, logger, override
    )
    override = gold_path if settings.test_mode else None
    gold_csv = create_csv_exporter_from_config(
        gold_config.csv_export if gold_config else None, logger, override
    )
    return silver_csv, gold_csv


def resolve_export_flags(
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
) -> tuple[bool, bool, bool, bool]:
    """Resolve (save_json, bronze_meta, silver_meta, gold_meta) flags."""
    return (
        bronze_config.save_json if bronze_config else False,
        bronze_config.save_metadata if bronze_config else False,
        silver_config.save_metadata if silver_config else False,
        gold_config.save_metadata if gold_config else False,
    )


def log_export_status(
    logger: LoggerPort,
    save_json: bool,
    silver_csv_exporter: CsvExporter | None,
    gold_csv_exporter: CsvExporter | None,
    bronze_save_metadata: bool,
    silver_save_metadata: bool,
    gold_save_metadata: bool,
) -> None:
    """Log active export settings for observability."""
    if save_json:
        logger.info("JSON export enabled for Bronze layer (alongside zst files)")
    if bronze_save_metadata:
        logger.info("metadata_export_enabled", layer="bronze")
    if silver_save_metadata:
        logger.info("metadata_export_enabled", layer="silver")
    if gold_save_metadata:
        logger.info("metadata_export_enabled", layer="gold")
    if silver_csv_exporter:
        logger.info(
            "csv_export_enabled",
            layer="silver",
            base_path=str(silver_csv_exporter.base_path),
        )
    if gold_csv_exporter:
        logger.info(
            "csv_export_enabled",
            layer="gold",
            base_path=str(gold_csv_exporter.base_path),
        )


def log_configured_export_status(
    *,
    logger: LoggerPort,
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
    silver_csv_exporter: CsvExporter | None,
    gold_csv_exporter: CsvExporter | None,
) -> None:
    """Resolve and log export settings for configured layers."""
    save_json, bronze_save_metadata, silver_save_metadata, gold_save_metadata = (
        resolve_export_flags(bronze_config, silver_config, gold_config)
    )
    log_export_status(
        logger,
        save_json,
        silver_csv_exporter,
        gold_csv_exporter,
        bronze_save_metadata,
        silver_save_metadata,
        gold_save_metadata,
    )


def resolve_flat_structure_flags(
    *,
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
    use_yaml_paths: bool,
) -> tuple[bool, bool, bool]:
    """Resolve (bronze, silver, gold) flat-structure flags."""
    return (
        (bronze_config.flat_structure if bronze_config else False) and use_yaml_paths,
        (silver_config.flat_structure if silver_config else False) and use_yaml_paths,
        (gold_config.flat_structure if gold_config else False) and use_yaml_paths,
    )


def build_storage_creation_context(
    *,
    settings: Settings,
    config: PipelineYamlConfig,
    logger: LoggerPort,
    pipeline_name: str,
) -> StorageCreationContext:
    """Run the full layer-resolution pipeline and return a bundled context."""
    bronze_config, silver_config, gold_config = get_layer_configs(config)
    use_yaml_paths, bronze_path, silver_path, gold_path = resolve_storage_paths(
        settings=settings,
        bronze_config=bronze_config,
        silver_config=silver_config,
        gold_config=gold_config,
    )
    silver_csv_exporter, gold_csv_exporter = create_layer_exporters(
        settings=settings,
        logger=logger,
        silver_config=silver_config,
        gold_config=gold_config,
        silver_path=silver_path,
        gold_path=gold_path,
    )
    log_configured_export_status(
        logger=logger,
        bronze_config=bronze_config,
        silver_config=silver_config,
        gold_config=gold_config,
        silver_csv_exporter=silver_csv_exporter,
        gold_csv_exporter=gold_csv_exporter,
    )
    bronze_flat, silver_flat, gold_flat = resolve_flat_structure_flags(
        bronze_config=bronze_config,
        silver_config=silver_config,
        gold_config=gold_config,
        use_yaml_paths=use_yaml_paths,
    )
    return StorageCreationContext(
        bronze_config=bronze_config,
        silver_config=silver_config,
        gold_config=gold_config,
        bronze_path=bronze_path,
        silver_path=silver_path,
        gold_path=gold_path,
        bronze_flat=bronze_flat,
        silver_flat=silver_flat,
        gold_flat=gold_flat,
        silver_csv_exporter=silver_csv_exporter,
        gold_csv_exporter=gold_csv_exporter,
        pipeline_name=pipeline_name,
    )

================================================================================
File: _gold.py
Path: factories\storage\_gold.py
================================================================================
"""Gold writer factory helpers for StorageFactory."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.control_plane import FileLineageStore
from bioetl.infrastructure.storage.gold.runtime_helpers import (
    GoldWriterRuntimeServices,
)
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter

if TYPE_CHECKING:
    from bioetl.application.services.lineage.metadata_coordinator import (
        MetadataCoordinator,
    )
    from bioetl.domain.ports import AuditPort, LoggerPort, MetricsPort, TracingPort
    from bioetl.infrastructure.export.csv_exporter import CsvExporter
    from bioetl.infrastructure.schemas.pipeline_config import SinkLayerConfig
    from bioetl.infrastructure.storage.gold_writer import GoldWriter


def create_gold_writer(
    *,
    writer_cls: type[GoldWriter],
    base_path: Path,
    config: SinkLayerConfig | None,
    logger: LoggerPort,
    tracing: TracingPort,
    csv_exporter: CsvExporter | None,
    metadata_coordinator: MetadataCoordinator | None,
    audit: AuditPort,
    transform_version: str | None,
    transform_steps: tuple[str, ...] | None,
    flat_structure: bool,
    metrics: MetricsPort | None = None,
    contract_rollout_policy: ContractRolloutPolicy | None = None,
) -> GoldWriter:
    """Create configured Gold writer.

    Args:
        writer_cls: GoldWriter class to instantiate.
        base_path: Root directory for Gold layer storage.
        config: Optional sink layer config providing save_metadata flag.
        logger: LoggerPort for structured logging.
        tracing: Explicit TracingPort resolved by composition bootstrap.
        csv_exporter: Optional CSV exporter for parallel Gold CSV output.
        metadata_coordinator: Optional coordinator for metadata side-effects.
        transform_version: Transform version tag written to Gold metadata.
        transform_steps: Ordered transform step labels for metadata.
        flat_structure: If True, writes files without provider/entity subdirectories.

    Returns:
        Configured GoldWriter instance for the Gold storage layer.
    """
    save_metadata = config.save_metadata if config else False
    lineage_store = (
        FileLineageStore(base_path=base_path.parent / "control" / "lineage")
        if save_metadata
        else None
    )
    metadata_writer = (
        MetadataWriter(logger=logger) if save_metadata else NoOpMetadataWriter()
    )
    if tracing is None:
        raise TypeError(
            "GoldWriter requires explicit tracing injection. "
            "Build NoOpTracing in composition when tracing is disabled."
        )
    return writer_cls(
        base_path=base_path,
        logger=logger,
        transform_version=transform_version,
        transform_steps=transform_steps,
        runtime_services=GoldWriterRuntimeServices(
            csv_exporter=csv_exporter,
            tracing=tracing,
            metrics=metrics,
            audit=audit,
            metadata_writer=metadata_writer,
            metadata_coordinator=metadata_coordinator,
            lineage_store=lineage_store,
            contract_rollout_policy=contract_rollout_policy,
        ),
        # Keep legacy kwarg for constructor-call compatibility in tests and shims.
        csv_exporter=csv_exporter,
        flat_structure=flat_structure,
    )

================================================================================
File: _helpers.py
Path: factories\storage\_helpers.py
================================================================================
"""Helper functions for StorageFactory assembly flow."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ._audit import create_audit_port
from ._bronze import create_bronze_writer
from ._context_resolution import (
    StorageCreationContext,
    build_storage_creation_context,
    create_csv_exporter_from_config,
    create_layer_exporters,
    get_layer_configs,
    log_configured_export_status,
    log_export_status,
    resolve_export_flags,
    resolve_flat_structure_flags,
    resolve_layer_path,
    resolve_storage_paths,
)
from ._layer_writers import (
    create_gold_layer_writer_impl,
    create_silver_layer_writer_impl,
    load_contract_rollout_policy,
)
from ._resilience import (
    create_silver_atomic_retry_policy,
    create_silver_merge_resilience_policy,
)
from .adapter import StorageAdapter

if TYPE_CHECKING:
    from bioetl.application.services.lineage.metadata_coordinator import (
        MetadataCoordinator,
    )
    from bioetl.domain.ports import (
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = [
    "StorageCreationContext",
    "build_storage_creation_context",
    "create_csv_exporter_from_config",
    "create_layer_exporters",
    "create_storage_adapter",
    "get_layer_configs",
    "log_configured_export_status",
    "log_export_status",
    "resolve_delta_writer_base_path",
    "resolve_delta_writer_flat_structure",
    "resolve_export_flags",
    "resolve_flat_structure_flags",
    "resolve_layer_path",
    "resolve_storage_paths",
]


def _has_provider_entity_suffix(
    path: Path,
    *,
    provider: str,
    entity_type: str,
) -> bool:
    """Return True when a path already ends with provider/entity segments."""
    parts = Path(str(path).replace("\\", "/")).parts
    if len(parts) < 2:
        return False
    return parts[-2:] == (provider, entity_type)


def resolve_delta_writer_base_path(
    resolved_path: Path,
    *,
    provider: str,
    entity_type: str,
    flat_structure: bool,
) -> Path:
    """Normalize Delta writer base_path to the layer root when path is entity-scoped.

    Storage contexts still expose the fully resolved per-pipeline target path for
    observability and report generation. Delta writers, however, must keep a
    layer-root base path so downstream maintenance helpers can append the logical
    table id exactly once.
    """
    runtime_path = Path(str(resolved_path).replace("\\", "/"))
    if flat_structure:
        return runtime_path
    if _has_provider_entity_suffix(
        runtime_path,
        provider=provider,
        entity_type=entity_type,
    ):
        return runtime_path.parent.parent
    return runtime_path


def resolve_delta_writer_flat_structure(
    resolved_path: Path,
    *,
    provider: str,
    entity_type: str,
    flat_structure: bool,
) -> bool:
    """Downgrade entity-scoped flat Delta paths to layer-root/table-name mode.

    When configuration normalization already materializes a path like
    ``data/output/silver/provider/entity``, keeping ``flat_structure=True`` would
    collapse all Delta writes onto that single directory and break maintenance
    helpers that work with logical table ids. In that case we switch writers back
    to the canonical layer-root + logical-table contract.
    """
    if not flat_structure:
        return False
    return not _has_provider_entity_suffix(
        resolved_path,
        provider=provider,
        entity_type=entity_type,
    )


def create_storage_adapter(
    *,
    ctx: StorageCreationContext,
    bronze_writer_cls: type[BronzeWriter],
    silver_writer_cls: type[SilverWriter],
    gold_writer_cls: type[GoldWriter],
    settings: Settings,
    config: PipelineYamlConfig,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracing: TracingPort,
    metadata_coordinator: MetadataCoordinator | None,
    silver_validator: SilverValidatorPort | None,
) -> StorageAdapter:
    """Create StorageAdapter with Bronze/Silver/Gold writers."""
    audit = create_audit_port(
        settings=settings,
        logger=logger,
        metrics=metrics,
        tracing=tracing,
    )
    metadata_atomic_retry_policy = create_silver_atomic_retry_policy(settings)
    merge_resilience_policy = create_silver_merge_resilience_policy(settings)
    silver_writer = create_silver_layer_writer_impl(
        ctx=ctx,
        silver_writer_cls=silver_writer_cls,
        config=config,
        logger=logger,
        metrics=metrics,
        tracing=tracing,
        metadata_coordinator=metadata_coordinator,
        silver_validator=silver_validator,
        audit=audit,
        metadata_atomic_retry_policy=metadata_atomic_retry_policy,
        merge_resilience_policy=merge_resilience_policy,
        resolve_delta_writer_base_path_fn=resolve_delta_writer_base_path,
        resolve_delta_writer_flat_structure_fn=resolve_delta_writer_flat_structure,
        load_contract_rollout_policy_fn=load_contract_rollout_policy,
    )
    gold_writer = create_gold_layer_writer_impl(
        ctx=ctx,
        gold_writer_cls=gold_writer_cls,
        config=config,
        logger=logger,
        metrics=metrics,
        tracing=tracing,
        metadata_coordinator=metadata_coordinator,
        audit=audit,
        resolve_delta_writer_base_path_fn=resolve_delta_writer_base_path,
        resolve_delta_writer_flat_structure_fn=resolve_delta_writer_flat_structure,
        load_contract_rollout_policy_fn=load_contract_rollout_policy,
    )
    bronze_writer = create_bronze_writer(
        writer_cls=bronze_writer_cls,
        base_path=ctx.bronze_path,
        config=ctx.bronze_config,
        logger=logger,
        metrics=metrics,
        tracing=tracing,
        metadata_coordinator=metadata_coordinator,
        audit=audit,
        flat_structure=ctx.bronze_flat,
    )
    return StorageAdapter(
        bronze_writer=bronze_writer,
        silver_writer=silver_writer,
        gold_writer=gold_writer,
    )

================================================================================
File: _layer_writers.py
Path: factories\storage\_layer_writers.py
================================================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)

from ._gold import create_gold_writer
from ._silver import CreateSilverWriterRequest, create_silver_writer

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.services.lineage.metadata_coordinator import (
        MetadataCoordinator,
    )
    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
    from bioetl.infrastructure.storage.delta.resilience import (
        AdaptiveRetryPolicy,
        SilverMergeResiliencePolicy,
    )
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

    from ._context_resolution import StorageCreationContext


def load_contract_rollout_policy(config: PipelineYamlConfig) -> ContractRolloutPolicy:
    return load_pipeline_contract_policy(
        config.provider,
        config.entity_type,
    ).to_contract_rollout_policy()


def create_silver_layer_writer_impl(
    *,
    ctx: StorageCreationContext,
    silver_writer_cls: type[SilverWriter],
    config: PipelineYamlConfig,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracing: TracingPort,
    metadata_coordinator: MetadataCoordinator | None,
    silver_validator: SilverValidatorPort | None,
    audit: AuditPort,
    metadata_atomic_retry_policy: AdaptiveRetryPolicy,
    merge_resilience_policy: SilverMergeResiliencePolicy,
    resolve_delta_writer_base_path_fn: Callable[..., object],
    resolve_delta_writer_flat_structure_fn: Callable[..., bool],
    load_contract_rollout_policy_fn: Callable[
        [PipelineYamlConfig], ContractRolloutPolicy
    ],
) -> SilverWriter:
    silver_writer_flat = resolve_delta_writer_flat_structure_fn(
        ctx.silver_path,
        provider=config.provider,
        entity_type=config.entity_type,
        flat_structure=ctx.silver_flat,
    )
    return create_silver_writer(
        CreateSilverWriterRequest(
            writer_cls=silver_writer_cls,
            base_path=resolve_delta_writer_base_path_fn(
                ctx.silver_path,
                provider=config.provider,
                entity_type=config.entity_type,
                flat_structure=silver_writer_flat,
            ),
            config=ctx.silver_config,
            logger=logger,
            tracing=tracing,
            csv_exporter=ctx.silver_csv_exporter,
            metadata_coordinator=metadata_coordinator,
            audit=audit,
            transform_version=config.transform.version,
            transform_steps=tuple(config.transform.steps),
            flat_structure=silver_writer_flat,
            silver_validator=silver_validator,
            metrics=metrics,
            metadata_atomic_retry_policy=metadata_atomic_retry_policy,
            merge_resilience_policy=merge_resilience_policy,
            contract_rollout_policy=load_contract_rollout_policy_fn(config),
            pipeline_name=ctx.pipeline_name,
        )
    )


def create_gold_layer_writer_impl(
    *,
    ctx: StorageCreationContext,
    gold_writer_cls: type[GoldWriter],
    config: PipelineYamlConfig,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracing: TracingPort,
    metadata_coordinator: MetadataCoordinator | None,
    audit: AuditPort,
    resolve_delta_writer_base_path_fn: Callable[..., object],
    resolve_delta_writer_flat_structure_fn: Callable[..., bool],
    load_contract_rollout_policy_fn: Callable[
        [PipelineYamlConfig], ContractRolloutPolicy
    ],
) -> GoldWriter:
    gold_writer_flat = resolve_delta_writer_flat_structure_fn(
        ctx.gold_path,
        provider=config.provider,
        entity_type=config.entity_type,
        flat_structure=ctx.gold_flat,
    )
    return create_gold_writer(
        writer_cls=gold_writer_cls,
        base_path=resolve_delta_writer_base_path_fn(
            ctx.gold_path,
            provider=config.provider,
            entity_type=config.entity_type,
            flat_structure=gold_writer_flat,
        ),
        config=ctx.gold_config,
        logger=logger,
        tracing=tracing,
        csv_exporter=ctx.gold_csv_exporter,
        metadata_coordinator=metadata_coordinator,
        audit=audit,
        transform_version=config.transform.version,
        transform_steps=tuple(config.transform.steps),
        flat_structure=gold_writer_flat,
        metrics=metrics,
        contract_rollout_policy=load_contract_rollout_policy_fn(config),
    )

================================================================================
File: _resilience.py
Path: factories\storage\_resilience.py
================================================================================
"""Factory helpers for storage write resilience policies."""

from __future__ import annotations

from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.storage.delta.resilience import (
    DEFAULT_ATOMIC_REPLACE_RETRY_POLICY,
    DEFAULT_SILVER_MERGE_POLICY,
    AdaptiveRetryPolicy,
    SilverMergeResiliencePolicy,
)

__all__ = [
    "create_silver_atomic_retry_policy",
    "create_silver_merge_resilience_policy",
]


def _resolve_merge_execution_timeout_seconds(timeout_cfg: object) -> float:
    """Resolve merge timeout from default/unit/e2e profile settings."""
    default_timeout = float(getattr(timeout_cfg, "execution_timeout_seconds", 45.0))
    profile = str(getattr(timeout_cfg, "profile", "default")).strip().lower()
    if profile == "unit":
        return float(
            getattr(timeout_cfg, "unit_execution_timeout_seconds", default_timeout)
        )
    if profile == "e2e":
        return float(
            getattr(timeout_cfg, "e2e_execution_timeout_seconds", default_timeout)
        )
    return default_timeout


def create_silver_atomic_retry_policy(settings: Settings) -> AdaptiveRetryPolicy:
    """Create atomic replace retry policy for Silver metadata writes.

    Args:
        settings: Application settings providing silver_resilience_enabled flag
            and silver_metadata_atomic_retry configuration.

    Returns:
        AdaptiveRetryPolicy configured for Silver metadata atomic replace operations.
    """
    if not settings.pipeline.silver_resilience_enabled:
        return DEFAULT_ATOMIC_REPLACE_RETRY_POLICY

    cfg = settings.pipeline.silver_metadata_atomic_retry
    return AdaptiveRetryPolicy(
        enabled=cfg.enabled,
        max_retries=cfg.max_retries,
        base_delay_seconds=cfg.base_delay_seconds,
        max_delay_seconds=cfg.max_delay_seconds,
        jitter_seconds=cfg.jitter_seconds,
        adaptive=cfg.adaptive_backoff,
    )


def create_silver_merge_resilience_policy(
    settings: Settings,
) -> SilverMergeResiliencePolicy:
    """Create merge timeout/retry policy bundle for Silver Delta writes.

    Args:
        settings: Application settings providing silver_resilience_enabled flag
            and silver_merge_retry / silver_merge_timeout configuration.

    Returns:
        SilverMergeResiliencePolicy with timeout and commit retry configuration.
    """
    if not settings.pipeline.silver_resilience_enabled:
        return DEFAULT_SILVER_MERGE_POLICY

    commit_cfg = settings.pipeline.silver_merge_retry
    timeout_cfg = settings.pipeline.silver_merge_timeout

    return SilverMergeResiliencePolicy(
        execution_timeout_seconds=_resolve_merge_execution_timeout_seconds(timeout_cfg),
        commit_retry=AdaptiveRetryPolicy(
            enabled=commit_cfg.enabled,
            max_retries=commit_cfg.max_retries,
            base_delay_seconds=commit_cfg.base_delay_seconds,
            max_delay_seconds=commit_cfg.max_delay_seconds,
            jitter_seconds=commit_cfg.jitter_seconds,
            adaptive=commit_cfg.adaptive_backoff,
        ),
        timeout_retry=AdaptiveRetryPolicy(
            enabled=timeout_cfg.retry_enabled,
            max_retries=timeout_cfg.max_retries,
            base_delay_seconds=timeout_cfg.base_delay_seconds,
            max_delay_seconds=timeout_cfg.max_delay_seconds,
            jitter_seconds=timeout_cfg.jitter_seconds,
            adaptive=timeout_cfg.adaptive_backoff,
        ),
    )

================================================================================
File: _silver.py
Path: factories\storage\_silver.py
================================================================================
"""Silver writer factory helpers for StorageFactory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.control_plane import FileLineageStore
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
    build_silver_writer_runtime_services,
)

if TYPE_CHECKING:
    from bioetl.application.services.lineage.metadata_coordinator import (
        MetadataCoordinator,
    )
    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.export.csv_exporter import CsvExporter
    from bioetl.infrastructure.schemas.pipeline_config import SinkLayerConfig
    from bioetl.infrastructure.storage.delta.resilience import (
        AdaptiveRetryPolicy,
        SilverMergeResiliencePolicy,
    )
    from bioetl.infrastructure.storage.silver_writer import SilverWriter


@dataclass(frozen=True, slots=True)
class CreateSilverWriterRequest:
    """Inputs required to build a configured Silver writer instance."""

    writer_cls: type[SilverWriter]
    base_path: Path
    config: SinkLayerConfig | None
    logger: LoggerPort
    tracing: TracingPort
    csv_exporter: CsvExporter | None
    metadata_coordinator: MetadataCoordinator | None
    audit: AuditPort
    transform_version: str | None
    transform_steps: tuple[str, ...] | None
    flat_structure: bool
    silver_validator: SilverValidatorPort | None
    metrics: MetricsPort | None = None
    metadata_atomic_retry_policy: AdaptiveRetryPolicy | None = None
    merge_resilience_policy: SilverMergeResiliencePolicy | None = None
    contract_rollout_policy: ContractRolloutPolicy | None = None
    pipeline_name: str | None = None


def create_silver_writer(request: CreateSilverWriterRequest) -> SilverWriter:
    """Create configured Silver writer.

    Args:
        writer_cls: SilverWriter class to instantiate.
        base_path: Root directory for Silver layer storage.
        config: Optional sink layer config providing save_metadata flag.
        logger: LoggerPort for structured logging.
        tracing: Explicit TracingPort resolved by composition bootstrap.
        csv_exporter: Optional CSV exporter for parallel Silver CSV output.
        metadata_coordinator: Optional coordinator for metadata side-effects.
        transform_version: Transform version tag written to Silver metadata.
        transform_steps: Ordered transform step labels for metadata.
        flat_structure: If True, writes files without provider/entity subdirectories.
        silver_validator: Optional PyArrow schema validator for Silver records.
        metrics: Optional MetricsPort for metadata writer; defaults to None.
        metadata_atomic_retry_policy: Optional retry policy for atomic metadata
            replace operations; defaults to None.
        merge_resilience_policy: Optional timeout/retry policy for Delta merge
            operations; defaults to None.

    Returns:
        Configured SilverWriter instance for the Silver storage layer.
    """
    save_metadata = request.config.save_metadata if request.config else False
    lineage_store = (
        FileLineageStore(base_path=request.base_path.parent / "control" / "lineage")
        if save_metadata
        else None
    )
    metadata_writer = (
        MetadataWriter(
            logger=request.logger,
            atomic_replace_retry_policy=request.metadata_atomic_retry_policy,
            metrics=request.metrics,
        )
        if save_metadata
        else NoOpMetadataWriter()
    )
    if request.tracing is None:
        raise TypeError(
            "SilverWriter requires explicit tracing injection. "
            "Build NoOpTracing in composition when tracing is disabled."
        )
    runtime_services = build_silver_writer_runtime_services(
        SilverWriterRuntimeServicesRequest(
            csv_exporter=request.csv_exporter,
            tracing=request.tracing,
            write_policy=None,
            metrics=request.metrics,
            audit=request.audit,
            logger=request.logger,
            silver_validator=request.silver_validator,
            metadata_writer=metadata_writer,
            metadata_coordinator=request.metadata_coordinator,
            lineage_store=lineage_store,
            dq_calculator=None,
            merge_resilience_policy=request.merge_resilience_policy,
            contract_rollout_policy=request.contract_rollout_policy,
            base_path=request.base_path,
            pipeline_name=request.pipeline_name,
        )
    )
    return request.writer_cls(
        base_path=request.base_path,
        logger=request.logger,
        transform_version=request.transform_version,
        transform_steps=request.transform_steps,
        runtime_services=runtime_services,
        pipeline_name=request.pipeline_name,
        # Keep legacy kwarg for constructor-call compatibility in tests and shims.
        csv_exporter=request.csv_exporter,
        flat_structure=request.flat_structure,
    )

================================================================================
File: adapter.py
Path: factories\storage\adapter.py
================================================================================
"""StorageAdapter - Unified storage adapter for Bronze/Silver/Gold layers.

Implements StoragePort protocol from ``bioetl.domain.ports``.

This module was extracted from storage.py as part of the storage factory split
to improve maintainability and reduce file size.

Note:
    Lock validation is performed at Application layer (BatchWriter).
    Infrastructure writers are pure I/O adapters.
"""

from __future__ import annotations

from typing import ClassVar

from bioetl.composition.factories.storage.clear_mixin import (
    StorageAdapterClearMixin,
)
from bioetl.composition.factories.storage.health_mixin import (
    StorageAdapterHealthMixin,
)
from bioetl.composition.factories.storage.maintenance_mixin import (
    StorageAdapterMaintenanceMixin,
)
from bioetl.composition.factories.storage.merged_mixin import (
    StorageAdapterMergedMixin,
)
from bioetl.composition.factories.storage.write_mixin import (
    StorageAdapterWriteMixin,
)
from bioetl.domain.contracts.gold.composite import (
    CompositeMoleculeGoldSchema,
    CompositePublicationGoldSchema,
)
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["StorageAdapter"]


class StorageAdapter(
    StorageAdapterWriteMixin,
    StorageAdapterMergedMixin,
    StorageAdapterClearMixin,
    StorageAdapterMaintenanceMixin,
    StorageAdapterHealthMixin,
):
    """Unified storage adapter for Bronze/Silver/Gold.

    Implements StoragePort protocol from ``bioetl.domain.ports``.
    Delegates to specialized writers for each layer.
    """

    _COMPOSITE_GOLD_SCHEMAS: ClassVar[
        JsonDict  # Any: record/metadata values are heterogeneous
    ] = {
        "composite/publication": CompositePublicationGoldSchema,
        "composite_publication": CompositePublicationGoldSchema,
        "composite/molecule": CompositeMoleculeGoldSchema,
        "composite_molecule": CompositeMoleculeGoldSchema,
    }

    # Protocol compliance marker
    REQUIRES_SILVER_SCHEMA: bool = True

    def __init__(
        self,
        bronze_writer: BronzeWriter,
        silver_writer: SilverWriter,
        gold_writer: GoldWriter,
    ):
        """Initialize StorageAdapter with injected layer writers.

        Args:
            bronze_writer: Writer for raw data ingestion into Bronze layer
                (zst-compressed JSONL files with optional JSON and metadata).
            silver_writer: Writer for transformed data into Silver layer
                (Delta Lake tables with schema enforcement and optional CSV export).
            gold_writer: Writer for aggregated/validated data into Gold layer
                (Delta Lake tables with Pandera validation and optional CSV export).
        """
        self.bronze = bronze_writer
        self.silver = silver_writer
        self.gold = gold_writer

================================================================================
File: audit.py
Path: factories\storage\audit.py
================================================================================
"""Public seam for canonical storage-audit wiring helpers."""

from __future__ import annotations

from bioetl.composition.factories.storage._audit import create_audit_port

__all__ = ["create_audit_port"]

================================================================================
File: clear_mixin.py
Path: factories\storage\clear_mixin.py
================================================================================
"""Clear and cleanup operations mixin for StorageAdapter."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["StorageAdapterClearMixin"]


class StorageAdapterClearMixin:
    """Mixin providing clear/cleanup operations for Silver, Gold, CSV, and Delta."""

    silver: SilverWriter
    gold: GoldWriter

    async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Silver layer data for a specific table.

        Implements StoragePort.clear_silver().
        Clears both Delta tables and CSV exports (if configured).

        Args:
            table_name: Database table name.
            dry_run: Dry run mode flag.

        Returns:
            Computed integer value.
        """
        return await self._run_clear(self.silver, table_name, dry_run)

    async def clear_gold(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Gold layer data for a specific table.

        Implements StoragePort.clear_gold().
        Clears both Delta tables and CSV exports (if configured).

        Args:
            table_name: Database table name.
            dry_run: Dry run mode flag.

        Returns:
            Computed integer value.
        """
        return await self._run_clear(self.gold, table_name, dry_run)

    async def _run_clear(
        self,
        writer: SilverWriter | GoldWriter,
        table_name: str,
        dry_run: bool,
    ) -> int:
        """Execute clear operation for a writer."""
        loop = asyncio.get_running_loop()
        cleared = await loop.run_in_executor(
            None, lambda: writer.clear(table_name, dry_run=dry_run)
        )
        if writer.csv_exporter and not dry_run:
            exporter = writer.csv_exporter
            deleted = await loop.run_in_executor(
                None, lambda: exporter.clear(table_name)
            )
            cleared += len(deleted)
        return int(cleared)

    async def clear_csv(self, table_name: str | None = None) -> int:
        """Clear CSV export files for Silver and Gold layers.

        Implements StoragePort.clear_csv().

        Args:
            table_name: Database table name.

        Returns:
            Computed integer value.
        """
        count = 0
        loop = asyncio.get_running_loop()

        if self.silver.csv_exporter:
            exporter = self.silver.csv_exporter
            deleted = await loop.run_in_executor(
                None, lambda: exporter.clear(table_name)
            )
            count += len(deleted) if isinstance(deleted, list) else deleted

        if self.gold.csv_exporter:
            exporter = self.gold.csv_exporter
            deleted = await loop.run_in_executor(
                None, lambda: exporter.clear(table_name)
            )
            count += len(deleted) if isinstance(deleted, list) else deleted

        return count

    async def clear_delta(self, table_name: str | None = None) -> int:
        """Clear Delta tables for Silver and Gold layers.

        Implements StoragePort.clear_delta().

        Args:
            table_name: If provided, only clear Delta table for this table.
                       If None, clear all Delta tables.

        Returns:
            Number of tables cleared.
        """
        loop = asyncio.get_running_loop()
        cleared_count = 0

        if table_name:
            cleared_count += await loop.run_in_executor(
                None, lambda: self.silver.clear(table_name)
            )
            cleared_count += await loop.run_in_executor(
                None, lambda: self.gold.clear(table_name)
            )

        return cleared_count

================================================================================
File: factory.py
Path: factories\storage\factory.py
================================================================================
"""StorageFactory - thin facade for creating StorageAdapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.observability_resolution import resolve_tracing_port
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

from ._helpers import (
    build_storage_creation_context,
    create_storage_adapter,
)
from .adapter import StorageAdapter

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "BronzeWriter",
    "GoldWriter",
    "SilverWriter",
    "StorageContext",
    "StorageFactory",
]


@dataclass(frozen=True)
class StorageContext:
    """Context object returned by StorageFactory containing adapter and paths."""

    adapter: StorageAdapter
    bronze_path: Path
    silver_path: Path
    gold_path: Path
    checkpoints_path: Path


class StorageFactory:
    """Factory for creating configured StorageAdapters for local deployment."""

    @staticmethod
    def create(
        settings: Settings,
        config: PipelineYamlConfig,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracing: TracingPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        silver_validator: SilverValidatorPort | None = None,
        pipeline_name: str | None = None,
    ) -> StorageContext:
        """Create local storage context with configured layer writers.

        Args:
            settings: Application settings providing base paths, test_mode, and
                resilience configuration.
            config: Pipeline YAML configuration with sink layer definitions.
            logger: LoggerPort for structured logging and export status events.
            metrics: MetricsPort for storage metrics collection.
            tracing: Optional TracingPort. When omitted, composition resolves an
                explicit NoOpTracing for the layer writers.
            metadata_coordinator: Optional coordinator for metadata side-effects;
                defaults to None.
            silver_validator: Optional PyArrow schema validator for Silver records;
                defaults to None.

        Returns:
            StorageContext with assembled adapter and resolved layer paths.
        """
        ctx = build_storage_creation_context(
            settings=settings,
            config=config,
            logger=logger,
            pipeline_name=(
                pipeline_name
                or getattr(config, "pipeline_name", None)
                or f"{config.provider}_{config.entity_type}"
            ),
        )
        logger.info(
            "Using local storage",
            bronze_path=str(ctx.bronze_path),
            silver_path=str(ctx.silver_path),
            gold_path=str(ctx.gold_path),
        )
        resolved_tracing = resolve_tracing_port(tracer=tracing, settings=settings)
        adapter = create_storage_adapter(
            ctx=ctx,
            bronze_writer_cls=BronzeWriter,
            silver_writer_cls=SilverWriter,
            gold_writer_cls=GoldWriter,
            settings=settings,
            config=config,
            logger=logger,
            metrics=metrics,
            tracing=resolved_tracing,
            metadata_coordinator=metadata_coordinator,
            silver_validator=silver_validator,
        )
        return StorageContext(
            adapter=adapter,
            bronze_path=ctx.bronze_path,
            silver_path=ctx.silver_path,
            gold_path=ctx.gold_path,
            checkpoints_path=settings.checkpoint_path,
        )

================================================================================
File: health_mixin.py
Path: factories\storage\health_mixin.py
================================================================================
"""Health check and preview operations mixin for StorageAdapter."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus, JsonDict

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["StorageAdapterHealthMixin"]


class StorageAdapterHealthMixin:
    """Mixin providing health check, preview, and lifecycle operations."""

    bronze: BronzeWriter
    silver: SilverWriter
    gold: GoldWriter

    async def aclose(self) -> None:
        """Close resources.

        Implements aclose() required by StoragePort protocol.
        """
        for audit in self._iter_unique_audit_ports():
            aclose = getattr(audit, "aclose", None)
            if callable(aclose):
                awaitable = aclose()
                if isinstance(awaitable, Awaitable):
                    await awaitable

    async def health_check(self) -> HealthStatus:
        """Check storage accessibility and write capability.

        Validates Bronze, Silver, and Gold directories are writable by
        attempting to create and delete a temporary file in each layer.

        Returns:
            HealthStatus:
            - HEALTHY: All layers accessible and writable
            - DEGRADED: Partial access (1-2 layers have issues)
            - UNHEALTHY: Critical storage failure (all layers unavailable)
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._check_storage_health_sync)

    def _check_storage_health_sync(self) -> HealthStatus:
        """Synchronous storage health check implementation.

        Checks if each layer's base directory is writable.
        """
        layers = [
            ("bronze", Path(self.bronze.base_path)),
            ("silver", Path(self.silver.base_path)),
            ("gold", Path(self.gold.base_path)),
        ]

        issues = 0
        for _layer_name, base_path in layers:
            if not self._check_directory_writable(base_path):
                issues += 1

        if issues == 0:
            return HealthStatus.HEALTHY
        elif issues < len(layers):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY

    def preview_cleanup(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> JsonDict:  # Any: factory wiring; concrete types resolved at runtime
        """Preview what would be cleared without actual deletion.

        Implements StoragePort.preview_cleanup().
        Used by CLI dry-run mode to show users what data would be affected.

        Args:
            silver_table: Silver table name (e.g., 'chembl.activity')
            gold_table: Optional Gold table name

        Returns:
            Dict with layer info including paths and file counts.
        """
        silver_preview = self._preview_layer(self.silver, silver_table)
        gold_preview = (
            self._preview_layer(self.gold, gold_table) if gold_table else None
        )
        result: JsonDict = {  # preview payload values are heterogeneous
            "silver": silver_preview,
            "gold": None,
            "total_files": 0,
        }

        if gold_preview is not None:
            result["gold"] = gold_preview

        result["total_files"] = silver_preview["file_count"] + (
            gold_preview["file_count"] if gold_preview else 0
        )
        return result

    def _preview_layer(
        self,
        writer: SilverWriter | GoldWriter,
        table_name: str,
    ) -> JsonDict:  # Any: factory wiring; concrete types resolved at runtime
        """Count files in a layer without deletion.

        Args:
            writer: Delta or Gold writer instance
            table_name: Table name to preview

        Returns:
            Dict with path, file_count, and exists status.
        """
        preview_method = getattr(writer, "preview_cleanup", None)
        if callable(preview_method):
            preview_result: JsonDict = preview_method(table_name)
            if self._is_layer_preview_payload(preview_result):
                return preview_result

        path = writer.get_table_path(table_name)
        file_count = 0
        exists = path.exists()

        if exists:
            file_count = sum(1 for f in path.rglob("*") if f.is_file())

        return {
            "path": str(path),
            "file_count": file_count,
            "exists": exists,
        }

    @staticmethod
    def _is_layer_preview_payload(value: object) -> bool:
        """Check whether a preview payload has the expected layer shape."""
        if not isinstance(value, dict):
            return False
        path = value.get("path")
        file_count = value.get("file_count")
        exists = value.get("exists")
        return (
            isinstance(path, str)
            and isinstance(file_count, int)
            and isinstance(exists, bool)
        )

    def _iter_unique_audit_ports(self) -> list[object]:
        """Return explicit per-writer audit ports without double-closing shared ones."""
        seen: set[int] = set()
        audits: list[object] = []
        for writer in (self.bronze, self.silver, self.gold):
            audit = self._get_explicit_writer_audit(writer)
            if audit is None:
                continue
            audit_id = id(audit)
            if audit_id in seen:
                continue
            seen.add(audit_id)
            audits.append(audit)
        return audits

    @staticmethod
    def _get_explicit_writer_audit(writer: object) -> object | None:
        """Return a writer's explicitly assigned audit port when present."""
        try:
            writer_dict = vars(writer)
        except TypeError:
            return None
        return writer_dict.get("_audit")

    @staticmethod
    def _check_directory_writable(dir_path: Path | str) -> bool:
        """Check if a directory is writable.

        Args:
            dir_path: Directory path to check (accepts Path or str).

        Returns:
            True if directory is writable, False otherwise.
        """
        try:
            path = Path(dir_path) if isinstance(dir_path, str) else dir_path
            path.mkdir(parents=True, exist_ok=True)
            temp_file = path / ".health_check_probe"
            temp_file.touch()
            temp_file.unlink()
            return True
        except (OSError, PermissionError):
            return False

================================================================================
File: maintenance_mixin.py
Path: factories\storage\maintenance_mixin.py
================================================================================
"""Maintenance operations mixin for StorageAdapter (vacuum, optimize, archive)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["StorageAdapterMaintenanceMixin"]


def _is_delta_table_dir(path: Path) -> bool:
    """Return True when a directory contains a Delta log with at least one commit file."""
    delta_log = path / "_delta_log"
    if not delta_log.is_dir():
        return False
    return any(delta_log.iterdir())


class StorageAdapterMaintenanceMixin:
    """Mixin providing maintenance operations: optimize, vacuum, archive, cleanup."""

    bronze: BronzeWriter
    silver: SilverWriter
    gold: GoldWriter

    def is_table_initialized(
        self,
        table_name: str,
        layer: Literal["silver", "gold"] = "silver",
    ) -> bool:
        """Check whether a Delta table has been written to."""
        writer = self.gold if layer == "gold" else self.silver
        table_path = writer.get_table_path(table_name)
        return _is_delta_table_dir(table_path)

    def get_table_version(
        self,
        table_path: str,
        *,
        layer: Literal["silver", "gold"] = "silver",
    ) -> int | None:
        """Return the current Delta table version, or None if table does not exist."""
        path = Path(table_path)
        if not _is_delta_table_dir(path):
            return None
        try:
            from deltalake import DeltaTable

            return int(DeltaTable(table_path).version())
        except (OSError, RuntimeError, ValueError, ImportError):
            return None

    async def optimize(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> None:
        """Optimize storage for a specific table/entity.

        Performs maintenance operations appropriate for the storage layer:
        - Delta Lake: Runs VACUUM to remove old files
        - JSONL/File: Removes files older than retention period

        Args:
            table_name: Target identifier (e.g., 'provider.entity' for Delta/Bronze)
            retention_hours: Retention period in hours (default 168h = 7 days)
            dry_run: If True, only log what would be done without action
        """
        # 1. Optimize Silver/Gold Delta Tables
        await self.vacuum(table_name, retention_hours, dry_run)

        # 2. Optimize Bronze (File cleanup)
        # Parse table_name to get provider/entity for targeted cleanup
        if "." in table_name:
            provider, entity = table_name.split(".", 1)
            cutoff_date = datetime.now(UTC) - timedelta(hours=retention_hours)
            await self.bronze.cleanup_old_files(
                cutoff_date=cutoff_date,
                dry_run=dry_run,
                provider=provider,
                entity=entity,
            )

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> int:
        """Vacuum Delta table via underlying writers.

        Implements StoragePort.vacuum().
        Vacuums both Silver and Gold layers for the specified table.

        Args:
            table_name: Table name in format "provider.entity"
            retention_hours: Minimum age of files to remove (default 168h = 7 days)
            dry_run: If True, only report what would be removed

        Returns:
            Total number of files removed (or would be removed if dry_run)
        """
        total_removed = 0

        # Vacuum Silver (only if table exists)
        silver_table_path = self.silver.get_table_path(table_name)
        if _is_delta_table_dir(silver_table_path):
            removed = await self.silver.vacuum(
                table_name=table_name,
                retention_hours=retention_hours,
                dry_run=dry_run,
            )
            total_removed += len(removed)

        # Vacuum Gold only when the directory is a real Delta table.
        # Metadata-only directories can exist when Gold writes are disabled.
        gold_table_path = self.gold.get_table_path(table_name)
        if _is_delta_table_dir(gold_table_path):
            from deltalake import DeltaTable

            loop = asyncio.get_running_loop()
            try:
                dt = await loop.run_in_executor(
                    None,
                    lambda: DeltaTable(str(gold_table_path)),
                )
                removed = await loop.run_in_executor(
                    None,
                    lambda: dt.vacuum(retention_hours=retention_hours, dry_run=dry_run),
                )
                total_removed += len(removed)
            except (OSError, RuntimeError):
                pass

        return total_removed

    async def archive(
        self,
        table_name: str,
        target_path: str,
        remove_source: bool = False,
    ) -> int:
        """Archive Silver and Gold table directories to a target path."""
        import shutil

        total_archived = 0

        # Archive Silver
        silver_table_path = self.silver.get_table_path(table_name)
        if silver_table_path.exists():
            silver_target = Path(target_path) / "silver" / table_name.replace(".", "/")
            silver_target.parent.mkdir(parents=True, exist_ok=True)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: shutil.copytree(silver_table_path, silver_target),
            )
            total_archived += sum(
                1 for f in silver_table_path.rglob("*") if f.is_file()
            )
            if remove_source:
                await loop.run_in_executor(
                    None,
                    lambda: shutil.rmtree(silver_table_path),
                )

        # Archive Gold
        gold_table_path = self.gold.get_table_path(table_name)
        if gold_table_path.exists():
            gold_target = Path(target_path) / "gold" / table_name.replace(".", "/")
            gold_target.parent.mkdir(parents=True, exist_ok=True)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: shutil.copytree(gold_table_path, gold_target),
            )
            total_archived += sum(1 for f in gold_table_path.rglob("*") if f.is_file())
            if remove_source:
                await loop.run_in_executor(
                    None,
                    lambda: shutil.rmtree(gold_table_path),
                )

        return total_archived

    async def deduplicate_silver(
        self,
        table_name: str,
        primary_keys: list[str],
    ) -> int:
        """Deduplicate Silver table by primary keys after append-mode writes.

        Args:
            table_name: Logical Silver table name.
            primary_keys: Business key columns for deduplication.

        Returns:
            Number of duplicate rows removed.
        """
        return int(await self.silver.deduplicate_silver(table_name, primary_keys))

    async def cleanup_bronze(
        self,
        cutoff_date: datetime,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """Remove Bronze files older than cutoff date (RULES.md §2.1 retention).

        Implements StoragePort.cleanup_bronze().
        Delegates to BronzeWriter.cleanup_old_files().

        Args:
            cutoff_date: Files older than this date will be removed.
            dry_run: If True, only count what would be removed.

        Returns:
            Dictionary with cleanup statistics.
        """
        return dict(
            await self.bronze.cleanup_old_files(
                cutoff_date=cutoff_date,
                dry_run=dry_run,
            )
        )

================================================================================
File: merged_mixin.py
Path: factories\storage\merged_mixin.py
================================================================================
"""Merged write and read operations mixin for StorageAdapter."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal, Protocol, cast

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["StorageAdapterMergedMixin"]


class _SilverMergedWriteProtocol(Protocol):
    """Minimal bound-method contract for merged Silver writes."""

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[JsonDict],
        primary_keys: list[str] | None = None,
        *,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None: ...


class StorageAdapterMergedMixin:
    """Mixin providing merged write and read operations for composite pipelines."""

    silver: SilverWriter
    gold: GoldWriter
    _COMPOSITE_GOLD_SCHEMAS: ClassVar[
        JsonDict  # Any: record/metadata values are heterogeneous
    ]

    def get_table_path(
        self,
        table_name: str,
        layer: Literal["silver", "gold"] = "silver",
    ) -> Path:
        """Resolve the full path to a Delta table.

        Delegates to the underlying writer implementation.

        Args:
            table_name: Database table name.
            layer: Storage layer path resolver (``"silver"`` or ``"gold"``).

        Returns:
            Table path.
        """
        if layer == "gold":
            return self.gold.get_table_path(table_name)
        return self.silver.get_table_path(table_name)

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[
        JsonDict  # Any: record/metadata values are heterogeneous
    ]:
        """Read records from a Silver layer Delta table.

        Args:
            table_name: The name of the table to read (e.g., 'chembl/activity').
            columns: Optional list of columns to select. If None, reads all columns.

        Returns:
            List of dictionaries, where each dictionary represents a record.

        Raises:
            FileNotFoundError: If the table does not exist.
        """
        return list(await self.silver.read_silver(table_name, columns=columns))

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[
            JsonDict  # Any: record/metadata values are heterogeneous
        ],
        primary_keys: list[str] | None = None,
        *,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged records to Silver layer without explicit schema.

        Used by composite pipelines where schema is dynamically determined.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
            preserve_column_order: If True, skip canonical reordering.
        """
        await cast(
            _SilverMergedWriteProtocol,
            self.silver,
        ).write_silver_merged(
            table_name,
            records,
            primary_keys,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=preserve_column_order,
        )

    async def write_gold_merged(
        self,
        table_name: str,
        records: list[
            JsonDict  # Any: record/metadata values are heterogeneous
        ],
        primary_keys: list[str] | None = None,
        *,
        completed_at: object | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
        schema: object | None = None,
    ) -> None:
        """Write merged records to Gold layer without Pandera schema.

        Used by composite pipelines where schema is dynamically determined.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            completed_at: Optional deterministic metadata timestamp for merged sidecars.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
            preserve_column_order: If True, skip canonical reordering.
            schema: Optional Pandera schema for strict contract validation.
        """
        composite_schema = self._COMPOSITE_GOLD_SCHEMAS.get(table_name)

        await self.gold.write_gold_merged(
            table_name,
            records,
            primary_keys,
            schema=composite_schema,
            completed_at=completed_at,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=preserve_column_order,
        )

================================================================================
File: resilience.py
Path: factories\storage\resilience.py
================================================================================
"""Public resilience-policy facade for storage factory wiring."""

from __future__ import annotations

from bioetl.composition.factories.storage._resilience import (
    create_silver_atomic_retry_policy,
    create_silver_merge_resilience_policy,
)

__all__ = [
    "create_silver_atomic_retry_policy",
    "create_silver_merge_resilience_policy",
]

================================================================================
File: storage_factory.py
Path: factories\storage\storage_factory.py
================================================================================
"""Canonical storage factory module.

Provides the storage context factory and related writer patch points.
The legacy ``factory`` module remains for backward compatibility.
"""

from __future__ import annotations

from bioetl.composition.factories.storage.factory import (
    BronzeWriter,
    GoldWriter,
    SilverWriter,
    StorageContext,
    StorageFactory,
)

__all__ = [
    "BronzeWriter",
    "GoldWriter",
    "SilverWriter",
    "StorageContext",
    "StorageFactory",
]

================================================================================
File: write_mixin.py
Path: factories\storage\write_mixin.py
================================================================================
"""Write operations mixin for StorageAdapter (Bronze/Silver/Gold)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from bioetl.domain.types import JsonDict, ScdConfig

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime

    from bioetl.domain.config import KeyNullabilityRule
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.types import ArrowSchema, BatchID, RunID, RunType
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["StorageAdapterWriteMixin"]


class StorageAdapterWriteMixin:
    """Mixin providing core write operations for Bronze, Silver, and Gold layers."""

    bronze: BronzeWriter
    silver: SilverWriter
    gold: GoldWriter

    async def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        source_metadata: SourceMetadata | None = None,
    ) -> BronzeWriteResult:
        """Write raw records to Bronze layer.

        Args:
            records: Iterator of JSON-encoded record bytes.
            provider: Provider name.
            entity: Entity type.
            date: Date for path partitioning.
            batch_id: Unique batch identifier.
            run_id: Pipeline run identifier.
            run_type: Type of run.
            ingestion_ts: Ingestion timestamp from application layer
                         (single source of time per ADR-014). Required.
            source_metadata: Optional pre-built SourceMetadata with API request
                           details for rich lineage tracking. If None, a minimal
                           SourceMetadata is created with type="api".

        Returns:
            BronzeWriteResult: Result containing path, record count, sizes,
                and checksum for downstream lineage tracking.

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard.
        """
        return await self.bronze.write_bronze(
            records=records,
            provider=provider,
            entity=entity,
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
            source_metadata=source_metadata,
        )

    async def write_silver(
        self,
        table_name: str,
        records: list[JsonDict],  # Any: record/metadata values are heterogeneous
        primary_keys: list[str],
        schema: ArrowSchema,
        mode: Literal["merge", "append", "delete"] = "merge",
        partition_cols: list[str] | None = None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
        column_order: list[str] | None = None,
        bronze_refs: list[BronzeWriteResult] | None = None,
        key_nullability_rules: list[KeyNullabilityRule] | None = None,
        *,
        run_id: RunID | None = None,
        run_type: RunType | None = None,
        source_batch_id: BatchID | None = None,
        ingestion_ts: datetime | None = None,
    ) -> SilverWriteResult | None:
        """Write transformed records to Silver layer.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries, where each dictionary is a transformed record.
            primary_keys: A list of column names that form the primary key.
            schema: The PyArrow schema definition for the records (ArrowSchema alias).
            mode: The write mode (e.g., 'merge', 'append', 'delete').
            partition_cols: Optional list of columns to partition by.
            on_schema_mismatch: How to handle schema drift.
            column_order: Optional explicit column order to apply.
            bronze_refs: Optional list of BronzeWriteResult from Bronze writes.
                If provided, bronze_paths will be populated in Silver metadata
                for complete lineage tracking (REQ-LINEAGE-001).
            key_nullability_rules: Optional per-column nullability override rules
                applied during Silver write to relax or tighten key constraints.
            run_id: Optional run identifier for tracing, audit, and metadata.
            run_type: Optional run type for tracing and audit semantics.
            source_batch_id: Optional Bronze batch identifier for lineage metadata.
            ingestion_ts: Optional ingestion timestamp for audit correlation.

        Returns:
            SilverWriteResult with table info and Delta version for Gold lineage tracking
            (REQ-LINEAGE-002), or None if no records were written.

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard.
        """
        return await self.silver.write_silver(
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            schema=schema,
            mode=mode,
            partition_cols=partition_cols,
            on_schema_mismatch=on_schema_mismatch,
            column_order=column_order,
            bronze_refs=bronze_refs,
            key_nullability_rules=key_nullability_rules,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
        )

    async def write_gold(
        self,
        table_name: str,
        records: list[JsonDict],  # Any: record/metadata values are heterogeneous
        schema: object,
        primary_keys: list[str] | None = None,
        mode: Literal["overwrite", "append", "scd2"] = "overwrite",
        *,
        scd_config: ScdConfig | None = None,
        column_order: list[str] | None = None,
        ingestion_ts: datetime | None = None,
        run_id: RunID | None = None,
        silver_refs: list[SilverWriteResult] | None = None,
    ) -> None:
        """Write aggregated records to Gold layer.

        Args:
            table_name: Target table name
            records: Records to write
            schema: Pandera schema for validation
            primary_keys: Optional primary key columns
            mode: Write mode
            scd_config: Optional typed SCD2 configuration when mode is 'scd2'.
            column_order: Optional explicit column order to apply.
            ingestion_ts: Ingestion timestamp for audit (ADR-014)
            run_id: Run identifier for audit correlation
            silver_refs: Optional list of SilverWriteResult from Silver writes.
                If provided, source_tables will be populated in Gold metadata
                for complete lineage tracking (REQ-LINEAGE-002).

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard.
        """
        await self.gold.write_gold(
            table_name=table_name,
            records=records,
            schema=schema,
            primary_keys=primary_keys,
            mode=mode,
            scd_config=scd_config,
            column_order=column_order,
            ingestion_ts=ingestion_ts,
            run_id=run_id,
            silver_refs=silver_refs,
        )

================================================================================
File: transformer_dependencies.py
Path: factories\transformer_dependencies.py
================================================================================
"""Canonical transformer collaborator wiring for composition-owned defaults."""

from __future__ import annotations

from bioetl.application.core.wiring.transformer import (
    DefaultContractPolicy,
    NoOpStructuralPolicy,
    StructuralPolicyProtocol,
    TransformerDependencyContext,
)
from bioetl.composition.observability_resolution import (
    resolve_metrics_port,
    resolve_tracing_port,
)
from bioetl.domain.ports import (
    ContractPolicyPort,
    DataNormalizationPort,
    MetricsPort,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.ports.noop import NoOpPiiHasher
from bioetl.domain.services import DataNormalizationService, IdentityService

__all__ = ["build_transformer_dependencies"]


def build_transformer_dependencies(
    *,
    tracer: TracingPort | None = None,
    metrics: MetricsPort | None = None,
    identity_service: IdentityService | None = None,
    pii_hasher: PiiHasherPort | None = None,
    data_normalizer: DataNormalizationPort | None = None,
    contract_policy: ContractPolicyPort | None = None,
    structural_policy: StructuralPolicyProtocol | None = None,
) -> TransformerDependencyContext:
    """Build explicit transformer collaborators in the composition layer."""
    return TransformerDependencyContext(
        tracer=resolve_tracing_port(tracer=tracer),
        metrics=resolve_metrics_port(metrics=metrics),
        identity_service=(
            identity_service if identity_service is not None else IdentityService()
        ),
        pii_hasher=pii_hasher if pii_hasher is not None else NoOpPiiHasher(),
        data_normalizer=(
            data_normalizer
            if data_normalizer is not None
            else DataNormalizationService()
        ),
        contract_policy=(
            contract_policy if contract_policy is not None else DefaultContractPolicy()
        ),
        structural_policy=(
            structural_policy
            if structural_policy is not None
            else NoOpStructuralPolicy()
        ),
    )

================================================================================
File: transformer_factory.py
Path: factories\transformer_factory.py
================================================================================
# src/bioetl/composition/factories/transformer_factory.py
"""Factory functions for DI-based transformer creation."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING, Final

from bioetl.composition.factories._transformer_spec_rows import (
    BUILTIN_TRANSFORMER_SPEC_ROWS,
)
from bioetl.composition.factories.transformer_dependencies import (
    build_transformer_dependencies,
)

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.base_transformer.types import (
        TransformerDependencyContext,
    )
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import (
        ContractPolicyPort,
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.services import IdentityService

# Mapping of (provider, entity_type) to transformer class
_TRANSFORMER_REGISTRY: dict[tuple[str, str], type[BaseTransformer]] = {}


@dataclass(frozen=True, slots=True)
class TransformerRegistrationSpec:
    """Declarative transformer registration entry."""

    provider: str
    entity_type: str
    module_path: str
    class_name: str


_BUILTIN_TRANSFORMER_SPECS: Final[tuple[TransformerRegistrationSpec, ...]] = tuple(
    TransformerRegistrationSpec(*spec) for spec in BUILTIN_TRANSFORMER_SPEC_ROWS
)


def register_transformer(
    provider: str,
    entity_type: str,
    transformer_class: type[BaseTransformer],
) -> None:
    """Register a transformer class for a provider/entity combination.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').
        entity_type: Entity type (e.g., 'activity', 'compound').
        transformer_class: The transformer class to register.

    """
    _TRANSFORMER_REGISTRY[(provider, entity_type)] = transformer_class


def create_transformer(
    provider: str,
    entity_type: str,
    tracer: TracingPort | None = None,
    metrics: MetricsPort | None = None,
    silver_filters: SilverFilterConfig | None = None,
    gold_filters: GoldFilterConfig | None = None,
    identity_service: IdentityService | None = None,
    pii_hasher: PiiHasherPort | None = None,
    data_normalizer: DataNormalizationPort | None = None,
    contract_policy: ContractPolicyPort | None = None,
    dependencies: TransformerDependencyContext | None = None,
) -> BaseTransformer:
    """Create a transformer instance for the given provider and entity type.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').
        entity_type: Entity type (e.g., 'activity', 'compound').
        tracer: Optional tracing port for distributed tracing (O1 observability).
        metrics: Optional metrics port for duration/error tracking (O1 observability).
        silver_filters: Optional domain-level filter configuration for Silver layer.
        gold_filters: Optional filter configuration for Gold layer.
        identity_service: Service for computing entity IDs and content hashes.
        pii_hasher: Optional PII hasher for hashing author names and other PII.
        data_normalizer: Optional data normalization service for text normalization
            (DOI, PMID, authors, HTML).
        contract_policy: Optional pipeline contract policy.
        dependencies: Optional explicit dependency bundle. When omitted,
            composition builds explicit defaults instead of relying on
            BaseTransformer fallbacks.

    Returns:
        Configured transformer instance with observability.

    Raises:
        KeyError: If no transformer is registered for the provider/entity combination.

    """
    key = (provider, entity_type)
    if key not in _TRANSFORMER_REGISTRY:
        raise KeyError(
            f"No transformer registered for provider='{provider}', "
            f"entity_type='{entity_type}'. "
            f"Available: {list(_TRANSFORMER_REGISTRY.keys())}"
        )

    transformer_class = _TRANSFORMER_REGISTRY[key]
    resolved_dependencies = (
        dependencies
        if dependencies is not None
        else build_transformer_dependencies(
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
            contract_policy=contract_policy,
        )
    )
    return transformer_class(
        provider=provider,
        entity_type=entity_type,
        silver_filters=silver_filters,
        gold_filters=gold_filters,
        dependencies=resolved_dependencies,
    )


def get_transformer_class(
    provider: str,
    entity_type: str,
) -> type[BaseTransformer] | None:
    """Get transformer class without instantiating.

    Args:
        provider: Provider name.
        entity_type: Entity type.

    Returns:
        Transformer class if registered, None otherwise.

    """
    return _TRANSFORMER_REGISTRY.get((provider, entity_type))


def _load_transformer_class(module_path: str, class_name: str) -> type:
    """Load transformer class by dotted module path and class name.

    Args:
        module_path: Dotted Python module path (e.g.,
            'bioetl.application.pipelines.chembl.activity_transformer').
        class_name: Name of the transformer class within the module.

    Returns:
        Transformer class type loaded from the module.

    Raises:
        TypeError: If the resolved attribute is not a class.
    """
    module = import_module(module_path)
    transformer_class = getattr(module, class_name)
    if not isinstance(transformer_class, type):
        raise TypeError(
            f"Expected class for {module_path}.{class_name}, "
            f"got {type(transformer_class).__name__}"
        )
    return transformer_class


def get_builtin_transformer_specs() -> tuple[TransformerRegistrationSpec, ...]:
    """Return declarative specs for built-in transformer registrations."""
    return _BUILTIN_TRANSFORMER_SPECS


def register_transformer_spec(
    spec: TransformerRegistrationSpec,
    *,
    load_transformer_class_fn: Callable[[str, str], type[BaseTransformer]]
    | None = None,
) -> None:
    """Register one transformer from a declarative module/class specification."""
    loader = (
        _load_transformer_class
        if load_transformer_class_fn is None
        else load_transformer_class_fn
    )
    register_transformer(
        spec.provider,
        spec.entity_type,
        loader(spec.module_path, spec.class_name),
    )


def register_all_transformers(
    specs: Iterable[TransformerRegistrationSpec] | None = None,
    *,
    load_transformer_class_fn: Callable[[str, str], type[BaseTransformer]]
    | None = None,
) -> None:
    """Register all known transformers.

    Called during application startup to populate the registry.
    Idempotent - safe to call multiple times.
    """
    spec_iter = get_builtin_transformer_specs() if specs is None else specs
    for spec in spec_iter:
        register_transformer_spec(
            spec,
            load_transformer_class_fn=load_transformer_class_fn,
        )


__all__ = [
    "TransformerRegistrationSpec",
    "create_transformer",
    "get_builtin_transformer_specs",
    "get_transformer_class",
    "register_all_transformers",
    "register_transformer",
    "register_transformer_spec",
]

================================================================================
File: health_api.py
Path: health_api.py
================================================================================
"""Public health-oriented composition API."""

from __future__ import annotations

from bioetl.composition._services import (
    get_health_server_dependencies,
    get_health_service,
    get_quarantine_port,
    get_quarantine_service,
)
from bioetl.composition.bootstrap.cli.health import HealthServerDependencies

__all__ = [
    "HealthServerDependencies",
    "get_health_server_dependencies",
    "get_health_service",
    "get_quarantine_port",
    "get_quarantine_service",
]

================================================================================
File: maintenance_api.py
Path: maintenance_api.py
================================================================================
"""Public maintenance-oriented composition API."""

from __future__ import annotations

from bioetl.composition._services import (
    cleanup_bronze,
    get_bronze_cleanup_service,
    get_contract_migration_service,
    get_vacuum_service,
)

__all__ = [
    "cleanup_bronze",
    "get_bronze_cleanup_service",
    "get_contract_migration_service",
    "get_vacuum_service",
]

================================================================================
File: deprecation_tracker.py
Path: monitoring\deprecation_tracker.py
================================================================================
"""Track usage of deprecated classes and methods."""

from __future__ import annotations

import logging
import warnings
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

# Set up deprecation logger
_deprecation_logger = logging.getLogger("bioetl.deprecation")
_deprecation_logger.setLevel(logging.WARNING)

# Add handler if not already configured
if not _deprecation_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    _deprecation_logger.addHandler(handler)


def track_deprecated_class(
    old_class_name: str, new_class_name: str
) -> Callable[[type[T]], type[T]]:
    """Decorator to track usage of deprecated classes."""

    def decorator(cls: type[T]) -> type[T]:
        original_init = cls.__init__

        def new_init(
            self: T,
            *args: Any,  # Any: Decorator must preserve arbitrary constructor signatures.
            **kwargs: Any,  # Any: Decorator must preserve arbitrary constructor signatures.
        ) -> None:
            # Log the usage
            _deprecation_logger.warning(
                "Deprecated class used: %s. Please migrate to %s. "
                "This will be removed in v2.0.",
                old_class_name,
                new_class_name,
            )

            # Call original init
            original_init(self, *args, **kwargs)

        # Replace init method
        cls.__init__ = new_init

        return cls

    return decorator


def log_deprecation_warning(message: str, stacklevel: int = 2) -> None:
    """Log a deprecation warning with consistent formatting."""
    _deprecation_logger.warning(message)
    warnings.warn(message, DeprecationWarning, stacklevel=stacklevel)


# Example usage:
# @track_deprecated_class("OldClassName", "NewClassName")
# class OldClassName(NewClassName):
#     pass

================================================================================
File: observability.py
Path: observability.py
================================================================================
"""Observability bundle for unified dependency injection.

Aggregates logger, tracer, and metrics into a single injectable dependency,
simplifying constructor signatures across the codebase.

This module enforces the Unified Observability Contract:
- logger: REQUIRED - pipeline cannot run without structured logging
- metrics: REQUIRED - always valid implementation (NoOpMetrics fallback)
- tracer: REQUIRED - explicit TracingPort owned by composition
- dq_monitor: Optional - data quality anomaly detection
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort

if TYPE_CHECKING:
    from bioetl.domain.ports import DQMonitorPort


class ObservabilityContractError(Exception):
    """Raised when observability contract requirements are not met.

    This error indicates a programming error in the bootstrap/composition layer
    where required observability components were not properly initialized.
    """


@dataclass(frozen=True)
class ObservabilityBundle:
    """Unified observability context for pipeline execution.

    Aggregates logger, tracer, metrics, and data quality monitor into
    a single injectable dependency. This reduces the number of constructor
    parameters and ensures consistent observability configuration across components.

    Unified Observability Contract:
    - logger: REQUIRED - structured logger, cannot be None
    - metrics: REQUIRED - MetricsPort implementation (NoOpMetrics if disabled)
    - tracer: REQUIRED - distributed tracing port (use NoOpTracing if disabled)
    - dq_monitor: Optional - data quality anomaly detector

    Raises:
        ObservabilityContractError: If required components are None.

    Attributes:
        logger: Structured logger for the pipeline.
        metrics: Metrics collection port (never None - uses NoOpMetrics fallback).
        tracer: Distributed tracing port (never None - use NoOpTracing if disabled).
        dq_monitor: Optional data quality anomaly detector.
    """

    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracingPort
    dq_monitor: DQMonitorPort | None = None

    def __post_init__(self) -> None:
        """Validate that required observability components are present."""
        if self.logger is None:
            raise ObservabilityContractError(
                "Logger is required. Cannot run pipeline without structured logging. "
                "Use bootstrap_observability_bundle() to create a valid bundle."
            )
        if self.metrics is None:
            raise ObservabilityContractError(
                "Metrics port is required. Use NoOpMetrics when metrics are disabled. "
                "Use bootstrap_observability_bundle() to create a valid bundle."
            )
        if self.tracer is None:
            raise ObservabilityContractError(
                "Tracer is required. Use NoOpTracing when tracing is disabled. "
                "Use bootstrap_observability_bundle() to create a valid bundle."
            )

    @classmethod
    def create(
        cls,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracer: TracingPort,
        dq_monitor: DQMonitorPort | None = None,
    ) -> ObservabilityBundle:
        """Factory method for creating observability bundle.

        Enforces the Unified Observability Contract by requiring
        valid logger and metrics implementations.

        Args:
            logger: Structured logger instance (required).
            metrics: Metrics port implementation (required, use NoOpMetrics if disabled).
            tracer: Tracer port (required, use NoOpTracing if disabled).
            dq_monitor: Optional data quality monitor port.

        Returns:
            Configured ObservabilityBundle instance.

        Raises:
            ObservabilityContractError: If logger or metrics is None.
        """
        return cls(logger=logger, metrics=metrics, tracer=tracer, dq_monitor=dq_monitor)

    def bind(self, **kwargs: object) -> ObservabilityBundle:
        """Create new bundle with bound logger context.

        Creates a new bundle with additional context bound to the logger.
        Useful for adding request-specific context (e.g., run_id, entity_id).

        Args:
            **kwargs: Key-value pairs to bind to the logger.

        Returns:
            New ObservabilityBundle with bound logger context.
        """
        return ObservabilityBundle(
            logger=self.logger.bind(**kwargs),
            tracer=self.tracer,
            metrics=self.metrics,
            dq_monitor=self.dq_monitor,
        )


__all__ = ["ObservabilityBundle", "ObservabilityContractError"]

================================================================================
File: observability_api.py
Path: observability_api.py
================================================================================
"""Canonical public observability composition API.

This module is the sanctioned public seam for observability-related runtime
helpers that need composition-owned dependency assembly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from bioetl.domain.exceptions import MetricsServerError
from bioetl.domain.ports import LoggerPort

if TYPE_CHECKING:
    from bioetl.application.services.audit_inspection_service import (
        AuditInspectionService,
    )
    from bioetl.application.services.checkpoint_service import CheckpointService
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.application.services.health_service import HealthService
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )
    from bioetl.application.services.metrics_service import MetricsService
    from bioetl.application.services.observability_workflow_service import (
        ObservabilityWorkflowService,
    )
    from bioetl.application.services.quarantine_service import QuarantineService

__all__ = [
    "MetricsOperatorProfile",
    "ObservabilityDiagnosticsBundle",
    "get_audit_service",
    "get_checkpoint_service",
    "get_health_service",
    "get_lineage_service",
    "get_metrics_operator_profile",
    "get_metrics_service",
    "get_observability_diagnostics_bundle",
    "get_observability_workflow_service",
    "get_quarantine_service",
    "get_run_manifest_service",
    "push_metrics_to_gateway",
    "start_metrics_server",
]


@dataclass(frozen=True, slots=True)
class ObservabilityDiagnosticsBundle:
    """Unified operator-facing observability diagnostics surface."""

    health_service: HealthService
    checkpoint_service: CheckpointService
    audit_service: AuditInspectionService
    metrics_service: MetricsService
    quarantine_service: QuarantineService
    run_manifest_service: RunManifestInspectionService
    lineage_service: LineageInspectionService
    workflow_service: ObservabilityWorkflowService


@dataclass(frozen=True, slots=True)
class MetricsOperatorProfile:
    """Operator-facing summary of metrics/admin observability behavior."""

    metrics_enabled: bool
    metrics_server_enabled: bool
    metrics_server_running: bool
    metrics_port: int
    metrics_addr: str
    metrics_started_at: datetime | None
    metrics_endpoint: str | None
    metrics_server_mode: str
    pushgateway_mode: str
    pushgateway_gateway: str
    tracing_enabled: bool
    audit_enabled: bool

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe diagnostics payload."""
        return {
            "metrics_enabled": self.metrics_enabled,
            "metrics_server_enabled": self.metrics_server_enabled,
            "metrics_server_running": self.metrics_server_running,
            "metrics_port": self.metrics_port,
            "metrics_addr": self.metrics_addr,
            "metrics_started_at": (
                self.metrics_started_at.isoformat()
                if self.metrics_started_at is not None
                else None
            ),
            "metrics_endpoint": self.metrics_endpoint,
            "metrics_server_mode": self.metrics_server_mode,
            "pushgateway_mode": self.pushgateway_mode,
            "pushgateway_gateway": self.pushgateway_gateway,
            "tracing_enabled": self.tracing_enabled,
            "audit_enabled": self.audit_enabled,
        }


def start_metrics_server(
    port: int = 8000,
    addr: str = "0.0.0.0",
    *,
    fail_fast: bool = False,
    retry_count: int = 3,
    retry_delay: float = 1.0,
    logger: LoggerPort | None = None,
) -> bool:
    """Start the metrics server through the canonical metrics service seam."""
    metrics_service = get_metrics_service()
    if logger is not None:
        metrics_service.logger = logger
    result = metrics_service.start(
        port=port,
        addr=addr,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
    )
    if fail_fast and not result.success and result.error is not None:
        raise MetricsServerError(port=port, reason=result.error)
    return bool(result.success)


def push_metrics_to_gateway(
    run_label: str = "bioetl",
    *,
    pipeline_name: str | None = None,
    run_type: str | None = None,
    logger: LoggerPort | None = None,
) -> bool:
    """Push metrics through the canonical composition-owned observability seam."""
    from bioetl.composition.bootstrap.runtime.observability import bootstrap_logger_port
    from bioetl.infrastructure.config import get_settings

    settings = get_settings()
    gateway = getattr(settings, "pushgateway_url", None) or "localhost:9091"
    grouping_key: dict[str, str] = {}
    if pipeline_name:
        grouping_key["pipeline"] = pipeline_name
    if run_type:
        grouping_key["run_type"] = run_type
    metrics_service = get_metrics_service()
    metrics_service.logger = logger or bootstrap_logger_port(
        pipeline=pipeline_name or "metrics_publication",
        run_id=uuid4(),
        log_level="INFO",
    )
    result = metrics_service.push_to_gateway(
        gateway=gateway,
        run_label=run_label,
        grouping_key=grouping_key,
    )
    return bool(result.success)


def get_audit_service() -> AuditInspectionService:
    """Load the audit diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_audit_service as _impl

    return _impl()


def get_checkpoint_service() -> CheckpointService:
    """Load the checkpoint diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_checkpoint_service as _impl

    return _impl()


def get_metrics_service() -> MetricsService:
    """Load the metrics diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_metrics_service as _impl

    return _impl()


def get_metrics_operator_profile() -> MetricsOperatorProfile:
    """Return the canonical operator-facing metrics/admin profile."""
    from bioetl.infrastructure.config import get_settings

    settings = get_settings()
    metrics_service = get_metrics_service()
    status = metrics_service.get_status()
    metrics_enabled = bool(settings.observability.metrics_enabled)
    metrics_server_enabled = bool(settings.observability.metrics_server_enabled)
    metrics_endpoint = None
    if metrics_enabled and metrics_server_enabled:
        metrics_endpoint = (
            f"http://{settings.metrics_addr}:{settings.metrics_port}/metrics"
        )
    metrics_server_mode = (
        "auto_managed_during_pipeline_runs"
        if metrics_enabled and metrics_server_enabled
        else "disabled"
    )
    pushgateway_mode = (
        "best_effort_on_run_completion" if metrics_enabled else "disabled"
    )
    pushgateway_gateway = getattr(settings, "pushgateway_url", None) or "localhost:9091"
    return MetricsOperatorProfile(
        metrics_enabled=metrics_enabled,
        metrics_server_enabled=metrics_server_enabled,
        metrics_server_running=status.running,
        metrics_port=settings.metrics_port,
        metrics_addr=settings.metrics_addr,
        metrics_started_at=status.started_at,
        metrics_endpoint=metrics_endpoint,
        metrics_server_mode=metrics_server_mode,
        pushgateway_mode=pushgateway_mode,
        pushgateway_gateway=pushgateway_gateway,
        tracing_enabled=bool(settings.observability.tracing_enabled),
        audit_enabled=bool(settings.observability.audit_enabled),
    )


def get_observability_workflow_service() -> ObservabilityWorkflowService:
    """Load the canonical observability workflow service on demand."""
    from bioetl.composition.services_api import (
        get_observability_workflow_service as _impl,
    )

    return _impl()


def get_health_service() -> HealthService:
    """Load the health diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_health_service as _impl

    return _impl()


def get_quarantine_service() -> QuarantineService:
    """Load the quarantine diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_quarantine_service as _impl

    return _impl()


def get_run_manifest_service() -> RunManifestInspectionService:
    """Load the run-manifest diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_run_manifest_service as _impl

    return _impl()


def get_lineage_service() -> LineageInspectionService:
    """Load the lineage diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_lineage_service as _impl

    return _impl()


def get_observability_diagnostics_bundle() -> ObservabilityDiagnosticsBundle:
    """Return the canonical unified observability diagnostics bundle."""

    return ObservabilityDiagnosticsBundle(
        health_service=get_health_service(),
        checkpoint_service=get_checkpoint_service(),
        audit_service=get_audit_service(),
        metrics_service=get_metrics_service(),
        quarantine_service=get_quarantine_service(),
        run_manifest_service=get_run_manifest_service(),
        lineage_service=get_lineage_service(),
        workflow_service=get_observability_workflow_service(),
    )

================================================================================
File: observability_resolution.py
Path: observability_resolution.py
================================================================================
"""Composition-owned helpers for resolving observability ports.

This module centralizes null-object fallback ownership for composition seams so
compatibility wrappers and factories do not each re-encode observability
defaults independently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.ports import MetricsPort, TracingPort
from bioetl.domain.ports.noop import NoOpMetrics, NoOpTracing

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings

__all__ = ["resolve_metrics_port", "resolve_tracing_port"]


def resolve_metrics_port(
    *,
    metrics: MetricsPort | None,
    settings: Settings | None = None,
) -> MetricsPort:
    """Return an explicit metrics port for composition-owned wiring.

    Preference order:
    1. use the injected metrics port when provided;
    2. derive the canonical runtime metrics port from settings;
    3. fall back to a composition-owned NoOpMetrics.
    """
    if metrics is not None:
        return metrics
    if settings is not None:
        from bioetl.composition.bootstrap.runtime.metrics_bootstrap import (
            bootstrap_metrics_port,
        )

        return bootstrap_metrics_port(settings)
    return NoOpMetrics(warn_on_use=False)


def resolve_tracing_port(
    *,
    tracer: TracingPort | None,
    settings: Settings | None = None,
    service_name: str = "bioetl",
) -> TracingPort:
    """Return an explicit tracing port for composition-owned wiring.

    Preference order:
    1. use the injected tracing port when provided;
    2. derive the canonical runtime tracing port from settings;
    3. fall back to a composition-owned NoOpTracing.
    """
    if tracer is not None:
        return tracer
    if settings is not None:
        from bioetl.composition.bootstrap.runtime.observability import (
            bootstrap_tracer_port,
        )

        return bootstrap_tracer_port(settings, service_name=service_name)
    return NoOpTracing()

================================================================================
File: __init__.py
Path: providers\__init__.py
================================================================================
"""Provider registration system.

Provides unified API for registering data source providers.

Example:
    >>> from bioetl.composition.providers import (
    ...     ProviderRegistry,
    ...     load_providers,
    ...     register_all_providers,
    ... )
    >>>
    >>> # Load all providers
    >>> load_providers()
    >>>
    >>> # Get provider configuration
    >>> config = ProviderRegistry.get("chembl")
    >>> config.http_config.rate
    10.0
"""

from __future__ import annotations

from bioetl.composition.providers.decorators import register_provider
from bioetl.composition.providers.loader import (
    ensure_providers_loaded,
    load_providers,
)
from bioetl.composition.providers.provider_registry import (
    DataSourceCreatorProtocol,
    HttpConfig,
    ProviderConfig,
    ProviderRegistry,
    create_provider_registry,
    get_default_provider_registry,
)
from bioetl.composition.providers.registration import register_all_providers

# Compatibility alias retained for legacy imports; new code should use
# DataSourceCreatorProtocol directly.
DataSourceCreatorPort = DataSourceCreatorProtocol

__all__ = [
    "DataSourceCreatorProtocol",
    "HttpConfig",
    "ProviderConfig",
    "ProviderRegistry",
    "create_provider_registry",
    "ensure_providers_loaded",
    "get_default_provider_registry",
    "load_providers",
    "register_all_providers",
    "register_provider",
]

================================================================================
File: _config_helpers.py
Path: providers\_config_helpers.py
================================================================================
"""Configuration helpers for provider registration."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.core.data_sources.filtered import FilteredDataSource
from bioetl.composition.bootstrap_contexts import (
    CircuitBreakerConfig,
    RateLimitContext,
)
from bioetl.composition.providers._models import ProviderSettingsProtocol
from bioetl.composition.source_config_access import load_source_config
from bioetl.domain.resilience import AdapterConfig
from bioetl.infrastructure.adapters.input.csv_filter_reader import CsvFilterReader

if TYPE_CHECKING:
    from bioetl.composition.bootstrap_contexts import RateLimitContext
    from bioetl.composition.providers._models import ProviderConfig
    from bioetl.composition.providers._registration_contracts import (
        HttpProviderConfigSpec,
        ProviderAssemblySupport,
    )
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.models.filter import ExtractionParams
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.schemas.source_config import SourceYamlConfig

ProviderFamilyExtraConfigBuilder = Callable[
    [dict[str, "RateLimitContext"], "ProviderAssemblySupport"],
    dict[str, "ProviderConfig"],
]


def _get_source_config(provider: str) -> SourceYamlConfig | None:
    """Load ``configs/providers/{provider}.yaml`` or return ``None``."""
    try:
        return load_source_config(provider)
    except ValueError:
        return None


def _get_batch_size_from_config(provider: str, default: int = 100) -> int:
    """Get batch size from source config, falling back to ``default``."""
    source_config = _get_source_config(provider)
    return source_config.batch_size if source_config else default


def _get_rate_limit_from_config(provider: str) -> RateLimitContext:
    """Get rate limit configuration from source config or defaults.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').

    Returns:
        RateLimitContext with rate and capacity values.
    """
    source_config = _get_source_config(provider)
    if source_config:
        return RateLimitContext(
            rate=source_config.rate_limit.requests_per_second,
            capacity=source_config.rate_limit.burst,
        )
    return RateLimitContext(rate=5.0, capacity=10)


def _get_rate_limits_from_config(*providers: str) -> dict[str, RateLimitContext]:
    """Resolve multiple provider rate limits through one canonical helper path."""
    return {provider: _get_rate_limit_from_config(provider) for provider in providers}


def _resolve_provider_family_registration_context(
    *providers: str,
    assembly_support: ProviderAssemblySupport | None = None,
) -> tuple[ProviderAssemblySupport, dict[str, RateLimitContext]]:
    """Resolve shared assembly support plus YAML-backed rate limits for a family."""
    from bioetl.composition.providers._registration_contracts import (
        resolve_provider_assembly_support,
    )

    return (
        resolve_provider_assembly_support(assembly_support),
        _get_rate_limits_from_config(*providers),
    )


def _build_provider_family_http_config_map(
    *,
    rate_limits: dict[str, RateLimitContext],
    assembly_support: ProviderAssemblySupport,
    spec_builder: Callable[
        [dict[str, RateLimitContext]], tuple[HttpProviderConfigSpec, ...]
    ],
) -> dict[str, ProviderConfig]:
    """Build one family's HTTP provider configs from a manifest builder."""
    from bioetl.composition.providers._registration_contracts import (
        build_http_provider_config_map,
    )

    return build_http_provider_config_map(
        specs=spec_builder(rate_limits),
        assembly_support=assembly_support,
    )


def _build_provider_family_config_map(
    *providers: str,
    assembly_support: ProviderAssemblySupport | None = None,
    http_spec_builder: Callable[
        [dict[str, RateLimitContext]],
        tuple[HttpProviderConfigSpec, ...],
    ],
    extra_config_builder: ProviderFamilyExtraConfigBuilder | None = None,
) -> dict[str, ProviderConfig]:
    """Build one provider family's config map from manifest builders."""
    support, rate_limits = _resolve_provider_family_registration_context(
        *providers,
        assembly_support=assembly_support,
    )
    configs = _build_provider_family_http_config_map(
        rate_limits=rate_limits,
        assembly_support=support,
        spec_builder=http_spec_builder,
    )
    if extra_config_builder is None:
        return configs
    return configs | extra_config_builder(rate_limits, support)


def _get_circuit_breaker_from_config(provider: str) -> CircuitBreakerConfig:
    """Get circuit breaker configuration from source config or defaults.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').

    Returns:
        CircuitBreakerConfig with failure_threshold and recovery_timeout.
    """
    source_config = _get_source_config(provider)
    if source_config:
        return CircuitBreakerConfig(
            failure_threshold=source_config.circuit_breaker.failure_threshold,
            recovery_timeout=source_config.circuit_breaker.recovery_timeout,
        )
    return CircuitBreakerConfig(failure_threshold=5, recovery_timeout=300)


def _get_adapter_config(provider: str, default_page_size: int = 1000) -> AdapterConfig:
    """Get AdapterConfig from source YAML config.

    This is the single source of truth for adapter parameters (RULES.md §12.1.2).
    Loads from configs/providers/{provider}.yaml and converts to domain dataclass.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem')
        default_page_size: Default page size if not specified in config

    Returns:
        AdapterConfig: Immutable adapter configuration

    Raises:
        ValueError: If source config file exists but is invalid.
    """
    source_config = _get_source_config(provider)
    if source_config is not None:
        return source_config.to_adapter_config(default_page_size=default_page_size)

    # Fallback to domain defaults when config file does not exist
    return AdapterConfig(page_size=default_page_size)


def _validate_extraction_input_filter_overlap(
    extraction_params: ExtractionParams,
    input_filter: InputFilterConfig,
    logger: LoggerPort,
) -> None:
    """Warn if input_filter field overlaps extraction_params keys.

    Args:
        extraction_params: Extraction parameters that may overlap with filter fields.
        input_filter: Input filter configuration specifying filter fields.
        logger: LoggerPort used to emit overlap warnings.
    """
    if not input_filter.enabled or extraction_params.is_empty:
        return

    filter_field = input_filter.filter_field
    if filter_field and filter_field in extraction_params.params:
        logger.warning(
            "extraction_params_input_filter_overlap",
            overlap_field=filter_field,
            extraction_value=str(extraction_params.params[filter_field]),
            resolution="input_filter will override extraction_params for this field",
        )

    if input_filter.columns:
        for col in input_filter.columns:
            if col.filter_field in extraction_params.params:
                logger.warning(
                    "extraction_params_input_filter_overlap",
                    overlap_field=col.filter_field,
                    extraction_value=str(extraction_params.params[col.filter_field]),
                    resolution="input_filter will override",
                )


def _wrap_with_filter(
    data_source: DataSourcePort,
    filter_config: InputFilterConfig | None,
    logger: LoggerPort | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Wrap data source with FilteredDataSource if filter is enabled.

    Args:
        data_source: Base data source to conditionally wrap.
        filter_config: Optional filter configuration; wraps only if enabled.
        logger: Optional LoggerPort for FilteredDataSource; defaults to None.
        metrics: Optional MetricsPort for filter statistics; defaults to None.
        pipeline_name: Pipeline name for metrics labels; defaults to 'unknown'.

    Returns:
        FilteredDataSource wrapping data_source, or data_source unchanged.
    """
    _wire_composable_fallback(data_source)

    if filter_config and filter_config.enabled:
        return FilteredDataSource(
            data_source=data_source,
            filter_reader=CsvFilterReader(logger=logger),
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
            logger=logger,
        )
    return data_source


def _wire_composable_fallback(data_source: DataSourcePort) -> None:
    """Apply provider fallback policy once from composition root wiring.

    Args:
        data_source: Data source adapter to configure with fallback policy if
            it exposes a configure_fallback_policy method and a provider_name.
    """
    provider_name = getattr(data_source, "provider_name", None)
    if not isinstance(provider_name, str) or not provider_name.strip():
        return

    source_config = _get_source_config(provider_name)
    if source_config is None:
        return

    configure = getattr(data_source, "configure_fallback_policy", None)
    policy = source_config.provider_config.fallback
    if callable(configure) and policy is not None:
        configure(policy)


def _create_http_data_source(
    provider: str,
    settings: ProviderSettingsProtocol,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None,
    metrics: MetricsPort | None,
    pipeline_name: str,
    *,
    adapter_factory: Callable[..., DataSourcePort],
    extra_kwargs: dict[str, object] | None = None,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Generic HTTP data source: http_client + helpers + adapter + filter wrap.

    Encapsulates the shared skeleton of biblio provider creators
    (PubMed, CrossRef, OpenAlex, SemanticScholar).

    Args:
        provider: Provider name for HTTP client creation.
        settings: Application settings.
        logger: Logger port.
        filter_config: Optional input filter configuration.
        metrics: Optional metrics port.
        pipeline_name: Pipeline name for filter wrapping.
        adapter_factory: Callable that constructs the concrete adapter.
        extra_kwargs: Provider-specific kwargs merged into adapter construction.

    Returns:
        DataSourcePort, optionally wrapped with FilteredDataSource.
    """
    from bioetl.composition.factories.datasource.adapter_helpers import (
        AdapterHelpersFactory,
    )
    from bioetl.composition.providers._registration_contracts import (
        resolve_provider_assembly_support,
    )

    support = resolve_provider_assembly_support(assembly_support)
    http_client = support.create_http_client(provider, settings, metrics=metrics)
    helper_services = AdapterHelpersFactory.create_http_helpers(
        provider=provider,
        logger=logger,
        metrics=metrics,
    )
    kwargs: dict[str, object] = {
        "http_client": http_client,
        "logger": logger,
        "metrics": metrics,
        **helper_services.as_injection_kwargs(),
        **(extra_kwargs or {}),
    }
    data_source = adapter_factory(**kwargs)
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _normalize_optional_override(value: str | None) -> str | None:
    """Normalize optional pipeline override values.

    Empty strings and `${ENV_VAR}` placeholders are treated as unset to allow
    fallback to centralized settings/config providers.

    Args:
        value: Optional string value potentially containing empty strings or
            unresolved environment variable placeholders.

    Returns:
        Cleaned string value, or None if absent, empty, or an unresolved placeholder.
    """
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.startswith("${") and cleaned.endswith("}"):
        return None
    return cleaned

================================================================================
File: _creation.py
Path: providers\_creation.py
================================================================================
"""Shared adapter/data-source creation helpers for provider registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.providers._models import (
    DataSourceCreatorProtocol,
    ProviderConfig,
    ProviderSettingsProtocol,
)

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class ProviderCreator:
    """Consolidated provider adapter and data-source creation logic."""

    def create_adapter(
        self,
        *,
        name: str,
        config: ProviderConfig,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: ProviderSettingsProtocol | None = None,
        **kwargs: object,
    ) -> DataSourcePort:
        """Create a provider adapter instance."""
        return create_provider_adapter(
            name=name,
            config=config,
            http_client=http_client,
            logger=logger,
            settings=settings,
            **kwargs,
        )

    def create_data_source(
        self,
        *,
        name: str,
        config: ProviderConfig,
        settings: ProviderSettingsProtocol,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        """Create a fully configured provider data source."""
        return create_provider_data_source(
            name=name,
            config=config,
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
        )

    def has_data_source_creator(self, config: ProviderConfig) -> bool:
        """Return whether the provider config exposes a data-source creator."""
        return provider_has_data_source_creator(config)

    def require_data_source_creator(self, *, name: str, config: ProviderConfig) -> None:
        """Raise a stable error when a provider lacks data-source creator support."""
        require_provider_data_source_creator(name=name, config=config)

    def build_bound_creator(
        self,
        *,
        name: str,
        create_data_source_fn: DataSourceCreatorProtocol,
    ) -> DataSourceCreatorProtocol:
        """Return a provider-bound data-source creator closure."""
        return build_bound_data_source_creator(
            name=name,
            create_data_source=create_data_source_fn,
        )


def create_provider_adapter(
    *,
    name: str,
    config: ProviderConfig,
    http_client: UnifiedHTTPClient | None = None,
    logger: LoggerPort | None = None,
    settings: ProviderSettingsProtocol | None = None,
    **kwargs: object,
) -> DataSourcePort:
    """Create a provider adapter instance using the supplied registry config."""
    if config.custom_creator is not None:
        return config.custom_creator(
            http_client=http_client,
            logger=logger,
            settings=settings,
            **kwargs,
        )

    init_kwargs: dict[str, object] = {
        **config.default_kwargs,
        **kwargs,
    }
    _inject_http_client(
        provider_name=name,
        config=config,
        http_client=http_client,
        init_kwargs=init_kwargs,
    )
    _inject_logger(
        provider_name=name,
        config=config,
        logger=logger,
        init_kwargs=init_kwargs,
    )
    return config.adapter_class(**init_kwargs)


def create_provider_data_source(
    *,
    name: str,
    config: ProviderConfig,
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create a fully configured provider data source from registry metadata."""
    if config.data_source_creator is None:
        raise ValueError(
            f"Provider '{name}' does not have a data_source_creator configured. "
            "Register the provider with a data_source_creator in registration.py."
        )

    return config.data_source_creator(
        settings=settings,
        pipeline_config=pipeline_config,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
    )


def provider_has_data_source_creator(config: ProviderConfig) -> bool:
    """Return whether the provider config exposes a data-source creator."""
    return config.data_source_creator is not None


def require_provider_data_source_creator(
    *,
    name: str,
    config: ProviderConfig,
) -> None:
    """Raise a stable error when a provider lacks data-source creator support."""
    if provider_has_data_source_creator(config):
        return
    raise KeyError(
        f"Provider '{name}' does not have a data_source_creator. "
        "Ensure it is registered with data_source_creator in registration.py."
    )


def build_bound_data_source_creator(
    *,
    name: str,
    create_data_source: DataSourceCreatorProtocol,
) -> DataSourceCreatorProtocol:
    """Return a provider-bound data-source creator closure."""
    del name

    def creator(
        settings: ProviderSettingsProtocol,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        return create_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
        )

    return creator


def _inject_http_client(
    *,
    provider_name: str,
    config: ProviderConfig,
    http_client: UnifiedHTTPClient | None,
    init_kwargs: dict[str, object],
) -> None:
    """Inject the shared HTTP client into adapter init kwargs when required."""
    if not config.requires_http_client:
        return
    if http_client is None:
        raise ValueError(
            f"Provider '{provider_name}' requires http_client but none was provided. "
            "Ensure http_client is passed from Composition Root."
        )
    init_kwargs["http_client"] = http_client


def _inject_logger(
    *,
    provider_name: str,
    config: ProviderConfig,
    logger: LoggerPort | None,
    init_kwargs: dict[str, object],
) -> None:
    """Inject structured logger into adapter init kwargs when required."""
    if not config.requires_logger:
        return
    if logger is None:
        raise ValueError(
            f"Provider '{provider_name}' requires logger but none was provided. "
            "Ensure logger is passed from Composition Root."
        )
    init_kwargs["logger"] = logger

================================================================================
File: _default_registry.py
Path: providers\_default_registry.py
================================================================================
"""Retained class-level compatibility helpers for the default provider registry.

This module is the private owner of the lazy default registry singleton used by
legacy class-level access patterns. New bootstrap logic should resolve
registries through ``_registry_resolution.py`` or explicit injection instead of
importing this helper directly.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Generic,
    Protocol,
    Self,
    TypeVar,
    overload,
)

if TYPE_CHECKING:
    from bioetl.composition.providers._models import ProviderConfig
    from bioetl.composition.providers.provider_registry import ProviderRegistry

R = TypeVar("R")


class _SupportsDefaultRegistry(Protocol):
    """Protocol for registries exposing a lazy default instance."""

    @classmethod
    def _get_default(
        cls,
    ) -> Self:
        """Return the lazy default registry instance."""


class _SupportsProviderStore(Protocol):
    """Protocol for provider stores exposing the underlying mapping."""

    _providers: dict[str, ProviderConfig]


class _SupportsProviderRegistryStore(_SupportsDefaultRegistry, Protocol):
    """Protocol for registries exposing a provider store."""

    _store: _SupportsProviderStore


RegistryT = TypeVar("RegistryT", bound=_SupportsDefaultRegistry)
ProviderRegistryT = TypeVar("ProviderRegistryT", bound=_SupportsProviderRegistryStore)

_default_provider_registry: ProviderRegistry | None = None


class DefaultRegistryMethod(Generic[R]):
    """Dispatch class access to the lazy default registry and instance access locally."""

    def __init__(self, func: Callable[..., R]) -> None:
        self._func = func
        self.__doc__ = func.__doc__
        self.__name__ = func.__name__

    @overload
    def __get__(
        self,
        obj: RegistryT,
        objtype: type[RegistryT] | None = None,
    ) -> Callable[..., R]: ...

    @overload
    def __get__(
        self,
        obj: None,
        objtype: type[RegistryT],
    ) -> Callable[..., R]: ...

    def __get__(
        self,
        obj: RegistryT | None,
        objtype: type[RegistryT] | None = None,
    ) -> Callable[..., R]:
        if obj is not None:
            target = obj
        else:
            if objtype is None:
                raise AssertionError(
                    "objtype is required for class-level registry access"
                )
            target = objtype._get_default()

        @wraps(self._func)
        def bound(*args: object, **kwargs: object) -> R:
            return self._func(target, *args, **kwargs)

        return bound


class ProvidersDescriptor(Generic[ProviderRegistryT]):
    """Expose the default singleton store on class access for compatibility."""

    def __get__(
        self,
        obj: ProviderRegistryT | None,
        objtype: type[ProviderRegistryT],
    ) -> dict[str, ProviderConfig]:
        target = obj if obj is not None else objtype._get_default()
        return target._store._providers


def get_default_provider_registry() -> ProviderRegistry:
    """Return the lazily-created default provider registry singleton."""
    global _default_provider_registry
    if _default_provider_registry is None:
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        _default_provider_registry = ProviderRegistry()
    return _default_provider_registry

================================================================================
File: _loading.py
Path: providers\_loading.py
================================================================================
"""Leaf provider-registry loading helpers with injected registration routine."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.composition.providers._registry_protocols import (
    ProviderRegistrarProtocol,
)


def _register_default_providers(registry: ProviderRegistrarProtocol) -> None:
    """Register providers using the canonical registration entrypoint."""
    from bioetl.composition.providers.registration import register_all_providers

    register_all_providers(registry=registry)


def _has_registered_providers(registry: ProviderRegistrarProtocol) -> bool:
    """Return whether the target registry currently contains providers."""
    return bool(registry.list_providers())


def load_provider_registry(
    registry: ProviderRegistrarProtocol,
    *,
    force: bool = False,
    register_providers: Callable[[ProviderRegistrarProtocol], None] | None = None,
) -> None:
    """Load and register all providers into the supplied registry."""
    register_fn = (
        register_providers
        if register_providers is not None
        else _register_default_providers
    )

    if _has_registered_providers(registry) and not force:
        return

    if force:
        registry.clear()

    register_fn(registry)


def ensure_provider_registry_loaded(
    registry: ProviderRegistrarProtocol,
    *,
    register_providers: Callable[[ProviderRegistrarProtocol], None] | None = None,
) -> None:
    """Ensure the supplied registry has been populated with providers."""
    if not get_provider_registry_loaded_status(registry):
        load_provider_registry(
            registry,
            register_providers=register_providers,
        )


def get_provider_registry_loaded_status(
    registry: ProviderRegistrarProtocol,
) -> bool:
    """Return current loaded status for the supplied registry."""
    return _has_registered_providers(registry)


def reset_provider_registry_loader(
    registry: ProviderRegistrarProtocol,
) -> None:
    """Reset loader state and clear the supplied registry. Testing only."""
    registry.clear()

================================================================================
File: _models.py
Path: providers\_models.py
================================================================================
"""Internal provider registry models and creator contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "AdapterCreator",
    "DataSourceCreatorPort",
    "DataSourceCreatorProtocol",
    "HttpConfig",
    "ProviderConfig",
    "ProviderSettingsProtocol",
]


AdapterCreator = Callable[..., "DataSourcePort"]


class SecretValueProviderProtocol(Protocol):
    """Minimal secret wrapper contract used by provider settings wiring."""

    def get_secret_value(self) -> str:
        """Return the resolved secret payload."""
        ...


class ProviderSettingsProtocol(Protocol):
    """Minimal settings surface required by provider registration helpers."""

    @property
    def default_email(self) -> str | None:
        """Return the default contact email used by provider clients."""
        ...

    @property
    def strict_error_handling(self) -> bool:
        """Return whether provider adapters should fail fast on recoverable errors."""
        ...

    @property
    def pubmed_api_key(self) -> SecretValueProviderProtocol | None:
        """Return the configured PubMed API key wrapper when available."""
        ...

    @property
    def semanticscholar_api_key(self) -> SecretValueProviderProtocol | None:
        """Return the configured Semantic Scholar API key wrapper when available."""
        ...


class DataSourceCreatorProtocol(Protocol):
    """Protocol for composition-side data source creator callables."""

    def __call__(
        self,
        settings: ProviderSettingsProtocol,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        """Create a fully configured data source."""
        ...


@dataclass(frozen=True)
class HttpConfig:
    """HTTP client configuration for a provider."""

    rate: float = 5.0
    capacity: int = 10
    rate_overrides: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderConfig:
    """Complete provider configuration used by the composition registry."""

    adapter_class: type[DataSourcePort]
    http_config: HttpConfig | None = None
    requires_http_client: bool = True
    requires_logger: bool = True
    default_kwargs: dict[str, object] = field(default_factory=dict)
    custom_creator: AdapterCreator | None = None
    data_source_creator: DataSourceCreatorProtocol | None = None


# Compatibility alias retained for legacy imports; new code should use
# DataSourceCreatorProtocol directly.
DataSourceCreatorPort = DataSourceCreatorProtocol

================================================================================
File: _registration_biblio_adapters.py
Path: providers\_registration_biblio_adapters.py
================================================================================
"""Adapter creation helpers for bibliographic provider registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.composition.factories.datasource.adapter_helpers import (
    AdapterHelpersFactory,
)
from bioetl.composition.providers._models import ProviderSettingsProtocol

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.adapters.openalex import OpenAlexAdapter
    from bioetl.infrastructure.adapters.pubmed import PubMedAdapter


def _get_default_email(settings: ProviderSettingsProtocol | None) -> str | None:
    """Return non-empty default email from settings when available."""
    return None if settings is None else settings.default_email or None


def _get_pubmed_api_key(settings: ProviderSettingsProtocol | None) -> str | None:
    """Return resolved PubMed API key from settings when configured."""
    if settings is None or settings.pubmed_api_key is None:
        return None
    return settings.pubmed_api_key.get_secret_value()


def _build_pubmed_adapter_from_settings(
    *,
    adapter_cls: type[PubMedAdapter],
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: ProviderSettingsProtocol | None,
    **kwargs: Any,  # Any: forward arbitrary adapter kwargs
) -> PubMedAdapter:
    """Create PubMedAdapter with credential resolution owned by composition."""
    email = kwargs.get("email") or _get_default_email(settings)
    if not email:
        raise ValueError("PubMed adapter requires email")

    api_key = kwargs.get("api_key") or _get_pubmed_api_key(settings)

    if http_client is None:
        raise ValueError("PubMed adapter requires http_client")
    if logger is None:
        raise ValueError("PubMed adapter requires logger")
    metrics = kwargs.get("metrics")
    helper_services = AdapterHelpersFactory.create_http_helpers(
        provider="pubmed",
        logger=logger,
        metrics=metrics,
    )

    return adapter_cls(
        http_client=http_client,
        logger=logger,
        email=email,
        api_key=api_key,
        batch_size=kwargs.get("batch_size", 200),
        metrics=metrics,
        dependency_context=kwargs.get("dependency_context"),
        error_handler=kwargs.get("error_handler", helper_services.error_handler),
        adapter_metrics=kwargs.get(
            "adapter_metrics",
            helper_services.adapter_metrics,
        ),
        request_collector=kwargs.get(
            "request_collector",
            helper_services.request_collector,
        ),
        fallback_fetch_service=kwargs.get(
            "fallback_fetch_service",
            helper_services.fallback_fetch_service,
        ),
    )


def _build_openalex_adapter_from_settings(
    *,
    adapter_cls: type[OpenAlexAdapter],
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: ProviderSettingsProtocol | None,
    **kwargs: Any,  # Any: forward arbitrary adapter kwargs
) -> OpenAlexAdapter:
    """Create OpenAlexAdapter with mailto resolution owned by composition."""
    mailto = kwargs.get("mailto") or _get_default_email(settings)
    if not mailto:
        raise ValueError(
            "OpenAlex adapter requires mailto. "
            "Provide via 'mailto' kwarg or settings.default_email"
        )

    if http_client is None:
        raise ValueError("OpenAlex adapter requires http_client")
    if logger is None:
        raise ValueError("OpenAlex adapter requires logger")
    metrics = kwargs.get("metrics")
    helper_services = AdapterHelpersFactory.create_http_helpers(
        provider="openalex",
        logger=logger,
        metrics=metrics,
    )

    return adapter_cls(
        http_client=http_client,
        logger=logger,
        mailto=mailto,
        batch_size=kwargs.get("batch_size", 50),
        metrics=metrics,
        dependency_context=kwargs.get("dependency_context"),
        error_handler=kwargs.get("error_handler", helper_services.error_handler),
        adapter_metrics=kwargs.get(
            "adapter_metrics",
            helper_services.adapter_metrics,
        ),
        request_collector=kwargs.get(
            "request_collector",
            helper_services.request_collector,
        ),
        fallback_fetch_service=kwargs.get(
            "fallback_fetch_service",
            helper_services.fallback_fetch_service,
        ),
    )


__all__ = [
    "_build_openalex_adapter_from_settings",
    "_build_pubmed_adapter_from_settings",
]

================================================================================
File: _registration_biblio_profiles.py
Path: providers\_registration_biblio_profiles.py
================================================================================
"""Request-profile helpers for bibliographic provider registration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.providers._config_helpers import _normalize_optional_override
from bioetl.composition.providers._models import ProviderSettingsProtocol

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True)
class MailtoBatchProfile:
    """Resolved mailto + batch settings for polite-pool biblio providers."""

    mailto: str | None
    batch_size: int


@dataclass(frozen=True)
class PubMedRequestProfile:
    """Resolved PubMed request credentials for data-source assembly."""

    email: str | None
    api_key: str | None


@dataclass(frozen=True)
class SemanticScholarRequestProfile:
    """Resolved Semantic Scholar request settings."""

    api_key: str
    batch_size: int


def _resolve_biblio_contact_email(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
) -> str | None:
    """Resolve pipeline email override with settings fallback."""
    configured_email = _normalize_optional_override(pipeline_config.source.email)
    return configured_email or settings.default_email


def _resolve_pubmed_request_profile(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
) -> PubMedRequestProfile:
    """Resolve PubMed email + API key using pipeline override precedence."""
    configured_api_key = _normalize_optional_override(pipeline_config.source.api_key)
    settings_api_key = (
        settings.pubmed_api_key.get_secret_value() if settings.pubmed_api_key else None
    )
    return PubMedRequestProfile(
        email=_resolve_biblio_contact_email(settings, pipeline_config),
        api_key=configured_api_key or settings_api_key,
    )


def _resolve_mailto_batch_profile(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    *,
    batch_size: int,
) -> MailtoBatchProfile:
    """Resolve polite-pool mailto and batch size for a biblio provider."""
    return MailtoBatchProfile(
        mailto=_resolve_biblio_contact_email(settings, pipeline_config),
        batch_size=batch_size,
    )


def _resolve_semanticscholar_request_profile(
    settings: ProviderSettingsProtocol,
    *,
    batch_size: int,
) -> SemanticScholarRequestProfile:
    """Resolve Semantic Scholar API key and batch defaults."""
    api_key = (
        settings.semanticscholar_api_key.get_secret_value()
        if settings.semanticscholar_api_key
        else ""
    )
    return SemanticScholarRequestProfile(
        api_key=api_key,
        batch_size=batch_size,
    )


__all__ = [
    "MailtoBatchProfile",
    "PubMedRequestProfile",
    "SemanticScholarRequestProfile",
    "_resolve_biblio_contact_email",
    "_resolve_mailto_batch_profile",
    "_resolve_pubmed_request_profile",
    "_resolve_semanticscholar_request_profile",
]

================================================================================
File: _registration_contracts.py
Path: providers\_registration_contracts.py
================================================================================
"""Leaf contracts and injected support for provider registration assembly."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, Protocol, cast

from bioetl.composition.providers._models import (
    AdapterCreator,
    DataSourceCreatorProtocol,
    HttpConfig,
    ProviderConfig,
    ProviderSettingsProtocol,
)

if TYPE_CHECKING:
    from bioetl.composition.providers.provider_registry import ProviderRegistry
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class ProviderHttpClientFactoryProtocol(Protocol):
    """Callable contract for provider HTTP client construction."""

    def __call__(
        self,
        provider: str,
        settings: ProviderSettingsProtocol | None = None,
        *,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
    ) -> UnifiedHTTPClient:
        """Create a provider-scoped HTTP client."""
        ...


class ProviderAdapterFactoryProtocol(Protocol):
    """Callable contract for provider adapter construction."""

    def __call__(
        self,
        provider: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: ProviderSettingsProtocol | None = None,
        **kwargs: object,
    ) -> DataSourcePort:
        """Create a provider adapter via composition-owned wiring."""
        ...


class SupportAwareDataSourceCreatorProtocol(Protocol):
    """Protocol for data-source creators that accept injected assembly support."""

    def __call__(
        self,
        settings: ProviderSettingsProtocol,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
        *,
        assembly_support: ProviderAssemblySupport | None = None,
    ) -> DataSourcePort:
        """Create a fully configured data source with optional support injection."""
        ...


@dataclass(frozen=True)
class ProviderAssemblySupport:
    """Injected factory callbacks for provider registration definitions."""

    create_http_client: ProviderHttpClientFactoryProtocol
    create_adapter: ProviderAdapterFactoryProtocol


@dataclass(frozen=True)
class HttpProviderConfigSpec:
    """Declarative manifest entry for one HTTP-backed provider config."""

    provider_name: str
    adapter_class: type[DataSourcePort]
    rate: float
    capacity: int
    data_source_creator: SupportAwareDataSourceCreatorProtocol
    rate_overrides: dict[str, float] | None = None
    custom_creator: AdapterCreator | None = None


def _create_http_client_for_provider(
    provider: str,
    settings: ProviderSettingsProtocol | None = None,
    *,
    metrics: MetricsPort | None = None,
    logger: LoggerPort | None = None,
    provider_registry: ProviderRegistry | None = None,
) -> UnifiedHTTPClient:
    """Resolve the canonical HTTP client factory lazily at the composition edge."""
    from bioetl.composition.factories.datasource.http_client import HttpClientFactory

    return HttpClientFactory.create_for_provider(
        provider,
        cast("Any", settings),  # Any: concrete settings model is resolved at runtime.
        metrics=metrics,
        logger=logger,
        provider_registry=provider_registry,
    )


def _create_adapter_for_provider(
    provider: str,
    http_client: UnifiedHTTPClient | None = None,
    logger: LoggerPort | None = None,
    settings: ProviderSettingsProtocol | None = None,
    *,
    provider_registry: ProviderRegistry | None = None,
    **kwargs: object,
) -> DataSourcePort:
    """Resolve the canonical adapter factory lazily at the composition edge."""
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceFactory,
    )

    return DataSourceFactory.create(
        provider,
        http_client=http_client,
        logger=logger,
        settings=cast(
            "Any",  # Any: provider settings object is adapter-specific at runtime.
            settings,
        ),  # Any: adapter factory accepts provider-specific settings surfaces.
        provider_registry=provider_registry,
        **kwargs,
    )


def create_provider_assembly_support(
    *,
    provider_registry: object | None = None,
) -> ProviderAssemblySupport:
    """Build the default injected support bundle for provider registration."""
    resolved_registry = _resolve_provider_registry_candidate(provider_registry)
    return ProviderAssemblySupport(
        create_http_client=partial(
            _create_http_client_for_provider,
            provider_registry=resolved_registry,
        ),
        create_adapter=partial(
            _create_adapter_for_provider,
            provider_registry=resolved_registry,
        ),
    )


def resolve_provider_assembly_support(
    assembly_support: ProviderAssemblySupport | None,
    *,
    provider_registry: object | None = None,
) -> ProviderAssemblySupport:
    """Return the injected support bundle or build the canonical default one."""
    if assembly_support is not None:
        return assembly_support

    return create_provider_assembly_support(provider_registry=provider_registry)


def _resolve_provider_registry_candidate(
    provider_registry: object | None,
) -> ProviderRegistry | None:
    """Return registry candidate only when it exposes full registry surface."""
    required_methods = (
        "get_http_config",
        "create_data_source",
        "build_data_source_creator",
        "is_registered",
        "list_providers",
    )
    if provider_registry is None:
        return None
    if not all(
        hasattr(provider_registry, method_name) for method_name in required_methods
    ):
        return None
    return cast("ProviderRegistry", provider_registry)


def bind_provider_data_source_creator(
    creator: SupportAwareDataSourceCreatorProtocol,
    *,
    assembly_support: ProviderAssemblySupport,
) -> DataSourceCreatorProtocol:
    """Bind the shared assembly support to a support-aware data-source creator."""
    return cast(
        DataSourceCreatorProtocol,
        partial(creator, assembly_support=assembly_support),
    )


def build_data_source_provider_config(
    *,
    adapter_class: type[DataSourcePort],
    http_config: HttpConfig | None,
    requires_http_client: bool,
    requires_logger: bool = True,
    custom_creator: AdapterCreator | None = None,
    data_source_creator: DataSourceCreatorProtocol | None = None,
) -> ProviderConfig:
    """Build the canonical ProviderConfig shape for registry data-source entries."""
    return ProviderConfig(
        adapter_class=adapter_class,
        http_config=http_config,
        requires_http_client=requires_http_client,
        requires_logger=requires_logger,
        custom_creator=custom_creator,
        data_source_creator=data_source_creator,
    )


def build_http_provider_config(
    *,
    adapter_class: type[DataSourcePort],
    rate: float,
    capacity: int,
    data_source_creator: SupportAwareDataSourceCreatorProtocol,
    assembly_support: ProviderAssemblySupport,
    rate_overrides: dict[str, float] | None = None,
    custom_creator: AdapterCreator | None = None,
) -> ProviderConfig:
    """Build the common HTTP-oriented ProviderConfig shape for registration."""
    return build_data_source_provider_config(
        adapter_class=adapter_class,
        http_config=HttpConfig(
            rate=rate,
            capacity=capacity,
            rate_overrides=rate_overrides or {},
        ),
        requires_http_client=True,
        requires_logger=True,
        custom_creator=custom_creator,
        data_source_creator=bind_provider_data_source_creator(
            data_source_creator,
            assembly_support=assembly_support,
        ),
    )


def build_http_provider_config_map(
    *,
    specs: tuple[HttpProviderConfigSpec, ...],
    assembly_support: ProviderAssemblySupport,
) -> dict[str, ProviderConfig]:
    """Build multiple HTTP-backed provider configs from one declarative manifest."""
    return {
        spec.provider_name: build_http_provider_config(
            adapter_class=spec.adapter_class,
            rate=spec.rate,
            capacity=spec.capacity,
            rate_overrides=spec.rate_overrides,
            custom_creator=spec.custom_creator,
            data_source_creator=spec.data_source_creator,
            assembly_support=assembly_support,
        )
        for spec in specs
    }

================================================================================
File: _registry_protocols.py
Path: providers\_registry_protocols.py
================================================================================
"""Neutral protocol contracts shared by provider-registry helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.composition.providers._models import ProviderConfig


class ProviderRegistrarProtocol(Protocol):
    """Minimal registry contract for provider registration assembly."""

    def register(self, name: str, config: ProviderConfig) -> None:
        """Register a provider config."""
        ...

    def is_registered(self, name: str) -> bool:
        """Return whether the provider is already registered."""
        ...

    def list_providers(self) -> list[str]:
        """List registered providers."""
        ...

    def clear(self) -> None:
        """Clear all registered providers."""
        ...

================================================================================
File: _registry_resolution.py
Path: providers\_registry_resolution.py
================================================================================
"""Canonical provider-registry resolution helpers for composition seams."""

from __future__ import annotations

from typing import Literal, TypeVar, cast, overload

from bioetl.composition.providers._registry_protocols import (
    ProviderRegistrarProtocol,
)
from bioetl.composition.providers.provider_registry import (
    ProviderRegistry,
)
from bioetl.composition.providers.provider_registry import (
    resolve_provider_registry as _resolve_public_provider_registry,
)

__all__ = ["resolve_provider_registry"]

RegistryT = TypeVar("RegistryT", bound=ProviderRegistrarProtocol)


@overload
def resolve_provider_registry(
    provider_registry: None = None,
    *,
    ensure_ready: Literal[False] = False,
) -> ProviderRegistry:
    """Resolve default provider registry without forcing readiness."""
    ...


@overload
def resolve_provider_registry(
    provider_registry: ProviderRegistry | None = None,
    *,
    ensure_ready: Literal[True],
) -> ProviderRegistry:
    """Resolve provider registry and guarantee ready/loaded state."""
    ...


@overload
def resolve_provider_registry(
    provider_registry: RegistryT,
    *,
    ensure_ready: Literal[False] = False,
) -> RegistryT:
    """Pass through explicit registry implementation without readiness forcing."""
    ...


def resolve_provider_registry(
    provider_registry: ProviderRegistrarProtocol | None = None,
    *,
    ensure_ready: bool = False,
) -> ProviderRegistrarProtocol:
    """Resolve explicit-or-default registry access through one private seam."""
    return _resolve_public_provider_registry(
        cast("ProviderRegistry | None", provider_registry),
        ensure_ready=ensure_ready,
    )

================================================================================
File: _store.py
Path: providers\_store.py
================================================================================
"""Internal registry-store helpers for provider metadata."""

from __future__ import annotations

from bioetl.composition.providers._models import ProviderConfig


class ProviderStore:
    """Thread-safe-compatible provider configuration store."""

    def __init__(self, providers: dict[str, ProviderConfig] | None = None) -> None:
        self._providers = providers if providers is not None else {}

    def register(self, name: str, config: ProviderConfig) -> None:
        """Register or overwrite a provider config in the shared store."""
        self._providers[name] = config

    def get(self, name: str) -> ProviderConfig:
        """Return provider config or raise a KeyError with available options."""
        if name not in self._providers:
            available = ", ".join(sorted(self._providers.keys()))
            raise KeyError(f"Unknown provider: {name}. Available: {available}")
        return self._providers[name]

    def is_registered(self, name: str) -> bool:
        """Return whether a provider name is present in the shared store."""
        return name in self._providers

    def list_names(self) -> list[str]:
        """Return registered provider names in stable sorted order."""
        return sorted(self._providers.keys())

    def clear(self) -> None:
        """Clear all registered providers."""
        self._providers.clear()


def register_provider_config(
    providers: dict[str, ProviderConfig],
    name: str,
    config: ProviderConfig,
) -> None:
    """Register or overwrite a provider config (backward-compatible function)."""
    providers[name] = config


def get_provider_config(
    providers: dict[str, ProviderConfig],
    name: str,
) -> ProviderConfig:
    """Return provider config (backward-compatible function)."""
    if name not in providers:
        available = ", ".join(sorted(providers.keys()))
        raise KeyError(f"Unknown provider: {name}. Available: {available}")
    return providers[name]


def is_provider_registered(
    providers: dict[str, ProviderConfig],
    name: str,
) -> bool:
    """Return whether a provider name is present (backward-compatible function)."""
    return name in providers


def list_provider_names(providers: dict[str, ProviderConfig]) -> list[str]:
    """Return registered provider names (backward-compatible function)."""
    return sorted(providers.keys())

================================================================================
File: decorators.py
Path: providers\decorators.py
================================================================================
"""Decorators for provider registration.

Provides a declarative API for registering provider adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from bioetl.composition.providers._models import (
    AdapterCreator,
    HttpConfig,
    ProviderConfig,
)
from bioetl.composition.providers.provider_registry import (
    register_default_provider_config,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.ports import DataSourcePort


__all__ = [
    "T",
    "register_provider",
]

T = TypeVar("T", bound="DataSourcePort")


def _register_provider_class(
    *,
    cls: type[T],
    name: str,
    http_rate: float,
    http_capacity: int,
    requires_http_client: bool,
    requires_logger: bool,
    rate_overrides: dict[str, float] | None,
    custom_creator: AdapterCreator | None,
    default_kwargs: dict[str, object],
) -> None:
    """Register decorated adapter class in provider registry.

    Args:
        cls: Adapter class implementing DataSourcePort to register.
        name: Unique provider name (e.g., 'chembl', 'pubchem').
        http_rate: Base rate limit in requests per second.
        http_capacity: Token bucket capacity for burst handling.
        requires_http_client: If True, http_client is injected at adapter creation.
        requires_logger: If True, logger is injected at adapter creation.
        rate_overrides: Optional dict mapping settings attribute names to boosted
            rate limits when API keys are present.
        custom_creator: Optional callable replacing the standard adapter creation
            logic for complex initialization.
        default_kwargs: Additional kwargs merged into the adapter constructor call.
    """
    http_config: HttpConfig | None = None
    if requires_http_client:
        http_config = HttpConfig(
            rate=http_rate,
            capacity=http_capacity,
            rate_overrides=rate_overrides or {},
        )

    config = ProviderConfig(
        adapter_class=cls,
        http_config=http_config,
        requires_http_client=requires_http_client,
        requires_logger=requires_logger,
        default_kwargs=default_kwargs,
        custom_creator=custom_creator,
    )
    # Decorators remain the sanctioned import-time compatibility seam for
    # populating the lazy default registry.
    register_default_provider_config(name, config)
    cls.__provider_name__ = name  # type: ignore[attr-defined]


def register_provider(
    name: str,
    *,
    http_rate: float = 5.0,
    http_capacity: int = 10,
    requires_http_client: bool = True,
    requires_logger: bool = True,
    rate_overrides: dict[str, float] | None = None,
    custom_creator: AdapterCreator | None = None,
    **default_kwargs: object,
) -> Callable[[type[T]], type[T]]:
    """Decorator for registering a provider adapter class.

    Args:
        name: Unique provider name (e.g., 'chembl', 'pubchem').
        http_rate: Base rate limit in requests per second; defaults to 5.0.
        http_capacity: Token bucket capacity; defaults to 10.
        requires_http_client: If True, http_client is injected at adapter creation;
            defaults to True.
        requires_logger: If True, logger is injected at adapter creation;
            defaults to True.
        rate_overrides: Optional dict mapping settings attribute names to boosted
            rate limits when API keys are present; defaults to None.
        custom_creator: Optional callable replacing standard adapter creation;
            defaults to None.
        **default_kwargs: Additional kwargs merged into the adapter constructor.

    Returns:
        Class decorator that registers the adapter and returns it unchanged.
    """
    resolved_defaults = dict(default_kwargs)

    def decorator(cls: type[T]) -> type[T]:
        """Register class and return it unchanged."""
        _register_provider_class(
            cls=cls,
            name=name,
            http_rate=http_rate,
            http_capacity=http_capacity,
            requires_http_client=requires_http_client,
            requires_logger=requires_logger,
            rate_overrides=rate_overrides,
            custom_creator=custom_creator,
            default_kwargs=dict(resolved_defaults),
        )
        return cls

    return decorator

================================================================================
File: loader.py
Path: providers\loader.py
================================================================================
"""Retained bootstrap convenience seam for provider loading.

Wave 3 ownership classification: retain.

This module remains a thin bootstrap facade over ``_loading.py`` and routes the
default-registry path through ``_registry_resolution.py`` instead of owning
registry bootstrap logic directly.
"""

from __future__ import annotations

from bioetl.composition.providers._loading import (
    ensure_provider_registry_loaded,
    get_provider_registry_loaded_status,
    load_provider_registry,
    reset_provider_registry_loader,
)
from bioetl.composition.providers._registry_resolution import (
    resolve_provider_registry,
)
from bioetl.composition.providers.provider_registry import ProviderRegistry

__all__ = [
    "ensure_providers_loaded",
    "get_loaded_status",
    "load_providers",
    "reset_loader",
]


def _get_loader_registry() -> ProviderRegistry:
    """Resolve the canonical default provider registry for loader entrypoints."""
    return resolve_provider_registry()


def load_providers(force: bool = False) -> None:
    """Load and register all providers.

    This function should be called once at application startup
    (e.g., in bootstrap.py) to initialize ProviderRegistry.

    Idempotent - repeated calls are safe (if force=False).

    Args:
        force: If True, re-register providers even if already loaded.
            Used in tests to reset state.

    Example:
        >>> from bioetl.composition.providers import load_providers
        >>> load_providers()
        >>> # Now ProviderRegistry is ready
        >>> from bioetl.composition.providers import ProviderRegistry
        >>> config = ProviderRegistry.get("chembl")

    """
    load_provider_registry(
        _get_loader_registry(),
        force=force,
    )


def ensure_providers_loaded() -> None:
    """Ensure providers are loaded.

    Convenience function for use in places where ProviderRegistry
    must be initialized.
    """
    ensure_provider_registry_loaded(
        _get_loader_registry(),
    )


def get_loaded_status() -> bool:
    """Return provider loading status.

    Returns:
        Loaded status.
    """
    return get_provider_registry_loaded_status(_get_loader_registry())


def reset_loader() -> None:
    """Reset loading status. Only for tests."""
    reset_provider_registry_loader(_get_loader_registry())


_LOADER_API = (get_loaded_status, reset_loader)

================================================================================
File: provider_registry.py
Path: providers\provider_registry.py
================================================================================
"""Provider registry facade over split helpers.

Retained compatibility obligations are intentionally narrow:
- class-level ``DefaultRegistryMethod`` mirror for legacy call sites;
- ``register_default_provider_config()`` and ``ensure_provider_registry_ready()``.
"""

from __future__ import annotations

import threading
from importlib import import_module
from typing import TYPE_CHECKING

from bioetl.composition.providers._creation import ProviderCreator
from bioetl.composition.providers._default_registry import (
    DefaultRegistryMethod,
    ProvidersDescriptor,
    get_default_provider_registry,
)
from bioetl.composition.providers._models import (
    AdapterCreator,
    DataSourceCreatorProtocol,
    HttpConfig,
    ProviderConfig,
    ProviderSettingsProtocol,
)
from bioetl.composition.providers._store import ProviderStore

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "AdapterCreator",
    "DataSourceCreatorProtocol",
    "HttpConfig",
    "ProviderConfig",
    "ProviderRegistry",
    "create_provider_registry",
    "ensure_provider_registry_ready",
    "get_default_provider_registry",
    "resolve_provider_registry",
]

# Compatibility alias retained during the RF-008 terminology cleanup. New code
# should use DataSourceCreatorProtocol directly.
DataSourceCreatorPort = DataSourceCreatorProtocol


def _ensure_registry_loaded(registry: ProviderRegistry) -> None:
    """Late-bind registry loading to avoid hard import coupling into providers."""
    loading_module = import_module("bioetl.composition.providers._loading")
    loading_module.ensure_provider_registry_loaded(registry)


class ProviderRegistry:
    """Unified data provider registry (thread-safe, instance-scoped)."""

    def __init__(
        self,
        store: ProviderStore | None = None,
        creator: ProviderCreator | None = None,
    ) -> None:
        self._store = store if store is not None else ProviderStore()
        self._creator = creator if creator is not None else ProviderCreator()
        self._lock = threading.RLock()

    if TYPE_CHECKING:
        _providers: dict[str, ProviderConfig]
    else:
        _providers = ProvidersDescriptor()

    @classmethod
    def _get_default(cls) -> ProviderRegistry:
        return get_default_provider_registry()

    def _get_registered_config(
        self,
        name: str,
        *,
        allow_missing: bool = False,
    ) -> ProviderConfig | None:
        with self._lock:
            if allow_missing and not self._store.is_registered(name):
                return None
            return self._store.get(name)

    @classmethod
    def ensure_loaded(cls) -> None:
        """Ensure provider registrations are loaded into the registry."""
        _ensure_registry_loaded(cls._get_default())

    @DefaultRegistryMethod
    def register(self, name: str, config: ProviderConfig) -> None:
        """Register a provider (re-registration overwrites, thread-safe)."""
        with self._lock:
            self._store.register(name, config)

    @DefaultRegistryMethod
    def get(self, name: str) -> ProviderConfig:
        """Return provider configuration; raises KeyError if unknown."""
        with self._lock:
            return self._store.get(name)

    @DefaultRegistryMethod
    def is_registered(self, name: str) -> bool:
        """Check whether a provider is registered."""
        with self._lock:
            return self._store.is_registered(name)

    @DefaultRegistryMethod
    def list_providers(self) -> list[str]:
        """Return sorted list of registered provider names."""
        with self._lock:
            return self._store.list_names()

    @DefaultRegistryMethod
    def has_data_source_creator(self, name: str) -> bool:
        """Check whether a provider has a data_source_creator."""
        config = self._get_registered_config(name, allow_missing=True)
        if config is None:
            return False
        return self._creator.has_data_source_creator(config)

    @DefaultRegistryMethod
    def clear(self) -> None:
        """Clear the registry (testing only, thread-safe)."""
        with self._lock:
            self._store.clear()

    @DefaultRegistryMethod
    def create_adapter(
        self,
        name: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: ProviderSettingsProtocol | None = None,
        **kwargs: object,
    ) -> DataSourcePort:
        """Create a provider adapter instance using registry metadata."""
        config = self._get_registered_config(name)
        assert config is not None
        return self._creator.create_adapter(
            name=name,
            config=config,
            http_client=http_client,
            logger=logger,
            settings=settings,
            **kwargs,
        )

    @DefaultRegistryMethod
    def get_http_config(self, name: str) -> HttpConfig | None:
        """Return the HTTP configuration for a provider, or None."""
        return self.get(name).http_config

    @DefaultRegistryMethod
    def create_data_source(
        self,
        name: str,
        settings: ProviderSettingsProtocol,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        """Create a fully configured data source with filtering support."""
        config = self._get_registered_config(name)
        assert config is not None
        return self._creator.create_data_source(
            name=name,
            config=config,
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
        )

    @DefaultRegistryMethod
    def build_data_source_creator(self, name: str) -> DataSourceCreatorProtocol:
        """Return a provider-bound data-source creator closure."""
        if self is type(self)._get_default():
            type(self).ensure_loaded()

        config = self._get_registered_config(name)
        assert config is not None
        self._creator.require_data_source_creator(name=name, config=config)

        def create_data_source_for_provider(
            settings: ProviderSettingsProtocol,
            pipeline_config: PipelineYamlConfig,
            logger: LoggerPort,
            filter_config: InputFilterConfig | None = None,
            metrics: MetricsPort | None = None,
            pipeline_name: str = "unknown",
        ) -> DataSourcePort:
            return self.create_data_source(
                name=name,
                settings=settings,
                pipeline_config=pipeline_config,
                logger=logger,
                filter_config=filter_config,
                metrics=metrics,
                pipeline_name=pipeline_name,
            )

        return self._creator.build_bound_creator(
            name=name,
            create_data_source_fn=create_data_source_for_provider,
        )

    @DefaultRegistryMethod
    def list_keys(self) -> list[str]:
        """List all registered provider names (unified API)."""
        return self.list_providers()

    @DefaultRegistryMethod
    def contains(self, key: str) -> bool:
        """Check if provider is registered (unified API)."""
        return self.is_registered(key)


def register_default_provider_config(name: str, config: ProviderConfig) -> None:
    """Register a provider config through the retained import-time compat seam."""
    get_default_provider_registry().register(name, config)


def ensure_provider_registry_ready(registry: ProviderRegistry) -> ProviderRegistry:
    """Ensure a provider registry instance is populated before use.

    This remains the sanctioned bootstrap seam for callers that need an
    initialized registry instance without importing provider loading internals.
    """
    _ensure_registry_loaded(registry)
    return registry


def resolve_provider_registry(
    provider_registry: ProviderRegistry | None = None,
    *,
    ensure_ready: bool = False,
) -> ProviderRegistry:
    """Resolve explicit-or-default registry access through a public seam."""
    resolved_registry = (
        provider_registry
        if provider_registry is not None
        else get_default_provider_registry()
    )
    if ensure_ready:
        return ensure_provider_registry_ready(resolved_registry)
    return resolved_registry


def create_provider_registry() -> ProviderRegistry:
    """Create a new isolated provider registry instance."""
    return ProviderRegistry()

================================================================================
File: registration.py
Path: providers\registration.py
================================================================================
"""Explicit provider registration entrypoint for the composition layer.

Wave 3 ownership classification: simplify-now closeout complete.

Canonical assembly ownership now lives in ``_registration_contracts.py``,
``_config_helpers.py``, and the family-specific manifest builders. This module
stays as a thin explicit bootstrap seam that merges family builders onto an
injected or canonically resolved registry.
"""

from __future__ import annotations

from collections.abc import Callable

from bioetl.composition.providers._models import ProviderConfig
from bioetl.composition.providers._registration_contracts import (
    ProviderAssemblySupport,
    resolve_provider_assembly_support,
)
from bioetl.composition.providers._registry_protocols import (
    ProviderRegistrarProtocol,
)
from bioetl.composition.providers._registry_resolution import (
    resolve_provider_registry,
)
from bioetl.composition.providers.registration_biblio import (
    _get_biblio_provider_configs,
)
from bioetl.composition.providers.registration_bio import (
    _get_bio_provider_configs,
)

__all__ = [
    "register_all_providers",
]


def register_all_providers(
    registry: ProviderRegistrarProtocol | None = None,
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> None:
    """Explicitly register all data source providers.

    This function MUST be called from bootstrap before using ProviderRegistry.
    Idempotent - safe to call multiple times.

    Configuration Priority:
    1. configs/providers/{provider}.yaml - PRIMARY (rate limits, circuit breaker, batch_size)
    2. HttpConfig in ProviderConfig - FALLBACK only

    Each provider includes a data_source_creator for unified registry access.
    """
    target_registry = resolve_provider_registry(registry)
    support = resolve_provider_assembly_support(
        assembly_support,
        provider_registry=target_registry,
    )
    for provider_name, config in _build_provider_configs(
        assembly_support=support
    ).items():
        if target_registry.is_registered(provider_name):
            continue
        target_registry.register(provider_name, config)


def _build_provider_configs(
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> dict[str, ProviderConfig]:
    """Build provider registry configs from YAML-backed rate limits."""
    support = resolve_provider_assembly_support(assembly_support)
    return _merge_provider_config_families(
        assembly_support=support,
    )


def _merge_provider_config_families(
    *,
    assembly_support: ProviderAssemblySupport,
) -> dict[str, ProviderConfig]:
    """Merge provider-config families through one canonical assembly path."""
    merged: dict[str, ProviderConfig] = {}
    for build_family_configs in _iter_provider_config_family_builders():
        merged.update(build_family_configs(assembly_support=assembly_support))
    return merged


def _iter_provider_config_family_builders() -> tuple[
    Callable[..., dict[str, ProviderConfig]],
    ...,
]:
    """Return ordered family builders for provider registration assembly."""
    return (
        _get_bio_provider_configs,
        _get_biblio_provider_configs,
    )

================================================================================
File: registration_biblio.py
Path: providers\registration_biblio.py
================================================================================
"""Data source creators for bibliographic providers extracted from registration.py."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.composition.factories.datasource.crossref import (
    create_crossref_adapter,
)
from bioetl.composition.providers._config_helpers import (
    _build_provider_family_http_config_map,
    _create_http_data_source,
    _get_batch_size_from_config,
    _get_rate_limits_from_config,
)
from bioetl.composition.providers._models import (
    ProviderConfig,
    ProviderSettingsProtocol,
)
from bioetl.composition.providers._registration_biblio_adapters import (
    _build_openalex_adapter_from_settings,
    _build_pubmed_adapter_from_settings,
)
from bioetl.composition.providers._registration_biblio_profiles import (
    _resolve_mailto_batch_profile,
    _resolve_pubmed_request_profile,
    _resolve_semanticscholar_request_profile,
)
from bioetl.composition.providers._registration_contracts import (
    HttpProviderConfigSpec,
    ProviderAssemblySupport,
    resolve_provider_assembly_support,
)
from bioetl.infrastructure.adapters.crossref import CrossRefAdapter
from bioetl.infrastructure.adapters.openalex import OpenAlexAdapter
from bioetl.infrastructure.adapters.pubmed import PubMedAdapter
from bioetl.infrastructure.adapters.semanticscholar import SemanticScholarAdapter

if TYPE_CHECKING:
    from bioetl.composition.bootstrap_contexts import RateLimitContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _create_pubmed_adapter_from_settings(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: ProviderSettingsProtocol | None,
    **kwargs: object,
) -> PubMedAdapter:
    """Create PubMedAdapter with patch-friendly composition-local adapter binding."""
    return _build_pubmed_adapter_from_settings(
        adapter_cls=PubMedAdapter,
        http_client=http_client,
        logger=logger,
        settings=settings,
        **kwargs,
    )


def _create_openalex_adapter_from_settings(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: ProviderSettingsProtocol | None,
    **kwargs: object,
) -> OpenAlexAdapter:
    """Create OpenAlexAdapter with patch-friendly composition-local adapter binding."""
    return _build_openalex_adapter_from_settings(
        adapter_cls=OpenAlexAdapter,
        http_client=http_client,
        logger=logger,
        settings=settings,
        **kwargs,
    )


def _create_pubmed_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create PubMed data source with optional CSV filtering.

    PubMed requires an email address and optionally an API key for higher rate
    limits (10 req/sec with key vs 3 req/sec without). The API key is resolved
    with the following priority:

    1. ``pipeline_config.source.api_key`` -- per-pipeline override (highest).
    2. ``settings.pubmed_api_key`` -- application-wide setting from
       ``BIOETL_PUBMED_API_KEY`` env var (fallback).
    3. ``None`` -- unauthenticated access with lower rate limits.

    Email follows a similar resolution: ``pipeline_config.source.email`` takes
    precedence over ``settings.default_email``.
    """
    profile = _resolve_pubmed_request_profile(settings, pipeline_config)

    return _create_http_data_source(
        provider="pubmed",
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        adapter_factory=PubMedAdapter,
        extra_kwargs={"email": profile.email, "api_key": profile.api_key},
        assembly_support=assembly_support,
    )


def _create_mailto_batch_data_source(
    *,
    provider: str,
    adapter_factory: Callable[..., DataSourcePort],
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None,
    metrics: MetricsPort | None,
    pipeline_name: str,
    default_batch_size: int,
    assembly_support: ProviderAssemblySupport | None,
    include_settings: bool = False,
) -> DataSourcePort:
    """Create a mailto/batch driven HTTP data source for biblio providers."""
    profile = _resolve_mailto_batch_profile(
        settings,
        pipeline_config,
        batch_size=_get_batch_size_from_config(provider, default=default_batch_size),
    )
    extra_kwargs: dict[str, object] = {
        "mailto": profile.mailto,
        "batch_size": profile.batch_size,
    }
    if include_settings:
        extra_kwargs["settings"] = settings
    return _create_http_data_source(
        provider=provider,
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        adapter_factory=adapter_factory,
        extra_kwargs=extra_kwargs,
        assembly_support=assembly_support,
    )


def _create_crossref_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create CrossRef data source with optional CSV filtering."""
    return _create_mailto_batch_data_source(
        provider="crossref",
        adapter_factory=create_crossref_adapter,
        settings=settings,
        pipeline_config=pipeline_config,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        default_batch_size=50,
        assembly_support=assembly_support,
        include_settings=True,
    )


def _create_openalex_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create OpenAlex data source with optional CSV filtering."""
    return _create_mailto_batch_data_source(
        provider="openalex",
        adapter_factory=OpenAlexAdapter,
        settings=settings,
        pipeline_config=pipeline_config,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        default_batch_size=50,
        assembly_support=assembly_support,
    )


def _create_semanticscholar_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create Semantic Scholar adapter and optionally wrap it with input filtering."""
    profile = _resolve_semanticscholar_request_profile(
        settings,
        batch_size=_get_batch_size_from_config("semanticscholar", default=100),
    )
    api_key = profile.api_key
    if not api_key:
        logger.warning(
            "semanticscholar_no_api_key",
            message="No API key provided. Rate limits will be shared with other users.",
        )

    return _create_http_data_source(
        provider="semanticscholar",
        settings=settings,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
        adapter_factory=SemanticScholarAdapter,
        extra_kwargs={"api_key": api_key, "batch_size": profile.batch_size},
        assembly_support=assembly_support,
    )


def _build_biblio_http_provider_specs(
    rate_limits: dict[str, RateLimitContext],
) -> tuple[HttpProviderConfigSpec, ...]:
    """Build the declarative HTTP provider manifest for the biblio family."""
    pubmed = rate_limits["pubmed"]
    crossref = rate_limits["crossref"]
    openalex = rate_limits["openalex"]
    semanticscholar = rate_limits["semanticscholar"]

    return (
        HttpProviderConfigSpec(
            provider_name="pubmed",
            adapter_class=PubMedAdapter,
            rate=pubmed.rate,
            capacity=pubmed.capacity,
            rate_overrides={"pubmed_api_key": 10.0},
            custom_creator=_create_pubmed_adapter_from_settings,
            data_source_creator=_create_pubmed_data_source,
        ),
        HttpProviderConfigSpec(
            provider_name="crossref",
            adapter_class=CrossRefAdapter,
            rate=crossref.rate,
            capacity=crossref.capacity,
            custom_creator=create_crossref_adapter,
            data_source_creator=_create_crossref_data_source,
        ),
        HttpProviderConfigSpec(
            provider_name="openalex",
            adapter_class=OpenAlexAdapter,
            rate=openalex.rate,
            capacity=openalex.capacity,
            custom_creator=_create_openalex_adapter_from_settings,
            data_source_creator=_create_openalex_data_source,
        ),
        HttpProviderConfigSpec(
            provider_name="semanticscholar",
            adapter_class=SemanticScholarAdapter,
            rate=semanticscholar.rate,
            capacity=semanticscholar.capacity,
            data_source_creator=_create_semanticscholar_data_source,
        ),
    )


def _get_biblio_provider_configs(
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> dict[str, ProviderConfig]:
    """Build ProviderConfig entries for bibliographic providers."""
    support = resolve_provider_assembly_support(assembly_support)
    rate_limits = _get_rate_limits_from_config(
        "pubmed",
        "crossref",
        "openalex",
        "semanticscholar",
    )
    return _build_provider_family_http_config_map(
        rate_limits=rate_limits,
        assembly_support=support,
        spec_builder=_build_biblio_http_provider_specs,
    )

================================================================================
File: registration_bio.py
Path: providers\registration_bio.py
================================================================================
"""Data source creators for bio providers: ChEMBL, PubChem, UniProt, IDMapping."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.data_sources.idmapping import IDMappingDataSource
from bioetl.application.core.data_sources.publication_term import (
    PublicationTermDataSource,
)
from bioetl.application.core.data_sources.subcellular_fraction import (
    SubcellularFractionDataSource,
)
from bioetl.composition.factories.datasource.adapter_helpers import (
    AdapterHelpersFactory,
)
from bioetl.composition.factories.datasource.pubchem import (
    create_pubchem_adapter,
)
from bioetl.composition.providers._config_helpers import (
    _build_provider_family_http_config_map,
    _get_adapter_config,
    _get_rate_limits_from_config,
    _validate_extraction_input_filter_overlap,
    _wrap_with_filter,
)
from bioetl.composition.providers._models import (
    HttpConfig,
    ProviderConfig,
    ProviderSettingsProtocol,
)
from bioetl.composition.providers._registration_contracts import (
    HttpProviderConfigSpec,
    ProviderAssemblySupport,
    build_data_source_provider_config,
    resolve_provider_assembly_support,
)
from bioetl.domain.models.filter import ExtractionParams
from bioetl.infrastructure.adapters.chembl import ChemblAdapter
from bioetl.infrastructure.adapters.input import IDMappingCsvReaderAdapter
from bioetl.infrastructure.adapters.pubchem import PubChemAdapter
from bioetl.infrastructure.adapters.uniprot import UniProtAdapter
from bioetl.infrastructure.adapters.uniprot.constants import UNIPROT_API_BASE
from bioetl.infrastructure.adapters.uniprot.idmapping_client import (
    UniProtIDMappingClient,
)

if TYPE_CHECKING:
    from bioetl.composition.bootstrap_contexts import RateLimitContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _create_chembl_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create ChEMBL data source with optional CSV filtering.

    Configuration is loaded from configs/providers/chembl.yaml via AdapterConfig.
    This ensures YAML is the single source of truth (RULES.md §12.1.2).

    For document_term entity type, wraps the adapter with PublicationTermDataSource
    to extract terms from publication records (derived entity pattern).
    """
    support = resolve_provider_assembly_support(assembly_support)
    http_client = support.create_http_client("chembl", settings, metrics=metrics)

    # Load adapter configuration from YAML (single source of truth)
    adapter_config = _get_adapter_config("chembl", default_page_size=1000)

    # Build ExtractionParams from pipeline config (ADR-028 §3)
    extraction_params = ExtractionParams(params=pipeline_config.extraction_params)

    # Validate overlap between extraction_params and input_filter
    if filter_config is not None:
        _validate_extraction_input_filter_overlap(
            extraction_params, filter_config, logger
        )

    base_adapter = support.create_adapter(
        "chembl",
        http_client=http_client,
        logger=logger,
        settings=settings,
        adapter_config=adapter_config,
        metrics=metrics,
        extraction_params=extraction_params,
    )

    # Wrap derived-entity pipelines with their record-shaping data sources.
    # publication_term is extracted from publication records (1:M relationship)
    if pipeline_config.entity_type == "publication_term":
        base_adapter = PublicationTermDataSource(base_adapter)
    if pipeline_config.entity_type == "subcellular_fraction":
        base_adapter = SubcellularFractionDataSource(base_adapter)

    return _wrap_with_filter(
        base_adapter, filter_config, logger, metrics, pipeline_name
    )


def _create_pubchem_adapter(
    http_client: UnifiedHTTPClient | None = None,
    logger: LoggerPort | None = None,
    settings: ProviderSettingsProtocol | None = None,
    **kwargs: object,
) -> DataSourcePort:
    """Retained provider-registration wrapper for the PubChem composition factory."""
    return create_pubchem_adapter(
        http_client=http_client,
        logger=logger,
        settings=settings,
        **kwargs,
    )


def _create_pubchem_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create PubChem data source with composition-owned adapter wiring."""
    data_source = _create_pubchem_adapter(
        logger=logger,
        settings=settings,
        strict_error_handling=settings.strict_error_handling,
        metrics=metrics,
    )
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_uniprot_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create UniProt data source with optional CSV filtering.

    UniProt uses the generic DataSourceFactory path with a UnifiedHTTPClient.
    The base URL defaults to ``https://rest.uniprot.org`` but can be overridden
    via ``pipeline_config.source.api.base_url`` for testing or alternative
    deployments.
    """
    support = resolve_provider_assembly_support(assembly_support)
    http_client = support.create_http_client("uniprot", settings, metrics=metrics)
    helper_services = AdapterHelpersFactory.create_http_helpers(
        provider="uniprot",
        logger=logger,
        metrics=metrics,
    )
    data_source = support.create_adapter(
        "uniprot",
        http_client=http_client,
        logger=logger,
        settings=settings,
        base_url=pipeline_config.source.api.base_url or UNIPROT_API_BASE,
        strict_error_handling=settings.strict_error_handling,
        metrics=metrics,
        **helper_services.as_injection_kwargs(),
    )
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_uniprot_idmapping_data_source(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Create UniProt ID Mapping data source.

    Creates an IDMappingDataSource that:
    1. Reads ChEMBL target IDs via an infrastructure source reader
    2. Calls UniProt ID Mapping API to map to UniProt accessions
    3. Yields records with mapping results
    """
    support = resolve_provider_assembly_support(assembly_support)
    http_client = support.create_http_client("uniprot", settings, metrics=metrics)
    from_db, to_db = _resolve_uniprot_mapping_databases(pipeline_config)
    return IDMappingDataSource(
        idmapping_client=UniProtIDMappingClient(
            http_client=http_client,
            logger=logger,
            metrics=metrics,
            base_url=_resolve_uniprot_mapping_base_url(pipeline_config),
        ),
        id_source_reader=IDMappingCsvReaderAdapter(logger=logger),
        input_path=_resolve_uniprot_mapping_input_path(pipeline_config),
        logger=logger,
        from_db=from_db,
        to_db=to_db,
        seed_ids=_extract_uniprot_mapping_seed_ids(filter_config),
    )


def _resolve_uniprot_mapping_base_url(pipeline_config: PipelineYamlConfig) -> str:
    """Resolve UniProt ID Mapping base URL from config with safe default."""
    if pipeline_config.source.api and pipeline_config.source.api.base_url:
        return str(pipeline_config.source.api.base_url)
    return str(UNIPROT_API_BASE)


def _resolve_uniprot_mapping_input_path(pipeline_config: PipelineYamlConfig) -> str:
    """Resolve input CSV path for UniProt ID Mapping seed IDs."""
    configured = getattr(pipeline_config.source, "input_path", None)
    return configured or "data/input/target.csv"


def _resolve_uniprot_mapping_databases(
    pipeline_config: PipelineYamlConfig,
) -> tuple[str, str]:
    """Resolve source/target database names for UniProt mapping API."""
    from_db = "ChEMBL"
    to_db = "UniProtKB"
    if pipeline_config.source.api:
        from_db = getattr(pipeline_config.source.api, "from_db", None) or from_db
        to_db = getattr(pipeline_config.source.api, "to_db", None) or to_db
    return from_db, to_db


def _extract_uniprot_mapping_seed_ids(
    filter_config: InputFilterConfig | None,
) -> list[str] | None:
    """Extract optional seed IDs from input filter config."""
    if filter_config and filter_config.direct_filter_ids:
        return list(filter_config.direct_filter_ids)
    return None


def _build_bio_http_provider_specs(
    rate_limits: dict[str, RateLimitContext],
) -> tuple[HttpProviderConfigSpec, ...]:
    """Build the declarative HTTP provider manifest for the bio family."""
    chembl = rate_limits["chembl"]
    uniprot = rate_limits["uniprot"]

    return (
        HttpProviderConfigSpec(
            provider_name="chembl",
            adapter_class=ChemblAdapter,
            rate=chembl.rate,
            capacity=chembl.capacity,
            data_source_creator=_create_chembl_data_source,
        ),
        HttpProviderConfigSpec(
            provider_name="uniprot",
            adapter_class=UniProtAdapter,
            rate=uniprot.rate,
            capacity=uniprot.capacity,
            rate_overrides={"uniprot_api_key": 100.0},
            data_source_creator=_create_uniprot_data_source,
        ),
        HttpProviderConfigSpec(
            provider_name="uniprot_idmapping",
            adapter_class=IDMappingDataSource,
            rate=uniprot.rate,
            capacity=uniprot.capacity,
            data_source_creator=_create_uniprot_idmapping_data_source,
        ),
    )


def _build_bio_extra_provider_configs(
    rate_limits: dict[str, RateLimitContext],
    _assembly_support: ProviderAssemblySupport,
) -> dict[str, ProviderConfig]:
    """Build non-HTTP special-case provider configs for the bio family."""
    pubchem = rate_limits["pubchem"]

    return {
        "pubchem": build_data_source_provider_config(
            adapter_class=PubChemAdapter,
            http_config=HttpConfig(rate=pubchem.rate, capacity=pubchem.capacity),
            requires_http_client=False,
            requires_logger=True,
            custom_creator=_create_pubchem_adapter,
            data_source_creator=_create_pubchem_data_source,
        ),
    }


def _get_bio_provider_configs(
    *,
    assembly_support: ProviderAssemblySupport | None = None,
) -> dict[str, ProviderConfig]:
    """Build ProviderConfig entries for bio providers."""
    support = resolve_provider_assembly_support(assembly_support)
    rate_limits = _get_rate_limits_from_config(
        "chembl",
        "pubchem",
        "uniprot",
    )
    configs = _build_provider_family_http_config_map(
        rate_limits=rate_limits,
        assembly_support=support,
        spec_builder=_build_bio_http_provider_specs,
    )
    return dict(configs | _build_bio_extra_provider_configs(rate_limits, support))

================================================================================
File: registry.py
Path: registry.py
================================================================================
"""Pipeline Registry for discovering and instantiating pipelines.

MOVED to composition layer to fix dependency direction.

This module provides the canonical instance-level ``PipelineRegistry`` for:
- Test isolation (each test can have its own registry)
- Parallel test execution without clear()
- Proper DI through composition root
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, NamedTuple

from bioetl.domain.ports import PipelineFactoryPort

if TYPE_CHECKING:
    import pyarrow as pa

__all__ = [
    "PipelineDefinition",
    "PipelineFactoryPort",
    "PipelineRegistry",
    "create_registry",
]


class PipelineDefinition(NamedTuple):
    """Definition of a registered pipeline."""

    factory: PipelineFactoryPort
    """Factory instance."""

    silver_schema: pa.Schema | None
    """PyArrow schema for Silver layer validation."""

    gold_schema: object
    """Pandera schema for Gold layer validation (required)."""

    pandera_silver_schema: object | None = None
    """Pandera DataFrameModel class for Silver layer validation."""


class PipelineRegistry:
    """Registry for pipeline factories.

    Thread-safe instance-level registry for pipeline factory instances.
    All public methods are protected with RLock for concurrent access.

    This class can be instantiated for test isolation or used via the
    default global instance for backward compatibility.

    Example (instance-level for tests):
        >>> registry = PipelineRegistry()
        >>> factory = GenericPipelineFactory(...)
        >>> registry.register_factory(factory)

    Example (backward-compatible class method API):
        >>> factory = GenericPipelineFactory(...)
        >>> PipelineRegistry.register_factory(factory)  # Uses default instance
    """

    def __init__(self) -> None:
        """Initialize a new empty registry."""
        self._registry: dict[str, PipelineDefinition] = {}
        self._lock = threading.RLock()

    def _build_definition(self, factory: PipelineFactoryPort) -> PipelineDefinition:
        """Build the stored pipeline definition after schema validation."""
        gold_schema = getattr(factory, "gold_schema", None)
        if gold_schema is None:
            raise ValueError(
                f"Factory '{factory.pipeline_name}' must have gold_schema. "
                "All Gold layer writes require schema validation."
            )
        return PipelineDefinition(
            factory=factory,
            silver_schema=factory.silver_schema,
            gold_schema=gold_schema,
            pandera_silver_schema=getattr(factory, "pandera_silver_schema", None),
        )

    def register_factory(
        self,
        factory: PipelineFactoryPort,
    ) -> None:
        """Register a pipeline factory instance.

        Thread-safe registration with duplicate detection.

        Args:
            factory: Factory instance with pipeline_name and silver_schema attributes

        Raises:
            ValueError: If factory does not have gold_schema attribute
            ValueError: If pipeline is already registered (prevents double registration)
        """
        self.register(factory.pipeline_name, factory)

    def get(self, pipeline_name: str) -> PipelineDefinition:
        """Get pipeline definition by name.

        Thread-safe read access to registry.

        Args:
            pipeline_name: Pipeline identifier

        Returns:
            PipelineDefinition with factory and schema

        Raises:
            RuntimeError: If registry is empty (registration not called)
            ValueError: If pipeline is not registered
        """
        with self._lock:
            if not self._registry:
                raise RuntimeError(
                    "PipelineRegistry is empty. "
                    "Did you forget to call register_all_pipelines()?"
                )
            if pipeline_name not in self._registry:
                raise ValueError(
                    f"Unknown pipeline name: {pipeline_name}. "
                    f"Available: {sorted(self._registry.keys())}"
                )
            return self._registry[pipeline_name]

    def list_pipelines(self) -> list[str]:
        """List all registered pipeline names.

        Thread-safe listing with deterministic ordering.
        Returns a snapshot of keys sorted alphabetically.

        Returns:
            Sorted list of pipeline names (deterministic order).
        """
        with self._lock:
            return sorted(self._registry.keys())

    def register(
        self,
        key: str,
        value: PipelineFactoryPort,
    ) -> None:
        """Register a pipeline factory (unified API).

        Thread-safe registration with duplicate detection.
        This method provides a unified API consistent with other registries.
        For backward compatibility, use register_factory() which extracts
        the key from factory.pipeline_name.

        Args:
            key: Pipeline name (must match factory.pipeline_name)
            value: Pipeline factory instance

        Raises:
            ValueError: If factory does not have gold_schema attribute
            ValueError: If key does not match factory.pipeline_name
            ValueError: If pipeline is already registered
        """
        if key != value.pipeline_name:
            raise ValueError(
                f"Pipeline key '{key}' does not match "
                f"factory.pipeline_name '{value.pipeline_name}'."
            )
        with self._lock:
            if key in self._registry:
                raise ValueError(
                    f"Pipeline already registered: {key}. "
                    "Use a new registry instance or clear() for tests."
                )
            self._registry[key] = self._build_definition(value)

    def list_keys(self) -> list[str]:
        """List all registered pipeline names (unified API).

        Alias for list_pipelines().

        Returns:
            Collection of keys.
        """
        return self.list_pipelines()

    def contains(self, key: str) -> bool:
        """Check if pipeline is registered.

        Thread-safe check for key existence.

        Args:
            key: Pipeline name to check

        Returns:
            True if pipeline is registered, False otherwise
        """
        with self._lock:
            return key in self._registry

    def clear(self) -> None:
        """Clear all registrations (for testing).

        Thread-safe reset of registry state.
        WARNING: Only use in tests. Not for production.
        """
        with self._lock:
            self._registry.clear()


def create_registry() -> PipelineRegistry:
    """Create a new isolated registry instance.

    Use this for test isolation or when you need multiple registries
    in the same process.

    Returns:
        A new empty PipelineRegistry instance.
    """
    return PipelineRegistry()

================================================================================
File: registry_api.py
Path: registry_api.py
================================================================================
"""Public registry-oriented composition API."""

from __future__ import annotations

from bioetl.composition import (
    PipelineDefinition,
    PipelineRegistry,
    create_registry,
    get_default_registry,
)
from bioetl.composition.factories.pipeline.registry import register_all_pipelines

__all__ = [
    "PipelineDefinition",
    "PipelineRegistry",
    "create_registry",
    "get_default_registry",
    "register_all_pipelines",
]

================================================================================
File: registry_default.py
Path: registry_default.py
================================================================================
"""Shared default registry state used by compatibility re-exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["get_default_registry"]

if TYPE_CHECKING:
    from bioetl.composition.registry import PipelineRegistry

_compat_default_registry: PipelineRegistry | None = None


def get_default_registry() -> PipelineRegistry:
    """Return the compatibility-only shared default registry instance."""
    global _compat_default_registry
    if _compat_default_registry is None:
        from bioetl.composition.registry import PipelineRegistry

        _compat_default_registry = PipelineRegistry()
    return _compat_default_registry

================================================================================
File: resource_management_api.py
Path: resource_management_api.py
================================================================================
"""Deprecated alias module for ``bioetl.composition.resources_api``."""

from __future__ import annotations

import warnings

from bioetl.composition.resources_api import (
    ArchiveOptions,
    VacuumOptions,
    archive_table,
    get_checkpoint_manager,
    get_lifecycle_service,
    get_quarantine_manager,
    inspect_quarantine,
    list_checkpoints,
    preview_cleanup,
    vacuum_table,
)

__all__ = [
    "ArchiveOptions",
    "VacuumOptions",
    "archive_table",
    "get_checkpoint_manager",
    "get_lifecycle_service",
    "get_quarantine_manager",
    "inspect_quarantine",
    "list_checkpoints",
    "preview_cleanup",
    "vacuum_table",
]

warnings.warn(
    (
        "`bioetl.composition.resource_management_api` is deprecated; "
        "use `bioetl.composition.resources_api`."
    ),
    DeprecationWarning,
    stacklevel=2,
)

================================================================================
File: resources_api.py
Path: resources_api.py
================================================================================
"""Public resource-management composition API."""

from __future__ import annotations

from bioetl.composition._pipeline_execution import ArchiveOptions, VacuumOptions
from bioetl.composition._resource_management import (
    archive_table,
    get_checkpoint_manager,
    get_lifecycle_service,
    get_quarantine_manager,
    inspect_quarantine,
    list_checkpoints,
    preview_cleanup,
    vacuum_table,
)

__all__ = [
    "ArchiveOptions",
    "VacuumOptions",
    "archive_table",
    "get_checkpoint_manager",
    "get_lifecycle_service",
    "get_quarantine_manager",
    "inspect_quarantine",
    "list_checkpoints",
    "preview_cleanup",
    "vacuum_table",
]

================================================================================
File: __init__.py
Path: runtime_builders\__init__.py
================================================================================
"""Leaf runtime builders used by composition factories and bootstrap wrappers."""

from __future__ import annotations


def build_pipeline_runner(*args: object, **kwargs: object) -> object:
    """Lazily dispatch to the concrete runner builder without package import cycles."""
    from bioetl.composition.runtime_builders.runner_builder import (
        build_pipeline_runner as _build_pipeline_runner_impl,
    )

    return _build_pipeline_runner_impl(*args, **kwargs)


__all__ = ["build_pipeline_runner"]

================================================================================
File: _cached_bronze_snapshot_support.py
Path: runtime_builders\_cached_bronze_snapshot_support.py
================================================================================
"""Shared cached-Bronze snapshot helpers for exact-replay provenance."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from bioetl.domain.control_plane import RunInputSnapshotRef

__all__ = [
    "build_cached_bronze_input_snapshot_refs",
]


def build_cached_bronze_input_snapshot_refs(
    *,
    bronze_root: Path,
    bronze_date: str | None,
    pipeline_name: str,
) -> tuple[RunInputSnapshotRef, ...]:
    """Return deterministic batch-level snapshot refs for cached-Bronze replay."""
    search_root = bronze_root / bronze_date if bronze_date else bronze_root
    if not search_root.exists():
        return ()

    pattern = "batch_*.jsonl.zst" if bronze_date else "**/batch_*.jsonl.zst"
    batch_files = sorted(search_root.glob(pattern))
    if not batch_files:
        return ()

    snapshot_refs = [
        _build_cached_bronze_snapshot_ref(
            bronze_root=bronze_root,
            batch_file=batch_file,
            pipeline_name=pipeline_name,
        )
        for batch_file in batch_files
    ]
    # Persist manifest snapshots in a stable identity order so replay metadata
    # does not depend on filesystem enumeration or content-hash/path interplay.
    return tuple(sorted(snapshot_refs, key=lambda ref: ref.snapshot_id))


def _build_cached_bronze_snapshot_ref(
    *,
    bronze_root: Path,
    batch_file: Path,
    pipeline_name: str,
) -> RunInputSnapshotRef:
    """Build one immutable snapshot ref for one cached Bronze batch file."""
    content_hash = _compute_cached_bronze_batch_content_hash(batch_file)
    relative_path = str(batch_file.relative_to(bronze_root))
    snapshot_id = hashlib.sha256(
        f"{pipeline_name}:{relative_path}:{content_hash}".encode()
    ).hexdigest()
    captured_at = datetime.fromtimestamp(batch_file.stat().st_mtime, tz=UTC)
    return RunInputSnapshotRef(
        snapshot_id=snapshot_id,
        content_hash=content_hash,
        immutable_uri=str(batch_file),
        captured_at=captured_at,
    )


def _compute_cached_bronze_batch_content_hash(batch_file: Path) -> str:
    """Compute the content hash for one persisted cached-Bronze batch file."""
    digest = hashlib.sha256()
    with batch_file.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()

================================================================================
File: _inputs_resolution_support.py
Path: runtime_builders\_inputs_resolution_support.py
================================================================================
from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import TYPE_CHECKING, Literal, Protocol, cast

from bioetl.domain.config import RuntimeConfig

if TYPE_CHECKING:
    from bioetl.composition.builders import FilterConfigBuilder
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
    from bioetl.domain.context import VacuumSettings as CliVacuumSettings
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterYamlConfig as YamlInputFilter,
    )
    from bioetl.infrastructure.schemas.pipeline_config import (
        MaintenanceConfig,
        PipelineYamlConfig,
    )


class PaginationConfigLike(Protocol):
    id_batch_size: object


class SourceConfigLike(Protocol):
    pagination: PaginationConfigLike


def apply_tracing_override(
    *,
    settings: Settings,
    enabled: bool | None,
) -> Settings:
    if enabled is None:
        return settings

    observability = getattr(settings, "observability", None)
    if observability is None:
        return settings

    if hasattr(settings, "model_copy") and hasattr(observability, "model_copy"):
        updated_observability = observability.model_copy(
            update={"tracing_enabled": enabled}
        )
        copied_settings: Settings = settings.model_copy(
            update={"observability": updated_observability}
        )
        return copied_settings

    namespace_settings = SimpleNamespace(**vars(settings))
    namespace_observability = SimpleNamespace(**vars(observability))
    namespace_observability.tracing_enabled = enabled
    namespace_settings.observability = namespace_observability
    return cast("Settings", namespace_settings)


def assemble_vacuum_settings_impl(
    *,
    cli_vacuum: CliVacuumSettings,
    yaml_maintenance: MaintenanceConfig,
    result_cls: type[object],
) -> object:
    enabled = (
        cli_vacuum.enabled
        if cli_vacuum.enabled is not None
        else yaml_maintenance.auto_vacuum
    )
    retention = (
        cli_vacuum.retention_days
        if cli_vacuum.enabled is not None
        else yaml_maintenance.vacuum_retention_days
    )
    return result_cls(enabled=enabled, retention_days=retention)


def assemble_runtime_config_impl(
    *,
    ctx: PipelineRunContext,
    heartbeat_interval: int,
    vacuum_enabled: bool,
    vacuum_retention_days: int,
    health_check_mode: Literal["strict", "probe"],
    skip_gold: bool,
) -> RuntimeConfig:
    return RuntimeConfig(
        run_type=ctx.run_type,
        resume=ctx.resume,
        start_offset=ctx.start_offset,
        limit=ctx.limit,
        heartbeat_interval=heartbeat_interval,
        query=ctx.query,
        dry_run=ctx.dry_run,
        exact_replay=getattr(ctx, "exact_replay", False),
        replay_anchor_date=(
            ctx.cached_bronze.bronze_date
            if getattr(ctx, "exact_replay", False)
            else None
        ),
        vacuum_after_run=vacuum_enabled,
        vacuum_retention_days=vacuum_retention_days,
        skip_gold=skip_gold,
        health_check_mode=health_check_mode,
    )


def assemble_filter_config_impl(
    *,
    yaml_filter: YamlInputFilter,
    ctx: PipelineRunContext,
    test_mode: bool,
    filter_builder: type[FilterConfigBuilder],
) -> InputFilterConfig | None:
    inp_filter = ctx.input_filter
    enabled = inp_filter.enabled
    return filter_builder.build(
        yaml_filter=yaml_filter,
        cli_csv=inp_filter.source_path if enabled else None,
        cli_column=inp_filter.column_name if enabled else None,
        cli_field=inp_filter.filter_field if enabled else None,
        cli_fallback_column=inp_filter.fallback_column if enabled else None,
        test_mode=test_mode or ctx.ignore_yaml_filter,
        direct_filter_ids=inp_filter.filter_ids,
        direct_fallback_mapping=inp_filter.fallback_mapping,
        direct_multi_filter_ids=inp_filter.multi_filter_ids,
        direct_valid_combinations=inp_filter.valid_combinations,
    )


def assemble_cached_bronze_context_impl(ctx: PipelineRunContext) -> CachedBronzeContext:
    return ctx.cached_bronze


def validate_pk_contract_impl(config: PipelineYamlConfig) -> None:
    business_primary_keys = tuple(getattr(config, "business_primary_keys", ()) or ())
    technical_primary_key = getattr(config, "technical_primary_key", "entity_id")

    if not business_primary_keys:
        raise ValueError("business_primary_keys must be non-empty")
    if not technical_primary_key:
        raise ValueError("technical_primary_key must be non-empty")


def resolve_filter_batch_size_impl(
    yaml_config: PipelineYamlConfig,
    *,
    source_loader: Callable[..., object],
) -> int | None:
    filter_batch_size = getattr(yaml_config, "filter_batch_size", None)
    if isinstance(filter_batch_size, int):
        return filter_batch_size
    try:
        source_cfg = cast(SourceConfigLike, source_loader(yaml_config.provider))
        batch_size = source_cfg.pagination.id_batch_size
        return batch_size if isinstance(batch_size, int) else None
    except (ValueError, AttributeError):
        return None


def adjust_batch_size_for_filter_impl(
    *,
    yaml_config: PipelineYamlConfig,
    filter_config: InputFilterConfig | None,
    observability: ObservabilityBundle,
    filter_batch_size: int | None,
) -> None:
    if filter_config and filter_batch_size is not None:
        observability.logger.info(
            "batch_size_auto_adjusted",
            original=yaml_config.batch_size,
            adjusted=filter_batch_size,
            reason="input_filter_active",
        )
        yaml_config.batch_size = filter_batch_size

================================================================================
File: _run_manifest_contract_identity.py
Path: runtime_builders\_run_manifest_contract_identity.py
================================================================================
"""Contract-registry identity helpers for manifested runs."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml


def resolve_contract_identity(
    *,
    provider: str,
    entity: str,
) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Resolve contract identity fields from canonical registry when available."""
    contract_ref = f"{provider}.{entity}"
    registry_path = Path("configs/base/contract_registry.yaml")
    if not registry_path.exists():
        return contract_ref, None, None, None, None
    entry = _load_contract_registry_entry(registry_path, contract_ref)
    if entry is None:
        return contract_ref, None, None, None, None
    return (contract_ref, *_extract_contract_identity_fields(entry))


def _load_contract_registry_entry(
    registry_path: Path,
    contract_ref: str,
) -> dict[str, object] | None:
    payload = _read_contract_registry_payload(registry_path)
    if payload is None:
        return None
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        return None
    entry = entries.get(contract_ref)
    if not isinstance(entry, dict):
        return None
    return entry


def _read_contract_registry_payload(
    registry_path: Path,
) -> dict[str, object] | None:
    try:
        payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _extract_contract_identity_fields(
    entry: dict[str, object],
) -> tuple[str | None, str | None, str | None, str | None]:
    identity_payload = _identity_payload(entry)
    contract_version = _coerce_optional_text(identity_payload.get("contract_version"))
    contract_schema_hash = _coerce_optional_text(identity_payload.get("schema_hash"))
    dq_policy_ref = _coerce_optional_text(
        identity_payload.get("dq_policy_ref") or entry.get("dq_policy_ref")
    )
    rule_bundle_version = _coerce_optional_text(
        identity_payload.get("rule_bundle_version") or entry.get("rule_bundle_version")
    )
    return (
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    )


def _identity_payload(entry: Mapping[str, object]) -> Mapping[str, object]:
    identity = entry.get("identity")
    if isinstance(identity, Mapping):
        return identity
    return {}


def _coerce_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

================================================================================
File: _run_manifest_refs.py
Path: runtime_builders\_run_manifest_refs.py
================================================================================
"""Control-plane ref helpers for manifest builders."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.control_plane import RunArtifactRef

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config import Settings


def _resolve_data_root(settings: Settings) -> Path:
    """Resolve a writable data root for control-plane artifacts.

    Explicit `settings.data_dir` values are preserved. When no data directory is
    configured, try the conventional `data/` under the current working
    directory, but fall back to `/tmp/bioetl-data` if the checkout is mounted
    read-only in the current execution environment.
    """
    configured_root = getattr(settings, "data_dir", None)
    if configured_root:
        return Path(configured_root)

    candidate = Path("data")
    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError:
        return Path(tempfile.gettempdir()) / "bioetl-data"
    if not os.access(candidate, os.W_OK):
        return Path(tempfile.gettempdir()) / "bioetl-data"
    return candidate


def build_planned_artifacts(
    *,
    settings: Settings,
    provider: str,
    entity: str,
) -> tuple[RunArtifactRef, ...]:
    """Capture planned layer roots for the manifest control-plane snapshot."""
    output_root = _resolve_data_root(settings) / "output"
    return (
        RunArtifactRef(
            layer="bronze", path=str(output_root / "bronze" / provider / entity)
        ),
        RunArtifactRef(
            layer="silver", path=str(output_root / "silver" / provider / entity)
        ),
        RunArtifactRef(
            layer="gold", path=str(output_root / "gold" / provider / entity)
        ),
    )


def control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return _resolve_data_root(settings) / "output" / "control" / leaf


@dataclass(frozen=True, slots=True)
class ManifestControlPlaneRefs:
    """Resolved control-plane references produced before factory runner wiring."""

    manifest_id: str
    config_hash: str | None
    dq_contract_compatibility_hash: str | None
    effective_config_artifact_id: str | None
    contract_ref: str | None
    contract_version: str | None
    contract_schema_hash: str | None
    dq_policy_ref: str | None
    rule_bundle_version: str | None


def resolve_run_context_values(
    ctx: PipelineRunContext,
) -> tuple[str, str]:
    """Resolve run type and execution context values from context."""
    raw_run_type = getattr(ctx, "run_type", "incremental")
    run_type_value = str(getattr(raw_run_type, "value", raw_run_type))
    raw_execution_context = getattr(ctx, "execution_context", "isolated")
    execution_context_value = str(
        getattr(raw_execution_context, "value", raw_execution_context)
    )
    return run_type_value, execution_context_value


def create_control_plane_refs(
    manifest_id: str,
    effective_config_hash: str,
    dq_contract_compatibility_hash: str,
    effective_config_artifact_id: str,
    contract_ref: str,
    contract_version: str | None,
    contract_schema_hash: str | None,
    dq_policy_ref: str | None,
    rule_bundle_version: str | None,
) -> ManifestControlPlaneRefs:
    """Build the compact control-plane refs bundle returned to callers."""
    return ManifestControlPlaneRefs(
        manifest_id=manifest_id,
        config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
    )

================================================================================
File: _run_manifest_snapshot_support.py
Path: runtime_builders\_run_manifest_snapshot_support.py
================================================================================
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import TYPE_CHECKING, cast
from uuid import UUID

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from bioetl.domain.context import PipelineRunContext


def normalize_snapshot(value: object) -> object:
    if not isinstance(value, type) and is_dataclass(value):
        return normalize_snapshot(asdict(cast("DataclassInstance", value)))
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return normalize_snapshot(
            {key: item for key, item in vars(value).items() if not key.startswith("_")}
        )
    if isinstance(value, dict):
        return {str(key): normalize_snapshot(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [normalize_snapshot(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    return value


def to_serializable_mapping(value: object) -> dict[str, object]:
    if hasattr(value, "model_dump"):
        payload = value.model_dump(mode="json", exclude_none=True)
    elif hasattr(value, "dict"):
        payload = value.dict(exclude_none=True)
    elif hasattr(value, "__dict__"):
        payload = {
            key: item for key, item in vars(value).items() if not key.startswith("_")
        }
    else:
        payload = normalize_snapshot(value)
    if not isinstance(payload, dict):
        return {"value": normalize_snapshot(payload)}
    normalized = normalize_snapshot(payload)
    if not isinstance(normalized, dict):
        raise TypeError("Manifest snapshot normalization must return a mapping")
    return normalized


def build_launch_context_snapshot(
    ctx: PipelineRunContext,
    *,
    run_type_value: str,
    execution_context_value: str,
    required_persistence_profile: str,
) -> dict[str, object]:
    """Build a snapshot of the launch context."""
    snapshot = _build_base_snapshot(ctx, run_type_value, execution_context_value)
    snapshot.update(
        {
            "required_persistence_profile": required_persistence_profile,
            "exact_replay_support_boundary": _determine_replay_support_boundary(
                execution_context_value
            ),
        }
    )
    _add_optional_fields(snapshot, ctx)
    return snapshot


def _build_base_snapshot(
    ctx: PipelineRunContext,
    run_type_value: str,
    execution_context_value: str,
) -> dict[str, object]:
    """Build the base snapshot."""
    return {
        "pipeline_name": str(ctx.pipeline_name),
        "run_type": run_type_value,
        "resume": getattr(ctx, "resume", False),
        "dry_run": getattr(ctx, "dry_run", False),
        "limit": getattr(ctx, "limit", None),
        "query": getattr(ctx, "query", None),
        "start_offset": getattr(ctx, "start_offset", None),
        "log_level": getattr(ctx, "log_level", "INFO"),
        "ignore_yaml_filter": getattr(ctx, "ignore_yaml_filter", False),
        "skip_gold": getattr(ctx, "skip_gold", False),
        "exact_replay": getattr(ctx, "exact_replay", False),
        "execution_context": execution_context_value,
    }


def _determine_replay_support_boundary(execution_context_value: str) -> str:
    """Determine the replay support boundary."""
    return (
        "snapshot_backed_source_runs_only"
        if execution_context_value != "composite"
        else "composite_execution_unsupported"
    )


def _add_optional_fields(snapshot: dict[str, object], ctx: PipelineRunContext) -> None:
    """Add optional fields to the snapshot."""
    snapshot["vacuum"] = to_serializable_mapping(getattr(ctx, "vacuum", None))
    snapshot["input_filter"] = to_serializable_mapping(
        getattr(ctx, "input_filter", None)
    )
    snapshot["cached_bronze"] = to_serializable_mapping(
        getattr(ctx, "cached_bronze", None)
    )


def resolve_replay_parentage(
    *,
    ctx: PipelineRunContext,
    runtime_config: object,
) -> tuple[str | None, str | None]:
    """Resolve the replay parentage."""
    runtime_config_mapping = _as_runtime_config_mapping(runtime_config)
    replay_of_run_id = _resolve_replay_id(
        ctx, "replay_of_run_id", runtime_config_mapping
    )
    replay_of_manifest_id = _resolve_replay_id(
        ctx, "replay_of_manifest_id", runtime_config_mapping
    )
    return replay_of_run_id, replay_of_manifest_id


def _resolve_replay_id(
    ctx: PipelineRunContext,
    attr_name: str,
    runtime_config_mapping: Mapping[str, object],
) -> str | None:
    """Resolve the replay ID from context or runtime config."""
    ctx_value = _coerce_optional_text(getattr(ctx, attr_name, None))
    if ctx_value is not None:
        return ctx_value

    keys = (attr_name, f"exact_replay_parent_{attr_name}")
    return _resolve_replay_parentage_mapping_value(runtime_config_mapping, *keys)


def resolve_provider_entity(
    *,
    pipeline_name: str,
    yaml_config: object,
) -> tuple[str, str]:
    """Resolve provider and entity from pipeline name and config."""
    fallback_provider, fallback_entity = _determine_fallbacks(pipeline_name)
    provider = _resolve_provider(yaml_config, fallback_provider)
    entity = _resolve_entity(yaml_config, fallback_entity)
    return provider, entity


def _determine_fallbacks(pipeline_name: str) -> tuple[str, str]:
    """Determine fallback provider and entity from pipeline name."""
    if "_" in pipeline_name:
        return pipeline_name.split("_", 1)
    return pipeline_name, pipeline_name


def _resolve_provider(yaml_config: object, fallback: str) -> str:
    """Resolve provider from config or use fallback."""
    return _resolve_name_component(
        getattr(yaml_config, "provider", None),
        fallback=fallback,
    )


def _resolve_entity(yaml_config: object, fallback: str) -> str:
    """Resolve entity from config or use fallback."""
    return _resolve_name_component(
        getattr(yaml_config, "entity_type", None),
        fallback=fallback,
    )


def _as_runtime_config_mapping(runtime_config: object) -> Mapping[str, object]:
    if isinstance(runtime_config, Mapping):
        return runtime_config
    return {}


def _resolve_replay_parentage_mapping_value(
    runtime_config: Mapping[str, object],
    *keys: str,
) -> str | None:
    for key in keys:
        direct_value = _coerce_optional_text(runtime_config.get(key))
        if direct_value is not None:
            return direct_value
        control_plane = runtime_config.get("control_plane")
        if isinstance(control_plane, Mapping):
            nested_value = _coerce_optional_text(control_plane.get(key))
            if nested_value is not None:
                return nested_value
        pipeline = runtime_config.get("pipeline")
        if isinstance(pipeline, Mapping):
            nested_direct = _coerce_optional_text(pipeline.get(key))
            if nested_direct is not None:
                return nested_direct
            nested_control_plane = pipeline.get("control_plane")
            if isinstance(nested_control_plane, Mapping):
                nested_value = _coerce_optional_text(nested_control_plane.get(key))
                if nested_value is not None:
                    return nested_value
    return None


def _resolve_name_component(value: object, *, fallback: str) -> str:
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    return fallback


def _coerce_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

================================================================================
File: _run_manifest_support.py
Path: runtime_builders\_run_manifest_support.py
================================================================================
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from bioetl.composition.runtime_builders._cached_bronze_snapshot_support import (
    build_cached_bronze_input_snapshot_refs,
)
from bioetl.composition.runtime_builders._run_manifest_contract_identity import (
    resolve_contract_identity,
)
from bioetl.composition.runtime_builders._run_manifest_refs import (
    ManifestControlPlaneRefs,
    build_planned_artifacts,
    control_plane_root,
    create_control_plane_refs,
    resolve_run_context_values,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    build_launch_context_snapshot,
    normalize_snapshot,
    resolve_provider_entity,
    resolve_replay_parentage,
    to_serializable_mapping,
)
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunInputSnapshotRef,
    RunSourceRef,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config import Settings

__all__ = [
    "ManifestControlPlaneRefs",
    "build_launch_context_snapshot",
    "build_planned_artifacts",
    "build_run_source_refs",
    "control_plane_root",
    "create_control_plane_refs",
    "normalize_snapshot",
    "resolve_contract_identity",
    "resolve_provider_entity",
    "resolve_replay_capability",
    "resolve_replay_parentage",
    "resolve_run_context_values",
    "to_serializable_mapping",
]


def build_run_source_refs(
    *,
    ctx: PipelineRunContext,
    cached_bronze: object | None,
    settings: Settings,
    provider: str,
    entity: str,
) -> tuple[RunSourceRef, ...]:
    input_snapshots = _build_cached_bronze_snapshot_refs(
        cached_bronze=cached_bronze,
        settings=settings,
        pipeline_name=ctx.pipeline_name,
        provider=provider,
        entity=entity,
    )
    if getattr(ctx, "exact_replay", False) and not input_snapshots:
        raise RuntimeError(
            "Exact replay requires immutable input snapshots; no snapshot-backed source refs were resolved for this run"
        )
    return (
        RunSourceRef(
            provider=provider,
            entity=entity,
            pipeline_name=ctx.pipeline_name,
            query=getattr(ctx, "query", None),
            input_snapshots=input_snapshots,
        ),
    )


def resolve_replay_capability(
    *,
    source_refs: tuple[RunSourceRef, ...],
    resume_requested: bool,
) -> ReplayCapability:
    has_input_snapshots = any(ref.input_snapshots for ref in source_refs)
    if has_input_snapshots:
        return ReplayCapability.EXACT_REPLAY_SUPPORTED
    if resume_requested:
        return ReplayCapability.RESUME_ONLY
    return ReplayCapability.REBUILD_ONLY


def _build_cached_bronze_snapshot_refs(
    *,
    cached_bronze: object | None,
    settings: Settings,
    pipeline_name: str,
    provider: str,
    entity: str,
) -> tuple[RunInputSnapshotRef, ...]:
    """Build immutable snapshot refs for cached-Bronze executions."""
    if cached_bronze is None or not getattr(cached_bronze, "enabled", False):
        return ()
    bronze_path = getattr(cached_bronze, "bronze_path", None)
    bronze_date = getattr(cached_bronze, "bronze_date", None)
    bronze_root = (
        Path(str(bronze_path))
        if bronze_path is not None
        else settings.bronze_path / provider / entity
    )
    snapshot_refs = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date=cast("str | None", bronze_date),
        pipeline_name=pipeline_name,
    )
    if not snapshot_refs:
        raise RuntimeError(
            "Cached Bronze execution requires at least one persisted batch file for snapshot provenance"
        )
    return snapshot_refs

================================================================================
File: _runner_builder_support.py
Path: runtime_builders\_runner_builder_support.py
================================================================================
"""Private helpers for runtime runner builder control-plane glue."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Protocol, cast

from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders.inputs_resolver import (
    RunnerInputs as _RunnerInputs,
)

_DEFAULT_REQUIRED_PERSISTENCE_PROFILE = "degraded_observable"
_PERSISTENCE_PROFILE_REQUIREMENTS = {"replay_ready", "forensic_grade"}
_PERSISTENCE_PROFILE_ACTIVE_LAYERS = ("bronze", "silver", "gold")


class _LoggerBindableObservability(Protocol):
    logger: object


def _normalize_required_persistence_profile(required_profile: object) -> str:
    profile = (
        str(required_profile).strip()
        if required_profile is not None
        else _DEFAULT_REQUIRED_PERSISTENCE_PROFILE
    )
    return profile or _DEFAULT_REQUIRED_PERSISTENCE_PROFILE


def _coerce_sink_layer_mapping(yaml_config: object) -> Mapping[str, object]:
    sink = getattr(yaml_config, "sink", None)
    if isinstance(sink, Mapping):
        return sink
    return {}


def _is_sink_layer_enabled(layer_config: object | None) -> bool:
    if layer_config is None:
        return True
    return bool(getattr(layer_config, "enabled", True))


def _has_lineage_sidecar_persistence(layer_config: object | None) -> bool:
    if layer_config is None:
        return False
    return bool(getattr(layer_config, "save_metadata", False))


def resolve_required_artifact_lineage_layers(
    *,
    yaml_config: object | None,
    skip_gold: bool = False,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return active layers and layers missing metadata-sidecar persistence."""
    if yaml_config is None:
        active_layers = tuple(
            layer
            for layer in _PERSISTENCE_PROFILE_ACTIVE_LAYERS
            if not (layer == "gold" and skip_gold)
        )
        return active_layers, active_layers
    sink_mapping = _coerce_sink_layer_mapping(yaml_config)
    active_layers: list[str] = []
    missing_lineage_layers: list[str] = []
    for layer in _PERSISTENCE_PROFILE_ACTIVE_LAYERS:
        if layer == "gold" and skip_gold:
            continue
        layer_config = sink_mapping.get(layer)
        if not _is_sink_layer_enabled(layer_config):
            continue
        active_layers.append(layer)
        if not _has_lineage_sidecar_persistence(layer_config):
            missing_lineage_layers.append(layer)
    return tuple(active_layers), tuple(missing_lineage_layers)


def validate_required_persistence_profile(
    *,
    manifest_enabled: bool,
    ledger_enabled: bool,
    required_profile: object,
    execution_label: str,
    exact_replay_execution_context_supported: bool = True,
    missing_artifact_lineage_layers: tuple[str, ...] = (),
) -> None:
    """Fail closed when static control-plane flags cannot satisfy required profile."""
    profile = _normalize_required_persistence_profile(required_profile)
    if profile in _PERSISTENCE_PROFILE_REQUIREMENTS and not manifest_enabled:
        raise RuntimeError(
            f"{execution_label} requires run manifests for required persistence "
            f"profile '{profile}'; set "
            "pipeline.control_plane.run_manifest_enabled=true"
        )
    if (
        profile in _PERSISTENCE_PROFILE_REQUIREMENTS
        and not exact_replay_execution_context_supported
    ):
        raise RuntimeError(
            f"{execution_label} cannot satisfy required persistence profile "
            f"'{profile}' because this execution context is outside the strict "
            "exact-replay support boundary"
        )
    if profile == "forensic_grade" and not ledger_enabled:
        raise RuntimeError(
            f"{execution_label} requires run ledgers for required persistence "
            "profile 'forensic_grade'; set "
            "pipeline.control_plane.run_ledger_enabled=true"
        )
    if profile == "forensic_grade" and missing_artifact_lineage_layers:
        layers = ", ".join(missing_artifact_lineage_layers)
        raise RuntimeError(
            f"{execution_label} requires metadata sidecars / lineage persistence "
            f"for active layers [{layers}] to satisfy required persistence profile "
            "'forensic_grade'; enable sink.<layer>.save_metadata for each active "
            "published layer"
        )


def resolve_control_plane_flags(
    settings: object,
    *,
    yaml_config: object | None = None,
    skip_gold: bool = False,
) -> tuple[bool, bool]:
    """Resolve control-plane feature flags for executable pipeline runs."""
    pipeline_settings = getattr(settings, "pipeline", None)
    control_plane = getattr(pipeline_settings, "control_plane", None)
    manifest_enabled = bool(getattr(control_plane, "run_manifest_enabled", True))
    ledger_enabled = bool(getattr(control_plane, "run_ledger_enabled", True))
    required_profile = getattr(
        control_plane,
        "required_persistence_profile",
        "degraded_observable",
    )
    if not manifest_enabled:
        raise RuntimeError(
            "Pipeline execution requires run manifests; set "
            "pipeline.control_plane.run_manifest_enabled=true"
        )
    _active_layers, missing_artifact_lineage_layers = (
        resolve_required_artifact_lineage_layers(
            yaml_config=yaml_config,
            skip_gold=skip_gold,
        )
    )
    validate_required_persistence_profile(
        manifest_enabled=manifest_enabled,
        ledger_enabled=ledger_enabled,
        required_profile=required_profile,
        execution_label="Pipeline execution",
        missing_artifact_lineage_layers=missing_artifact_lineage_layers,
    )
    return True, ledger_enabled


def bind_manifest_logger_context(
    inputs: _RunnerInputs,
    manifest_id: str,
) -> _RunnerInputs:
    """Bind ``manifest_id`` into runtime observability when available."""
    observability = getattr(inputs, "observability", None)
    rebound_observability = _rebind_observability_logger(
        observability=observability,
        manifest_id=manifest_id,
    )
    if rebound_observability is observability:
        return inputs
    if isinstance(inputs, _RunnerInputs):
        return cast(
            _RunnerInputs,
            replace(
                inputs,
                observability=cast("ObservabilityBundle", rebound_observability),
            ),
        )
    return inputs


def _rebind_observability_logger(
    *,
    observability: object,
    manifest_id: str,
) -> object:
    """Return observability with ``manifest_id`` bound to its logger context."""
    bind_fn = getattr(observability, "bind", None)
    if callable(bind_fn):
        return bind_fn(manifest_id=manifest_id)

    logger = getattr(observability, "logger", None)
    logger_bind = getattr(logger, "bind", None)
    if not callable(logger_bind):
        return observability

    typed_observability = cast("_LoggerBindableObservability", observability)
    try:
        typed_observability.logger = logger_bind(manifest_id=manifest_id)
    except (AttributeError, TypeError):
        return observability
    return observability

================================================================================
File: cached_bronze_snapshot_support.py
Path: runtime_builders\cached_bronze_snapshot_support.py
================================================================================
"""Public seam for cached-Bronze snapshot provenance helpers."""

from __future__ import annotations

from bioetl.composition.runtime_builders._cached_bronze_snapshot_support import (
    build_cached_bronze_input_snapshot_refs,
)

__all__ = ["build_cached_bronze_input_snapshot_refs"]

================================================================================
File: config_access.py
Path: runtime_builders\config_access.py
================================================================================
"""Composition-facing seam for runtime configuration access helpers."""

from __future__ import annotations

from bioetl.composition.source_config_access import load_source_config
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config

__all__ = ["get_settings", "load_pipeline_config", "load_source_config"]

================================================================================
File: control_plane.py
Path: runtime_builders\control_plane.py
================================================================================
"""Control-plane helpers for runtime runner assembly."""

from __future__ import annotations

from dataclasses import is_dataclass, replace
from typing import TYPE_CHECKING, cast

from bioetl.composition.runtime_builders.effective_config_artifact_builder import (
    create_and_persist_effective_config_artifact,
)
from bioetl.composition.runtime_builders.run_manifest_builder import (
    _ManifestControlPlaneRefs,
    create_run_manifest,
)
from bioetl.domain.normalization import normalize_runtime_anchor_payload

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext


_OPTIONAL_CONTROL_PLANE_FIELDS = (
    "config_hash",
    "dq_contract_compatibility_hash",
    "effective_config_artifact_id",
    "contract_ref",
    "contract_version",
    "contract_schema_hash",
    "dq_policy_ref",
    "rule_bundle_version",
)


def _iter_optional_control_plane_updates(
    *,
    config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    contract_schema_hash: str | None = None,
    dq_policy_ref: str | None = None,
    rule_bundle_version: str | None = None,
) -> tuple[tuple[str, str], ...]:
    values = normalize_runtime_anchor_payload(
        {
            "config_hash": config_hash,
            "dq_contract_compatibility_hash": dq_contract_compatibility_hash,
            "effective_config_artifact_id": effective_config_artifact_id,
            "contract_ref": contract_ref,
            "contract_version": contract_version,
            "contract_schema_hash": contract_schema_hash,
            "dq_policy_ref": dq_policy_ref,
            "rule_bundle_version": rule_bundle_version,
        }
    )
    return tuple(
        (field_name, field_value)
        for field_name, field_value in values.items()
        if field_value is not None
    )


def _build_dataclass_manifest_updates(
    ctx: PipelineRunContext,
    manifest_id: str,
    *,
    optional_updates: tuple[tuple[str, str], ...],
) -> dict[str, object]:
    updates: dict[str, object] = {"manifest_id": manifest_id}
    for field_name, field_value in optional_updates:
        if hasattr(ctx, field_name):
            updates[field_name] = field_value
    return updates


def _apply_manifest_updates_to_mutable_context(
    ctx: object,
    manifest_id: str,
    *,
    optional_updates: tuple[tuple[str, str], ...],
) -> object:
    ctx.manifest_id = manifest_id
    for field_name, field_value in optional_updates:
        setattr(ctx, field_name, field_value)
    return ctx


def attach_manifest_id(
    ctx: PipelineRunContext,
    manifest_id: str,
    *,
    config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    contract_schema_hash: str | None = None,
    dq_policy_ref: str | None = None,
    rule_bundle_version: str | None = None,
) -> PipelineRunContext:
    """Return context carrying manifest/control-plane provenance values."""
    optional_updates = _iter_optional_control_plane_updates(
        config_hash=config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
    )
    if is_dataclass(ctx):
        return cast(
            "PipelineRunContext",
            replace(
                cast("DataclassInstance", ctx),
                **_build_dataclass_manifest_updates(
                    ctx,
                    manifest_id,
                    optional_updates=optional_updates,
                ),
            ),
        )
    if hasattr(ctx, "__dict__"):
        return cast(
            "PipelineRunContext",
            _apply_manifest_updates_to_mutable_context(
                ctx,
                manifest_id,
                optional_updates=optional_updates,
            ),
        )
    raise TypeError("PipelineRunContext must support manifest_id attachment")


def create_run_manifest_with_effective_config(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    ledger_enabled: bool,
) -> tuple[_ManifestControlPlaneRefs, RunLedgerService | None]:
    """Create immutable manifest before pipeline assembly begins."""
    if "_" in ctx.pipeline_name:
        provider, entity = ctx.pipeline_name.split("_", 1)
    else:
        provider = ctx.pipeline_name
        entity = ctx.pipeline_name
    (
        effective_config_artifact_id,
        effective_config_hash,
        dq_contract_compatibility_hash,
    ) = create_and_persist_effective_config_artifact(
        ctx=ctx,
        inputs=inputs,
        provider=provider,
        entity=entity,
    )
    return create_run_manifest(
        ctx=ctx,
        inputs=inputs,
        ledger_enabled=ledger_enabled,
        effective_config_artifact_id=effective_config_artifact_id,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
    )

================================================================================
File: effective_config_artifact_builder.py
Path: runtime_builders\effective_config_artifact_builder.py
================================================================================
"""Effective config artifact creation for control-plane."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID

from bioetl.application.services.control_plane.effective_config_service import (
    create_effective_config_service,
)
from bioetl.composition.runtime_builders._run_manifest_refs import (
    control_plane_root as _shared_control_plane_root,
)
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef
from bioetl.infrastructure.control_plane import FileEffectiveConfigArtifactStore

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config import Settings


def _normalize_snapshot(value: object) -> object:
    """Normalize dataclass/Pydantic values into JSON-safe primitives."""
    if not isinstance(value, type) and is_dataclass(value):
        return _normalize_snapshot(asdict(cast("DataclassInstance", value)))
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return _normalize_snapshot(
            {key: item for key, item in vars(value).items() if not key.startswith("_")}
        )
    if isinstance(value, dict):
        return {str(key): _normalize_snapshot(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_normalize_snapshot(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    return value


def _to_serializable_mapping(value: object) -> dict[str, object]:
    """Convert dataclass or model objects into plain mappings."""
    if hasattr(value, "model_dump"):
        payload = value.model_dump(mode="json", exclude_none=True)
    elif hasattr(value, "dict"):
        payload = value.dict(exclude_none=True)
    elif hasattr(value, "__dict__"):
        payload = {
            key: item for key, item in vars(value).items() if not key.startswith("_")
        }
    else:
        payload = _normalize_snapshot(value)
    if not isinstance(payload, dict):
        return {"value": _normalize_snapshot(payload)}
    normalized = _normalize_snapshot(payload)
    if not isinstance(normalized, dict):
        raise TypeError("Manifest snapshot normalization must return a mapping")
    return normalized


def _build_runtime_overrides_snapshot(ctx: PipelineRunContext) -> dict[str, object]:
    """Convert launch context options into runtime-override snapshot shape."""
    raw_run_type = getattr(ctx, "run_type", "incremental")
    run_type_value = (
        raw_run_type.value if isinstance(raw_run_type, Enum) else str(raw_run_type)
    )
    raw_execution_context = getattr(ctx, "execution_context", "isolated")
    execution_context_value = (
        raw_execution_context.value
        if isinstance(raw_execution_context, Enum)
        else str(raw_execution_context)
    )
    return {
        "cli": {},
        "env": {},
        "runtime": {
            "pipeline_name": str(getattr(ctx, "pipeline_name", "unknown")),
            "run_type": run_type_value,
            "resume": getattr(ctx, "resume", False),
            "dry_run": getattr(ctx, "dry_run", False),
            "limit": getattr(ctx, "limit", None),
            "query": getattr(ctx, "query", None),
            "start_offset": getattr(ctx, "start_offset", None),
            "log_level": getattr(ctx, "log_level", "INFO"),
            "ignore_yaml_filter": getattr(ctx, "ignore_yaml_filter", False),
            "skip_gold": getattr(ctx, "skip_gold", False),
            "execution_context": execution_context_value,
            "vacuum": _to_serializable_mapping(getattr(ctx, "vacuum", None)),
            "input_filter": _to_serializable_mapping(
                getattr(ctx, "input_filter", None)
            ),
            "cached_bronze": _to_serializable_mapping(
                getattr(ctx, "cached_bronze", None)
            ),
        },
    }


def _compute_file_hash(path: Path) -> str | None:
    """Return a stable SHA-256 hash for one config source file when available."""
    if not path.exists() or not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_config_source_ref(
    *,
    relative_path: str,
    priority: int,
    repo_root: Path,
) -> ConfigSourceRef:
    """Build one canonical file-backed source ref with provenance hash."""
    source_path = repo_root / relative_path
    return ConfigSourceRef(
        source_type="file",
        source_path=relative_path,
        source_hash=_compute_file_hash(source_path),
        priority=priority,
    )


def _build_effective_config_source_refs(
    *,
    provider: str,
    entity: str,
    repo_root: Path | None = None,
) -> list[ConfigSourceRef]:
    """Build source references used to materialize effective config artifacts."""
    resolved_repo_root = repo_root or Path(__file__).resolve().parents[4]
    return [
        _build_config_source_ref(
            relative_path="configs/base/pipeline.yaml",
            priority=1,
            repo_root=resolved_repo_root,
        ),
        _build_config_source_ref(
            relative_path=f"configs/entities/{provider}/{entity}.yaml",
            priority=2,
            repo_root=resolved_repo_root,
        ),
        _build_config_source_ref(
            relative_path="configs/base/contract_registry.yaml",
            priority=3,
            repo_root=resolved_repo_root,
        ),
    ]


def _control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return _shared_control_plane_root(settings, leaf)


def create_and_persist_effective_config_artifact(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
) -> tuple[str, str, str]:
    """Create effective config artifact, persist it, and return provenance fields."""
    logger = inputs.observability.logger
    service = create_effective_config_service()
    artifact = service.create_effective_config_artifact(
        pipeline_name=ctx.pipeline_name,
        pipeline_kind="standard",
        resolved_config=_to_serializable_mapping(inputs.yaml_config),
        runtime_overrides=_build_runtime_overrides_snapshot(ctx),
        source_refs=_build_effective_config_source_refs(
            provider=provider, entity=entity
        ),
    )
    serialized_payload = service.serialize_artifact(artifact)
    loaded_payload = json.loads(serialized_payload)
    if not isinstance(loaded_payload, dict):
        raise ValueError("Effective-config artifact payload must be a JSON object")
    artifact_payload = {str(key): value for key, value in loaded_payload.items()}
    artifact_store = FileEffectiveConfigArtifactStore(
        base_path=_control_plane_root(inputs.settings, "effective_config")
    )
    try:
        artifact_store.save(
            artifact_id=artifact.artifact_id,
            run_id=ctx.run_id,
            payload=artifact_payload,
        )
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        log_error = getattr(logger, "error", None)
        if callable(log_error):
            log_error(
                "effective_config_artifact_persist_failed",
                artifact_id=artifact.artifact_id,
                pipeline_name=ctx.pipeline_name,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        raise
    log_info = getattr(logger, "info", None)
    if callable(log_info):
        log_info(
            "effective_config_artifact_persisted",
            artifact_id=artifact.artifact_id,
            pipeline_name=ctx.pipeline_name,
            effective_config_hash=artifact.effective_config_hash,
            dq_contract_compatibility_hash=artifact.dq_contract_compatibility_hash,
        )
    return (
        artifact.artifact_id,
        artifact.effective_config_hash,
        artifact.dq_contract_compatibility_hash,
    )

================================================================================
File: inputs_resolver.py
Path: runtime_builders\inputs_resolver.py
================================================================================
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    adjust_batch_size_for_filter_impl as _adjust_batch_size_for_filter_impl,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    apply_tracing_override as _apply_tracing_override_impl,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    assemble_cached_bronze_context_impl as _assemble_cached_bronze_context_impl,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    assemble_filter_config_impl as _assemble_filter_config_impl,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    assemble_runtime_config_impl as _assemble_runtime_config_impl,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    assemble_vacuum_settings_impl as _assemble_vacuum_settings_impl,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    resolve_filter_batch_size_impl as _resolve_filter_batch_size_impl,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    validate_pk_contract_impl as _validate_pk_contract_impl,
)
from bioetl.composition.runtime_builders.config_access import load_source_config
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    build_runtime_config as _build_runtime_config,
)
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    log_cached_bronze as _log_cached_bronze,
)
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    log_filter_config as _log_filter_config,
)
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    resolve_health_check_mode_policy as _resolve_health_check_mode_policy,
)
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    resolve_runtime_projection as _resolve_runtime_projection,
)
from bioetl.domain.config import RuntimeConfig

if TYPE_CHECKING:
    from bioetl.domain.context import (
        CachedBronzeContext,
        PipelineRunContext,
    )
    from bioetl.domain.context import VacuumSettings as CliVacuumSettings
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterYamlConfig as YamlInputFilter,
    )
    from bioetl.infrastructure.schemas.pipeline_config import (
        MaintenanceConfig,
        PipelineYamlConfig,
    )


@dataclass(frozen=True, slots=True)
class ResolvedVacuumSettings:
    enabled: bool
    retention_days: int


@dataclass(frozen=True, slots=True)
class RunnerInputs:
    settings: Settings
    yaml_config: PipelineYamlConfig
    observability: ObservabilityBundle
    runtime_config: RuntimeConfig
    filter_config: InputFilterConfig | None
    cached_bronze: CachedBronzeContext


__all__ = [
    "ResolvedVacuumSettings",
    "RunnerInputs",
    "adjust_batch_size_for_filter",
    "assemble_cached_bronze_context",
    "assemble_filter_config",
    "assemble_runtime_config",
    "assemble_vacuum_settings",
    "prepare_runner_inputs",
    "resolve_filter_batch_size",
    "resolve_health_check_mode",
    "validate_pk_contract",
]

_DEFAULT_HEALTH_CHECK_MODE: Literal["strict", "probe"] = "strict"


def assemble_vacuum_settings(
    *,
    cli_vacuum: CliVacuumSettings,
    yaml_maintenance: MaintenanceConfig,
) -> ResolvedVacuumSettings:
    return cast(
        ResolvedVacuumSettings,
        _assemble_vacuum_settings_impl(
            cli_vacuum=cli_vacuum,
            yaml_maintenance=yaml_maintenance,
            result_cls=ResolvedVacuumSettings,
        ),
    )


def assemble_runtime_config(
    *,
    ctx: PipelineRunContext,
    heartbeat_interval: int,
    vacuum: ResolvedVacuumSettings,
    health_check_mode: Literal["strict", "probe"],
    skip_gold: bool,
) -> RuntimeConfig:
    return _assemble_runtime_config_impl(
        ctx=ctx,
        heartbeat_interval=heartbeat_interval,
        vacuum_enabled=vacuum.enabled,
        vacuum_retention_days=vacuum.retention_days,
        health_check_mode=health_check_mode,
        skip_gold=skip_gold,
    )


def assemble_filter_config(
    *,
    yaml_filter: YamlInputFilter,
    ctx: PipelineRunContext,
    test_mode: bool,
    filter_builder: type[FilterConfigBuilder] = FilterConfigBuilder,
) -> InputFilterConfig | None:
    return _assemble_filter_config_impl(
        yaml_filter=yaml_filter,
        ctx=ctx,
        test_mode=test_mode,
        filter_builder=filter_builder,
    )


def assemble_cached_bronze_context(ctx: PipelineRunContext) -> CachedBronzeContext:
    return _assemble_cached_bronze_context_impl(ctx)


def validate_pk_contract(config: PipelineYamlConfig) -> None:
    _validate_pk_contract_impl(config)


def resolve_health_check_mode(*, settings: Settings) -> Literal["strict", "probe"]:
    return cast(
        Literal["strict", "probe"],
        _resolve_health_check_mode_policy(
            settings=settings,
            default_health_check_mode=_DEFAULT_HEALTH_CHECK_MODE,
        ),
    )


def resolve_filter_batch_size(
    yaml_config: PipelineYamlConfig,
    *,
    load_source_config_fn: Callable[..., object] | None = None,
) -> int | None:
    source_loader = (
        load_source_config if load_source_config_fn is None else load_source_config_fn
    )
    return _resolve_filter_batch_size_impl(
        yaml_config,
        source_loader=source_loader,
    )


def adjust_batch_size_for_filter(
    *,
    yaml_config: PipelineYamlConfig,
    filter_config: InputFilterConfig | None,
    observability: ObservabilityBundle,
    load_source_config_fn: Callable[..., object] | None = None,
) -> None:
    _adjust_batch_size_for_filter_impl(
        yaml_config=yaml_config,
        filter_config=filter_config,
        observability=observability,
        filter_batch_size=resolve_filter_batch_size(
            yaml_config,
            load_source_config_fn=load_source_config_fn,
        ),
    )


def prepare_runner_inputs(
    *,
    ctx: PipelineRunContext,
    get_settings_fn: Callable[[], Settings],
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
    build_observability_bundle_fn: Callable[..., ObservabilityBundle],
    assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings],
    assemble_runtime_config_fn: Callable[..., RuntimeConfig],
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None],
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ],
    load_source_config_fn: Callable[..., object] | None = None,
) -> RunnerInputs:
    settings = _apply_tracing_override_impl(
        settings=get_settings_fn(),
        enabled=getattr(ctx, "tracing_enabled_override", None),
    )
    yaml_config = load_pipeline_config_fn(ctx.pipeline_name)
    validate_pk_contract(yaml_config)
    observability = build_observability_bundle_fn(
        pipeline=ctx.pipeline_name,
        run_id=ctx.run_id,
        settings=settings,
        log_level=ctx.log_level,
    )
    vacuum = assemble_vacuum_settings_fn(
        cli_vacuum=ctx.vacuum, yaml_maintenance=yaml_config.maintenance
    )
    runtime_projection = _resolve_runtime_projection(
        ctx=ctx,
        settings=settings,
        yaml_config=yaml_config,
        observability=observability,
        default_health_check_mode=_DEFAULT_HEALTH_CHECK_MODE,
    )
    runtime_config = _build_runtime_config(
        assemble_runtime_config_fn=assemble_runtime_config_fn,
        ctx=ctx,
        vacuum=vacuum,
        runtime_projection=runtime_projection,
    )
    filter_config = assemble_filter_config_fn(
        yaml_filter=yaml_config.input_filter,
        ctx=ctx,
        test_mode=settings.test_mode,
    )
    _log_filter_config(
        observability=observability,
        filter_config=filter_config,
        from_cli=ctx.input_filter.enabled,
    )
    adjust_batch_size_for_filter(
        yaml_config=yaml_config,
        filter_config=filter_config,
        observability=observability,
        load_source_config_fn=load_source_config_fn,
    )
    cached_bronze = assemble_cached_bronze_context_fn(ctx)
    _log_cached_bronze(observability=observability, cached_bronze=cached_bronze)
    return RunnerInputs(
        settings=settings,
        yaml_config=yaml_config,
        observability=observability,
        runtime_config=runtime_config,
        filter_config=filter_config,
        cached_bronze=cached_bronze,
    )

================================================================================
File: inputs_runtime_helpers.py
Path: runtime_builders\inputs_runtime_helpers.py
================================================================================
"""Internal runtime/logging helpers for runner input resolution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast

from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.config import RuntimeConfig

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.inputs_resolver import (
        ResolvedVacuumSettings,
    )
    from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class ResolvedRuntimeProjection:
    """Explicit runtime policy projected from settings, CLI context, and YAML."""

    heartbeat_interval: int
    health_check_mode: Literal["strict", "probe"]
    skip_gold: bool


def resolve_heartbeat_interval_policy(*, settings: Settings) -> int:
    """Resolve heartbeat interval from canonical composition settings."""
    return int(settings.pipeline.heartbeat_interval)


def log_filter_config(
    *,
    observability: ObservabilityBundle,
    filter_config: InputFilterConfig | None,
    from_cli: bool,
) -> None:
    """Emit one structured log when input filtering is active."""
    if not filter_config:
        return
    observability.logger.info(
        "input_filter_enabled",
        csv_path=filter_config.source_path,
        column=filter_config.column_name,
        filter_field=filter_config.filter_field,
        source="cli" if from_cli else "config",
    )


def log_cached_bronze(
    *,
    observability: ObservabilityBundle,
    cached_bronze: CachedBronzeContext,
) -> None:
    """Emit one structured log when cached Bronze mode is enabled."""
    if not cached_bronze.enabled:
        return
    observability.logger.info(
        "cached_bronze_mode_enabled",
        bronze_path=cached_bronze.bronze_path,
        bronze_date=cached_bronze.bronze_date,
    )


def is_gold_sink_enabled(yaml_config: PipelineYamlConfig) -> bool:
    """Return whether Gold sink remains enabled in YAML configuration."""
    sink = getattr(yaml_config, "sink", {})
    gold_sink = sink.get("gold") if isinstance(sink, dict) else None
    return gold_sink is None or bool(gold_sink.enabled)


def resolve_skip_gold_policy(
    *,
    ctx: PipelineRunContext,
    yaml_config: PipelineYamlConfig,
    observability: ObservabilityBundle,
) -> bool:
    """Resolve skip-gold policy from CLI intent plus YAML sink availability."""
    if ctx.skip_gold:
        return True
    if is_gold_sink_enabled(yaml_config):
        return False
    observability.logger.info(
        "gold_sink_disabled",
        reason="sink.gold.enabled_false",
        pipeline=getattr(yaml_config, "pipeline_name", None),
    )
    return True


def resolve_health_check_mode_policy(
    *,
    settings: Settings,
    default_health_check_mode: Literal["strict", "probe"],
) -> Literal["strict", "probe"]:
    """Resolve health-check policy from settings with explicit default fallback."""
    if settings.test_mode:
        return "probe"
    configured_mode = getattr(settings.pipeline, "health_check_mode", None)
    if configured_mode in ("strict", "probe"):
        return cast(Literal["strict", "probe"], configured_mode)
    return default_health_check_mode


def resolve_runtime_projection(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    yaml_config: PipelineYamlConfig,
    observability: ObservabilityBundle,
    default_health_check_mode: Literal["strict", "probe"],
) -> ResolvedRuntimeProjection:
    """Resolve explicit runtime policy before RuntimeConfig assembly."""
    return ResolvedRuntimeProjection(
        heartbeat_interval=resolve_heartbeat_interval_policy(settings=settings),
        health_check_mode=resolve_health_check_mode_policy(
            settings=settings,
            default_health_check_mode=default_health_check_mode,
        ),
        skip_gold=resolve_skip_gold_policy(
            ctx=ctx,
            yaml_config=yaml_config,
            observability=observability,
        ),
    )


def build_runtime_config(
    *,
    assemble_runtime_config_fn: Callable[..., RuntimeConfig],
    ctx: PipelineRunContext,
    vacuum: ResolvedVacuumSettings,
    runtime_projection: ResolvedRuntimeProjection,
) -> RuntimeConfig:
    """Build RuntimeConfig from explicit runtime projection values."""
    return assemble_runtime_config_fn(
        ctx=ctx,
        heartbeat_interval=runtime_projection.heartbeat_interval,
        vacuum=vacuum,
        health_check_mode=runtime_projection.health_check_mode,
        skip_gold=runtime_projection.skip_gold,
    )

================================================================================
File: ledger_collaborator.py
Path: runtime_builders\ledger_collaborator.py
================================================================================
"""Ledger collaborator attachment for control-plane."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )


class PipelineRunnerProtocol(Protocol):
    """Minimal runner contract required for ledger collaborator attachment."""

    services: object

    def attach_run_ledger_service(self, service: RunLedgerService) -> None:
        """Attach the run-ledger collaborator."""
        ...


def _record_artifact(
    service: RunLedgerService,
    *,
    layer: str,
    artifact_path: str,
    details: dict[str, object] | None,
) -> object:
    """Record one published artifact in the control-plane ledger."""
    dataset_ref = None
    lineage_fragment_id = None
    if details is not None:
        raw_dataset_ref = details.get("dataset_ref")
        raw_lineage_fragment_id = details.get("lineage_fragment_id")
        dataset_ref = None if raw_dataset_ref is None else str(raw_dataset_ref)
        lineage_fragment_id = (
            None if raw_lineage_fragment_id is None else str(raw_lineage_fragment_id)
        )
    return service.record_artifact_published(
        layer=layer,
        artifact_path=artifact_path,
        dataset_ref=dataset_ref,
        lineage_fragment_id=lineage_fragment_id,
        details=details,
    )


def _attach_artifact_recorder(
    target: object,
    service: RunLedgerService,
) -> None:
    """Attach an artifact-recorder callback to one metadata writer when supported."""
    attach = getattr(target, "attach_artifact_recorder", None)
    if callable(attach):
        attach(
            lambda layer, artifact_path, details=None: _record_artifact(
                service,
                layer=layer,
                artifact_path=artifact_path,
                details=details,
            )
        )


def attach_control_plane_collaborators(
    runner: PipelineRunnerProtocol,
    run_ledger_service: RunLedgerService,
) -> None:
    """Attach ledger collaborators to the runner and its metadata writers."""
    runner.attach_run_ledger_service(run_ledger_service)

    services = getattr(runner, "services", None)
    if services is None:
        return

    candidates: list[object] = []
    metadata_writer = getattr(services, "metadata_writer", None)
    if metadata_writer is not None:
        candidates.append(metadata_writer)

    storage = getattr(services, "storage", None)
    if storage is not None:
        for writer_name in ("bronze", "silver", "gold"):
            writer = getattr(storage, writer_name, None)
            if writer is None:
                continue
            writer_metadata = getattr(writer, "_metadata_writer", None)
            if writer_metadata is not None:
                candidates.append(writer_metadata)

    seen: set[int] = set()
    for candidate in candidates:
        candidate_id = id(candidate)
        if candidate_id in seen:
            continue
        seen.add(candidate_id)
        _attach_artifact_recorder(candidate, run_ledger_service)

================================================================================
File: observability_builder.py
Path: runtime_builders\observability_builder.py
================================================================================
"""Runtime observability bundle assembly helpers."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.composition.bootstrap.runtime.dq_bootstrap import (
    bootstrap_dq_monitor_port as _bootstrap_dq_monitor_port_impl,
)
from bioetl.composition.bootstrap.runtime.metrics_bootstrap import (
    bootstrap_metrics_port as _bootstrap_metrics_port_impl,
)
from bioetl.composition.bootstrap.runtime.observability_bundle import (
    bootstrap_observability_bundle_impl,
    validate_observability_preflight_impl,
)
from bioetl.composition.bootstrap.runtime.tracing_bootstrap import (
    bootstrap_tracer_port as _bootstrap_tracer_port_impl,
)
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.observability_resolution import (
    resolve_metrics_port,
    resolve_tracing_port,
)
from bioetl.domain.ports import DQMonitorPort, LoggerPort, MetricsPort, TracingPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.observability.anomaly import DataQualityMonitorService
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.unified_logger import UnifiedLogger

__all__ = ["build_observability_bundle"]


def _build_logger_bootstrapper(
    logger_factory: Callable[..., LoggerPort],
) -> Callable[[str, RunID, str], LoggerPort]:
    """Build logger bootstrapper closure for canonical observability bundle."""

    def bootstrap_logger(
        logger_pipeline: str,
        logger_run_id: RunID,
        logger_level: str,
    ) -> LoggerPort:
        return logger_factory(
            pipeline=logger_pipeline,
            run_id=logger_run_id,
            log_level=logger_level,
            json_format=True,
        )

    return bootstrap_logger


def _resolve_tracer_port(
    *,
    tracer_settings: Settings,
    tracer_factory: Callable[[str], TracingPort] | None,
    noop_tracing_factory: Callable[[], TracingPort] | None,
) -> TracingPort:
    """Resolve tracing port using explicit factories or canonical fallbacks."""
    if tracer_factory is None and noop_tracing_factory is None:
        return _bootstrap_tracer_port_impl(
            settings=tracer_settings,
            service_name="bioetl",
        )
    if tracer_settings.observability.tracing_enabled and tracer_factory is not None:
        return tracer_factory("bioetl")
    if noop_tracing_factory is not None:
        return noop_tracing_factory()
    return resolve_tracing_port(tracer=None, settings=tracer_settings)


def _build_tracer_bootstrapper(
    *,
    tracer_factory: Callable[[str], TracingPort] | None,
    noop_tracing_factory: Callable[[], TracingPort] | None,
) -> Callable[[Settings], TracingPort]:
    """Build tracer bootstrapper closure for canonical observability bundle."""

    def bootstrap_tracer(tracer_settings: Settings) -> TracingPort:
        return _resolve_tracer_port(
            tracer_settings=tracer_settings,
            tracer_factory=tracer_factory,
            noop_tracing_factory=noop_tracing_factory,
        )

    return bootstrap_tracer


def _resolve_metrics_port(
    *,
    metrics_settings: Settings,
    metrics_factory: Callable[[], MetricsPort] | None,
    noop_metrics_factory: Callable[..., MetricsPort] | None,
) -> MetricsPort:
    """Resolve metrics port using explicit factories or canonical fallbacks."""
    if metrics_factory is None and noop_metrics_factory is None:
        return _bootstrap_metrics_port_impl(
            settings=metrics_settings,
        )
    if metrics_settings.observability.metrics_enabled and metrics_factory is not None:
        return metrics_factory()
    if noop_metrics_factory is not None:
        return noop_metrics_factory(warn_on_use=False)
    return resolve_metrics_port(metrics=None, settings=metrics_settings)


def _build_metrics_bootstrapper(
    *,
    metrics_factory: Callable[[], MetricsPort] | None,
    noop_metrics_factory: Callable[..., MetricsPort] | None,
) -> Callable[[Settings], MetricsPort]:
    """Build metrics bootstrapper closure for canonical observability bundle."""

    def bootstrap_metrics(metrics_settings: Settings) -> MetricsPort:
        return _resolve_metrics_port(
            metrics_settings=metrics_settings,
            metrics_factory=metrics_factory,
            noop_metrics_factory=noop_metrics_factory,
        )

    return bootstrap_metrics


def _build_dq_monitor_bootstrapper(
    *,
    dq_monitor_factory: Callable[..., DQMonitorPort],
    noop_logger_factory: Callable[[], LoggerPort],
) -> Callable[[Settings, LoggerPort], DQMonitorPort]:
    """Build DQ monitor bootstrapper closure for canonical observability bundle."""

    def bootstrap_dq_monitor(
        dq_settings: Settings,
        dq_logger: LoggerPort,
    ) -> DQMonitorPort:
        return _bootstrap_dq_monitor_port_impl(
            settings=dq_settings,
            logger=dq_logger,
            monitor_factory=dq_monitor_factory,
            noop_logger_factory=noop_logger_factory,
        )

    return bootstrap_dq_monitor


def build_observability_bundle(
    *,
    pipeline: str,
    run_id: RunID,
    settings: Settings,
    log_level: str = "INFO",
    logger_factory: Callable[..., LoggerPort] = UnifiedLogger,
    tracer_factory: Callable[[str], TracingPort] | None = None,
    metrics_factory: Callable[[], MetricsPort] | None = None,
    noop_tracing_factory: Callable[[], TracingPort] | None = None,
    noop_metrics_factory: Callable[..., MetricsPort] | None = None,
    dq_monitor_factory: Callable[..., DQMonitorPort] = DataQualityMonitorService,
    noop_logger_factory: Callable[[], LoggerPort] = NoOpLogger,
) -> ObservabilityBundle:
    """Build observability bundle via the canonical bootstrap implementation."""

    return bootstrap_observability_bundle_impl(
        pipeline=pipeline,
        run_id=run_id,
        settings=settings,
        log_level=log_level,
        logger_bootstrapper=_build_logger_bootstrapper(logger_factory),
        tracer_bootstrapper=_build_tracer_bootstrapper(
            tracer_factory=tracer_factory,
            noop_tracing_factory=noop_tracing_factory,
        ),
        metrics_bootstrapper=_build_metrics_bootstrapper(
            metrics_factory=metrics_factory,
            noop_metrics_factory=noop_metrics_factory,
        ),
        dq_monitor_bootstrapper=_build_dq_monitor_bootstrapper(
            dq_monitor_factory=dq_monitor_factory,
            noop_logger_factory=noop_logger_factory,
        ),
        preflight_validator=validate_observability_preflight_impl,
    )

================================================================================
File: run_manifest_builder.py
Path: runtime_builders\run_manifest_builder.py
================================================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.run_ledger_service import (
    RunLedgerService,
)
from bioetl.application.services.control_plane.run_manifest_service import (
    RunManifestCreateSpec,
    RunManifestService,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    ManifestControlPlaneRefs as _ManifestControlPlaneRefs,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    build_launch_context_snapshot as _build_launch_context_snapshot,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    build_planned_artifacts as _build_planned_artifacts,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    build_run_source_refs as _build_run_source_refs,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    control_plane_root as _control_plane_root,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    create_control_plane_refs as _create_control_plane_refs,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    resolve_contract_identity as _resolve_contract_identity,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    resolve_provider_entity as _resolve_provider_entity,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    resolve_replay_capability as _resolve_replay_capability,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    resolve_replay_parentage as _resolve_replay_parentage,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    resolve_run_context_values as _resolve_run_context_values,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    to_serializable_mapping as _to_serializable_mapping,
)
from bioetl.composition.services.versioning import (
    get_git_commit,
    get_pipeline_version,
)
from bioetl.domain.control_plane import ReplayCapability
from bioetl.infrastructure.control_plane import FileRunManifestStore

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext


def _create_ledger_service(
    inputs: RunnerInputs,
    ctx: PipelineRunContext,
) -> RunLedgerService | None:
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.infrastructure.control_plane import FileRunLedgerStore

    return RunLedgerService(
        ledger_port=FileRunLedgerStore(
            base_path=_control_plane_root(inputs.settings, "run_ledger"),
            metrics=inputs.observability.metrics,
        ),
        manifest_id="pending",
        run_id=ctx.run_id,
    )


def _build_manifest_create_request(
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
    run_type_value: str,
    execution_context_value: str,
    effective_config_hash: str,
    contract_ref: str,
    contract_version: str | None,
    contract_schema_hash: str | None,
    dq_policy_ref: str | None,
    rule_bundle_version: str | None,
    dq_contract_compatibility_hash: str,
    effective_config_artifact_id: str,
) -> RunManifestCreateSpec:
    yaml_config = inputs.yaml_config
    source_refs = _build_run_source_refs(
        ctx=ctx,
        cached_bronze=inputs.cached_bronze,
        settings=inputs.settings,
        provider=provider,
        entity=entity,
    )
    replay_of_run_id, replay_of_manifest_id = _resolve_replay_parentage(
        ctx=ctx,
        runtime_config=inputs.runtime_config,
    )
    control_plane = getattr(
        getattr(inputs.settings, "pipeline", None), "control_plane", None
    )
    required_persistence_profile = str(
        getattr(
            control_plane,
            "required_persistence_profile",
            "degraded_observable",
        )
    )
    request = RunManifestCreateSpec(
        run_id=ctx.run_id,
        run_type=getattr(ctx, "run_type", "incremental"),
        pipeline_name=ctx.pipeline_name,
        provider=provider,
        entity=entity,
        launch_context=_build_launch_context_snapshot(
            ctx,
            run_type_value=run_type_value,
            execution_context_value=execution_context_value,
            required_persistence_profile=required_persistence_profile,
        ),
        runtime_config=_to_serializable_mapping(inputs.runtime_config),
        resolved_config=_to_serializable_mapping(yaml_config),
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        source_refs=source_refs,
        planned_artifacts=_build_planned_artifacts(
            settings=inputs.settings,
            provider=provider,
            entity=entity,
        ),
        pipeline_version=get_pipeline_version(yaml_config),
        git_commit=get_git_commit(),
        config_hash=effective_config_hash,
        contract_ref=contract_ref,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        replay_capability=_resolve_replay_capability(
            source_refs=source_refs,
            resume_requested=bool(getattr(ctx, "resume", False)),
        ),
    )
    _validate_required_runtime_persistence_profile(
        request=request,
        required_persistence_profile=required_persistence_profile,
    )
    return request


def _validate_required_runtime_persistence_profile(
    *,
    request: RunManifestCreateSpec,
    required_persistence_profile: str,
) -> None:
    if required_persistence_profile not in {"replay_ready", "forensic_grade"}:
        return
    if request.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED:
        raise RuntimeError(
            "Pipeline execution cannot satisfy required persistence profile "
            f"'{required_persistence_profile}' because immutable input snapshots "
            "and exact replay capability are not available for this run"
        )


def create_run_manifest(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    ledger_enabled: bool,
    effective_config_artifact_id: str,
    effective_config_hash: str,
    dq_contract_compatibility_hash: str,
) -> tuple[_ManifestControlPlaneRefs, RunLedgerService | None]:
    yaml_config = inputs.yaml_config
    run_type_value, execution_context_value = _resolve_run_context_values(ctx)
    provider, entity = _resolve_provider_entity(
        pipeline_name=ctx.pipeline_name,
        yaml_config=yaml_config,
    )
    (
        contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    ) = _resolve_contract_identity(provider=provider, entity=entity)
    manifest_store = FileRunManifestStore(
        base_path=_control_plane_root(inputs.settings, "run_manifest"),
        metrics=inputs.observability.metrics,
    )
    ledger_service: RunLedgerService | None = None
    if ledger_enabled:
        ledger_service = _create_ledger_service(inputs, ctx)
    manifest_create_request = _build_manifest_create_request(
        ctx,
        inputs,
        provider,
        entity,
        run_type_value,
        execution_context_value,
        effective_config_hash,
        contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
        dq_contract_compatibility_hash,
        effective_config_artifact_id,
    )

    manifest = RunManifestService(manifest_port=manifest_store).create_manifest(
        manifest_create_request
    )
    if ledger_service is not None:
        ledger_service.manifest_id = manifest.manifest_id
        ledger_service.record_manifest_created(manifest)
    control_plane_refs = _create_control_plane_refs(
        manifest.manifest_id,
        effective_config_hash,
        dq_contract_compatibility_hash,
        effective_config_artifact_id,
        contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    )

    return control_plane_refs, ledger_service

================================================================================
File: run_manifest_support.py
Path: runtime_builders\run_manifest_support.py
================================================================================
"""Public seam for control-plane manifest helper functions."""

from __future__ import annotations

from bioetl.composition.runtime_builders._run_manifest_support import (
    ManifestControlPlaneRefs,
    build_launch_context_snapshot,
    build_planned_artifacts,
    build_run_source_refs,
    control_plane_root,
    create_control_plane_refs,
    normalize_snapshot,
    resolve_contract_identity,
    resolve_provider_entity,
    resolve_replay_capability,
    resolve_run_context_values,
    to_serializable_mapping,
)

__all__ = [
    "ManifestControlPlaneRefs",
    "build_launch_context_snapshot",
    "build_planned_artifacts",
    "build_run_source_refs",
    "control_plane_root",
    "create_control_plane_refs",
    "normalize_snapshot",
    "resolve_contract_identity",
    "resolve_provider_entity",
    "resolve_replay_capability",
    "resolve_run_context_values",
    "to_serializable_mapping",
]

================================================================================
File: runner_builder.py
Path: runtime_builders\runner_builder.py
================================================================================
"""Leaf builder for runtime pipeline runner construction."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.application.services.control_plane.run_ledger_service import (
    RunLedgerService,
)
from bioetl.composition import PipelineRegistry, create_registry
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.runtime_builders._runner_builder_support import (
    bind_manifest_logger_context as _bind_manifest_logger_context,
)
from bioetl.composition.runtime_builders._runner_builder_support import (
    resolve_control_plane_flags as _resolve_control_plane_flags,
)
from bioetl.composition.runtime_builders.config_access import (
    get_settings,
    load_pipeline_config,
    load_source_config,
)
from bioetl.composition.runtime_builders.control_plane import (
    attach_manifest_id,
    create_run_manifest_with_effective_config,
)
from bioetl.composition.runtime_builders.inputs_resolver import (
    ResolvedVacuumSettings,
    assemble_cached_bronze_context,
    assemble_filter_config,
    assemble_runtime_config,
    assemble_vacuum_settings,
    prepare_runner_inputs,
)
from bioetl.composition.runtime_builders.inputs_resolver import (
    RunnerInputs as _RunnerInputs,
)
from bioetl.composition.runtime_builders.ledger_collaborator import (
    attach_control_plane_collaborators,
)
from bioetl.composition.runtime_builders.observability_builder import (
    build_observability_bundle,
)
from bioetl.domain.config import RuntimeConfig

if TYPE_CHECKING:
    from bioetl.domain.context import (
        CachedBronzeContext,
        PipelineRunContext,
    )
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import (
        ExecutionObservabilityPort,
        PipelineFactoryPort,
        SettingsPort,
    )
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        PipelineYamlConfig,
    )


__all__ = ["build_pipeline_runner"]


class PipelineRunnerProtocol(Protocol):
    """Minimal runner contract returned by the runtime builder."""

    services: object

    def attach_run_ledger_service(self, service: RunLedgerService) -> None:
        """Attach the run-ledger collaborator."""
        ...


def _initialize_registry(
    *,
    registry: PipelineRegistry | None,
    create_registry_fn: Callable[[], PipelineRegistry],
    ensure_providers_loaded_fn: Callable[[], None],
    register_all_pipelines_fn: Callable[..., None],
) -> PipelineRegistry:
    """Initialize provider/pipeline registry with optional explicit registry."""
    effective_registry = registry if registry is not None else create_registry_fn()
    ensure_providers_loaded_fn()
    register_all_pipelines_fn(registry=effective_registry)
    return effective_registry


def _create_runner_from_factory(
    *,
    factory: PipelineFactoryPort,
    ctx: PipelineRunContext,
    inputs: _RunnerInputs,
) -> PipelineRunnerProtocol:
    return cast(
        "PipelineRunnerProtocol",
        factory.create_runner(
            run_id=ctx.run_id,
            runtime=inputs.runtime_config,
            settings=cast("SettingsPort", inputs.settings),
            observability=cast(
                "ExecutionObservabilityPort",
                inputs.observability,
            ),
            manifest_id=getattr(ctx, "manifest_id", None),
            config_hash=getattr(ctx, "config_hash", None),
            dq_contract_compatibility_hash=getattr(
                ctx, "dq_contract_compatibility_hash", None
            ),
            effective_config_artifact_id=getattr(
                ctx, "effective_config_artifact_id", None
            ),
            filter_config=inputs.filter_config,
            config=inputs.yaml_config,
            cached_bronze=inputs.cached_bronze,
        ),
    )


def _resolve_optional_functions(
    build_observability_bundle_fn: Callable[..., ObservabilityBundle] | None,
    assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings] | None,
    assemble_runtime_config_fn: Callable[..., RuntimeConfig] | None,
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None] | None,
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ]
    | None,
) -> tuple[
    Callable[..., ObservabilityBundle],
    Callable[..., ResolvedVacuumSettings],
    Callable[..., RuntimeConfig],
    Callable[..., InputFilterConfig | None],
    Callable[[PipelineRunContext], CachedBronzeContext],
]:
    """Resolve optional function parameters to their implementations."""
    return (
        build_observability_bundle
        if build_observability_bundle_fn is None
        else build_observability_bundle_fn,
        assemble_vacuum_settings
        if assemble_vacuum_settings_fn is None
        else assemble_vacuum_settings_fn,
        assemble_runtime_config
        if assemble_runtime_config_fn is None
        else assemble_runtime_config_fn,
        assemble_filter_config
        if assemble_filter_config_fn is None
        else assemble_filter_config_fn,
        assemble_cached_bronze_context
        if assemble_cached_bronze_context_fn is None
        else assemble_cached_bronze_context_fn,
    )


def _prepare_runner_inputs_with_resolved_functions(
    ctx: PipelineRunContext,
    get_settings_fn: Callable[[], Settings],
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
    load_source_config_fn: Callable[[], object],
    resolved_functions: tuple[
        Callable[..., ObservabilityBundle],
        Callable[..., ResolvedVacuumSettings],
        Callable[..., RuntimeConfig],
        Callable[..., InputFilterConfig | None],
        Callable[[PipelineRunContext], CachedBronzeContext],
    ],
) -> _RunnerInputs:
    """Prepare runner inputs using resolved function implementations."""
    (
        build_obs_bundle,
        assemble_vacuum,
        assemble_runtime,
        assemble_filter,
        assemble_cached_bronze,
    ) = resolved_functions
    return prepare_runner_inputs(
        ctx=ctx,
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        build_observability_bundle_fn=build_obs_bundle,
        assemble_vacuum_settings_fn=assemble_vacuum,
        assemble_runtime_config_fn=assemble_runtime,
        assemble_filter_config_fn=assemble_filter,
        assemble_cached_bronze_context_fn=assemble_cached_bronze,
        load_source_config_fn=load_source_config_fn,
    )


def _handle_control_plane_setup(
    ctx: PipelineRunContext,
    inputs: _RunnerInputs,
) -> tuple[PipelineRunContext, _RunnerInputs, RunLedgerService | None]:
    """Handle control plane setup including manifest and ledger services."""
    manifest_enabled, ledger_enabled = _resolve_control_plane_flags(
        inputs.settings,
        yaml_config=inputs.yaml_config,
        skip_gold=bool(getattr(ctx, "skip_gold", False)),
    )
    run_ledger_service: RunLedgerService | None = None

    if manifest_enabled:
        control_plane_refs, run_ledger_service = (
            create_run_manifest_with_effective_config(
                ctx=ctx,
                inputs=inputs,
                ledger_enabled=ledger_enabled,
            )
        )
        ctx = attach_manifest_id(
            ctx,
            control_plane_refs.manifest_id,
            config_hash=control_plane_refs.config_hash,
            dq_contract_compatibility_hash=control_plane_refs.dq_contract_compatibility_hash,
            effective_config_artifact_id=control_plane_refs.effective_config_artifact_id,
            contract_ref=control_plane_refs.contract_ref,
            contract_version=control_plane_refs.contract_version,
            contract_schema_hash=control_plane_refs.contract_schema_hash,
            dq_policy_ref=control_plane_refs.dq_policy_ref,
            rule_bundle_version=control_plane_refs.rule_bundle_version,
        )
        inputs = _bind_manifest_logger_context(
            inputs,
            control_plane_refs.manifest_id,
        )

    return ctx, inputs, run_ledger_service


def build_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
    *,
    create_registry_fn: Callable[[], PipelineRegistry] = create_registry,
    ensure_providers_loaded_fn: Callable[[], None] = ensure_providers_loaded,
    register_all_pipelines_fn: Callable[..., None] = register_all_pipelines,
    get_settings_fn: Callable[[], Settings] = get_settings,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] = load_pipeline_config,
    load_source_config_fn: Callable[..., object] = load_source_config,
    build_observability_bundle_fn: Callable[..., ObservabilityBundle] | None = None,
    assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings] | None = None,
    assemble_runtime_config_fn: Callable[..., RuntimeConfig] | None = None,
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None] | None = None,
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ]
    | None = None,
) -> PipelineRunnerProtocol:
    """Assemble and return a fully configured ``PipelineRunner``.

    Args:
        ctx: Pipeline run context containing pipeline name, run type, and execution options.
        registry: Optional PipelineRegistry for test isolation; creates a fresh
            runtime registry when None.
        create_registry_fn: Callable returning a fresh PipelineRegistry instance.
        ensure_providers_loaded_fn: Callable ensuring provider adapters are loaded.
        register_all_pipelines_fn: Callable registering all pipeline factories.
        get_settings_fn: Callable returning global application Settings.
        load_pipeline_config_fn: Callable loading PipelineYamlConfig by pipeline name.
        build_observability_bundle_fn: Optional callable returning an ObservabilityBundle.
            Uses the canonical observability builder when omitted.
        assemble_vacuum_settings_fn: Optional callable merging CLI and YAML vacuum
            settings. Uses the canonical runtime input resolver when omitted.
        assemble_runtime_config_fn: Optional callable building RuntimeConfig from
            context. Uses the canonical runtime input resolver when omitted.
        assemble_filter_config_fn: Optional callable building InputFilterConfig from
            YAML and CLI. Uses the canonical runtime input resolver when omitted.
        assemble_cached_bronze_context_fn: Optional callable resolving cached bronze
            context. Uses the canonical runtime input resolver when omitted.

    Returns:
        Fully configured PipelineRunner ready for execution.
    """
    # Initialize registry
    effective_registry = _initialize_registry(
        registry=registry,
        create_registry_fn=create_registry_fn,
        ensure_providers_loaded_fn=ensure_providers_loaded_fn,
        register_all_pipelines_fn=register_all_pipelines_fn,
    )

    # Resolve optional functions
    resolved_functions = _resolve_optional_functions(
        build_observability_bundle_fn,
        assemble_vacuum_settings_fn,
        assemble_runtime_config_fn,
        assemble_filter_config_fn,
        assemble_cached_bronze_context_fn,
    )

    # Prepare runner inputs
    inputs = _prepare_runner_inputs_with_resolved_functions(
        ctx=ctx,
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        load_source_config_fn=load_source_config_fn,
        resolved_functions=resolved_functions,
    )

    # Handle control plane setup
    ctx, inputs, run_ledger_service = _handle_control_plane_setup(ctx, inputs)

    # Create and configure runner
    runner = _create_runner_from_factory(
        factory=effective_registry.get(ctx.pipeline_name).factory,
        ctx=ctx,
        inputs=inputs,
    )

    # Attach ledger service if available
    if run_ledger_service is not None:
        attach_control_plane_collaborators(runner, run_ledger_service)

    return runner

================================================================================
File: runner_builder_support.py
Path: runtime_builders\runner_builder_support.py
================================================================================
"""Public seam for runtime runner-builder control-plane helpers."""

from __future__ import annotations

from bioetl.composition.runtime_builders._runner_builder_support import (
    bind_manifest_logger_context,
    resolve_control_plane_flags,
    validate_required_persistence_profile,
)

__all__ = [
    "bind_manifest_logger_context",
    "resolve_control_plane_flags",
    "validate_required_persistence_profile",
]

================================================================================
File: __init__.py
Path: services\__init__.py
================================================================================
"""Composition services for cross-cutting concerns.

Services in the composition layer coordinate between layers and build
complex objects. Unlike application services, these do not contain
business logic but rather assemble components.

Services:
- MetadataCoordinator: Centralized metadata creation for Medallion layers
- Versioning utilities: Git commit, config hash, pipeline version
"""

from __future__ import annotations

from importlib import import_module

from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_git_commit,
    get_pipeline_version,
)

# Re-export input types from domain.ports for convenience
from bioetl.domain.ports import (
    BronzeMetadataInput,
    GoldMetadataInput,
    SilverMetadataInput,
)

_LAZY_EXPORT_MODULES: dict[str, str] = {
    "MetadataCoordinator": "bioetl.composition._services",
}

__all__ = [
    "BronzeMetadataInput",
    "GoldMetadataInput",
    "MetadataCoordinator",
    "SilverMetadataInput",
    "compute_config_hash",
    "get_git_commit",
    "get_pipeline_version",
]


def __getattr__(name: str) -> object:
    """Resolve compatibility exports lazily to avoid bootstrap import cycles."""
    try:
        module_name = _LAZY_EXPORT_MODULES[name]
    except KeyError as exc:  # pragma: no cover - standard attribute path
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy re-exports for help() and shell introspection."""
    return sorted(set(globals()) | set(__all__))

================================================================================
File: effective_config_serializer.py
Path: services\effective_config_serializer.py
================================================================================
"""Deterministic serialization for EffectiveConfigArtifact with DQ support."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime

from bioetl.domain.control_plane.effective_config_artifact import (
    ConfigResolutionPolicy,
    ConfigSourceRef,
    DQPolicySnapshot,
    EffectiveConfigArtifact,
    EffectiveConfigHashes,
    EffectiveExecutionConfig,
    ResolvedConfigSnapshot,
    RuntimeOverrideSnapshot,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import DQDisposition, DQPolicyRef


def _dataclass_to_dict(value: object) -> JsonDict | None:
    """Convert dataclass instances into JsonDict payloads when possible."""
    if not is_dataclass(value) or isinstance(value, type):
        return None
    return asdict(value)


def _to_jsonable(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, DQDisposition):
        return value.value
    dataclass_value = _dataclass_to_dict(value)
    if dataclass_value is not None:
        return {key: _to_jsonable(raw) for key, raw in dataclass_value.items()}
    if isinstance(value, dict):
        return {str(key): _to_jsonable(raw) for key, raw in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(raw) for raw in value]
    return value


def _stable_hash(value: object) -> str:
    serialized = json.dumps(_to_jsonable(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class EffectiveConfigSerializer:
    """Serializer for EffectiveConfigArtifact with deterministic output."""

    def serialize_artifact(self, artifact: EffectiveConfigArtifact) -> str:
        """Serialize one persisted artifact envelope with semantic + occurrence data."""
        artifact_dict = self._artifact_to_dict(artifact)
        return json.dumps(artifact_dict, sort_keys=True, separators=(",", ":"))

    def serialize_semantic_artifact(self, artifact: EffectiveConfigArtifact) -> str:
        """Serialize only the semantic effective-config payload deterministically."""
        artifact_dict = self._semantic_artifact_to_dict(artifact)
        return json.dumps(artifact_dict, sort_keys=True, separators=(",", ":"))

    def compute_artifact_hashes(
        self,
        artifact: EffectiveConfigArtifact,
    ) -> EffectiveConfigHashes:
        """Compute deterministic section hashes for one artifact."""
        return EffectiveConfigHashes(
            resolved_config_hash=self._compute_section_hash(artifact.resolved_config),
            effective_config_hash=self._compute_section_hash(
                artifact.effective_execution_config
            ),
            source_fingerprint=self._compute_source_fingerprint(artifact.source_refs),
            dq_contract_compatibility_hash=self._compute_dq_compatibility_hash(
                artifact
            ),
        )

    def _compute_section_hash(self, section: object) -> str:
        return _stable_hash(self._normalize_section(section))

    def _compute_source_fingerprint(self, source_refs: list[ConfigSourceRef]) -> str:
        if not source_refs:
            return "no_sources"
        source_data = [
            {
                "type": src.source_type,
                "path": src.source_path,
                "hash": src.source_hash or "no_hash",
            }
            for src in sorted(source_refs, key=lambda item: item.source_path)
        ]
        return _stable_hash(source_data)

    def _compute_dq_compatibility_hash(self, artifact: EffectiveConfigArtifact) -> str:
        if not artifact.dq_policy_refs and not artifact.dq_policy_snapshots:
            return "no_dq_policies"
        dq_data: list[JsonDict] = []
        for policy_ref in artifact.dq_policy_refs:
            dq_data.append(self._dq_policy_ref_to_dict(policy_ref))
        for snapshot in artifact.dq_policy_snapshots:
            dq_data.append(self._dq_policy_snapshot_to_dict(snapshot))
        dq_data.sort(key=lambda item: str(item["contract_ref"]))
        return _stable_hash(dq_data)

    def _artifact_to_dict(self, artifact: EffectiveConfigArtifact) -> JsonDict:
        return {
            "artifact_id": artifact.artifact_id,
            "schema_version": artifact.schema_version,
            "semantic_artifact": self._semantic_artifact_to_dict(artifact),
            "occurrence_envelope": self._occurrence_envelope_to_dict(artifact),
        }

    def _semantic_artifact_to_dict(
        self,
        artifact: EffectiveConfigArtifact,
    ) -> JsonDict:
        return {
            "artifact_id": artifact.artifact_id,
            "schema_version": artifact.schema_version,
            "pipeline_name": artifact.pipeline_name,
            "pipeline_kind": artifact.pipeline_kind,
            "source_refs": [
                self._source_ref_to_dict(src) for src in artifact.source_refs
            ],
            "resolution_policy": self._resolution_policy_to_dict(
                artifact.resolution_policy
            ),
            "resolved_config": self._resolved_config_to_dict(artifact.resolved_config),
            "runtime_overrides": self._runtime_overrides_to_dict(
                artifact.runtime_overrides
            ),
            "effective_execution_config": self._effective_config_to_dict(
                artifact.effective_execution_config
            ),
            "resolved_config_hash": artifact.resolved_config_hash,
            "effective_config_hash": artifact.effective_config_hash,
            "source_fingerprint": artifact.source_fingerprint,
            "contract_refs": artifact.contract_refs,
            "dq_policy_refs": [
                self._dq_policy_ref_to_dict(ref) for ref in artifact.dq_policy_refs
            ],
            "dq_rule_bundle_versions": artifact.dq_rule_bundle_versions,
            "dq_contract_compatibility_hash": artifact.dq_contract_compatibility_hash,
            "dq_policy_snapshots": [
                self._dq_policy_snapshot_to_dict(snapshot)
                for snapshot in artifact.dq_policy_snapshots
            ],
        }

    def _occurrence_envelope_to_dict(
        self,
        artifact: EffectiveConfigArtifact,
    ) -> JsonDict:
        return {
            "created_at": artifact.created_at.isoformat(),
            "resolved_config_timestamp": artifact.resolved_config.timestamp.isoformat(),
            "effective_execution_timestamp": (
                artifact.effective_execution_config.timestamp.isoformat()
            ),
        }

    def _source_ref_to_dict(self, source_ref: ConfigSourceRef) -> JsonDict:
        result: JsonDict = {
            "source_type": source_ref.source_type,
            "source_path": source_ref.source_path,
            "priority": source_ref.priority,
        }
        if source_ref.source_hash:
            result["source_hash"] = source_ref.source_hash
        return result

    def _resolution_policy_to_dict(
        self,
        policy: ConfigResolutionPolicy,
    ) -> JsonDict:
        return {
            "merge_strategy": policy.merge_strategy,
            "default_materialization": policy.default_materialization,
            "strict_validation": policy.strict_validation,
            "allow_runtime_overrides": policy.allow_runtime_overrides,
        }

    def _resolved_config_to_dict(self, config: ResolvedConfigSnapshot) -> JsonDict:
        return {
            "config_type": config.config_type,
            "config_data": self._normalize_config_data(config.config_data),
            "config_hash": config.config_hash,
        }

    def _runtime_overrides_to_dict(
        self,
        overrides: RuntimeOverrideSnapshot,
    ) -> JsonDict:
        result: JsonDict = {
            "cli_overrides": self._normalize_config_data(overrides.cli_overrides),
            "env_overrides": self._normalize_config_data(overrides.env_overrides),
            "runtime_adjustments": self._normalize_config_data(
                overrides.runtime_adjustments
            ),
        }
        if overrides.override_hash:
            result["override_hash"] = overrides.override_hash
        return result

    def _effective_config_to_dict(
        self, config: EffectiveExecutionConfig
    ) -> JsonDict:  # Any: EffectiveExecutionConfig serialization
        return {
            "config_data": self._normalize_config_data(config.config_data),
            "effective_hash": config.effective_hash,
        }

    def _dq_policy_ref_to_dict(self, policy_ref: DQPolicyRef) -> JsonDict:
        return {
            "contract_ref": policy_ref.contract_ref,
            "contract_version": policy_ref.contract_version,
            "rule_bundle_version": policy_ref.rule_bundle_version,
            "policy_hash": policy_ref.policy_hash,
        }

    def _dq_policy_snapshot_to_dict(
        self,
        snapshot: DQPolicySnapshot,
    ) -> JsonDict:  # Any: DQPolicySnapshot serialization
        return {
            "contract_ref": snapshot.contract_ref,
            "contract_version": snapshot.contract_version,
            "rule_bundle_version": snapshot.rule_bundle_version,
            "policy_hash": snapshot.policy_hash,
            "default_disposition": snapshot.default_disposition.value,
            "disposition_overrides": {
                str(key): value.value
                for key, value in snapshot.disposition_overrides.items()
            },
            "strictness_mode": snapshot.strictness_mode,
        }

    def _normalize_config_data(self, data: JsonDict) -> JsonDict:
        normalized: JsonDict = {}
        for key, value in sorted(data.items()):
            normalized[str(key)] = self._normalize_value(value)
        return normalized

    def _normalize_value(self, value: object) -> object:
        if isinstance(value, dict):
            return self._normalize_config_data(value)
        if isinstance(value, (list, tuple)):
            return [self._normalize_value(item) for item in value]
        if isinstance(value, DQDisposition):
            return value.value
        return value

    def _normalize_section(self, section: object) -> JsonDict:
        dataclass_value = _dataclass_to_dict(section)
        if dataclass_value is not None:
            return self._normalize_config_data(dataclass_value)
        if isinstance(section, dict):
            return self._normalize_config_data(section)
        return {"value": self._normalize_value(section)}


def create_effective_config_serializer() -> EffectiveConfigSerializer:
    """Factory function to create EffectiveConfigSerializer instance."""
    return EffectiveConfigSerializer()

================================================================================
File: versioning.py
Path: services\versioning.py
================================================================================
"""Versioning and reproducibility utilities for pipeline metadata.

Provides functions to compute:
- Git commit hash for reproducibility tracking
- Config hash for change detection
- Pipeline version from config or package

These utilities support PipelineMetadata population as per RULES.md §2.3.
"""

from __future__ import annotations

import hashlib
import subprocess
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from typing import TYPE_CHECKING

from bioetl.domain.normalization import serialize_json_canonical

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "compute_config_hash",
    "get_git_commit",
    "get_pipeline_version",
]


@lru_cache(maxsize=1)
def get_git_commit() -> str | None:
    """Get the current git commit hash.

    Returns the short (7-character) git commit hash of HEAD.
    Returns None if:
    - Not in a git repository
    - Git is not installed
    - Any other git error occurs

    Results are cached for the process lifetime since the commit
    doesn't change during execution.

    Returns:
        Short git commit hash (e.g., 'abc1234') or None.

    Example:
        >>> commit = get_git_commit()
        >>> commit  # 'abc1234' or None
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,  # Local git subprocess — 5s is generous
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def _normalize_for_hash(obj: object) -> object:
    """Normalize object for deterministic hashing.

    Converts:
    - Lists to sorted lists (for sets represented as lists)
    - Dicts to sorted key-value pairs
    - None to null string
    - Other values as-is

    Args:
        obj: Object to normalize.

    Returns:
        Normalized object suitable for deterministic JSON serialization.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: _normalize_for_hash(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_normalize_for_hash(item) for item in obj]
    if isinstance(obj, tuple):
        return [_normalize_for_hash(item) for item in obj]
    return obj


def compute_config_hash(
    config: PipelineYamlConfig | dict[str, object],
) -> str:
    """Compute SHA256 hash of pipeline configuration.

    Creates a deterministic hash of the configuration for change detection.
    The hash is computed from a normalized JSON representation to ensure
    consistency regardless of dict ordering or whitespace.

    Args:
        config: Pipeline configuration (PipelineYamlConfig or dict).

    Returns:
        SHA256 hash string (64 characters).

    Example:
        >>> config = load_pipeline_config("chembl_activity")
        >>> hash_value = compute_config_hash(config)
        >>> hash_value  # '3a7bd3e2...'
    """
    # Convert Pydantic model to dict if needed
    if hasattr(config, "model_dump"):
        config_dict = config.model_dump(mode="json", exclude_none=True)
    elif hasattr(config, "dict"):
        # Legacy Pydantic v1 support
        config_dict = config.dict(exclude_none=True)
    else:
        config_dict = dict(config)

    # Normalize for deterministic serialization
    normalized = _normalize_for_hash(config_dict)

    # Reuse the same canonical JSON contract as the run-manifest fingerprint.
    json_str = serialize_json_canonical(normalized)

    # Compute SHA256 hash
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def get_pipeline_version(
    config: PipelineYamlConfig | dict[str, object] | None = None,
) -> str:
    """Get pipeline version from config or fallback to package version.

    Priority:
    1. config.version if available
    2. bioetl package version
    3. "unknown" as last resort

    Args:
        config: Optional pipeline configuration.

    Returns:
        Version string (e.g., '1.0.0' or package version).

    Example:
        >>> version = get_pipeline_version(config)
        >>> version  # '1.0.0'
    """
    # Try to get version from config
    if config is not None:
        # Handle Pydantic model
        if hasattr(config, "version") and config.version:
            return str(config.version)
        # Handle dict
        if isinstance(config, dict) and config.get("version"):
            return str(config["version"])

    # Fallback to bioetl package version
    try:
        return pkg_version("bioetl")
    except (PackageNotFoundError, RuntimeError, ValueError, TypeError):
        return "unknown"

================================================================================
File: services_api.py
Path: services_api.py
================================================================================
"""Public services-oriented composition API."""

from __future__ import annotations

from bioetl.composition._services import (
    cleanup_bronze,
    get_adr_service,
    get_audit_service,
    get_bronze_cleanup_service,
    get_checkpoint_service,
    get_config_service,
    get_contract_migration_service,
    get_export_service,
    get_health_server_dependencies,
    get_health_service,
    get_lineage_service,
    get_lock_service,
    get_metrics_service,
    get_observability_workflow_service,
    get_pipeline_runner_service,
    get_quarantine_port,
    get_quarantine_service,
    get_run_manifest_service,
    get_vacuum_service,
    load_workflow_config,
)

__all__ = [
    "cleanup_bronze",
    "get_adr_service",
    "get_audit_service",
    "get_bronze_cleanup_service",
    "get_checkpoint_service",
    "get_config_service",
    "get_contract_migration_service",
    "get_export_service",
    "get_health_server_dependencies",
    "get_health_service",
    "get_lineage_service",
    "get_lock_service",
    "get_metrics_service",
    "get_observability_workflow_service",
    "get_pipeline_runner_service",
    "get_quarantine_port",
    "get_quarantine_service",
    "get_run_manifest_service",
    "get_vacuum_service",
    "load_workflow_config",
]

================================================================================
File: source_config_access.py
Path: source_config_access.py
================================================================================
"""Composition-facing seam for source configuration access."""

from __future__ import annotations

from bioetl.infrastructure.config.source_config_loader import load_source_config

__all__ = ["load_source_config"]

================================================================================
File: types.py
Path: types.py
================================================================================
"""Public types for composition layer.

This module provides type definitions and re-exports for external annotation needs.
Use these types when you need to annotate variables or function parameters
that work with composition-layer constructs.

For actual runtime imports, use the specific modules:
- ObservabilityBundle: from bioetl.composition.observability
- StorageAdapter: from bioetl.composition.factories.storage.storage_factory
- PipelineRegistry: from bioetl.composition
- create_registry: from bioetl.composition (isolated instance for tests)
- get_default_registry: shared default-registry export from the package root

Typed contexts for bootstrap functions (replacing untyped tuples):
- PipelineCallbacksContext: transform, gold_filter, gold_transform callbacks
- DQConfigsContext: Bronze/Silver/Gold DQ report configurations
- DQOutputPathsContext: DQ report output paths and flat_structure flag
- RateLimitContext: rate and capacity for token bucket
- CircuitBreakerConfig: failure_threshold and recovery_timeout
"""

from __future__ import annotations

from bioetl.composition import (
    PipelineDefinition,
    PipelineRegistry,
    create_registry,
    get_default_registry,
)
from bioetl.composition.bootstrap_contexts import (
    CircuitBreakerConfig,
    DQConfigsContext,
    DQOutputPathsContext,
    PipelineCallbacksContext,
    RateLimitContext,
)
from bioetl.composition.factories.storage import StorageAdapter
from bioetl.composition.observability import ObservabilityBundle

__all__ = [
    "CircuitBreakerConfig",
    "DQConfigsContext",
    "DQOutputPathsContext",
    "ObservabilityBundle",
    "PipelineCallbacksContext",
    "PipelineDefinition",
    "PipelineRegistry",
    "RateLimitContext",
    "StorageAdapter",
    "create_registry",
    "get_default_registry",
]

