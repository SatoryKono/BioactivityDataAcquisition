"""Cross-validation quarantine side-effect helpers for composite runner."""

from __future__ import annotations

from typing import cast

from bioetl.application.composite.runner_pkg.runner_constants import (
    QUARANTINE_WRITE_NON_FATAL_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_observability_helpers import (
    CompositeRunnerObservabilityHostProtocol,
    build_composite_cv_quarantine_metadata,
    record_cv_quarantine_policy_if_supported,
    resolve_composite_dq_timestamp,
)
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.exceptions import BioETLError

_COMPOSITE_CV_QUARANTINE_ARTIFACT_POLICY = "occurrence_only_diagnostic"
_COMPOSITE_CV_QUARANTINE_REPLAY_CONTRACT = "excluded_from_exact_replay"

__all__ = ["write_cv_quarantine"]


async def write_cv_quarantine(
    host: CompositeRunnerObservabilityHostProtocol,
    merge_result: MergeResult,
) -> None:
    """Write cross-validation quarantine records if any exist."""
    if host._quarantine_port is None or not merge_result.quarantine_payloads:
        return

    from bioetl.domain.types import BatchID

    cached_bronze_date = cast(
        str | None,
        getattr(host._runtime, "cached_bronze_date", None),
    )
    quarantine_timestamp = resolve_composite_dq_timestamp(
        cached_bronze_date=cached_bronze_date,
        started_at=host._started_at,
    )
    pipeline_name = f"composite:{host._config.name}"
    quarantine_metadata = build_composite_cv_quarantine_metadata()
    written = 0

    for payload in merge_result.quarantine_payloads:
        try:
            await host._quarantine_port.write(
                pipeline=pipeline_name,
                error_code="CROSS_VALIDATION_QUARANTINE",
                payload=dict(payload),
                bronze_batch_id=cast(BatchID, host._run_id),  # pyright: ignore[reportInvalidCast]
                run_id=host._run_id,
                metadata=quarantine_metadata,
                ingestion_ts=quarantine_timestamp,
            )
            written += 1
        except QUARANTINE_WRITE_NON_FATAL_ERRORS as error:
            host._logger.warning(
                "Failed to write quarantine record",
                pipeline=pipeline_name,
                error=str(error),
                error_type=type(error).__name__,
            )
        except BioETLError as error:
            host._logger.warning(
                "Failed to write quarantine record",
                pipeline=pipeline_name,
                error=str(error),
                error_type=type(error).__name__,
                reason_code="unexpected_bioetl_error",
            )

    if written <= 0:
        return
    record_cv_quarantine_policy_if_supported(
        host,
        written=written,
        quarantine_metadata=quarantine_metadata,
    )
    host._logger.info(
        "Cross-validation quarantine records written",
        composite=host._config.name,
        quarantine_count=written,
        artifact_policy=_COMPOSITE_CV_QUARANTINE_ARTIFACT_POLICY,
        replay_contract=_COMPOSITE_CV_QUARANTINE_REPLAY_CONTRACT,
    )
    metrics_recorder = PipelineMetricsRecorder(host._metrics, pipeline_name)
    metrics_recorder.record_quarantine_records(
        reason="cross_validation",
        count=written,
    )
    metrics_recorder.record_record_flow(
        run_type="composite",
        flow_stage="quarantined",
        count=written,
    )
    metrics_recorder.record_dq_disposition(
        stage="validation",
        disposition="quarantine",
        terminal_status="success",
        count=written,
    )
    metrics_recorder.record_stage_records(
        run_type="composite",
        stage="validation",
        outcome="quarantined",
        count=written,
    )
    metrics_recorder.record_stage_records(
        run_type="composite",
        stage="silver",
        outcome="quarantined",
        count=written,
    )
