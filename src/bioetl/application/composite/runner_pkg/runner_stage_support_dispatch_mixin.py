# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Support-layer dispatch stubs and recording seams for stage orchestration."""

from __future__ import annotations

from collections.abc import Callable

import polars as pl

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointService,
    CompositeCheckpointState,
)
from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
from bioetl.application.composite.dependency_coordinator import (
    DependencyCoordinatorService,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.runner_pkg.runner_stage_support_types import (
    _CompositeRunnerStageSupportHostProtocol,
)
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.composite import CompositeConfig, EnricherConfig
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    SeedResult,
)
from bioetl.domain.ports import ExecutionMetricsRunnerPort, LoggerPort

__all__ = ["_CompositeRunnerStageSupportDispatchMixin"]


class _CompositeRunnerStageSupportDispatchMixin:
    """Declaration stubs, dispatchers, and recording seams."""

    _config: CompositeConfig  # pyright: ignore[reportUninitializedInstanceVariable]
    _runtime: CompositeRuntimeConfig  # pyright: ignore[reportUninitializedInstanceVariable]
    _logger: LoggerPort  # pyright: ignore[reportUninitializedInstanceVariable]
    _run_id_str: str  # pyright: ignore[reportUninitializedInstanceVariable]
    _fsm: FSMStateHelperService  # pyright: ignore[reportUninitializedInstanceVariable]
    _checkpoint_manager: CompositeCheckpointService  # pyright: ignore[reportUninitializedInstanceVariable]
    _dependency_coordinator: DependencyCoordinatorService | None  # pyright: ignore[reportUninitializedInstanceVariable]
    _dependencies_runner_factory: (  # pyright: ignore[reportUninitializedInstanceVariable]
        Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort] | None
    )
    _coordinator: EnrichmentCoordinatorService  # pyright: ignore[reportUninitializedInstanceVariable]
    _enricher_runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort]  # pyright: ignore[reportUninitializedInstanceVariable]

    async def _save_checkpoint_safe(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:  # pragma: no cover - declaration-only contract (#10534, review 2026-12-31)
        raise NotImplementedError

    async def _run_seed(
        self: _CompositeRunnerStageSupportHostProtocol,
    ) -> SeedResult:  # pragma: no cover - declaration-only contract (#10534, review 2026-12-31)
        raise NotImplementedError

    def _get_enrichers_to_run(
        self: _CompositeRunnerStageSupportHostProtocol,
        state: CompositeCheckpointState,
    ) -> list[EnricherConfig]:  # pragma: no cover - declaration-only contract (#10534, review 2026-12-31)
        raise NotImplementedError

    def _check_required_enrichers(
        self: _CompositeRunnerStageSupportHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:  # pragma: no cover - declaration-only contract (#10534, review 2026-12-31)
        raise NotImplementedError

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
