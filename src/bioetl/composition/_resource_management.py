"""Resource management entrypoints.

Runtime services, maintenance operations (vacuum, archive),
and inspection functions (quarantine, checkpoints).
Split from entrypoints.py per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.composition._json_types import JsonDict
from bioetl.composition._pipeline_execution import (
    ArchiveOptions,
    VacuumOptions,
    _ensure_registrations,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


__all__ = [
    "archive_table",
    "get_checkpoint_runtime_service",
    "get_lifecycle_service",
    "get_quarantine_runtime_service",
    "inspect_quarantine",
    "list_checkpoints",
    "preview_cleanup",
    "vacuum_table",
]


class QuarantineRuntimeServiceProtocol(Protocol):
    """Minimal quarantine runtime-service contract exposed by resource APIs."""

    def inspect(
        self,
        limit: int = 100,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> Awaitable[list[JsonDict]]:
        """Inspect quarantined records."""
        ...

    def get_stats(
        self,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> Awaitable[JsonDict]:
        """Return aggregate quarantine statistics."""
        ...


class CheckpointRuntimeServiceProtocol(Protocol):
    """Minimal checkpoint runtime-service contract exposed by resource APIs."""

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

    @property
    def total_files(self) -> int:
        """Return the number of files affected by the cleanup."""
        ...


class CleanupServiceProtocol(Protocol):
    """Minimal cleanup service contract used by preview entrypoints."""

    def preview(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> Awaitable[CleanupPreviewProtocol]:
        """Preview cleanup impact for the requested tables."""
        ...


def bootstrap_quarantine_runtime_service(pipeline: str) -> object:
    """Resolve the quarantine runtime bootstrap lazily for patch-friendly tests."""
    from bioetl.composition.bootstrap.cli.checkpoint import (
        bootstrap_quarantine_runtime_service as impl,
    )

    return impl(pipeline)


def bootstrap_checkpoint_runtime_service(pipeline: str) -> object:
    """Resolve the checkpoint runtime bootstrap lazily for patch-friendly tests."""
    from bioetl.composition.bootstrap.cli.checkpoint import (
        bootstrap_checkpoint_runtime_service as impl,
    )

    return impl(pipeline)


def bootstrap_lifecycle_service() -> object:
    """Resolve the lifecycle bootstrap lazily for patch-friendly tests."""
    from bioetl.composition.bootstrap.cli.storage import (
        bootstrap_lifecycle_service as impl,
    )

    return impl()


def bootstrap_cleanup_service() -> CleanupServiceProtocol:
    """Resolve the cleanup bootstrap lazily for patch-friendly tests."""
    from bioetl.composition.bootstrap.cli.storage import (
        bootstrap_cleanup_service as impl,
    )

    return impl()


def load_pipeline_config(pipeline: str) -> PipelineYamlConfig:
    """Resolve pipeline config loading lazily for patch-friendly tests."""
    from bioetl.infrastructure.config.pipeline_config_api import (
        load_pipeline_config as impl,
    )

    return impl(pipeline)


def _bootstrap_registered_resource[**P, T](
    bootstrap_fn: Callable[P, T],
    /,
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    """Run registration bootstrap before delegating to a resource builder."""
    _ensure_registrations()
    return bootstrap_fn(*args, **kwargs)


def get_quarantine_runtime_service(pipeline: str) -> QuarantineRuntimeServiceProtocol:
    """Get the quarantine runtime service for the given pipeline.

    Used for inspecting and managing quarantined (failed) records.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').

    Returns:
        QuarantineRuntimeService instance for the pipeline.

    Example:
        >>> service = get_quarantine_runtime_service("chembl_activity")
        >>> records = await service.inspect(limit=100)
    """
    return cast(
        QuarantineRuntimeServiceProtocol,
        _bootstrap_registered_resource(bootstrap_quarantine_runtime_service, pipeline),
    )


def get_checkpoint_runtime_service(pipeline: str) -> CheckpointRuntimeServiceProtocol:
    """Get the checkpoint runtime service for the given pipeline.

    Used for listing, loading, and managing pipeline checkpoints.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').

    Returns:
        CheckpointRuntimeService instance for the pipeline.

    Example:
        >>> service = get_checkpoint_runtime_service("chembl_activity")
        >>> checkpoints = await service.list_all()
    """
    return cast(
        CheckpointRuntimeServiceProtocol,
        _bootstrap_registered_resource(bootstrap_checkpoint_runtime_service, pipeline),
    )


def get_lifecycle_service() -> MedallionLifecycleServiceProtocol:
    """Get the lifecycle service for maintenance operations.

    Used for vacuum and archive operations on Delta tables.

    Returns:
        MedallionLifecycleService instance.

    Example:
        >>> service = get_lifecycle_service()
        >>> removed = await service.vacuum("chembl.activity", retention_days=7)
    """
    return cast(
        MedallionLifecycleServiceProtocol,
        _bootstrap_registered_resource(bootstrap_lifecycle_service),
    )


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
    return await service.vacuum(
        table=table,
        retention_days=options.retention_days,
        dry_run=options.dry_run,
    )


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
    return await service.archive(
        table=table,
        target_path=options.target_path,
        remove_source=options.remove_source,
    )


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
    runtime_service = get_quarantine_runtime_service(pipeline)
    records: list[
        JsonDict  # Any: factory wiring; concrete types resolved at runtime
    ] = await runtime_service.inspect(  # Any: factory wiring; concrete types resolved at runtime
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
    runtime_service = get_checkpoint_runtime_service(pipeline)
    return cast(list[str], await runtime_service.list_all())
