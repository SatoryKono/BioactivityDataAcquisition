"""Postrun Service for post-execution operations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.application.services.medallion_types import VacuumResult
from bioetl.domain.ports import ExecutorMetricsPort, NoOpMetrics, NoOpTracing
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.core.postrun.cleanup_orchestrator import (
        PostrunCleanupService,
    )
    from bioetl.application.core.postrun.compact_orchestrator import (
        CompactionResult,
        PostrunCompactService,
    )
    from bioetl.application.core.postrun.dq_report_orchestrator import (
        PostrunDQReportService,
    )
    from bioetl.application.core.postrun.metadata_version_resolver import (
        PostrunMetadataVersionResolver,
    )
    from bioetl.application.services.dq_report_service import (
        DQReportContext,
        DQReportResult,
    )
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        MetricsPort,
        StorageMaintenancePort,
        TracingPort,
    )


def _resolve_report_path(
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


def _get_run_statistics(executor: ExecutorMetricsPort) -> dict[str, object]:
    """Collect optional run-level statistics from executor."""
    get_stats = getattr(executor, "get_run_statistics", None)
    if not callable(get_stats):
        return {}
    raw_stats = get_stats()
    if isinstance(raw_stats, dict):
        return raw_stats
    return {}


def _resolve_legacy_or_service(
    legacy_kwargs: dict[str, object],
    *,
    key: str,
    services: PipelineService | None,
    service_attr: str | None = None,
) -> object | None:
    """Resolve collaborator from legacy kwargs first, then service container."""
    resolved = legacy_kwargs.get(key)
    if resolved is not None:
        return resolved
    if services is None:
        return None
    return cast("object | None", getattr(services, service_attr or key, None))


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
        dq_report_path=_resolve_report_path(dq_reports, layer="silver"),
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
        dq_report_path=_resolve_report_path(dq_reports, layer="gold"),
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


@dataclass(frozen=True, slots=True)
class PostrunResult:
    """Combined result of all post-run operations."""

    dq: DQResult
    dq_reports: DQReportResult | None
    vacuum: VacuumResult
    compaction: CompactionResult


@dataclass(frozen=True, slots=True)
class PostrunDependencyContext:
    """Injected postrun collaborators created by the composition layer."""

    cleanup_orchestrator: PostrunCleanupService
    dq_report_orchestrator: PostrunDQReportService
    metadata_version_resolver: PostrunMetadataVersionResolver
    compact_orchestrator: PostrunCompactService


class PostrunService:
    """Handles post-execution operations."""

    TRACER_NAME = "bioetl.postrun"

    @staticmethod
    def _resolve_collaborators(
        services: PipelineService | None,
        context: PipelineContext,
        legacy_kwargs: dict[str, object],
    ) -> tuple[
        StorageMaintenancePort,
        MetricsPort,
        LoggerPort,
        MetadataCoordinatorPort | None,
        MetadataWriterPort | None,
    ]:
        """Resolve storage/metrics/logger/metadata collaborators."""
        resolved_storage = _resolve_legacy_or_service(
            legacy_kwargs,
            key="storage",
            services=services,
        )
        resolved_logger = _resolve_legacy_or_service(
            legacy_kwargs,
            key="logger",
            services=services,
        )
        if resolved_logger is None:
            resolved_logger = context.logger

        if resolved_storage is None or resolved_logger is None:
            raise AssertionError(
                "PostrunService requires storage and logger (provide services or legacy kwargs)"
            )

        resolved_metrics = _resolve_legacy_or_service(
            legacy_kwargs,
            key="metrics",
            services=services,
        )
        if resolved_metrics is None:
            resolved_metrics = NoOpMetrics()

        resolved_metadata_coordinator = _resolve_legacy_or_service(
            legacy_kwargs,
            key="metadata_coordinator",
            services=services,
        )
        resolved_metadata_writer = _resolve_legacy_or_service(
            legacy_kwargs,
            key="metadata_writer",
            services=services,
        )
        return (
            resolved_storage,  # type: ignore[return-value]
            resolved_metrics,
            resolved_logger,  # type: ignore[return-value]
            resolved_metadata_coordinator,
            resolved_metadata_writer,
        )

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        context: PipelineContext,
        dq_service: DataQualityService,
        lifecycle_service: MedallionLifecycleService,
        dependencies: PostrunDependencyContext | None = None,
        services: PipelineService | None = None,
        tracer: TracingPort | None = None,
        **legacy_kwargs: object,
    ) -> None:
        self._config = config
        self._runtime = runtime
        self._context = context
        self._dq_service = dq_service
        self._lifecycle_service = lifecycle_service
        if dependencies is None:
            raise AssertionError("dependencies must be provided")

        (
            self._storage,
            self._metrics,
            self._logger,
            self._metadata_coordinator,
            self._metadata_writer,
        ) = self._resolve_collaborators(
            services=services,
            context=context,
            legacy_kwargs=legacy_kwargs,
        )
        self._cleanup_orchestrator = dependencies.cleanup_orchestrator
        self._dq_report_orchestrator = dependencies.dq_report_orchestrator
        self._metadata_version_resolver = dependencies.metadata_version_resolver
        self._compact_orchestrator = dependencies.compact_orchestrator
        self._tracer: TracingPort = tracer if tracer is not None else NoOpTracing()

    @contextmanager
    def _postrun_span(self, span_name: str) -> Generator[Span, None, None]:
        """Context manager for OTel span lifecycle."""
        otel_tracer = self._tracer.get_tracer(self.TRACER_NAME)
        with cast(
            "Span",
            otel_tracer.start_as_current_span(
                span_name,
                attributes={
                    "bioetl.pipeline": self._config.pipeline_name or "unknown",
                    "bioetl.provider": self._config.provider,
                    "bioetl.entity_type": self._config.entity_type,
                    "bioetl.run_type": self._runtime.run_type.value,
                },
            ),
        ) as span:
            yield span

    async def run(
        self,
        executor: ExecutorMetricsPort,
        dq_context: DQReportContext | None = None,
    ) -> PostrunResult:
        """Run all post-execution operations.

        Args:
            executor: Provides batch metrics and record counts for DQ evaluation.
            dq_context: Optional context with table paths for DQ report generation.

        Returns:
            PostrunResult with DQ check results, DQ report paths, and vacuum stats.
        """
        with self._postrun_span("postrun.run") as span:
            # Silver compact before DQ so checks see deduplicated data
            compaction = await self.run_silver_compact_if_needed()

            dq_result = await self.run_dq_checks(executor)
            dq_reports = await self._generate_dq_reports(dq_context)
            vacuum_result = await self.run_vacuum_if_enabled()

            # Write final run-level metadata (aggregates all batches)
            if self._metadata_coordinator and self._metadata_writer:
                await self._write_final_metadata(executor, dq_reports)

            result = PostrunResult(
                dq=dq_result,
                dq_reports=dq_reports,
                vacuum=vacuum_result,
                compaction=compaction,
            )
            span.set_attribute("bioetl.dq_status", dq_result.status.value)
            return result

    async def run_dq_checks(self, executor: ExecutorMetricsPort) -> DQResult:
        """Check data quality metrics and report anomalies.

        Args:
            executor: Provides batch metrics and record counts for evaluation.

        Returns:
            DQResult with overall DQ status and per-check results.
        """
        batch_metrics = self._collect_batch_metrics(executor)
        return await self._dq_service.evaluate(batch_metrics)

    async def run_vacuum_if_enabled(self) -> VacuumResult:
        """Run VACUUM on Silver and Gold tables if enabled.

        Returns:
            VacuumResult with file removal counts, or skipped=True if vacuum disabled.
        """
        return await self._lifecycle_service.finalize_run(
            config=self._config,
            runtime=self._runtime,
            metrics=self._metrics,
        )

    async def run_silver_compact_if_needed(self) -> CompactionResult:
        """Deduplicate Silver after append-mode run."""
        return await self._compact_orchestrator.run_if_needed()

    async def cleanup(self, tracer: TracingPort | None) -> None:
        """Cleanup all resources including observability.

        Args:
            tracer: Optional tracing provider to flush and close.
        """
        await self._cleanup_orchestrator.cleanup_tracer(tracer)

    async def _generate_dq_reports(
        self,
        context: DQReportContext | None,
    ) -> DQReportResult | None:
        """Generate DQ reports if enabled."""
        return await self._dq_report_orchestrator.generate_reports(context)

    async def _write_final_metadata(
        self,
        executor: ExecutorMetricsPort,
        dq_reports: DQReportResult | None,
    ) -> None:
        """Write final aggregated metadata for Silver and Gold layers."""
        from datetime import UTC, datetime

        if not self._metadata_coordinator or not self._metadata_writer:
            return

        import asyncio

        stats = _get_run_statistics(executor)
        completed_at = datetime.now(UTC)
        write_coros = [
            coro
            for coro in (
                _build_silver_metadata_write_coro(
                    metadata_coordinator=self._metadata_coordinator,
                    metadata_writer=self._metadata_writer,
                    storage=self._storage,
                    config=self._config,
                    context=self._context,
                    stats=stats,
                    dq_reports=dq_reports,
                    completed_at=completed_at,
                    resolve_delta_version=lambda table_path, layer: self._resolve_delta_version(
                        table_path,
                        layer=layer,
                    ),
                ),
                _build_gold_metadata_write_coro(
                    metadata_coordinator=self._metadata_coordinator,
                    metadata_writer=self._metadata_writer,
                    storage=self._storage,
                    config=self._config,
                    runtime=self._runtime,
                    stats=stats,
                    dq_reports=dq_reports,
                    completed_at=completed_at,
                ),
            )
            if coro is not None
        ]
        if write_coros:
            await asyncio.gather(*write_coros)

    def _collect_batch_metrics(self, executor: ExecutorMetricsPort) -> dict[str, float]:
        """Collect batch metrics from executor."""
        total_records = max(1, executor.records_fetched)
        return {
            "record_count": float(executor.records_fetched),
            "bronze_count": float(executor.records_bronze),
            "silver_count": float(executor.records_silver),
            "gold_count": float(executor.records_gold),
            "quarantined_count": float(executor.records_quarantined),
            "error_rate": executor.records_quarantined / total_records,
            "silver_yield": executor.records_silver / total_records,
            "gold_yield": executor.records_gold / total_records,
        }

    def _resolve_delta_version(
        self, table_path: str, *, layer: Literal["silver", "gold"]
    ) -> int | None:
        """Resolve Delta table version with warning-mode fallback and allowlist."""
        return self._metadata_version_resolver.resolve_delta_version(
            table_path,
            layer=layer,
        )


__all__ = [
    "DQEvaluationStatus",
    "DQResult",
    "ExecutorMetricsPort",
    "PostrunDependencyContext",
    "PostrunResult",
    "PostrunService",
    "VacuumResult",
]
