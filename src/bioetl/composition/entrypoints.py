"""Entrypoints for BioETL pipeline operations.

Provides high-level functions for running pipelines and managing resources.
These entrypoints are designed to be used by CLI, Prefect, REST APIs, or any
other orchestration layer without direct dependency on bootstrap functions.

The CLI should only import from this module, not from bootstrap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

from bioetl.domain.types import RunID

from bioetl.composition.bootstrap import (
    bootstrap_checkpoint_manager,
    bootstrap_cleanup,
    bootstrap_lifecycle_service,
    bootstrap_pipeline,
    bootstrap_quarantine_manager,
    load_pipeline_config,
)
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.providers.registration import register_all_providers
from bioetl.domain.context import PipelineRunContext
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    from bioetl.application.checkpoint.manager import CheckpointManager
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.quarantine.manager import QuarantineManager
    from bioetl.application.services.cleanup_service import CleanupPreview
    from bioetl.application.services.lifecycle_service import LifecycleService


@dataclass(frozen=True)
class RunOptions:
    """Options for running a pipeline.

    These are the user-facing options that can be set via CLI, Prefect, or REST.
    The entrypoint converts these to internal domain types.

    Attributes:
        run_type: Type of run (incremental, backfill, rebuild). Default: incremental.
        resume: Whether to resume from the last checkpoint.
        limit: Maximum number of records to process.
        input_csv: Path to CSV file with filter IDs.
        filter_column: Column name in CSV containing filter IDs.
        filter_field: API field name to filter by.
        dry_run: Preview mode without execution.
    """

    run_type: str = "incremental"
    resume: bool = False
    limit: int | None = None
    input_csv: str | None = None
    filter_column: str | None = None
    filter_field: str | None = None
    dry_run: bool = False


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


def _ensure_registrations() -> None:
    """Ensure all providers and pipelines are registered.

    This is idempotent and safe to call multiple times.
    """
    register_all_providers()
    register_all_pipelines()


def build_pipeline_context(name: str, options: RunOptions) -> PipelineRunContext:
    """Build a PipelineRunContext from user-facing options.

    Args:
        name: Pipeline name (e.g., 'chembl_activity').
        options: User-facing run options.

    Returns:
        PipelineRunContext ready for bootstrap_pipeline.
    """
    return PipelineRunContext(
        pipeline_name=name,
        run_id=cast(RunID, uuid4()),
        run_type=RunType(options.run_type),
        resume=options.resume,
        limit=options.limit,
        input_csv=options.input_csv,
        filter_column=options.filter_column,
        filter_field=options.filter_field,
        dry_run=options.dry_run,
    )


def create_pipeline_runner(name: str, options: RunOptions) -> PipelineRunner:
    """Create a pipeline runner for the given pipeline and options.

    This is the main entrypoint for pipeline execution. It handles:
    - Registration of providers and pipelines
    - Building the pipeline context
    - Bootstrapping the runner with all dependencies

    Args:
        name: Pipeline name (e.g., 'chembl_activity').
        options: User-facing run options.

    Returns:
        PipelineRunner ready for execution via runner.run().

    Raises:
        ValueError: If pipeline name is unknown or options are invalid.
        FileNotFoundError: If pipeline config file is missing.

    Example:
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> runner = create_pipeline_runner("chembl_activity", options)
        >>> await runner.run()
    """
    _ensure_registrations()
    ctx = build_pipeline_context(name, options)
    return bootstrap_pipeline(ctx)


async def run_pipeline(name: str, options: RunOptions) -> None:
    """Run a pipeline with the given options.

    Convenience function that creates and executes a pipeline runner.
    For more control over execution, use create_pipeline_runner() directly.

    Args:
        name: Pipeline name (e.g., 'chembl_activity').
        options: User-facing run options.

    Raises:
        ValueError: If pipeline name is unknown or options are invalid.
        FileNotFoundError: If pipeline config file is missing.
        PipelineShutdownError: If pipeline was gracefully shut down.

    Example:
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> await run_pipeline("chembl_activity", options)
    """
    runner = create_pipeline_runner(name, options)
    await runner.run()


def get_quarantine_manager(pipeline: str) -> QuarantineManager:
    """Get a quarantine manager for the given pipeline.

    Used for inspecting and managing quarantined (failed) records.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').

    Returns:
        QuarantineManager instance for the pipeline.

    Example:
        >>> manager = get_quarantine_manager("chembl_activity")
        >>> records = await manager.inspect(limit=100)
    """
    _ensure_registrations()
    return bootstrap_quarantine_manager(pipeline)


def get_checkpoint_manager(pipeline: str) -> CheckpointManager:
    """Get a checkpoint manager for the given pipeline.

    Used for listing, loading, and managing pipeline checkpoints.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').

    Returns:
        CheckpointManager instance for the pipeline.

    Example:
        >>> manager = get_checkpoint_manager("chembl_activity")
        >>> checkpoints = await manager.list_all()
    """
    _ensure_registrations()
    return bootstrap_checkpoint_manager(pipeline)


def get_lifecycle_service() -> LifecycleService:
    """Get the lifecycle service for maintenance operations.

    Used for vacuum and archive operations on Delta tables.

    Returns:
        LifecycleService instance.

    Example:
        >>> service = get_lifecycle_service()
        >>> removed = await service.vacuum("chembl.activity", retention_days=7)
    """
    _ensure_registrations()
    return bootstrap_lifecycle_service()


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


async def preview_cleanup(pipeline: str) -> CleanupPreview:
    """Preview what data would be cleared for a pipeline.

    Used for dry-run mode of rebuild/backfill operations.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').

    Returns:
        CleanupPreview with information about what would be cleared.

    Example:
        >>> preview = await preview_cleanup("chembl_activity")
        >>> print(f"Would clear {preview.total_files} files")
    """
    _ensure_registrations()
    config = load_pipeline_config(pipeline)
    cleanup_service = bootstrap_cleanup()
    return await cleanup_service.preview(
        silver_table=config.silver_table,
        gold_table=config.gold_table,
    )


async def inspect_quarantine(pipeline: str, limit: int = 100) -> list[dict[str, Any]]:
    """Inspect quarantined records for a pipeline.

    Convenience function for quick quarantine inspection.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').
        limit: Maximum number of records to return.

    Returns:
        List of quarantine record dictionaries.

    Example:
        >>> records = await inspect_quarantine("chembl_activity", limit=50)
        >>> for rec in records:
        ...     print(f"Error: {rec['error_code']}")
    """
    manager = get_quarantine_manager(pipeline)
    records: list[dict[str, Any]] = await manager.inspect(limit=limit)
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
        >>> for cp in checkpoints:
        ...     print(f"- {cp}")
    """
    manager = get_checkpoint_manager(pipeline)
    checkpoints: list[str] = await manager.list_all()
    return checkpoints
