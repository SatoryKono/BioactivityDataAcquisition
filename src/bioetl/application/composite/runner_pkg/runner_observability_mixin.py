"""Observability and quarantine helpers for CompositePipelineRunner."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, cast

from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.application.composite.runner_pkg.runner_constants import (
    DQ_REPORT_NON_FATAL_ERRORS,
    QUARANTINE_WRITE_NON_FATAL_ERRORS,
)
from bioetl.application.services.dq_report_service import DQReportService
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.ports import LoggerPort, MetricsPort, QuarantinePort
from bioetl.domain.types import RunID


class _CompositeRunnerObservabilityHostProtocol(Protocol):
    _config: CompositeConfig
    _logger: LoggerPort
    _run_id_str: str
    _run_id: RunID
    _dq_report_service: DQReportService | None
    _quarantine_port: QuarantinePort | None
    _metrics: MetricsPort | None


class CompositeRunnerObservabilityMixin:
    """Mixin with optional DQ reporting and quarantine side effects."""

    _config: CompositeConfig
    _logger: LoggerPort
    _run_id_str: str
    _run_id: RunID
    _dq_report_service: DQReportService | None
    _quarantine_port: QuarantinePort | None
    _metrics: MetricsPort | None

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

            context = DQReportContext(
                run_id=self._run_id_str,
                pipeline_name=f"composite_{self._config.name}",
                timestamp=datetime.now(tz=UTC),
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

        now = datetime.now(tz=UTC)
        pipeline_name = f"composite:{self._config.name}"
        written = 0

        for payload in merge_result.quarantine_payloads:
            try:
                await self._quarantine_port.write(
                    pipeline=pipeline_name,
                    error_code="CROSS_VALIDATION_QUARANTINE",
                    payload=dict(payload),
                    bronze_batch_id=cast(BatchID, self._run_id),
                    run_id=self._run_id,
                    ingestion_ts=now,
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
        self._logger.info(
            "Cross-validation quarantine records written",
            composite=self._config.name,
            quarantine_count=written,
        )
        PipelineMetricsRecorder(self._metrics, pipeline_name).record_quarantine_records(
            reason="cross_validation",
            count=written,
        )


__all__ = ["CompositeRunnerObservabilityMixin"]
