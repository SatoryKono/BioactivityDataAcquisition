"""Internal support-stage protocol types for composite runner."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

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
from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.composite import CompositeConfig, EnricherConfig
from bioetl.domain.composite.result import (
    EnrichmentResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.ports import ClockPort, ExecutionMetricsRunnerPort, LoggerPort


class _CompositeRunnerStageSupportHostProtocol(Protocol):
    _config: CompositeConfig
    _runtime: CompositeRuntimeConfig
    _logger: LoggerPort
    _observer: CompositeLifecycleObserverService
    _run_id_str: str
    _clock: ClockPort | None
    _fsm: FSMStateHelperService
    _checkpoint_manager: CompositeCheckpointService
    _dependency_coordinator: DependencyCoordinatorService | None
    _dependencies_runner_factory: (
        Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort] | None
    )
    _coordinator: EnrichmentCoordinatorService
    _enricher_runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort]

    def _build_correlation_log_context(
        self,
        **extra: object,
    ) -> dict[str, object]: ...

    async def _save_checkpoint_safe(
        self,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool: ...

    async def _run_seed(self) -> SeedResult: ...

    def _get_enrichers_to_run(
        self,
        state: CompositeCheckpointState,
    ) -> list[EnricherConfig]: ...

    def _check_required_enrichers(
        self,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None: ...

    async def _call_save_checkpoint_safe(
        self,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool: ...

    def _record_seed_stage_started(self) -> None: ...

    def _record_seed_stage_completed(self, seed_result: SeedResult) -> None: ...

    def _transition_state_with_fsm_log(
        self,
        state: CompositeCheckpointState,
        to_state: CompositePipelineState,
        *,
        stage: str,
        validate: bool = True,
        **transition_kwargs: object,
    ) -> CompositeCheckpointState: ...

    async def _persist_failed_state(
        self,
        state: CompositeCheckpointState,
        *,
        stage: str,
        error: str,
    ) -> CompositeCheckpointState: ...
