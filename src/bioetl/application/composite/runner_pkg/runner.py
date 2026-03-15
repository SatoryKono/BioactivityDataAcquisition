"""Composite pipeline runner facade.

Coordinates high-level execution flow while delegating stage logic to mixins.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from bioetl.application.composite.runner_pkg.runner_merge_stage_mixin import (
    CompositeRunnerMergeStageMixin,
)
from bioetl.application.composite.runner_pkg.runner_models import (
    CompositeExecutionContext,
    CompositeRuntimeConfig,
)
from bioetl.application.composite.runner_pkg.runner_observability_mixin import (
    CompositeRunnerObservabilityMixin,
)
from bioetl.application.composite.runner_pkg.runner_stage_mixin import (
    CompositeRunnerStageMixin,
)
from bioetl.application.composite.runner_pkg.runner_support_mixin import (
    CompositeRunnerSupportMixin,
)
from bioetl.domain.composite.result import CompositeResult
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions import (
    BioETLError,
    LockAcquisitionError,
    RunnerAlreadyExecutedError,
)
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.checkpoint import (
        CompositeCheckpointManager,
        CompositeCheckpointState,
    )
    from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
    from bioetl.application.composite.dependency_coordinator import (
        DependencyCoordinatorService,
    )
    from bioetl.application.composite.fsm_helper import FSMStateHelperService
    from bioetl.application.composite.key_extractor import KeyExtractorService
    from bioetl.application.composite.merger import MergeService
    from bioetl.application.composite.preflight_validator import (
        CompositePreflightValidator,
    )
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import (
        ExecutionMetricsRunnerPort,
        LockPort,
        LoggerPort,
        MetricsPort,
        QuarantinePort,
    )


__all__ = [
    "CompositeExecutionContext",
    "CompositePipelineRunner",
    "CompositePipelineRunnerService",
    "CompositeRuntimeConfig",
]


class CompositePipelineRunner(
    CompositeRunnerSupportMixin,
    CompositeRunnerObservabilityMixin,
    CompositeRunnerStageMixin,
    CompositeRunnerMergeStageMixin,
):
    """Facade/orchestrator for composite pipeline lifecycle."""

    def __init__(
        self,
        config: CompositeConfig,
        runtime: CompositeRuntimeConfig,
        seed_runner_factory: Callable[[], ExecutionMetricsRunnerPort],
        enricher_runner_factory: Callable[
            [str, pl.DataFrame], ExecutionMetricsRunnerPort
        ],
        key_extractor: KeyExtractorService,
        coordinator: EnrichmentCoordinatorService,
        merger: MergeService,
        checkpoint_manager: CompositeCheckpointManager,
        logger: LoggerPort,
        lock: LockPort,
        fsm_state_helper: FSMStateHelperService,
        run_id: str | None = None,
        dq_report_service: DQReportService | None = None,
        preflight_validator: CompositePreflightValidator | None = None,
        dependencies_runner_factory: Callable[
            [str, pl.DataFrame], ExecutionMetricsRunnerPort
        ]
        | None = None,
        dependency_coordinator: DependencyCoordinatorService | None = None,
        quarantine_port: QuarantinePort | None = None,
        metrics: MetricsPort | None = None,
    ) -> None:
        """Initialize composite pipeline orchestrator with injected dependencies."""
        self._config = config
        self._runtime = runtime
        self._seed_runner_factory = seed_runner_factory
        self._enricher_runner_factory = enricher_runner_factory
        self._dependencies_runner_factory = dependencies_runner_factory
        self._key_extractor = key_extractor
        self._dependency_coordinator = dependency_coordinator
        self._coordinator = coordinator
        self._merger = merger
        self._checkpoint_manager = checkpoint_manager
        self._logger = logger
        self._lock = lock
        self._run_id_str = run_id or str(uuid4())
        self._run_id: RunID = cast(RunID, UUID(self._run_id_str))
        self._started_at: datetime | None = None
        self._finished = False
        self._final_state: CompositePipelineState | None = None
        self._dq_report_service = dq_report_service
        self._preflight_validator = preflight_validator
        self._quarantine_port = quarantine_port
        self._metrics = metrics
        self._fsm = fsm_state_helper

    @property
    def run_id(self) -> str:
        """Return current run ID."""
        return self._run_id_str

    @property
    def config(self) -> CompositeConfig:
        """Return composite configuration."""
        return self._config

    def _mark_finished(self, final_state: CompositePipelineState) -> None:
        """Persist terminal runner state for re-entry guards and diagnostics."""
        self._finished = True
        self._final_state = final_state

    def _log_failed_run(
        self,
        error: Exception,
        *,
        reason_code: str,
        stage: str | None = None,
    ) -> None:
        """Emit the canonical runner failure log payload."""
        log_kwargs: dict[str, object] = {
            "composite": self._config.name,
            "run_id": self._run_id_str,
            "error": str(error),
            "error_type": type(error).__name__,
            "reason_code": reason_code,
        }
        if stage is not None:
            log_kwargs["stage"] = stage
        self._logger.error(PipelineEvent.FAILED, **log_kwargs)

    async def _run_with_managed_lock(self) -> CompositeResult:
        """Acquire/release the distributed lock around the canonical run body."""
        lock_key = self._config.lock_key
        acquired = await self._lock.acquire(
            key=lock_key,
            owner_id=self._run_id,
            ttl=3600,
        )
        if not acquired:
            raise LockAcquisitionError(key=lock_key)

        try:
            result = await self._run_with_lock()
            self._mark_finished(CompositePipelineState.COMPLETED)
            return result
        finally:
            await self._lock.release(key=lock_key, owner_id=self._run_id)

    async def run(self) -> CompositeResult:
        """Execute full composite pipeline under distributed lock.

        Returns:
            CompositeResult summarising seed, enrichment, dependency, and merge outcomes.
        """
        if self._finished:
            raise RunnerAlreadyExecutedError(
                runner_type="CompositePipelineRunner",
                run_id=self._run_id_str,
                final_state=self._final_state.value if self._final_state else None,
            )

        self._validate_config_consistency()
        self._run_preflight_validation()

        self._started_at = datetime.now(tz=UTC)
        self._logger.info(
            PipelineEvent.START,
            composite=self._config.name,
            run_id=self._run_id_str,
            stage="composite_start",
        )

        # Resolve exception group at call-time to avoid stale module-state issues
        # from test-time monkeypatching/reloads.
        from bioetl.application.composite.runner_pkg.runner_constants import (
            PIPELINE_EXECUTION_ERRORS as pipeline_execution_errors,
        )

        try:
            return await self._run_with_managed_lock()
        except pipeline_execution_errors as error:
            self._mark_finished(CompositePipelineState.FAILED)
            self._log_failed_run(
                error,
                reason_code="composite_pipeline_execution_failed",
                stage="run_with_lock",
            )
            raise
        except BioETLError as error:
            self._mark_finished(CompositePipelineState.FAILED)
            self._log_failed_run(error, reason_code="unexpected_bioetl_error")
            raise

    async def _prepare_run_state(self) -> CompositeCheckpointState:
        """Load checkpoint state and apply resume semantics when configured."""
        state = await self._checkpoint_manager.load()

        if self._runtime.resume and state.state == CompositePipelineState.FAILED:
            state = self._fsm.handle_resume_from_failed(state)
        if self._runtime.resume and state.is_resumable:
            self._fsm.log_resume_context(state)

        return state

    async def _run_with_lock(self) -> CompositeResult:
        """Execute pipeline stages while lock is held."""
        state = await self._prepare_run_state()

        state, seed_result = await self._execute_seed_phase(state)

        keys_df = await self._key_extractor.extract(
            silver_table=self._config.seed.silver_table,
            keys=self._config.seed.output_keys,
        )
        self._logger.info(
            "Extracted keys for enrichment",
            composite=self._config.name,
            keys_count=len(keys_df),
        )

        state, dependency_results = await self._execute_dependencies_phase(
            state, keys_df
        )
        state, enrichment_results = await self._execute_enrichment_phase(state, keys_df)
        state = await self._transition_to_enrichment_completed(state)
        state, merge_result = await self._execute_merge_stage(
            state,
            enrichment_results,
            dependency_results,
        )
        await self._finalize_pipeline(state)
        return self._build_composite_result(
            CompositeExecutionContext(
                seed_result=seed_result,
                dependency_results=dependency_results,
                enrichment_results=enrichment_results,
                merge_result=merge_result,
            )
        )


# Backward-compatible alias for iterative NAME-001 migration.
CompositePipelineRunnerService = CompositePipelineRunner
