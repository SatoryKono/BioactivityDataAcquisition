"""Persist pipeline-run-report artifacts for nested PipelineRunner executions.

Composite seed/enricher/dependency phases call ``PipelineRunner.run()``
directly and therefore skip ``PipelineRunnerService._finalize_report``.
This module is the shared writer used by those nested paths and by the
composite parent runner.
"""

from __future__ import annotations

from asyncio import CancelledError
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.runtime_clock import RuntimeClock
from bioetl.application.runtime_timestamps import (
    capture_runtime_timing_anchor,
    derive_completion_timestamp,
)
from bioetl.application.services.execution._pipeline_runner_support import (
    finalize_pipeline_run_report,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunOptions,
    RunResult,
)
from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP

if TYPE_CHECKING:
    from datetime import datetime

    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.composite.result import CompositeResult
    from bioetl.domain.ports import (
        ClockPort,
        ExecutionMetricsReadablePort,
        ExecutionMetricsRunnerPort,
        LoggerPort,
        RunReportStorePort,
    )

__all__ = [
    "ReportingExecutionRunner",
    "composite_run_report_pipeline_name",
    "extract_runner_metrics",
    "maybe_wrap_reporting_runner",
    "persist_composite_pipeline_run_report",
    "persist_nested_pipeline_run_report",
]


def composite_run_report_pipeline_name(composite_name: str) -> str:
    """Filesystem-safe pipeline identity for a composite parent report."""
    return f"composite_{composite_name}"


def extract_runner_metrics(runner: ExecutionMetricsReadablePort) -> dict[str, int]:
    """Read canonical execution counters, defaulting missing keys to zero."""
    try:
        raw = runner.execution_metrics
    except (AttributeError, TypeError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}

    def _as_int(key: str) -> int:
        try:
            return int(raw.get(key, 0) or 0)
        except (TypeError, ValueError):
            return 0

    return {
        "records_fetched": _as_int("records_fetched"),
        "records_bronze": _as_int("records_bronze"),
        "records_silver": _as_int("records_silver"),
        "records_gold": _as_int("records_gold"),
        "records_gold_excluded_by_contract": _as_int(
            "records_gold_excluded_by_contract"
        ),
        "records_quarantined": _as_int("records_quarantined"),
        "records_filtered_out": _as_int("records_filtered_out"),
    }


def persist_nested_pipeline_run_report(
    *,
    runner: ExecutionMetricsRunnerPort,
    pipeline_name: str,
    options: RunOptions,
    started_at: datetime,
    completed_at: datetime,
    store: RunReportStorePort,
    report_root: Path | None = None,
    status: PipelineRunResult = PipelineRunResult.SUCCESS,
    error_type: str | None = None,
    error_message: str | None = None,
) -> RunResult:
    """Build a RunResult from a nested runner and persist the canonical report."""
    metrics = extract_runner_metrics(runner)
    result = RunResult(
        status=status,
        pipeline_name=pipeline_name,
        run_id=str(runner.run_id),
        run_type=options.run_type,
        manifest_id=getattr(runner, "manifest_id", None),
        records_fetched=metrics["records_fetched"],
        records_bronze=metrics["records_bronze"],
        records_silver=metrics["records_silver"],
        records_gold=metrics["records_gold"],
        records_gold_excluded_by_contract=metrics["records_gold_excluded_by_contract"],
        records_quarantined=metrics["records_quarantined"],
        records_filtered_out=metrics["records_filtered_out"],
        started_at=started_at,
        completed_at=completed_at,
        error_message=error_message,
        error_type=error_type,
        debug_export_uri=getattr(runner, "debug_export_uri", None),
        debug_export_hash=getattr(runner, "debug_export_hash", None),
    )
    return finalize_pipeline_run_report(
        result=result,
        options=options,
        report_root=report_root,
        store=store,
    )


def persist_composite_pipeline_run_report(
    *,
    result: CompositeResult,
    store: RunReportStorePort,
    options: RunOptions,
    report_root: Path | None = None,
    manifest_id: str | None = None,
    logger: LoggerPort | None = None,
) -> RunResult:
    """Persist a pipeline-run-report for the composite parent occurrence."""
    merge = result.merge_result
    seed = result.seed_result
    started_at = result.started_at or MISSING_RUNTIME_TIMESTAMP
    completed_at = result.completed_at or started_at
    nested = RunResult(
        status=(
            PipelineRunResult.SUCCESS if result.is_success else PipelineRunResult.FAILED
        ),
        pipeline_name=composite_run_report_pipeline_name(result.composite_name),
        run_id=result.composite_run_id,
        run_type=options.run_type,
        manifest_id=manifest_id,
        records_fetched=seed.records_extracted,
        records_bronze=seed.records_extracted,
        records_silver=seed.records_silver,
        records_gold=0 if merge is None else merge.records_merged,
        started_at=started_at,
        completed_at=completed_at,
    )
    written = finalize_pipeline_run_report(
        result=nested,
        options=options,
        report_root=report_root,
        store=store,
    )
    if written.run_report_error is not None and logger is not None:
        logger.warning(
            "composite_run_report_unavailable",
            pipeline_name=nested.pipeline_name,
            run_id=nested.run_id,
            error=written.run_report_error,
        )
    return written


def maybe_wrap_reporting_runner(
    runner: object,
    *,
    pipeline_name: str,
    options: object,
    store: RunReportStorePort,
    report_root: Path | None = None,
    clock: ClockPort | None = None,
) -> object:
    """Wrap a real PipelineRunner so ``run()`` writes the canonical report.

    Snapshot/test doubles (dicts, MagicMock) are returned unchanged.
    """
    from bioetl.application.core.runner import PipelineRunner

    if not isinstance(runner, PipelineRunner) or not isinstance(options, RunOptions):
        return runner
    return ReportingExecutionRunner(
        inner=runner,
        pipeline_name=pipeline_name,
        options=options,
        store=store,
        report_root=report_root,
        clock=clock,
    )


class ReportingExecutionRunner:
    """Delegate to an inner metrics runner and persist the run report after ``run()``."""

    def __init__(
        self,
        *,
        inner: PipelineRunner,
        pipeline_name: str,
        options: RunOptions,
        store: RunReportStorePort,
        report_root: Path | None = None,
        clock: ClockPort | None = None,
    ) -> None:
        self._inner = inner
        self._pipeline_name = pipeline_name
        self._options = options
        self._store = store
        self._report_root = report_root
        self._clock = RuntimeClock() if clock is None else clock

    @property
    def run_id(self) -> str:
        return self._inner.run_id

    @property
    def shutdown_signal(self) -> object | None:
        return self._inner.shutdown_signal

    @property
    def execution_metrics(self) -> dict[str, int]:
        return extract_runner_metrics(self._inner)

    @property
    def manifest_id(self) -> str | None:
        return self._inner.manifest_id

    async def run(self) -> None:
        """Execute the inner runner, then persist success or failure reports."""
        started_at, started_monotonic = capture_runtime_timing_anchor(clock=self._clock)
        try:
            await self._inner.run()
        except CancelledError:
            self._persist(
                started_at=started_at,
                started_monotonic=started_monotonic,
                status=PipelineRunResult.SHUTDOWN,
                error_type="CancelledError",
                error_message=None,
            )
            raise
        except Exception as exc:
            self._persist(
                started_at=started_at,
                started_monotonic=started_monotonic,
                status=PipelineRunResult.FAILED,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise
        self._persist(
            started_at=started_at,
            started_monotonic=started_monotonic,
            status=PipelineRunResult.SUCCESS,
            error_type=None,
            error_message=None,
        )

    def _persist(
        self,
        *,
        started_at: datetime,
        started_monotonic: float,
        status: PipelineRunResult,
        error_type: str | None,
        error_message: str | None,
    ) -> None:
        completed_at, _duration = derive_completion_timestamp(
            started_at=started_at,
            started_monotonic=started_monotonic,
        )
        written = persist_nested_pipeline_run_report(
            runner=self._inner,
            pipeline_name=self._pipeline_name,
            options=self._options,
            started_at=started_at,
            completed_at=completed_at,
            store=self._store,
            report_root=self._report_root,
            status=status,
            error_type=error_type,
            error_message=error_message,
        )
        if written.run_report_error is None:
            return
        logger = getattr(self._inner, "logger", None)
        if logger is None:
            return
        logger.warning(
            "nested_run_report_unavailable",
            pipeline_name=self._pipeline_name,
            run_id=self.run_id,
            error=written.run_report_error,
        )
