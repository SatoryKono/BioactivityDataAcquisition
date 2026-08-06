# pyright: reportImportCycles=false
# Import cycle residual tracked in allowlist (product burn-down).
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
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.application.core.runner_flow_metrics import (
    record_flow_invariants as _record_flow_invariants_impl,
)
from bioetl.application.core.runner_flow_metrics import (
    record_output_ready as _record_output_ready_impl,
)
from bioetl.application.runtime_clock import current_utc_time
from bioetl.domain.events import PipelineEvent
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointRuntimeService,
    )
    from bioetl.application.core.pipeline_observability_service_protocols import (
        PipelineRunnerServicesProtocol,
    )
    from bioetl.application.services.control_plane.ledger.service import (
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
    _services: PipelineRunnerServicesProtocol
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
    raw_records = checkpoint_meta.get("records_processed")  # pyright: ignore[reportAttributeAccessIssue]
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
    from bioetl.application.observability.pipeline_metrics import (
        PipelineMetricsRecorder,
    )

    PipelineMetricsRecorder(
        host._services.metrics,
        host._config.pipeline_name,
    ).initialize_record_accounting_outcomes(run_type=host._runtime.run_type.value)
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
    return _record_output_ready_impl(host)


def record_run_shutdown(host: _PipelineRunnerFlowHostProtocol) -> None:
    """Append graceful shutdown ledger entry."""
    # Ledger write is primary; invariant projection must not block terminal recording.
    _record_run_metrics_event(
        host,
        lambda ledger_service, metrics_snapshot, details: (
            ledger_service.record_run_shutdown(
                metrics_snapshot=metrics_snapshot,
                details=details,
            )
        ),
    )
    try:
        _record_flow_invariants(host)
    except Exception:
        # Best-effort metrics projection after shutdown ledger is written.
        host._logger.warning(
            "shutdown_flow_invariants_failed",
            run_id=str(host._context.run_id),
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
    return _record_flow_invariants_impl(host, current_time_fn=current_utc_time)
