"""Lifecycle helpers for :mod:`bioetl.application.core.runner`."""

from __future__ import annotations

__all__ = [
    "emit_pipeline_completion",
    "emit_pipeline_start",
    "extract_checkpoint_offset",
    "record_run_failed",
    "record_run_finished",
    "record_run_shutdown",
    "record_run_started",
    "record_stage_completed",
    "record_stage_started",
    "resolve_execution_offset",
]

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.domain.context import current_utc_time
from bioetl.domain.events import PipelineEvent
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointRuntimeService,
    )
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.observability.pipeline_metrics import (
        PipelineMetricsRecorder,
    )
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


class _PipelineRunnerFlowHostProtocol(Protocol):
    _config: PipelineConfig
    _context: PipelineContext
    _runtime: RuntimeConfig
    _executor: BatchExecutor
    _checkpoint_manager: CheckpointRuntimeService
    _services: PipelineService
    _logger: LoggerPort
    _run_ledger_service: RunLedgerService | None

    @property
    def execution_metrics(self) -> dict[str, int]: ...

    @property
    def execution_diagnostics(self) -> JsonDict: ...


def _record_with_ledger_service(
    host: _PipelineRunnerFlowHostProtocol,
    recorder: Callable[[RunLedgerService], object],
) -> None:
    """Run one ledger write only when control-plane wiring is attached."""
    if host._run_ledger_service is None:
        return
    recorder(host._run_ledger_service)


def _record_run_metrics_event(
    host: _PipelineRunnerFlowHostProtocol,
    recorder: Callable[[RunLedgerService, dict[str, int], JsonDict | None], object],
) -> None:
    """Append one run-level ledger entry using the current execution metrics."""
    details = host.execution_diagnostics or None
    _record_with_ledger_service(
        host,
        lambda ledger_service: recorder(
            ledger_service,
            host.execution_metrics,
            details,
        ),
    )


async def resolve_execution_offset(
    host: _PipelineRunnerFlowHostProtocol,
    load_checkpoint: Callable[
        [CheckpointRuntimeService],
        Awaitable[CheckpointMetadata | dict[str, object] | None],
    ],
) -> int | None:
    """Resolve executor start offset from runtime overrides or checkpoint."""
    start_offset = getattr(host._runtime, "start_offset", None)
    if start_offset is not None:
        host._logger.info(
            "Using manual start offset",
            offset=start_offset,
        )
        return int(start_offset)

    checkpoint_meta = await load_checkpoint(host._checkpoint_manager)
    return extract_checkpoint_offset(checkpoint_meta)


def extract_checkpoint_offset(
    checkpoint_meta: CheckpointMetadata | dict[str, object] | None,
) -> int | None:
    """Extract persisted record offset from checkpoint metadata."""
    if checkpoint_meta is None:
        return None
    if hasattr(checkpoint_meta, "records_processed"):
        return int(cast("CheckpointMetadata", checkpoint_meta).records_processed)
    raw_records = checkpoint_meta.get("records_processed")
    return raw_records if isinstance(raw_records, int) else None


def emit_pipeline_start(host: _PipelineRunnerFlowHostProtocol) -> None:
    """Emit the pipeline start event."""
    host._logger.info(
        PipelineEvent.START,
        pipeline=host._config.pipeline_name,
        stage="startup",
        run_type=host._runtime.run_type.value,
    )


def emit_pipeline_completion(host: _PipelineRunnerFlowHostProtocol) -> None:
    """Emit the pipeline completion event."""
    host._logger.debug(
        PipelineEvent.COMPLETE,
        records_fetched=host._executor.records_fetched,
    )


def record_run_started(host: _PipelineRunnerFlowHostProtocol) -> None:
    """Append run_started ledger entry when control-plane ledger is attached."""
    _record_with_ledger_service(
        host,
        lambda ledger_service: ledger_service.record_run_started(),
    )


def record_stage_started(
    host: _PipelineRunnerFlowHostProtocol,
    stage: str,
) -> None:
    """Append stage_started ledger entry."""
    _record_with_ledger_service(
        host,
        lambda ledger_service: ledger_service.record_stage_started(stage=stage),
    )


def record_stage_completed(
    host: _PipelineRunnerFlowHostProtocol,
    stage: str,
) -> None:
    """Append stage_completed ledger entry."""
    _record_with_ledger_service(
        host,
        lambda ledger_service: ledger_service.record_stage_completed(
            stage=stage,
            metrics_snapshot=host.execution_metrics,
        ),
    )


def record_run_finished(host: _PipelineRunnerFlowHostProtocol) -> None:
    """Append successful completion ledger entry."""
    _record_output_ready(host)
    _record_flow_invariants(host)

    def _record_finished(
        ledger_service: RunLedgerService,
        metrics_snapshot: dict[str, int],
        details: JsonDict | None,
    ) -> object:
        if details is None:
            return ledger_service.record_run_finished(
                metrics_snapshot=metrics_snapshot,
            )
        return ledger_service.record_run_finished(
            metrics_snapshot=metrics_snapshot,
            details=details,
        )

    _record_run_metrics_event(host, _record_finished)


def _record_output_ready(host: _PipelineRunnerFlowHostProtocol) -> None:
    """Project the terminal output-ready count into the canonical stage model."""
    from bioetl.application.observability.pipeline_metrics import (
        PipelineMetricsRecorder,
    )

    output_count = max(
        0,
        host.execution_metrics.get("records_gold", 0),
        host.execution_metrics.get("records_silver", 0),
        host.execution_metrics.get("records_bronze", 0),
    )
    if output_count <= 0:
        return
    PipelineMetricsRecorder(
        host._services.metrics,
        host._config.pipeline_name,
    ).record_stage_records(
        run_type=host._runtime.run_type.value,
        stage="output",
        outcome="ready",
        count=output_count,
    )


def record_run_shutdown(host: _PipelineRunnerFlowHostProtocol) -> None:
    """Append graceful shutdown ledger entry."""
    _record_flow_invariants(host)
    _record_run_metrics_event(
        host,
        lambda ledger_service, metrics_snapshot, details: (
            ledger_service.record_run_shutdown(
                metrics_snapshot=metrics_snapshot,
                details=details,
            )
        ),
    )


def record_run_failed(
    host: _PipelineRunnerFlowHostProtocol,
    exc: Exception,
) -> None:
    """Append failed completion ledger entry."""
    _record_flow_invariants(host)
    _record_run_metrics_event(
        host,
        lambda ledger_service, metrics_snapshot, details: (
            ledger_service.record_run_exception(
                error=exc,
                metrics_snapshot=metrics_snapshot,
                details=details,
            )
        ),
    )


def _record_flow_invariants(host: _PipelineRunnerFlowHostProtocol) -> None:
    """Project terminal record-flow invariants and backlog gauges."""
    from bioetl.application.observability.pipeline_metrics import (
        PipelineMetricsRecorder,
    )

    pipeline_metrics = PipelineMetricsRecorder(
        host._services.metrics,
        host._config.pipeline_name,
    )
    run_type = host._runtime.run_type.value
    metrics = host.execution_metrics

    fetched = max(0, int(metrics.get("records_fetched", 0)))
    bronze = max(0, int(metrics.get("records_bronze", 0)))
    silver = max(0, int(metrics.get("records_silver", 0)))
    gold = max(0, int(metrics.get("records_gold", 0)))
    quarantined = max(0, int(metrics.get("records_quarantined", 0)))
    filtered_out = max(0, int(metrics.get("records_filtered_out", 0)))

    _record_count_flow_invariants(
        host=host,
        pipeline_metrics=pipeline_metrics,
        run_type=run_type,
        fetched=fetched,
        bronze=bronze,
        silver=silver,
        gold=gold,
        quarantined=quarantined,
        filtered_out=filtered_out,
    )

    config = host._config
    scd_config = getattr(config, "scd_config", None)
    table = getattr(config, "table", None)
    gold_write_mode = getattr(table, "gold_write_mode", None)
    gold_schema = getattr(config, "gold_schema", None)

    gold_expected = scd_config is not None or (
        gold_write_mode is not None and gold_schema is not None
    )
    pipeline_metrics.record_pipeline_stage_expected(stage="bronze", expected=True)
    pipeline_metrics.record_pipeline_stage_expected(stage="silver", expected=True)
    pipeline_metrics.record_pipeline_stage_expected(
        stage="gold", expected=gold_expected
    )

    pipeline_metrics.record_stage_backlog(
        run_type=run_type,
        stage="ingestion",
        count=max(fetched - bronze, 0),
    )
    pipeline_metrics.record_stage_backlog(
        run_type=run_type,
        stage="validation",
        count=quarantined,
    )
    pipeline_metrics.record_stage_backlog(
        run_type=run_type,
        stage="output",
        count=max(silver - gold, 0),
    )


def _record_count_flow_invariants(
    *,
    host: _PipelineRunnerFlowHostProtocol,
    pipeline_metrics: object,
    run_type: str,
    fetched: int,
    bronze: int,
    silver: int,
    gold: int,
    quarantined: int,
    filtered_out: int,
) -> None:
    """Record record-count invariant results for one completed run."""
    typed_pipeline_metrics = cast("PipelineMetricsRecorder", pipeline_metrics)

    fetched_equals_bronze = "unknown"
    if fetched > 0 or bronze > 0:
        fetched_equals_bronze = "passed" if fetched == bronze else "violated"
    typed_pipeline_metrics.record_flow_invariant(
        run_type=run_type,
        invariant="fetched_equals_bronze",
        status=fetched_equals_bronze,
    )

    bronze_partitioned = "unknown"
    partition_total = silver + quarantined + filtered_out
    if bronze > 0 or partition_total > 0:
        bronze_partitioned = "passed" if bronze == partition_total else "violated"
    typed_pipeline_metrics.record_flow_invariant(
        run_type=run_type,
        invariant="bronze_partitioned",
        status=bronze_partitioned,
    )

    silver_gold_monotonic = "unknown"
    if silver > 0 or gold > 0:
        silver_gold_monotonic = "passed" if silver >= gold else "violated"
    typed_pipeline_metrics.record_flow_invariant(
        run_type=run_type,
        invariant="silver_gold_monotonic",
        status=silver_gold_monotonic,
    )

    _record_stage_lag_gauges(
        host=host,
        pipeline_metrics=pipeline_metrics,
        run_type=run_type,
        ingestion_backlog=max(fetched - bronze, 0),
        validation_backlog=quarantined,
        output_backlog=max(silver - gold, 0),
    )


def _record_stage_lag_gauges(
    *,
    host: _PipelineRunnerFlowHostProtocol,
    pipeline_metrics: object,
    run_type: str,
    ingestion_backlog: int,
    validation_backlog: int,
    output_backlog: int,
) -> None:
    """Project unresolved stage lag gauges using the runtime wall-clock anchor."""
    started_at = getattr(getattr(host, "_context", None), "started_at", None)
    if not isinstance(started_at, datetime):
        lag_seconds = 0.0
    else:
        lag_seconds = max(0.0, (current_utc_time() - started_at).total_seconds())

    typed_pipeline_metrics = cast("PipelineMetricsRecorder", pipeline_metrics)
    typed_pipeline_metrics.record_stage_lag_seconds(
        run_type=run_type,
        stage="ingestion",
        seconds=lag_seconds if ingestion_backlog > 0 else 0.0,
    )
    typed_pipeline_metrics.record_stage_lag_seconds(
        run_type=run_type,
        stage="validation",
        seconds=lag_seconds if validation_backlog > 0 else 0.0,
    )
    typed_pipeline_metrics.record_stage_lag_seconds(
        run_type=run_type,
        stage="output",
        seconds=lag_seconds if output_backlog > 0 else 0.0,
    )
