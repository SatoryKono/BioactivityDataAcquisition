"""Private helper functions for :mod:`pipeline_runner_service`."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunOptions,
    RunResult,
)
from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.context import (
    get_stage_accounting,
)
from bioetl.domain.run_reports.models import StageId
from bioetl.domain.run_reports.pipeline_builder import build_pipeline_run_report

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_run_execution_service import (
        PipelineExecutionResult,
    )
    from bioetl.domain.ports import ClockPort, ExecutionMetricsRunnerPort, LoggerPort
    from bioetl.domain.types import RunID


def build_dry_run_result(
    *,
    clock: ClockPort,
    pipeline_name: str,
    run_id: RunID,
    options: RunOptions,
    started_at: datetime,
    run_logger: LoggerPort,
) -> RunResult | None:
    """Build dry-run result when execution is intentionally skipped."""
    if not options.dry_run:
        return None
    run_logger.info("Dry-run mode: no execution performed")
    return RunResult(
        status=PipelineRunResult.DRY_RUN,
        pipeline_name=pipeline_name,
        run_id=str(run_id),
        run_type=options.run_type,
        started_at=started_at,
        completed_at=clock.now(),
    )


def _seed_gold_removals_from_metrics(
    accounting: StageAccountingAccumulator,
    metrics: dict[str, Any],  # Any: report/json payload shape is dynamic
) -> None:
    """Backfill gold removals from coarse metrics when hooks did not fire."""
    excluded = int(metrics.get("records_gold_excluded_by_contract", 0) or 0)
    if excluded > 0 and accounting.sum_outcome(StageId.GOLD.value, "excluded_by_contract") == 0:
        accounting.record_removal(
            StageId.GOLD.value,
            outcome="excluded_by_contract",
            reason_code="gold_contract_schema_failure",
            count=excluded,
        )


def finalize_pipeline_run_report(
    *,
    result: RunResult,
    options: RunOptions | None = None,
    report_root: Path | None = None,
) -> RunResult:
    """Build and persist pipeline run report; attach paths onto result."""
    accounting = get_stage_accounting()
    metrics = {
        "records_fetched": result.records_fetched,
        "records_bronze": result.records_bronze,
        "records_silver": result.records_silver,
        "records_gold": result.records_gold,
        "records_gold_excluded_by_contract": result.records_gold_excluded_by_contract,
        "records_quarantined": result.records_quarantined,
        "records_filtered_out": result.records_filtered_out,
    }
    if accounting is not None:
        _seed_gold_removals_from_metrics(accounting, metrics)

    duration: float | None
    try:
        duration = result.duration_seconds
    except Exception:
        duration = None

    identity: dict[str, Any] = {  # Any: report/json payload shape is dynamic
        "run_id": result.run_id,
        "manifest_id": result.manifest_id,
        "pipeline_name": result.pipeline_name,
        "provider": None,
        "entity": None,
        "run_type": result.run_type,
        "status": result.status.value,
        "started_at": (
            result.started_at.isoformat() if result.started_at is not None else None
        ),
        "completed_at": (
            result.completed_at.isoformat() if result.completed_at is not None else None
        ),
        "duration_seconds": duration,
        "workflow_id": options.workflow_id if options is not None else None,
        "workflow_run_id": options.workflow_run_id if options is not None else None,
        "workflow_step_id": options.workflow_step_id if options is not None else None,
    }
    # Derive provider/entity from pipeline_name when pattern is provider_entity.
    if "_" in result.pipeline_name:
        provider, _sep, entity = result.pipeline_name.partition("_")
        identity["provider"] = provider or None
        identity["entity"] = entity or None

    try:
        report = build_pipeline_run_report(
            identity=identity,
            metrics=metrics,
            accounting=accounting,
        )
        written = write_pipeline_run_report(report, root=report_root)
    except Exception as exc:
        return replace(
            result,
            run_report_error=f"{type(exc).__name__}: {exc}",
        )

    return replace(
        result,
        run_report_json_path=str(written.json_path),
        run_report_markdown_path=str(written.markdown_path),
        run_report_funnel=report.funnel,
    )


def build_pipeline_run_result(
    *,
    outcome: PipelineExecutionResult,
    runner: ExecutionMetricsRunnerPort,
    pipeline_name: str,
    run_id: RunID,
    run_type: str,
    started_at: datetime,
    options: RunOptions | None = None,
    write_report: bool = True,
) -> RunResult:
    """Convert execution outcome to the public RunResult contract."""
    status = PipelineRunResult(outcome.status)
    metrics = outcome.metrics
    result = RunResult(
        status=status,
        pipeline_name=pipeline_name,
        run_id=str(run_id),
        manifest_id=getattr(runner, "manifest_id", None),
        run_type=run_type,
        records_fetched=metrics.get("records_fetched", 0),
        records_bronze=metrics.get("records_bronze", 0),
        records_silver=metrics.get("records_silver", 0),
        records_gold=metrics.get("records_gold", 0),
        records_gold_excluded_by_contract=metrics.get(
            "records_gold_excluded_by_contract",
            0,
        ),
        records_quarantined=metrics.get("records_quarantined", 0),
        records_filtered_out=metrics.get("records_filtered_out", 0),
        started_at=started_at,
        completed_at=outcome.completed_at,
        error_message=outcome.error_message,
        error_type=outcome.error_type,
        debug_export_uri=getattr(runner, "debug_export_uri", None),
        debug_export_hash=getattr(runner, "debug_export_hash", None),
    )
    if write_report:
        return finalize_pipeline_run_report(result=result, options=options)
    return result
