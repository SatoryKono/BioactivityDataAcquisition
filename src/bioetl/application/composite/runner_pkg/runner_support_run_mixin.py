# Host attrs/methods provided by concrete composition (PD2 W1).
"""Preflight, seed, and enricher runtime helpers for CompositePipelineRunner."""

from __future__ import annotations

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointState,
)
from bioetl.application.composite.runner_pkg.runner_support_flow import (
    run_preflight_validation,
    validate_config_consistency,
)
from bioetl.application.composite.runner_pkg.runner_support_policy import (
    build_enrichers_to_run,
    build_preflight_validation_context,
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
    _PreparedPreflightValidationContext,
)
from bioetl.domain.composite import EnricherConfig
from bioetl.domain.composite.result import EnrichmentResult, SeedResult
from bioetl.domain.exceptions import InvalidStateError

__all__ = ["_CompositeRunnerSupportRunMixin"]


class _CompositeRunnerSupportRunMixin:
    """Preflight gates, seed execution, and enricher runtime policy."""

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
        """Save checkpoint with graceful error handling; False means non-fatal failure."""
        checkpoint_saved: bool = await save_checkpoint_safe(self, state, operation)
        return checkpoint_saved

    async def _run_seed(self: _CompositeRunnerSupportHostProtocol) -> SeedResult:
        """Run the seed pipeline."""
        return await run_seed(self)

    def _get_enrichers_to_run(
        self: _CompositeRunnerSupportHostProtocol,
        state: CompositeCheckpointState,
    ) -> list[EnricherConfig]:
        """Return enrichers that still need to run under runtime policy."""
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
