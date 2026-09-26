# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Support-layer dispatchers and recording seams for stage orchestration."""

from __future__ import annotations

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointState,
)
from bioetl.application.composite.runner_pkg.runner_stage_support_types import (
    _CompositeRunnerStageSupportHostProtocol,
)
from bioetl.domain.composite import EnricherConfig
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    SeedResult,
)

__all__ = ["_CompositeRunnerStageSupportDispatchMixin"]


class _CompositeRunnerStageSupportDispatchMixin:
    """Dispatchers and recording seams (host methods via Protocol/MRO)."""

    async def _call_save_checkpoint_safe(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:
        """Invoke support-layer checkpoint save helper."""
        return await self._save_checkpoint_safe(state, operation)

    async def _call_run_seed(
        self: _CompositeRunnerStageSupportHostProtocol,
    ) -> SeedResult:
        """Invoke support-layer seed runner helper."""
        return await self._run_seed()

    def _call_get_enrichers_to_run(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
    ) -> list[EnricherConfig]:
        """Invoke support-layer enricher selection helper."""
        return self._get_enrichers_to_run(state)

    def _call_check_required_enrichers(
        self: _CompositeRunnerStageSupportHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:
        """Invoke support-layer required-enricher validation helper."""
        self._check_required_enrichers(enrichment_results)

    def _record_seed_stage_started(
        self: _CompositeRunnerStageSupportHostProtocol,
    ) -> None:
        """Default no-op seam for hosts without control-plane ledger wiring."""

    def _record_seed_stage_completed(
        self: _CompositeRunnerStageSupportHostProtocol,
        seed_result: SeedResult,
    ) -> None:
        """Default no-op seam for hosts without control-plane ledger wiring."""
        del seed_result

    def _record_dependencies_stage_started(
        self: _CompositeRunnerStageSupportHostProtocol,
        dependency_pipeline_names: list[str],
    ) -> None:
        """Default no-op seam for hosts without control-plane ledger wiring."""
        del dependency_pipeline_names

    def _record_dependencies_stage_completed(
        self: _CompositeRunnerStageSupportHostProtocol,
        dependency_results: dict[str, DependencyResult],
    ) -> None:
        """Default no-op seam for hosts without control-plane ledger wiring."""
        del dependency_results

    def _record_enrichment_stage_started(
        self: _CompositeRunnerStageSupportHostProtocol,
        enricher_names: list[str],
    ) -> None:
        """Default no-op seam for hosts without control-plane ledger wiring."""
        del enricher_names

    def _record_enrichment_stage_completed(
        self: _CompositeRunnerStageSupportHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:
        """Default no-op seam for hosts without control-plane ledger wiring."""
        del enrichment_results
