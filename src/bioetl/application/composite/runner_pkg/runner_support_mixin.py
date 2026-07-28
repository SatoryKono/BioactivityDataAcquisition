# pyright: reportUninitializedInstanceVariable=false
# Host attrs/methods provided by concrete composition (PD2 W1).
# pyright: reportArgumentType=false
# Boundary object/payload typing residual at this module.
"""Support helpers for CompositePipelineRunner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointService,
    CompositeCheckpointState,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
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
from bioetl.application.composite.runner_pkg.runner_support_flow import (
    build_correlation_log_context,
    run_preflight_validation,
    validate_config_consistency,
)
from bioetl.application.composite.runner_pkg.runner_support_policy import (
    build_enrichers_to_run,
    build_preflight_validation_context,
    build_result_build_request,
    can_run_enricher,
    get_preflight_skip_reason,
    get_required_enricher_failure,
)
from bioetl.application.composite.runner_pkg.runner_support_runtime import (
    run_seed,
    save_checkpoint_safe,
)
from bioetl.application.composite.runner_pkg.runner_support_types import (
    _CompositeRunnerSupportHostProtocol,
    _PreparedCompositeResultContext,
    _PreparedPreflightValidationContext,
)
from bioetl.application.composite.runtime_models import (
    CompositeExecutionContext,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite import CompositeConfig, EnricherConfig
from bioetl.domain.composite.result import CompositeResult, EnrichmentResult, SeedResult
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.ports import (
    ClockPort,
    ExecutionMetricsRunnerPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)

__all__ = ["CompositeRunnerSupportMixin"]


class CompositeRunnerSupportMixin:
    """Mixin with utility and side-effect helpers."""

    _config: CompositeConfig
    _runtime: CompositeRuntimeConfig
    _seed_runner_factory: Callable[[], ExecutionMetricsRunnerPort]
    _checkpoint_manager: CompositeCheckpointService
    _logger: LoggerPort
    _metrics: MetricsPort | None
    _tracing: TracingPort | None
    _observer: CompositeLifecycleObserverService
    _run_id_str: str
    _clock: ClockPort | None
    _start_time: float | None
    _started_at: datetime | None
    _original_run_id: str | None
    _preflight_validator: CompositePreflightValidationService | None
    _fsm: FSMStateHelperService

    def _build_correlation_log_context(self, **extra: object) -> dict[str, object]:
        """Build a stable correlation envelope for composite critical logs."""
        return dict(build_correlation_log_context(self, **extra))

    def _build_composite_result(
        self: _CompositeRunnerSupportHostProtocol,
        artifacts: CompositeExecutionContext,
    ) -> CompositeResult:
        """Build the final CompositeResult."""
        return build_composite_result(
            request=self._create_result_build_request(artifacts),
            logger=self._logger,
            observer=self._observer,
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
            observer=self._observer,
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
            start_time=self._start_time,
            started_at=self._started_at,
            original_run_id=self._original_run_id,
            required_enrichers=self._config.required_enrichers,
            required_dependencies=self._config.required_dependencies,
        )

    def _validate_config_consistency(
        self: _CompositeRunnerSupportHostProtocol,
    ) -> None:
        """Validate configuration consistency and log anomalies."""
        validate_config_consistency(self)

    def _run_preflight_validation(
        self: _CompositeRunnerSupportHostProtocol,
    ) -> None:
        """Run preflight validation for field_priorities configuration."""
        run_preflight_validation(self)

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
        checkpoint_saved: bool = await save_checkpoint_safe(self, state, operation)
        return checkpoint_saved

    async def _run_seed(self: _CompositeRunnerSupportHostProtocol) -> SeedResult:
        """Run the seed pipeline."""
        return await run_seed(self)

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
