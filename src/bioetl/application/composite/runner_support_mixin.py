"""Support helpers for CompositePipelineRunner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from bioetl.application.composite.runner_constants import (
    CHECKPOINT_NON_FATAL_ERRORS,
    DQ_REPORT_NON_FATAL_ERRORS,
    QUARANTINE_WRITE_NON_FATAL_ERRORS,
)
from bioetl.application.composite.runner_helpers import calculate_had_warnings
from bioetl.domain.composite.result import CompositeResult, EnrichmentResult, SeedResult
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions import BioETLError

if TYPE_CHECKING:
    from bioetl.application.composite.checkpoint import (
        CompositeCheckpointService,
        CompositeCheckpointState,
    )
    from bioetl.application.composite.fsm_helper import FSMStateHelperService
    from bioetl.application.composite.preflight_validator import (
        CompositePreflightValidationService,
    )
    from bioetl.application.composite.runner import CompositeRuntimeConfig
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.config import CompositeConfig, EnricherConfig
    from bioetl.domain.composite.result import DependencyResult, MergeResult
    from bioetl.domain.ports import LoggerPort, MetricsPort, QuarantinePort
    from bioetl.domain.types import RunID

__all__ = ["CompositeRunnerSupportHelper"]


class CompositeRunnerSupportHelper:
    """Mixin with utility and side-effect helpers."""

    _config: CompositeConfig
    _runtime: CompositeRuntimeConfig
    _seed_runner_factory: Callable[[], PipelineRunner]
    _checkpoint_manager: CompositeCheckpointService
    _logger: LoggerPort
    _run_id_str: str
    _run_id: RunID
    _started_at: datetime | None
    _dq_report_service: DQReportService | None
    _preflight_validator: CompositePreflightValidationService | None
    _quarantine_port: QuarantinePort | None
    _metrics: MetricsPort | None
    _fsm: FSMStateHelperService

    def _build_composite_result(
        self,
        seed_result: SeedResult,
        dependency_results: dict[str, DependencyResult],
        enrichment_results: dict[str, EnrichmentResult],
        merge_result: MergeResult | None,
    ) -> CompositeResult:
        """Build the final CompositeResult."""
        completed_at = datetime.now(tz=UTC)
        started = self._started_at or completed_at
        total_duration = (completed_at - started).total_seconds()

        had_warnings = calculate_had_warnings(
            enrichment_results,
            frozenset(self._config.required_enrichers),
            self._config.name,
            self._logger,
        )

        if had_warnings:
            self._logger.info(
                PipelineEvent.COMPLETE,
                composite=self._config.name,
                run_id=self._run_id_str,
                duration_seconds=total_duration,
                status="completed_with_warnings",
                had_warnings=True,
            )
        else:
            self._logger.info(
                PipelineEvent.COMPLETE,
                composite=self._config.name,
                run_id=self._run_id_str,
                duration_seconds=total_duration,
            )

        return CompositeResult(
            composite_name=self._config.name,
            composite_run_id=self._run_id_str,
            seed_result=seed_result,
            dependency_results=dependency_results,
            enrichment_results=enrichment_results,
            merge_result=merge_result,
            total_duration_seconds=total_duration,
            started_at=self._started_at,
            completed_at=completed_at,
            had_warnings=had_warnings,
            _required_enrichers=frozenset(self._config.required_enrichers),
            _required_dependencies=frozenset(self._config.required_dependencies),
        )

    def _validate_config_consistency(self) -> None:
        """Validate configuration consistency and log anomalies."""
        expected_required = frozenset(
            enricher.pipeline
            for enricher in self._config.enrichers
            if enricher.required
        )
        actual_required = frozenset(self._config.required_enrichers)

        if expected_required != actual_required:
            self._logger.warning(
                "Config inconsistency: required_enrichers mismatch",
                composite=self._config.name,
                expected_required=list(expected_required),
                actual_required=list(actual_required),
                note="This may indicate a bug in CompositeConfig",
            )

        if not expected_required and self._config.enrichers:
            self._logger.info(
                "All enrichers are optional",
                composite=self._config.name,
                enricher_count=len(self._config.enrichers),
                note="Pipeline will succeed even if all enrichers fail",
            )

    def _run_preflight_validation(self) -> None:
        """Run preflight validation for field_priorities configuration."""
        if self._preflight_validator is None:
            self._logger.debug(
                "Preflight validation skipped",
                composite=self._config.name,
                reason="preflight_validator not configured",
            )
            return

        if not self._config.merge.field_priorities:
            self._logger.debug(
                "Preflight validation skipped",
                composite=self._config.name,
                reason="no field_priorities configured",
            )
            return

        self._logger.info(
            PipelineEvent.phase_started("preflight_validation"),
            composite=self._config.name,
            run_id=self._run_id_str,
            field_count=len(self._config.merge.field_priorities),
        )

        result = self._preflight_validator.validate(
            self._config,
            fail_on_error=True,
        )
        self._preflight_validator.log_resolved_field_sources(result, self._config.name)

        self._logger.info(
            PipelineEvent.phase_completed("preflight_validation"),
            composite=self._config.name,
            run_id=self._run_id_str,
            fields_validated=len(result.resolved_fields),
            warnings=len(result.warnings),
        )

    async def _save_checkpoint_safe(
        self,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:
        """Save checkpoint with graceful error handling."""
        try:
            await self._checkpoint_manager.save(state)
            return True
        except CHECKPOINT_NON_FATAL_ERRORS as error:
            self._logger.warning(
                "checkpoint_save_failed",
                composite=self._config.name,
                run_id=self._run_id_str,
                operation=operation,
                error=str(error),
                error_type=type(error).__name__,
                note="Resume capability may be affected",
            )
            return False
        except BioETLError as error:
            self._logger.warning(
                "checkpoint_save_failed",
                composite=self._config.name,
                run_id=self._run_id_str,
                operation=operation,
                error=str(error),
                error_type=type(error).__name__,
                reason_code="unexpected_bioetl_error",
                note="Resume capability may be affected",
            )
            return False

    async def _run_seed(self) -> SeedResult:
        """Run the seed pipeline."""
        self._logger.info(
            "Running seed pipeline",
            composite=self._config.name,
            seed_pipeline=self._config.seed.pipeline,
        )

        started_at = datetime.now(tz=UTC)
        runner = self._seed_runner_factory()
        await runner.run()
        completed_at = datetime.now(tz=UTC)

        records_extracted = getattr(runner, "_executor", None)
        records_silver = 0
        if records_extracted:
            records_silver = getattr(records_extracted, "records_silver", 0)

        return SeedResult(
            pipeline_name=self._config.seed.pipeline,
            records_extracted=records_extracted.records_fetched
            if records_extracted
            else 0,
            records_silver=records_silver,
            keys_generated=records_silver,
            duration_seconds=(completed_at - started_at).total_seconds(),
            started_at=started_at,
            completed_at=completed_at,
        )

    def _get_enrichers_to_run(
        self,
        state: CompositeCheckpointState,
    ) -> list[EnricherConfig]:
        """Determine which enrichers should be run."""
        enrichers_to_run: list[EnricherConfig] = []

        for enricher in self._config.enrichers:
            if (
                enricher.pipeline in state.completed_enrichers
                and self._runtime.force_enricher != enricher.pipeline
            ):
                continue

            if self._runtime.required_only and not enricher.required:
                continue
            if (
                self._runtime.enrich_only
                and enricher.pipeline not in self._runtime.enrich_only
            ):
                continue

            enrichers_to_run.append(enricher)

        return enrichers_to_run

    def _check_required_enrichers(
        self,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:
        """Check that all required enrichers succeeded."""
        for enricher_name in self._config.required_enrichers:
            result = enrichment_results.get(enricher_name)
            if result is None:
                raise RuntimeError(f"Required enricher '{enricher_name}' did not run")
            if not result.is_success:
                raise RuntimeError(
                    f"Required enricher '{enricher_name}' failed: "
                    f"{result.error_message or result.status.value}"
                )

    async def _generate_dq_reports(self, merge_result: MergeResult) -> None:
        """Generate DQ reports for composite pipeline."""
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

    async def _write_cv_quarantine(self, merge_result: MergeResult) -> None:
        """Write cross-validation quarantine records if any exist."""
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

        if written > 0:
            self._logger.info(
                "Cross-validation quarantine records written",
                composite=self._config.name,
                quarantine_count=written,
            )
            if self._metrics:
                self._metrics.inc_quarantine_records(
                    pipeline=pipeline_name,
                    reason="cross_validation",
                    count=written,
                )
