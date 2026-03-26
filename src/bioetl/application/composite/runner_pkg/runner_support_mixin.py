"""Support helpers for CompositePipelineRunner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointService,
    CompositeCheckpointState,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.preflight_validator import (
    CompositePreflightValidationService,
)
from bioetl.application.composite.runner_pkg.runner_completion_helpers import (
    CompositeResultBuildRequest,
    build_composite_result,
    finalize_composite_result,
    log_composite_completion,
    prepare_composite_result_context,
)
from bioetl.application.composite.runner_pkg.runner_constants import (
    CHECKPOINT_NON_FATAL_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_models import (
    CompositeExecutionContext,
    CompositeRuntimeConfig,
)
from bioetl.application.composite.runner_pkg.runner_support_policy import (
    build_enrichers_to_run,
    build_preflight_validation_context,
    build_result_build_request,
    can_run_enricher,
    get_preflight_skip_reason,
    get_required_enricher_failure,
)
from bioetl.application.composite.runner_pkg.runner_support_types import (
    _CompositeRunnerSupportHostProtocol,
    _PreparedCompositeResultContext,
    _PreparedPreflightValidationContext,
)
from bioetl.domain.composite.config import CompositeConfig, EnricherConfig
from bioetl.domain.composite.result import CompositeResult, EnrichmentResult, SeedResult
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions import BioETLError, InvalidStateError
from bioetl.domain.ports import ExecutionMetricsRunnerPort, LoggerPort

__all__ = ["CompositeRunnerSupportMixin"]


def _normalize_optional_anchor(value: object) -> str | None:
    """Return stripped text anchors while ignoring mock/empty placeholders."""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _expected_effective_config_hash(
    host: _CompositeRunnerSupportHostProtocol,
) -> str | None:
    """Return effective-config hash anchor when checkpoint manager exposes it."""
    checkpoint_manager = getattr(host, "_checkpoint_manager", None)
    return _normalize_optional_anchor(
        getattr(checkpoint_manager, "expected_effective_config_hash", None)
    )


def _expected_contract_ref(host: _CompositeRunnerSupportHostProtocol) -> str | None:
    """Return contract-ref anchor from checkpoint manager or composite config."""
    checkpoint_manager = getattr(host, "_checkpoint_manager", None)
    return _normalize_optional_anchor(
        getattr(checkpoint_manager, "expected_contract_ref", None)
    ) or _normalize_optional_anchor(getattr(host._config, "name", None))


def _expected_contract_version(
    host: _CompositeRunnerSupportHostProtocol,
) -> str | None:
    """Return contract-version anchor from checkpoint manager or config."""
    checkpoint_manager = getattr(host, "_checkpoint_manager", None)
    return _normalize_optional_anchor(
        getattr(checkpoint_manager, "expected_contract_version", None)
    ) or _normalize_optional_anchor(getattr(host._config, "version", None))


class CompositeRunnerSupportMixin:
    """Mixin with utility and side-effect helpers."""

    _config: CompositeConfig
    _runtime: CompositeRuntimeConfig
    _seed_runner_factory: Callable[[], ExecutionMetricsRunnerPort]
    _checkpoint_manager: CompositeCheckpointService
    _logger: LoggerPort
    _run_id_str: str
    _started_at: datetime | None
    _original_run_id: str | None
    _preflight_validator: CompositePreflightValidationService | None
    _fsm: FSMStateHelperService

    def _build_correlation_log_context(self, **extra: object) -> dict[str, object]:
        """Build a stable correlation envelope for composite critical logs."""
        context: dict[str, object] = {
            "composite": self._config.name,
            "run_id": self._run_id_str,
            "composite_run_id": self._run_id_str,
        }
        effective_config_hash = _expected_effective_config_hash(self)
        if effective_config_hash is not None:
            context["effective_config_hash"] = effective_config_hash
        contract_ref = _expected_contract_ref(self)
        if contract_ref is not None:
            context["contract_ref"] = contract_ref
        contract_version = _expected_contract_version(self)
        if contract_version is not None:
            context["contract_version"] = contract_version
        context.update(extra)
        return context

    def _build_composite_result(
        self: _CompositeRunnerSupportHostProtocol,
        artifacts: CompositeExecutionContext,
    ) -> CompositeResult:
        """Build the final CompositeResult."""
        return build_composite_result(
            request=self._create_result_build_request(artifacts),
            logger=self._logger,
        )

    def _prepare_composite_result_context(
        self: _CompositeRunnerSupportHostProtocol,
        artifacts: CompositeExecutionContext,
    ) -> _PreparedCompositeResultContext:
        """Resolve completion metadata before final CompositeResult assembly."""
        return prepare_composite_result_context(
            request=self._create_result_build_request(artifacts),
            logger=self._logger,
        )

    def _log_composite_completion(
        self: _CompositeRunnerSupportHostProtocol,
        context: _PreparedCompositeResultContext,
    ) -> None:
        """Emit the canonical completion log payload for composite runs."""
        log_composite_completion(
            request=self._create_result_build_request(context.artifacts),
            context=context,
            logger=self._logger,
        )

    def _finalize_composite_result(
        self: _CompositeRunnerSupportHostProtocol,
        context: _PreparedCompositeResultContext,
    ) -> CompositeResult:
        """Assemble the final CompositeResult from the prepared completion context."""
        return finalize_composite_result(
            request=self._create_result_build_request(context.artifacts),
            context=context,
        )

    def _create_result_build_request(
        self: _CompositeRunnerSupportHostProtocol,
        artifacts: CompositeExecutionContext,
    ) -> CompositeResultBuildRequest:
        """Build an explicit result-assembly request for completion helpers."""
        return build_result_build_request(
            artifacts=artifacts,
            composite_name=self._config.name,
            run_id=self._run_id_str,
            started_at=self._started_at,
            original_run_id=self._original_run_id,
            required_enrichers=self._config.required_enrichers,
            required_dependencies=self._config.required_dependencies,
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
                **self._build_correlation_log_context(
                    expected_required=list(expected_required),
                    actual_required=list(actual_required),
                    note="This may indicate a bug in CompositeConfig",
                ),
            )

        if not expected_required and self._config.enrichers:
            self._logger.info(
                "All enrichers are optional",
                **self._build_correlation_log_context(
                    enricher_count=len(self._config.enrichers),
                    note="Pipeline will succeed even if all enrichers fail",
                ),
            )

    def _run_preflight_validation(
        self: _CompositeRunnerSupportHostProtocol,
    ) -> None:
        """Run preflight validation for field_priorities configuration."""
        context = self._prepare_preflight_validation_context()
        if context is None:
            self._logger.debug(
                "Preflight validation skipped",
                **self._build_correlation_log_context(
                    stage="preflight_validation",
                    reason=self._get_preflight_skip_reason(),
                ),
            )
            return

        self._logger.info(
            PipelineEvent.phase_started("preflight_validation"),
            **self._build_correlation_log_context(
                stage="preflight_validation",
                field_count=context.field_count,
            ),
        )

        result = context.validator.validate(
            self._config,
            fail_on_error=True,
        )
        context.validator.log_resolved_field_sources(result, self._config.name)

        self._logger.info(
            PipelineEvent.phase_completed("preflight_validation"),
            **self._build_correlation_log_context(
                stage="preflight_validation",
                fields_validated=len(result.resolved_fields),
                warnings=len(result.warnings),
            ),
        )

    def _prepare_preflight_validation_context(
        self: _CompositeRunnerSupportHostProtocol,
    ) -> _PreparedPreflightValidationContext | None:
        """Build the canonical preflight validation context when validation can run."""
        field_priorities = getattr(self._config.merge, "field_priorities", ())
        return build_preflight_validation_context(
            validator=self._preflight_validator,
            field_priorities=field_priorities,
        )

    def _get_preflight_skip_reason(
        self: _CompositeRunnerSupportHostProtocol,
    ) -> str | None:
        """Return skip reason for preflight validation when it should not run."""
        field_priorities = getattr(self._config.merge, "field_priorities", ())
        return get_preflight_skip_reason(
            validator=self._preflight_validator,
            field_priorities=field_priorities,
        )

    async def _save_checkpoint_safe(
        self: _CompositeRunnerSupportHostProtocol,
        state: CompositeCheckpointState,
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
                **self._build_correlation_log_context(
                    operation=operation,
                    error=str(error),
                    error_type=type(error).__name__,
                    note="Resume capability may be affected",
                ),
            )
            return False
        except BioETLError as error:
            self._logger.warning(
                "checkpoint_save_failed",
                **self._build_correlation_log_context(
                    operation=operation,
                    error=str(error),
                    error_type=type(error).__name__,
                    reason_code="unexpected_bioetl_error",
                    note="Resume capability may be affected",
                ),
            )
            return False

    async def _run_seed(self: _CompositeRunnerSupportHostProtocol) -> SeedResult:
        """Run the seed pipeline."""
        self._logger.info(
            "Running seed pipeline",
            **self._build_correlation_log_context(
                stage="seed",
                seed_pipeline=self._config.seed.pipeline,
            ),
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
        state: CompositeCheckpointState,
    ) -> list[EnricherConfig]:
        """Determine which enrichers should be run.

        Returns:
            List of EnricherConfig entries that have not been completed and match
            the current runtime filters (required_only, enrich_only, force_enricher).
        """
        return build_enrichers_to_run(
            self._config.enrichers,
            completed_enrichers=state.completed_enrichers,
            required_only=self._runtime.required_only,
            enrich_only=self._runtime.enrich_only,
            force_enricher=self._runtime.force_enricher,
        )

    def _should_run_enricher(
        self: _CompositeRunnerSupportHostProtocol,
        enricher: EnricherConfig,
        state: CompositeCheckpointState,
    ) -> bool:
        """Return whether an enricher should execute under current runtime policy."""
        return can_run_enricher(
            enricher,
            completed_enrichers=state.completed_enrichers,
            required_only=self._runtime.required_only,
            enrich_only=self._runtime.enrich_only,
            force_enricher=self._runtime.force_enricher,
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
        return get_required_enricher_failure(
            required_enrichers=self._config.required_enrichers,
            enrichment_results=enrichment_results,
        )
