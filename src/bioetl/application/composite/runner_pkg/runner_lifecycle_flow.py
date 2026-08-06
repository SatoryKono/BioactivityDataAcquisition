"""Lifecycle and failure-mapping helpers for CompositePipelineRunner."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.application.runtime_timestamps import capture_runtime_timing_anchor
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError

if TYPE_CHECKING:
    from bioetl.application.composite.lifecycle_observer_service import (
        CompositeLifecycleObserverService,
    )
    from bioetl.application.composite.runtime_models import (
        CompositeExecutionContext,
        CompositeRuntimeConfig,
    )
    from bioetl.domain.composite import CompositeConfig
    from bioetl.domain.composite.result import CompositeResult
    from bioetl.domain.ports import ClockPort

__all__ = [
    "complete_successful_run",
    "emit_failed_run",
    "handle_bioetl_failure",
    "handle_pipeline_execution_failure",
    "handle_shutdown",
    "mark_finished",
    "start_run_lifecycle",
]


class _RunnerLifecycleHost(Protocol):
    """Minimal host surface required for runner lifecycle helpers."""

    _config: CompositeConfig
    _runtime: CompositeRuntimeConfig
    _observer: CompositeLifecycleObserverService
    _clock: ClockPort | None
    _run_id_str: str
    _finished: bool
    _final_state: CompositePipelineState | None
    _started_at: object
    _start_time: object

    def _validate_config_consistency(self) -> None: ...

    def _run_preflight_validation(self) -> None: ...

    def _record_run_started(self) -> None: ...

    def _record_run_failed(self, error: Exception) -> None: ...

    def _record_run_shutdown(self) -> None: ...

    def _record_run_finished(self, execution_context: CompositeExecutionContext) -> None: ...

    async def _finalize_pipeline(self, state: object) -> None: ...

    def _prepare_composite_result_context(
        self, execution_context: CompositeExecutionContext
    ) -> object: ...

    def _log_composite_completion(self, completion_context: object) -> None: ...

    def _finalize_composite_result(self, completion_context: object) -> CompositeResult: ...


def mark_finished(
    host: _RunnerLifecycleHost,
    final_state: CompositePipelineState,
) -> None:
    """Persist terminal runner state for re-entry guards and diagnostics."""
    host._finished = True  # pyright: ignore[reportAttributeAccessIssue]
    host._final_state = final_state  # pyright: ignore[reportAttributeAccessIssue]


def emit_failed_run(
    host: _RunnerLifecycleHost,
    error: Exception,
    *,
    reason_code: str,
    stage: str | None = None,
) -> None:
    """Emit the canonical runner failure event through the observer seam."""
    host._observer.emit_run_failed(
        composite_name=host._config.name,
        run_id=host._run_id_str,
        error=error,
        reason_code=reason_code,
        stage=stage,
    )


def handle_pipeline_execution_failure(
    host: _RunnerLifecycleHost,
    error: Exception,
) -> None:
    """Map execution-phase failures to canonical runner diagnostics."""
    mark_finished(host, CompositePipelineState.FAILED)
    host._record_run_failed(error)
    emit_failed_run(
        host,
        error,
        reason_code="composite_pipeline_execution_failed",
        stage="run_with_lock",
    )


def handle_bioetl_failure(host: _RunnerLifecycleHost, error: BioETLError) -> None:
    """Map unexpected BioETL failures to canonical runner diagnostics."""
    mark_finished(host, CompositePipelineState.FAILED)
    host._record_run_failed(error)
    emit_failed_run(host, error, reason_code="unexpected_bioetl_error")


def handle_shutdown(host: _RunnerLifecycleHost, error: PipelineShutdownError) -> None:
    """Map graceful shutdown to canonical terminal ledger/log semantics."""
    mark_finished(host, CompositePipelineState.FAILED)
    host._record_run_shutdown()
    host._observer.emit_run_shutdown(
        composite_name=host._config.name,
        run_id=host._run_id_str,
        error=error,
        reason=str(error.reason.value),
        reason_code="composite_pipeline_shutdown",
    )


def start_run_lifecycle(host: _RunnerLifecycleHost) -> None:
    """Validate and log the start of one composite runner execution."""
    host._validate_config_consistency()
    host._run_preflight_validation()
    host._started_at, host._start_time = capture_runtime_timing_anchor(  # pyright: ignore[reportAttributeAccessIssue]
        clock=host._clock
    )
    host._observer.emit_run_started(
        composite_name=host._config.name,
        run_id=host._run_id_str,
    )
    host._record_run_started()


async def complete_successful_run(
    host: _RunnerLifecycleHost,
    state: object,
    execution_context: CompositeExecutionContext,
) -> CompositeResult:
    """Finalize state and emit canonical terminal success artifacts."""
    await host._finalize_pipeline(state)
    completion_context = host._prepare_composite_result_context(execution_context)
    host._log_composite_completion(completion_context)
    result = host._finalize_composite_result(completion_context)
    host._record_run_finished(execution_context)
    return result
