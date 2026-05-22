"""Internal enrichment-stage protocol/context types for composite runner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import polars as pl

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.composite.config import CompositeConfig, EnricherConfig
from bioetl.domain.composite.result import EnrichmentResult
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.ports import ClockPort, ExecutionMetricsRunnerPort, LoggerPort


class _CompositeRunnerStageEnrichmentHostProtocol(Protocol):
    _config: CompositeConfig
    _coordinator: EnrichmentCoordinatorService
    _enricher_runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort]
    _fsm: FSMStateHelperService
    _logger: LoggerPort
    _observer: CompositeLifecycleObserverService
    _runtime: CompositeRuntimeConfig
    _run_id_str: str
    _clock: ClockPort | None

    def _call_get_enrichers_to_run(
        self,
        state: CompositeCheckpointState,
    ) -> list[EnricherConfig]: ...

    def _prepare_enrichment_run_context(
        self,
        state: CompositeCheckpointState,
    ) -> _PreparedEnrichmentRunContext: ...

    def _call_check_required_enrichers(
        self,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None: ...

    async def _call_save_checkpoint_safe(
        self,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool: ...

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

    async def _start_enrichment_stage(
        self,
        state: CompositeCheckpointState,
        context: _PreparedEnrichmentRunContext,
    ) -> CompositeCheckpointState: ...

    async def _run_enrichers_and_update_state(
        self,
        state: CompositeCheckpointState,
        keys_df: pl.DataFrame,
        context: _PreparedEnrichmentRunContext,
    ) -> tuple[CompositeCheckpointState, dict[str, EnrichmentResult]]: ...

    async def _skip_enrichment_stage(
        self,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, dict[str, EnrichmentResult]]: ...

    def _finalize_enrichment_results(
        self,
        state: CompositeCheckpointState,
        context: _PreparedEnrichmentRunContext,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> dict[str, EnrichmentResult]: ...

    def _record_completed_enrichment_results(
        self,
        state: CompositeCheckpointState,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> CompositeCheckpointState: ...

    async def _validate_required_enrichment_results(
        self,
        state: CompositeCheckpointState,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None: ...

    def _transition_to_empty_enrichment_start(
        self,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState: ...

    def _record_enrichment_stage_started(
        self,
        enricher_names: list[str],
    ) -> None: ...

    async def _complete_enrichment_stage(
        self,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState: ...

    def _record_enrichment_stage_completed(
        self,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None: ...

    async def _save_failed_enrichment_state(
        self,
        state: CompositeCheckpointState,
        error: InvalidStateError,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class _PreparedEnrichmentRunContext:
    """Selected enrichers and derived names for one enrichment-stage run."""

    enrichers_to_run: list[EnricherConfig]
    enricher_names: list[str]
