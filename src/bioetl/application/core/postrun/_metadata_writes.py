"""Private final-metadata write helpers for the postrun service."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from bioetl.application.services.quality.dq_report_service import DQReportResult
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        ExecutorMetricsPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        StorageMaintenancePort,
    )


def resolve_report_path(
    dq_reports: DQReportResult | None,
    *,
    layer: str,
) -> str | None:
    """Resolve report path by layer from optional DQ report result."""
    if dq_reports is None:
        return None
    if layer == "silver":
        path = dq_reports.silver_report_path
    elif layer == "gold":
        path = dq_reports.gold_report_path
    else:
        return None
    if not path:
        return None
    return Path(path).as_posix()


def get_run_statistics(executor: ExecutorMetricsPort) -> dict[str, object]:
    """Collect optional run-level statistics from executor."""
    get_stats = getattr(executor, "get_run_statistics", None)
    if not callable(get_stats):
        return {}
    raw_stats = get_stats()
    if isinstance(raw_stats, dict):
        return raw_stats
    return {}


def build_final_metadata_write_coroutines(
    *,
    metadata_coordinator: MetadataCoordinatorPort | None,
    metadata_writer: MetadataWriterPort | None,
    storage: StorageMaintenancePort,
    config: PipelineConfig,
    runtime: RuntimeConfig,
    context: PipelineContext,
    stats: dict[str, object],
    dq_reports: DQReportResult | None,
    completed_at: datetime,
    resolve_delta_version: Callable[[str, Literal["silver", "gold"]], int | None],
) -> list[Awaitable[object]]:
    """Build final Silver/Gold metadata finalization coroutines for postrun."""
    _ = metadata_coordinator
    return [
        coro
        for coro in (
            _build_silver_metadata_write_coro(
                metadata_coordinator=metadata_coordinator,
                metadata_writer=metadata_writer,
                storage=storage,
                config=config,
                context=context,
                stats=stats,
                dq_reports=dq_reports,
                completed_at=completed_at,
                resolve_delta_version=resolve_delta_version,
            ),
            _build_gold_metadata_write_coro(
                metadata_coordinator=metadata_coordinator,
                metadata_writer=metadata_writer,
                storage=storage,
                config=config,
                runtime=runtime,
                stats=stats,
                dq_reports=dq_reports,
                completed_at=completed_at,
            ),
        )
        if coro is not None
    ]


def _build_silver_metadata_write_coro(
    *,
    metadata_coordinator: MetadataCoordinatorPort | None,
    metadata_writer: MetadataWriterPort | None,
    storage: StorageMaintenancePort,
    config: PipelineConfig,
    context: PipelineContext,
    stats: dict[str, object],
    dq_reports: DQReportResult | None,
    completed_at: datetime,
    resolve_delta_version: Callable[[str, Literal["silver", "gold"]], int | None],
) -> Awaitable[object] | None:
    """Build coroutine for finalizing an existing Silver metadata sidecar."""
    _ = metadata_coordinator, stats
    if not metadata_writer:
        return None
    silver_table = config.table.silver_table
    if not silver_table:
        return None
    if not storage.is_table_initialized(silver_table, layer="silver"):
        return None
    silver_path = Path(storage.get_table_path(silver_table, layer="silver")).as_posix()
    version_after = resolve_delta_version(silver_path, "silver")

    async def _finalize_silver() -> object:
        return await metadata_writer.finalize_silver_metadata(
            silver_path,
            dq_report_path=resolve_report_path(dq_reports, layer="silver"),
            completed_at=completed_at,
            delta_version_after=version_after,
            provider=config.provider,
            entity=config.entity_type,
        )

    return _finalize_silver()


def _build_gold_metadata_write_coro(
    *,
    metadata_coordinator: MetadataCoordinatorPort | None,
    metadata_writer: MetadataWriterPort | None,
    storage: StorageMaintenancePort,
    config: PipelineConfig,
    runtime: RuntimeConfig,
    stats: dict[str, object],
    dq_reports: DQReportResult | None,
    completed_at: datetime,
) -> Awaitable[object] | None:
    """Build coroutine for finalizing an existing Gold metadata sidecar."""
    _ = metadata_coordinator
    _ = stats
    if not metadata_writer:
        return None
    if runtime.skip_gold:
        return None
    gold_table = config.table.gold_table
    if not gold_table:
        return None
    if not storage.is_table_initialized(gold_table, layer="gold"):
        return None
    gold_path = Path(storage.get_table_path(gold_table, layer="gold")).as_posix()

    async def _finalize_gold() -> object:
        return await metadata_writer.finalize_gold_metadata(
            gold_path,
            dq_report_path=resolve_report_path(dq_reports, layer="gold"),
            completed_at=completed_at,
            provider=config.provider,
            entity=config.entity_type,
        )

    return _finalize_gold()
