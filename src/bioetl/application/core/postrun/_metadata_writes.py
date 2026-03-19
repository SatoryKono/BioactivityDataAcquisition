"""Private final-metadata write helpers for the postrun service."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from bioetl.application.services.dq_report_service import DQReportResult
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
    return str(path) if path else None


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
    """Build final Silver/Gold metadata write coroutines for the postrun flow."""
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
    """Build coroutine for writing final Silver metadata."""
    from bioetl.domain.ports import SilverMetadataInput

    if not metadata_coordinator or not metadata_writer:
        return None
    silver_table = config.table.silver_table
    if not silver_table:
        return None

    silver_path = storage.get_table_path(silver_table, layer="silver")
    version_after = resolve_delta_version(str(silver_path), "silver")
    silver_input = SilverMetadataInput(
        table_path=str(silver_path),
        primary_keys=list(config.table.primary_keys),
        mode=config.table.silver_write_mode,
        total_records=cast("int | None", stats.get("records_silver")),
        source_batch_ids=cast("list[str] | None", stats.get("source_batch_ids")),
        version_after=version_after,
        dq_report_path=resolve_report_path(dq_reports, layer="silver"),
        started_at=context.started_at,
        completed_at=completed_at,
    )
    silver_metadata = metadata_coordinator.create_silver_metadata(silver_input)
    return metadata_writer.write_silver_metadata(
        str(silver_path),
        silver_metadata,
        provider=config.provider,
        entity=config.entity_type,
    )


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
    """Build coroutine for writing final Gold metadata."""
    from bioetl.domain.ports import GoldMetadataInput

    if not metadata_coordinator or not metadata_writer:
        return None
    if runtime.skip_gold:
        return None
    gold_table = config.table.gold_table
    if not gold_table:
        return None

    if not storage.is_table_initialized(gold_table, layer="gold"):
        return None
    gold_path = Path(storage.get_table_path(gold_table, layer="gold"))
    gold_input = GoldMetadataInput(
        table_path=str(gold_path),
        table_name=gold_table,
        mode=config.table.gold_write_mode,
        total_records=cast("int | None", stats.get("records_gold")),
        dq_report_path=resolve_report_path(dq_reports, layer="gold"),
        completed_at=completed_at,
        gold_schema=config.gold_schema,
    )
    gold_metadata = metadata_coordinator.create_gold_metadata(gold_input)
    return metadata_writer.write_gold_metadata(
        str(gold_path),
        gold_metadata,
        provider=config.provider,
        entity=config.entity_type,
    )
