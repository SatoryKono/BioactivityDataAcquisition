"""Metrics projection helpers for :mod:`bioetl.application.core.runner_flow`."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.application.runtime_clock import current_utc_time

if TYPE_CHECKING:
    from bioetl.application.core.runner_flow import _PipelineRunnerFlowHostProtocol
    from bioetl.application.observability.pipeline_metrics import (
        PipelineMetricsRecorder,
    )


def record_output_ready(host: _PipelineRunnerFlowHostProtocol) -> None:
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


def record_flow_invariants(
    host: _PipelineRunnerFlowHostProtocol,
    *,
    current_time_fn: Callable[[], datetime] = current_utc_time,
) -> None:
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
    gold_excluded_by_contract = max(
        0,
        int(metrics.get("records_gold_excluded_by_contract", 0)),
    )
    quarantined = max(0, int(metrics.get("records_quarantined", 0)))
    filtered_out = max(0, int(metrics.get("records_filtered_out", 0)))
    _record_count_flow_invariants(
        pipeline_metrics=pipeline_metrics,
        run_type=run_type,
        fetched=fetched,
        bronze=bronze,
        silver=silver,
        gold=gold,
        gold_excluded_by_contract=gold_excluded_by_contract,
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
    gold_terminal = gold + gold_excluded_by_contract
    ingestion_backlog = max(fetched - bronze, 0)
    validation_backlog = quarantined
    output_backlog = max(silver - gold_terminal, 0)
    pipeline_metrics.record_stage_backlog(
        run_type=run_type,
        stage="ingestion",
        count=ingestion_backlog,
    )
    pipeline_metrics.record_stage_backlog(
        run_type=run_type,
        stage="validation",
        count=validation_backlog,
    )
    pipeline_metrics.record_stage_backlog(
        run_type=run_type,
        stage="output",
        count=output_backlog,
    )
    _record_stage_lag_gauges(
        host=host,
        pipeline_metrics=pipeline_metrics,
        run_type=run_type,
        ingestion_backlog=ingestion_backlog,
        validation_backlog=validation_backlog,
        output_backlog=output_backlog,
        current_time_fn=current_time_fn,
    )


def _record_count_flow_invariants(
    *,
    pipeline_metrics: object,
    run_type: str,
    fetched: int,
    bronze: int,
    silver: int,
    gold: int,
    gold_excluded_by_contract: int,
    quarantined: int,
    filtered_out: int,
) -> None:
    """Record record-count invariant results for one completed run."""
    typed_pipeline_metrics = cast("PipelineMetricsRecorder", pipeline_metrics)
    typed_pipeline_metrics.record_flow_invariant(
        run_type=run_type,
        invariant="fetched_equals_bronze",
        status=_equality_invariant_status(
            left=fetched,
            right=bronze,
            observed=fetched > 0 or bronze > 0,
        ),
    )
    partition_total = silver + quarantined + filtered_out
    typed_pipeline_metrics.record_flow_invariant(
        run_type=run_type,
        invariant="bronze_partitioned",
        status=_equality_invariant_status(
            left=bronze,
            right=partition_total,
            observed=bronze > 0 or partition_total > 0,
        ),
    )
    typed_pipeline_metrics.record_flow_invariant(
        run_type=run_type,
        invariant="silver_gold_monotonic",
        status=_monotonic_invariant_status(
            upper=silver,
            lower=gold,
            observed=silver > 0 or gold > 0,
        ),
    )
    gold_terminal = gold + gold_excluded_by_contract
    typed_pipeline_metrics.record_flow_invariant(
        run_type=run_type,
        invariant="silver_gold_terminal_accounted",
        status=_monotonic_invariant_status(
            upper=silver,
            lower=gold_terminal,
            observed=silver > 0 or gold_terminal > 0,
        ),
    )


def _equality_invariant_status(*, left: int, right: int, observed: bool) -> str:
    """Return stable invariant status for equality checks."""
    if not observed:
        return "unknown"
    return "passed" if left == right else "violated"


def _monotonic_invariant_status(*, upper: int, lower: int, observed: bool) -> str:
    """Return stable invariant status for monotonicity checks."""
    if not observed:
        return "unknown"
    return "passed" if upper >= lower else "violated"


def _record_stage_lag_gauges(
    *,
    host: _PipelineRunnerFlowHostProtocol,
    pipeline_metrics: object,
    run_type: str,
    ingestion_backlog: int,
    validation_backlog: int,
    output_backlog: int,
    current_time_fn: Callable[[], datetime],
) -> None:
    """Project unresolved stage lag gauges using the runtime wall-clock anchor."""
    started_at = getattr(getattr(host, "_context", None), "started_at", None)
    if not isinstance(started_at, datetime):
        lag_seconds = 0.0
    else:
        lag_seconds = max(0.0, (current_time_fn() - started_at).total_seconds())
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


__all__ = ["record_flow_invariants", "record_output_ready"]
