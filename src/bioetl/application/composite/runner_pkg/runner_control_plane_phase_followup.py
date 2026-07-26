"""Follow-up completion helpers for enrichment and merge composite phases."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from bioetl.application.composite.runner_pkg.runner_control_plane_lifecycle import (
    ENRICHMENT_STAGE_NAME,
    MERGE_STAGE_NAME,
    CompositeRunnerControlPlaneHostProtocol,
    record_stage_completed,
    record_with_ledger_service,
)
from bioetl.application.composite.runner_pkg.runner_stage_payloads import (
    build_enrichment_result_payload,
    build_enrichment_stage_metrics,
    build_merge_result_payload,
    build_merge_stage_metrics,
)
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )
    from bioetl.domain.composite.result import EnrichmentResult, MergeResult


def _record_enricher_completion(
    ledger_service: RunLedgerService,
    *,
    name: str,
    data: dict[str, object],
) -> object:
    return ledger_service.record_composite_enricher_completed(
        enricher_name=name,
        result=data,
    )


def _build_pipeline_metrics(
    host: CompositeRunnerControlPlaneHostProtocol,
) -> PipelineMetricsRecorder:
    return PipelineMetricsRecorder(host._metrics, f"composite:{host._config.name}")


def record_enrichment_stage_completed(
    host: CompositeRunnerControlPlaneHostProtocol,
    enrichment_results: dict[str, EnrichmentResult],
) -> None:
    """Append one ``stage_completed`` entry for enrichment phase."""
    pipeline_metrics = _build_pipeline_metrics(host)
    records_input = sum(
        int(result.records_input) for result in enrichment_results.values()
    )
    records_enriched = sum(
        int(result.records_enriched) for result in enrichment_results.values()
    )
    records_not_found = sum(
        int(result.records_not_found) for result in enrichment_results.values()
    )
    records_errored = sum(
        int(result.records_errored) for result in enrichment_results.values()
    )
    failed = sum(
        1 for result in enrichment_results.values() if result.status.value == "failed"
    )
    timed_out = sum(
        1 for result in enrichment_results.values() if result.status.value == "timeout"
    )
    pipeline_metrics.record_composite_phase_records(
        phase="enrichment",
        outcome="input",
        count=records_input,
    )
    pipeline_metrics.record_composite_phase_records(
        phase="enrichment",
        outcome="enriched",
        count=records_enriched,
    )
    pipeline_metrics.record_composite_phase_loss(
        phase="enrichment",
        loss_kind="not_found",
        count=records_not_found,
    )
    pipeline_metrics.record_composite_phase_errors(
        phase="enrichment",
        error_kind="record_error",
        count=records_errored,
    )
    pipeline_metrics.record_composite_phase_errors(
        phase="enrichment",
        error_kind="failed",
        count=failed,
    )
    pipeline_metrics.record_composite_phase_errors(
        phase="enrichment",
        error_kind="timeout",
        count=timed_out,
    )
    for enricher_name, result in sorted(enrichment_results.items()):
        payload = build_enrichment_result_payload(result)
        record_with_ledger_service(
            host,
            partial(
                _record_enricher_completion,
                name=enricher_name,
                data=payload,
            ),
        )
    record_stage_completed(
        host,
        stage=ENRICHMENT_STAGE_NAME,
        metrics_snapshot=build_enrichment_stage_metrics(enrichment_results),
    )


def record_merge_stage_completed(
    host: CompositeRunnerControlPlaneHostProtocol,
    merge_result: MergeResult,
) -> None:
    """Append one ``stage_completed`` entry for merge phase."""
    pipeline_metrics = _build_pipeline_metrics(host)
    pipeline_metrics.record_composite_phase_records(
        phase="merge",
        outcome="merged",
        count=int(merge_result.records_merged),
    )
    pipeline_metrics.record_composite_phase_records(
        phase="merge",
        outcome="enriched",
        count=int(merge_result.records_enriched),
    )
    pipeline_metrics.record_composite_phase_records(
        phase="merge",
        outcome="fully_enriched",
        count=int(merge_result.records_fully_enriched),
    )
    pipeline_metrics.record_composite_phase_loss(
        phase="merge",
        loss_kind="partially_enriched",
        count=max(
            int(merge_result.records_merged) - int(merge_result.records_fully_enriched),
            0,
        ),
    )
    pipeline_metrics.record_composite_phase_loss(
        phase="merge",
        loss_kind="quarantined",
        count=len(merge_result.quarantine_payloads),
    )
    merge_payload = build_merge_result_payload(merge_result)
    record_with_ledger_service(
        host,
        lambda ledger_service: ledger_service.record_composite_merge_completed(
            result=merge_payload,
        ),
    )
    record_stage_completed(
        host,
        stage=MERGE_STAGE_NAME,
        metrics_snapshot=build_merge_stage_metrics(merge_result),
    )


__all__ = ["record_enrichment_stage_completed", "record_merge_stage_completed"]
