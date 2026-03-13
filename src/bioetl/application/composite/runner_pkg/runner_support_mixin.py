"""Support helpers for CompositePipelineRunner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from bioetl.application.composite.runner_pkg.runner_constants import (
    CHECKPOINT_NON_FATAL_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_helpers import (
    calculate_had_warnings,
)
from bioetl.domain.composite.result import CompositeResult, EnrichmentResult, SeedResult
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions import BioETLError, InvalidStateError

if TYPE_CHECKING:
    from bioetl.application.composite import (
        checkpoint as composite_checkpoint,
    )
    from bioetl.application.composite import (
        fsm_helper as composite_fsm_helper,
    )
    from bioetl.application.composite import (
        preflight_validator as composite_preflight_validator,
    )
    from bioetl.application.composite.runner_pkg import (
        runner as composite_runner_module,
    )
    from bioetl.domain import ports as domain_ports
    from bioetl.domain.composite import (
        config as composite_config,
    )


class _CompositeRunnerSupportHostProtocol(Protocol):
    _config: composite_config.CompositeConfig
    _runtime: composite_runner_module.CompositeRuntimeConfig
    _seed_runner_factory: Callable[[], domain_ports.ExecutionMetricsRunnerPort]
    _checkpoint_manager: composite_checkpoint.CompositeCheckpointService
    _logger: domain_ports.LoggerPort
    _run_id_str: str
    _started_at: datetime | None
    _preflight_validator: (
        composite_preflight_validator.CompositePreflightValidationService | None
    )
    _fsm: composite_fsm_helper.FSMStateHelperService

    def _get_preflight_skip_reason(self) -> str | None: ...

    def _should_run_enricher(
        self,
        enricher: composite_config.EnricherConfig,
        state: composite_checkpoint.CompositeCheckpointState,
    ) -> bool: ...

    def _get_required_enricher_failure(
        self,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> str | None: ...

    def _prepare_preflight_validation_context(
        self,
    ) -> _PreparedPreflightValidationContext | None: ...

    def _prepare_composite_result_context(
        self,
        artifacts: composite_runner_module.CompositeExecutionContext,
    ) -> _PreparedCompositeResultContext: ...

    def _log_composite_completion(
        self,
        context: _PreparedCompositeResultContext,
    ) -> None: ...

    def _finalize_composite_result(
        self,
        context: _PreparedCompositeResultContext,
    ) -> CompositeResult: ...


@dataclass(frozen=True, slots=True)
class _PreparedPreflightValidationContext:
    """Resolved runtime data for preflight validation execution."""

    validator: composite_preflight_validator.CompositePreflightValidationService
    field_count: int


@dataclass(frozen=True, slots=True)
class _PreparedCompositeResultContext:
    """Resolved completion metadata used for final result assembly."""

    artifacts: composite_runner_module.CompositeExecutionContext
    completed_at: datetime
    total_duration: float
    had_warnings: bool


__all__ = ["CompositeRunnerSupportMixin"]


class CompositeRunnerSupportMixin:
    """Mixin with utility and side-effect helpers."""

    _config: composite_config.CompositeConfig
    _runtime: composite_runner_module.CompositeRuntimeConfig
    _seed_runner_factory: Callable[[], domain_ports.ExecutionMetricsRunnerPort]
    _checkpoint_manager: composite_checkpoint.CompositeCheckpointService
    _logger: domain_ports.LoggerPort
    _run_id_str: str
    _started_at: datetime | None
    _preflight_validator: (
        composite_preflight_validator.CompositePreflightValidationService | None
    )
    _fsm: composite_fsm_helper.FSMStateHelperService

    def _build_composite_result(
        self: _CompositeRunnerSupportHostProtocol,
        artifacts: composite_runner_module.CompositeExecutionContext,
    ) -> CompositeResult:
        """Build the final CompositeResult."""
        context = self._prepare_composite_result_context(artifacts)
        self._log_composite_completion(context)
        return self._finalize_composite_result(context)

    def _prepare_composite_result_context(
        self: _CompositeRunnerSupportHostProtocol,
        artifacts: composite_runner_module.CompositeExecutionContext,
    ) -> _PreparedCompositeResultContext:
        """Resolve completion metadata before final CompositeResult assembly."""
        completed_at = datetime.now(tz=UTC)
        started = self._started_at or completed_at
        had_warnings = calculate_had_warnings(
            artifacts.enrichment_results,
            frozenset(self._config.required_enrichers),
            self._config.name,
            self._logger,
        )
        return _PreparedCompositeResultContext(
            artifacts=artifacts,
            completed_at=completed_at,
            total_duration=(completed_at - started).total_seconds(),
            had_warnings=had_warnings,
        )

    def _log_composite_completion(
        self: _CompositeRunnerSupportHostProtocol,
        context: _PreparedCompositeResultContext,
    ) -> None:
        """Emit the canonical completion log payload for composite runs."""
        log_kwargs: dict[str, object] = {
            "composite": self._config.name,
            "run_id": self._run_id_str,
            "duration_seconds": context.total_duration,
        }
        if context.had_warnings:
            log_kwargs["status"] = "completed_with_warnings"
            log_kwargs["had_warnings"] = True
        self._logger.info(PipelineEvent.COMPLETE, **log_kwargs)

    def _finalize_composite_result(
        self: _CompositeRunnerSupportHostProtocol,
        context: _PreparedCompositeResultContext,
    ) -> CompositeResult:
        """Assemble the final CompositeResult from the prepared completion context."""
        artifacts = context.artifacts
        return CompositeResult(
            composite_name=self._config.name,
            composite_run_id=self._run_id_str,
            seed_result=artifacts.seed_result,
            dependency_results=artifacts.dependency_results,
            enrichment_results=artifacts.enrichment_results,
            merge_result=artifacts.merge_result,
            total_duration_seconds=context.total_duration,
            started_at=self._started_at,
            completed_at=context.completed_at,
            had_warnings=context.had_warnings,
            _required_enrichers=frozenset(self._config.required_enrichers),
            _required_dependencies=frozenset(self._config.required_dependencies),
        )

    def _validate_config_consistency(
        self: _CompositeRunnerSupportHostProtocol,
    ) -> None:
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

    def _run_preflight_validation(
        self: _CompositeRunnerSupportHostProtocol,
    ) -> None:
        """Run preflight validation for field_priorities configuration."""
        context = self._prepare_preflight_validation_context()
        if context is None:
            self._logger.debug(
                "Preflight validation skipped",
                composite=self._config.name,
                reason=self._get_preflight_skip_reason(),
            )
            return

        self._logger.info(
            PipelineEvent.phase_started("preflight_validation"),
            composite=self._config.name,
            run_id=self._run_id_str,
            field_count=context.field_count,
        )

        result = context.validator.validate(
            self._config,
            fail_on_error=True,
        )
        context.validator.log_resolved_field_sources(result, self._config.name)

        self._logger.info(
            PipelineEvent.phase_completed("preflight_validation"),
            composite=self._config.name,
            run_id=self._run_id_str,
            fields_validated=len(result.resolved_fields),
            warnings=len(result.warnings),
        )

    def _prepare_preflight_validation_context(
        self: _CompositeRunnerSupportHostProtocol,
    ) -> _PreparedPreflightValidationContext | None:
        """Build the canonical preflight validation context when validation can run."""
        if self._get_preflight_skip_reason() is not None:
            return None

        validator = self._preflight_validator
        assert validator is not None
        return _PreparedPreflightValidationContext(
            validator=validator,
            field_count=len(self._config.merge.field_priorities),
        )

    def _get_preflight_skip_reason(
        self: _CompositeRunnerSupportHostProtocol,
    ) -> str | None:
        """Return skip reason for preflight validation when it should not run."""
        if self._preflight_validator is None:
            return "preflight_validator not configured"
        if not self._config.merge.field_priorities:
            return "no field_priorities configured"
        return None

    async def _save_checkpoint_safe(
        self: _CompositeRunnerSupportHostProtocol,
        state: composite_checkpoint.CompositeCheckpointState,
        operation: str,
    ) -> bool:
        """Save checkpoint with graceful error handling.

        Returns:
            True if the checkpoint was saved successfully, False if a non-fatal error
            occurred (resume capability may be degraded).
        """
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

    async def _run_seed(self: _CompositeRunnerSupportHostProtocol) -> SeedResult:
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

        metrics = runner.execution_metrics
        records_extracted = int(metrics["records_fetched"])
        records_silver = int(metrics["records_silver"])

        return SeedResult(
            pipeline_name=self._config.seed.pipeline,
            records_extracted=records_extracted,
            records_silver=records_silver,
            keys_generated=records_silver,
            duration_seconds=(completed_at - started_at).total_seconds(),
            started_at=started_at,
            completed_at=completed_at,
        )

    def _get_enrichers_to_run(
        self: _CompositeRunnerSupportHostProtocol,
        state: composite_checkpoint.CompositeCheckpointState,
    ) -> list[composite_config.EnricherConfig]:
        """Determine which enrichers should be run.

        Returns:
            List of EnricherConfig entries that have not been completed and match
            the current runtime filters (required_only, enrich_only, force_enricher).
        """
        return [
            enricher
            for enricher in self._config.enrichers
            if self._should_run_enricher(enricher, state)
        ]

    def _should_run_enricher(
        self: _CompositeRunnerSupportHostProtocol,
        enricher: composite_config.EnricherConfig,
        state: composite_checkpoint.CompositeCheckpointState,
    ) -> bool:
        """Return whether an enricher should execute under current runtime policy."""
        if (
            enricher.pipeline in state.completed_enrichers
            and self._runtime.force_enricher != enricher.pipeline
        ):
            return False

        if self._runtime.required_only and not enricher.required:
            return False

        return not (
            self._runtime.enrich_only
            and enricher.pipeline not in self._runtime.enrich_only
        )

    def _check_required_enrichers(
        self: _CompositeRunnerSupportHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:
        """Check that all required enrichers succeeded."""
        failure = self._get_required_enricher_failure(enrichment_results)
        if failure is not None:
            raise InvalidStateError(failure)

    def _get_required_enricher_failure(
        self: _CompositeRunnerSupportHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> str | None:
        """Return failure reason for required enricher validation, if any."""
        for enricher_name in self._config.required_enrichers:
            result = enrichment_results.get(enricher_name)
            if result is None:
                return f"Required enricher '{enricher_name}' did not run"
            if not result.is_success:
                return (
                    f"Required enricher '{enricher_name}' failed: "
                    f"{result.error_message or result.status.value}"
                )
        return None
