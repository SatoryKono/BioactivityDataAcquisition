"""Result and error handling helpers for enrichment coordinator."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.composite.config import CompositeDQConfig, EnricherConfig
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import JsonDict


class EnrichmentCoordinatorResultMixin:
    """Host mixin with result assembly and exception mapping logic."""

    _logger: LoggerPort
    _dq_config: CompositeDQConfig

    def _build_enricher_result(
        self,
        *,
        enricher: EnricherConfig,
        runner: PipelineRunner,
        records_input: int,
        started_at: datetime,
        completed_at: datetime,
        duration: float,
    ) -> EnrichmentResult:
        records_enriched, records_errored, dq_error_rate = self._extract_runner_stats(
            runner, records_input
        )
        hard_threshold = self._dq_config.get_enricher_hard_threshold(enricher.pipeline)
        if dq_error_rate > hard_threshold:
            return self._build_threshold_failure_result(
                enricher=enricher,
                records_input=records_input,
                records_enriched=records_enriched,
                records_errored=records_errored,
                dq_error_rate=dq_error_rate,
                hard_threshold=hard_threshold,
                started_at=started_at,
                completed_at=completed_at,
                duration=duration,
            )

        status = (
            EnrichmentStatus.PARTIAL
            if records_enriched < records_input
            else EnrichmentStatus.SUCCESS
        )
        self._logger.info(
            "Enricher completed",
            enricher=enricher.pipeline,
            status=status.value,
            records_enriched=records_enriched,
            duration_seconds=duration,
        )
        return EnrichmentResult(
            enricher_name=enricher.pipeline,
            status=status,
            records_input=records_input,
            records_enriched=records_enriched,
            records_not_found=records_input - records_enriched - records_errored,
            records_errored=records_errored,
            dq_error_rate=dq_error_rate,
            duration_seconds=duration,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _build_threshold_failure_result(
        self,
        *,
        enricher: EnricherConfig,
        records_input: int,
        records_enriched: int,
        records_errored: int,
        dq_error_rate: float,
        hard_threshold: float,
        started_at: datetime,
        completed_at: datetime,
        duration: float,
    ) -> EnrichmentResult:
        self._logger.warning(
            "Enricher exceeded hard DQ threshold",
            enricher=enricher.pipeline,
            dq_error_rate=dq_error_rate,
            threshold=hard_threshold,
        )
        return EnrichmentResult(
            enricher_name=enricher.pipeline,
            status=EnrichmentStatus.FAILED,
            records_input=records_input,
            records_enriched=records_enriched,
            records_errored=records_errored,
            dq_error_rate=dq_error_rate,
            duration_seconds=duration,
            started_at=started_at,
            completed_at=completed_at,
            error_message=(
                f"DQ error rate {dq_error_rate:.2%} "
                f"exceeds threshold {hard_threshold:.2%}"
            ),
        )

    def _build_timeout_result(
        self,
        enricher: EnricherConfig,
        records_input: int,
        started_at: datetime,
    ) -> EnrichmentResult:
        duration = (datetime.now(tz=UTC) - started_at).total_seconds()
        self._logger.warning(
            "Enricher timed out",
            enricher=enricher.pipeline,
            timeout_seconds=enricher.timeout_seconds,
            duration_seconds=duration,
        )
        return EnrichmentResult.timeout(
            enricher_name=enricher.pipeline,
            timeout_seconds=enricher.timeout_seconds,
            records_input=records_input,
        )

    @staticmethod
    def _extract_runner_stats(
        runner: PipelineRunner,
        records_input: int,
    ) -> tuple[int, int, float]:
        """Extract enrichment stats from runner executor."""
        executor = getattr(runner, "_executor", None)
        records_enriched = getattr(executor, "records_silver", 0) if executor else 0
        records_errored = getattr(executor, "records_quarantined", 0) if executor else 0
        dq_error_rate = records_errored / records_input if records_input > 0 else 0.0
        return records_enriched, records_errored, dq_error_rate

    def _handle_enricher_error(
        self,
        error: Exception,
        enricher: EnricherConfig,
        records_input: int,
        started_at: datetime,
        *,
        reason_code: str | None = None,
    ) -> EnrichmentResult:
        """Handle enricher execution error."""
        duration = (datetime.now(tz=UTC) - started_at).total_seconds()
        log_kwargs: JsonDict = {
            "enricher": enricher.pipeline,
            "error": str(error),
            "error_type": type(error).__name__,
            "required": enricher.required,
        }
        if reason_code:
            log_kwargs["reason_code"] = reason_code

        if enricher.required:
            self._logger.error("Required enricher failed", **log_kwargs)
            raise

        self._logger.warning("Optional enricher failed", **log_kwargs)
        return EnrichmentResult.failed(
            enricher_name=enricher.pipeline,
            error_message=str(error),
            records_input=records_input,
            duration_seconds=duration,
        )

    def _process_results(
        self,
        enricher_names: list[str],
        results: list[EnrichmentResult | BaseException],
    ) -> dict[str, EnrichmentResult]:
        """Process gathered results, handling exceptions."""
        processed: dict[str, EnrichmentResult] = {}

        for name, result in zip(enricher_names, results, strict=True):
            if isinstance(result, BaseException):
                # Should not happen for required (already re-raised)
                processed[name] = EnrichmentResult.failed(
                    enricher_name=name,
                    error_message=str(result),
                )
            else:
                processed[name] = result

        return processed


__all__ = ["EnrichmentCoordinatorResultMixin"]
