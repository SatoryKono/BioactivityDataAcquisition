"""Private observer emission helpers for runner execution flow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol


class _RunnerObservabilityHostProtocol(Protocol):
    _config: PipelineConfig
    _runtime: RuntimeConfig
    _observer: PipelineObserver


if TYPE_CHECKING:
    from bioetl.application.core.postrun.service import PostrunResult
    from bioetl.application.observability.observer import PipelineObserver
    from bioetl.domain.config import PipelineConfig, RuntimeConfig


def emit_postrun_observability(
    host: _RunnerObservabilityHostProtocol,
    result: PostrunResult,
    *,
    runner_stage: str,
) -> None:
    """Emit DQ anomaly and VACUUM events from one postrun result."""
    for anomaly in result.dq.anomalies:
        host._observer.emit_dq_anomaly(
            metric_name=anomaly.metric_name,
            severity=anomaly.severity.value,
            anomaly_type=anomaly.anomaly_type.value,
            current_value=anomaly.current_value,
            baseline_mean=anomaly.baseline_mean,
            baseline_stddev=anomaly.baseline_stddev,
            z_score=anomaly.z_score,
            message=anomaly.message,
            runner_stage=runner_stage,
        )

    if result.vacuum.skipped:
        return

    host._observer.emit_vacuum_result(
        layer="silver",
        table=host._config.effective_silver_table,
        files_removed=result.vacuum.silver_files_removed,
        runner_stage=runner_stage,
    )

    if not getattr(host._runtime, "skip_gold", False):
        host._observer.emit_vacuum_result(
            layer="gold",
            table=host._config.effective_gold_table,
            files_removed=result.vacuum.gold_files_removed,
            runner_stage=runner_stage,
        )
