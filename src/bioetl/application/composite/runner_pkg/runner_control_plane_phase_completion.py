"""Phase-completion support for composite runner control-plane flows."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.runner_pkg.runner_control_plane_lifecycle import (
    CompositeRunnerControlPlaneHostProtocol,
    DEPENDENCIES_STAGE_NAME,
    SEED_STAGE_NAME,
    record_run_metrics_event,
    record_stage_completed,
    record_with_ledger_service,
)
from bioetl.application.composite.runner_pkg.runner_control_plane_phase_followup import (
    record_enrichment_stage_completed,
    record_merge_stage_completed,
)
from bioetl.application.composite.runner_pkg.runner_stage_payloads import (
    build_composite_run_completion_metrics,
    build_dependency_result_payload,
    build_dependency_stage_metrics,
    build_seed_stage_metrics,
)
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeExecutionContext
    from bioetl.domain.composite.result import DependencyResult, SeedResult


def _build_pipeline_metrics(
    host: CompositeRunnerControlPlaneHostProtocol,
) -> PipelineMetricsRecorder:
    return PipelineMetricsRecorder(host._metrics, f"composite:{host._config.name}")


def record_run_finished(
    host: CompositeRunnerControlPlaneHostProtocol,
    artifacts: CompositeExecutionContext,
) -> None:
    """Append ``run_finished`` when control-plane ledger is attached."""
    record_run_metrics_event(
        host,
        metrics_snapshot=build_composite_run_completion_metrics(artifacts),
        recorder=lambda ledger_service, metrics_snapshot: (
            ledger_service.record_run_finished(
                metrics_snapshot=metrics_snapshot,
            )
        ),
    )


def record_seed_stage_completed(
    host: CompositeRunnerControlPlaneHostProtocol,
    seed_result: SeedResult,
) -> None:
    """Append one ``stage_completed`` entry for seed phase."""
    pipeline_metrics = _build_pipeline_metrics(host)
    pipeline_metrics.record_composite_phase_records(
        phase="seed",
        outcome="extracted",
        count=int(seed_result.records_extracted),
    )
    pipeline_metrics.record_composite_phase_records(
        phase="seed",
        outcome="silver",
        count=int(seed_result.records_silver),
    )
    pipeline_metrics.record_composite_phase_loss(
        phase="seed",
        loss_kind="unwritten",
        count=max(
            int(seed_result.records_extracted) - int(seed_result.records_silver),
            0,
        ),
    )
    if seed_result.resumed:
        pipeline_metrics.record_composite_phase_retries(
            phase="seed",
            retry_kind="resume",
        )
    record_stage_completed(
        host,
        stage=SEED_STAGE_NAME,
        metrics_snapshot=build_seed_stage_metrics(seed_result),
    )


def record_dependencies_stage_completed(
    host: CompositeRunnerControlPlaneHostProtocol,
    dependency_results: dict[str, DependencyResult],
) -> None:
    """Append one ``stage_completed`` entry for dependencies phase."""
    pipeline_metrics = _build_pipeline_metrics(host)
    records_extracted = sum(
        int(result.records_extracted) for result in dependency_results.values()
    )
    records_silver = sum(
        int(result.records_silver) for result in dependency_results.values()
    )
    failed = sum(
        1 for result in dependency_results.values() if result.status.value == "failed"
    )
    timed_out = sum(
        1 for result in dependency_results.values() if result.status.value == "timeout"
    )
    resumed = sum(1 for result in dependency_results.values() if result.resumed)
    pipeline_metrics.record_composite_phase_records(
        phase="dependencies",
        outcome="extracted",
        count=records_extracted,
    )
    pipeline_metrics.record_composite_phase_records(
        phase="dependencies",
        outcome="silver",
        count=records_silver,
    )
    pipeline_metrics.record_composite_phase_loss(
        phase="dependencies",
        loss_kind="unwritten",
        count=max(records_extracted - records_silver, 0),
    )
    pipeline_metrics.record_composite_phase_errors(
        phase="dependencies",
        error_kind="failed",
        count=failed,
    )
    pipeline_metrics.record_composite_phase_errors(
        phase="dependencies",
        error_kind="timeout",
        count=timed_out,
    )
    pipeline_metrics.record_composite_phase_retries(
        phase="dependencies",
        retry_kind="resume",
        count=resumed,
    )
    for dependency_name, result in sorted(dependency_results.items()):
        payload = build_dependency_result_payload(result)
        record_with_ledger_service(
            host,
            lambda ledger_service, name=dependency_name, data=payload: (
                ledger_service.record_composite_dependency_completed(
                    dependency_name=name,
                    result=data,
                )
            ),
        )
    record_stage_completed(
        host,
        stage=DEPENDENCIES_STAGE_NAME,
        metrics_snapshot=build_dependency_stage_metrics(dependency_results),
    )


__all__ = [
    "record_dependencies_stage_completed",
    "record_enrichment_stage_completed",
    "record_merge_stage_completed",
    "record_run_finished",
    "record_seed_stage_completed",
]
