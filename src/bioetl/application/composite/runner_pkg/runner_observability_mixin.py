# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
# pyright: reportInvalidCast=false
# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Observability and quarantine helpers for CompositePipelineRunner."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any, Protocol, cast

from bioetl.application.composite.runner_pkg.runner_constants import (
    DQ_REPORT_NON_FATAL_ERRORS,
    QUARANTINE_WRITE_NON_FATAL_ERRORS,
)
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.application.services.dq_report_service import DQReportService
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.ports import LoggerPort, MetricsPort, QuarantinePort
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )


_COMPOSITE_CV_QUARANTINE_ARTIFACT_POLICY = "occurrence_only_diagnostic"
_COMPOSITE_CV_QUARANTINE_REPLAY_CONTRACT = "excluded_from_exact_replay"
_COMPOSITE_CV_QUARANTINE_SCOPE = "composite_cross_validation_quarantine"
_COMPOSITE_CV_QUARANTINE_RULE_ID = "composite.cross_validation.quarantine"
_COMPOSITE_CV_QUARANTINE_VIOLATION_KIND = "cross_validation_mismatch"


class _CompositeRunnerObservabilityHostProtocol(Protocol):
    _config: CompositeConfig = cast(Any, None)  # Any: host attr default (PD3)
    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD3)
    _run_id_str: str = cast(Any, None)  # Any: host attr default (PD3)
    _run_id: RunID = cast(Any, None)  # Any: host attr default (PD3)
    _runtime: object = cast(Any, None)  # Any: host attr default (PD3)
    _started_at: datetime | None = cast(Any, None)  # Any: host attr default (PD3)
    _dq_report_service: DQReportService | None = cast(Any, None)  # Any: host attr default (PD3)
    _quarantine_port: QuarantinePort | None = cast(Any, None)  # Any: host attr default (PD3)
    _metrics: MetricsPort | None = cast(Any, None)  # Any: host attr default (PD3)
    _run_ledger_service: RunLedgerService | None = cast(Any, None)  # Any: host attr default (PD3)

    def _record_with_ledger_service(
        self,
        recorder: Callable[[RunLedgerService], object],
    ) -> None: ...


def _resolve_composite_dq_timestamp(
    *,
    cached_bronze_date: str | None,
    started_at: datetime | None,
) -> datetime:
    """Resolve a deterministic timestamp for composite DQ side effects."""
    if cached_bronze_date is not None:
        replay_date = date.fromisoformat(cached_bronze_date)
        return datetime.combine(replay_date, datetime.min.time(), tzinfo=UTC)
    if started_at is not None:
        return started_at
    return datetime(1970, 1, 1, tzinfo=UTC)


def _build_composite_cv_quarantine_metadata() -> dict[str, object]:
    """Return the canonical replay policy for composite quarantine side effects."""
    return {
        "artifact_policy": _COMPOSITE_CV_QUARANTINE_ARTIFACT_POLICY,
        "replay_contract": _COMPOSITE_CV_QUARANTINE_REPLAY_CONTRACT,
        "diagnostic_scope": _COMPOSITE_CV_QUARANTINE_SCOPE,
        "violation_kind": _COMPOSITE_CV_QUARANTINE_VIOLATION_KIND,
        "semantic_artifact": False,
    }


def _record_cv_quarantine_policy_if_supported(
    host: _CompositeRunnerObservabilityHostProtocol,
    *,
    written: int,
    quarantine_metadata: dict[str, object],
) -> None:
    """Emit one control-plane policy event when the host exposes ledger wiring."""
    recorder = getattr(host, "_record_with_ledger_service", None)
    if not callable(recorder):
        return
    recorder(
        lambda ledger_service: ledger_service.record_dq_policy_applied(
            stage="cross_validation",
            status="quarantined",
            rule_id=_COMPOSITE_CV_QUARANTINE_RULE_ID,
            disposition="quarantine",
            details={
                "config_path": "cross_validation",
                "quarantine_record_count": written,
                **quarantine_metadata,
            },
        )
    )


class CompositeRunnerObservabilityMixin:
    """Mixin with optional DQ reporting and quarantine side effects."""

    _config: CompositeConfig = cast(Any, None)  # Any: host attr default (PD3)
    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD3)
    _run_id_str: str = cast(Any, None)  # Any: host attr default (PD3)
    _run_id: RunID = cast(Any, None)  # Any: host attr default (PD3)
    _dq_report_service: DQReportService | None = cast(Any, None)  # Any: host attr default (PD3)
    _quarantine_port: QuarantinePort | None = cast(Any, None)  # Any: host attr default (PD3)
    _metrics: MetricsPort | None = cast(Any, None)  # Any: host attr default (PD3)
    _run_ledger_service: RunLedgerService | None = cast(Any, None)  # Any: host attr default (PD3)

    async def _generate_dq_reports(
        self: _CompositeRunnerObservabilityHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        """Generate DQ reports for composite pipeline.

        Args:
            merge_result: Merge execution result providing table paths and record counts
                used to populate the DQ report context.
        """
        if self._dq_report_service is None:
            self._logger.debug(
                "dq_reports_skipped",
                reason="DQReportService not configured",
                composite=self._config.name,
            )
            return

        try:
            from bioetl.application.services.dq_report_service import DQReportContext

            cached_bronze_date = cast(
                str | None,
                getattr(self._runtime, "cached_bronze_date", None),
            )
            dq_timestamp = _resolve_composite_dq_timestamp(
                cached_bronze_date=cached_bronze_date,
                started_at=self._started_at,
            )
            context = DQReportContext(
                run_id=self._run_id_str,
                pipeline_name=f"composite_{self._config.name}",
                timestamp=dq_timestamp,
                provider="composite",
                entity=self._config.name,
                silver_target_table=self._config.merge.output_silver_path,
                silver_input_count=merge_result.records_from_seed,
                gold_target_table=self._config.merge.output_gold_path,
                dq_soft_threshold=self._config.dq.soft_fail_threshold,
                dq_hard_threshold=self._config.dq.hard_fail_threshold,
            )
            await self._dq_report_service.generate_reports(context)
            self._logger.info(
                "dq_reports_generated",
                composite=self._config.name,
                run_id=self._run_id_str,
            )
        except DQ_REPORT_NON_FATAL_ERRORS as error:
            self._logger.warning(
                "dq_reports_failed",
                composite=self._config.name,
                error=str(error),
                error_type=type(error).__name__,
            )
        except BioETLError as error:
            self._logger.warning(
                "dq_reports_failed",
                composite=self._config.name,
                error=str(error),
                error_type=type(error).__name__,
                reason_code="unexpected_bioetl_error",
            )

    async def _write_cv_quarantine(
        self: _CompositeRunnerObservabilityHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        """Write cross-validation quarantine records if any exist.

        Args:
            merge_result: Merge result containing ``quarantine_payloads`` from
                cross-validation. When empty or quarantine port is absent, no writes occur.
        """
        if self._quarantine_port is None or not merge_result.quarantine_payloads:
            return

        from bioetl.domain.types import BatchID

        cached_bronze_date = cast(
            str | None,
            getattr(self._runtime, "cached_bronze_date", None),
        )
        quarantine_timestamp = _resolve_composite_dq_timestamp(
            cached_bronze_date=cached_bronze_date,
            started_at=self._started_at,
        )
        pipeline_name = f"composite:{self._config.name}"
        quarantine_metadata = _build_composite_cv_quarantine_metadata()
        written = 0

        for payload in merge_result.quarantine_payloads:
            try:
                await self._quarantine_port.write(
                    pipeline=pipeline_name,
                    error_code="CROSS_VALIDATION_QUARANTINE",
                    payload=dict(payload),
                    bronze_batch_id=cast(BatchID, self._run_id),
                    run_id=self._run_id,
                    metadata=quarantine_metadata,
                    ingestion_ts=quarantine_timestamp,
                )
                written += 1
            except QUARANTINE_WRITE_NON_FATAL_ERRORS as error:
                self._logger.warning(
                    "Failed to write quarantine record",
                    pipeline=pipeline_name,
                    error=str(error),
                    error_type=type(error).__name__,
                )
            except BioETLError as error:
                self._logger.warning(
                    "Failed to write quarantine record",
                    pipeline=pipeline_name,
                    error=str(error),
                    error_type=type(error).__name__,
                    reason_code="unexpected_bioetl_error",
                )

        if written <= 0:
            return
        _record_cv_quarantine_policy_if_supported(
            self,
            written=written,
            quarantine_metadata=quarantine_metadata,
        )
        self._logger.info(
            "Cross-validation quarantine records written",
            composite=self._config.name,
            quarantine_count=written,
            artifact_policy=_COMPOSITE_CV_QUARANTINE_ARTIFACT_POLICY,
            replay_contract=_COMPOSITE_CV_QUARANTINE_REPLAY_CONTRACT,
        )
        metrics_recorder = PipelineMetricsRecorder(self._metrics, pipeline_name)
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


__all__ = ["CompositeRunnerObservabilityMixin"]
