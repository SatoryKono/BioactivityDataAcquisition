# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Composite pipeline runner facade coordinating stage mixins."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.runner_pkg.runner_control_plane_mixin import (
    CompositeRunnerControlPlaneMixin,
)
from bioetl.application.composite.runner_pkg.runner_execution_orchestrator import (
    CompositeLockedExecutionContext,
    execute_locked_run_phases,
)
from bioetl.application.composite.runner_pkg.runner_key_flow import (
    CompositeEnrichmentKeyContext,
    extract_enrichment_keys,
)
from bioetl.application.composite.runner_pkg.runner_lifecycle_flow import (
    complete_successful_run,
    emit_failed_run,
    handle_bioetl_failure,
    handle_pipeline_execution_failure,
    handle_shutdown,
    mark_finished,
    start_run_lifecycle,
)
from bioetl.application.composite.runner_pkg.runner_runtime_helpers import (
    bind_runner_dependencies,
    initialize_runner_runtime_state,
    prepare_run_state,
    resolve_original_run_id,
    run_with_managed_lock,
    validate_runner_can_start,
)
from bioetl.application.composite.runner_pkg.runner_stage_mixin import (
    CompositeRunnerStageMixin,
)
from bioetl.application.composite.runner_pkg.runner_support_mixin import (
    CompositeRunnerSupportMixin,
)
from bioetl.application.composite.runtime_models import (
    CompositeExecutionContext,
    CompositeRunnerDependencies,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite.result import CompositeResult
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.checkpoint import CompositeCheckpointState
    from bioetl.application.composite.key_extractor import KeyExtractorService
    from bioetl.domain.composite import CompositeConfig
    from bioetl.domain.ports import ClockPort, LockPort, TracingPort

__all__ = ["CompositePipelineRunner"]


class CompositePipelineRunner(
    CompositeRunnerControlPlaneMixin,
    CompositeRunnerSupportMixin,
    CompositeRunnerStageMixin,
):
    """Facade/orchestrator for composite pipeline lifecycle.

    ARCH-REF-R2 / #7729: host direct bases reduced to 3 (merge+obs composed into
    stage/support mixins).
    """

    _lock: LockPort  # pyright: ignore[reportUninitializedInstanceVariable]
    _clock: ClockPort | None
    _key_extractor: KeyExtractorService  # pyright: ignore[reportUninitializedInstanceVariable]
    _observer: CompositeLifecycleObserverService
    _tracing: TracingPort | None

    def __init__(
        self,
        config: CompositeConfig,
        runtime: CompositeRuntimeConfig,
        deps: CompositeRunnerDependencies,
        run_id: str | None = None,
    ) -> None:
        """Initialize composite runner with config, runtime flags, and deps."""
        self._config = config
        self._runtime = runtime
        bind_runner_dependencies(self, deps)
        initialize_runner_runtime_state(self, run_id)

    @property
    def run_id(self) -> str:
        """Return current run ID."""
        return self._run_id_str

    def _mark_finished(self, final_state: CompositePipelineState) -> None:
        """Persist terminal runner state for re-entry guards and diagnostics."""
        mark_finished(self, final_state)

    @property
    def config(self) -> CompositeConfig:
        """Return composite configuration."""
        return self._config

    def _emit_failed_run(
        self,
        error: Exception,
        *,
        reason_code: str,
        stage: str | None = None,
    ) -> None:
        """Emit the canonical runner failure event through the observer seam."""
        emit_failed_run(self, error, reason_code=reason_code, stage=stage)

    def _handle_pipeline_execution_failure(self, error: Exception) -> None:
        """Map execution-phase failures to canonical runner diagnostics."""
        handle_pipeline_execution_failure(self, error)

    def _handle_bioetl_failure(self, error: BioETLError) -> None:
        """Map unexpected BioETL failures to canonical runner diagnostics."""
        handle_bioetl_failure(self, error)

    def _handle_shutdown(self, error: PipelineShutdownError) -> None:
        """Map graceful shutdown to canonical terminal ledger/log semantics."""
        handle_shutdown(self, error)

    def _start_run_lifecycle(self) -> None:
        """Validate and log the start of one composite runner execution."""
        start_run_lifecycle(self)

    async def run(self) -> CompositeResult:
        """Execute full composite pipeline under runtime lock."""
        validate_runner_can_start(
            finished=self._finished,
            run_id=self._run_id_str,
            final_state=self._final_state,
        )
        self._start_run_lifecycle()

        # Resolve exception group at call-time to avoid stale module-state issues
        # from test-time monkeypatching/reloads.
        from bioetl.application.composite.runner_pkg.runner_constants import (
            PIPELINE_EXECUTION_ERRORS as pipeline_execution_errors,
        )

        try:
            return await self._run_with_managed_lock()
        except PipelineShutdownError as error:
            self._handle_shutdown(error)
            raise
        except pipeline_execution_errors as error:
            self._handle_pipeline_execution_failure(error)
            raise
        except BioETLError as error:
            self._handle_bioetl_failure(error)
            raise

    async def _run_with_managed_lock(self) -> CompositeResult:
        """Acquire/release the runtime lock around the canonical run body."""
        lock_run_result = await run_with_managed_lock(
            lock_port=self._lock,
            lock_key=self._config.lock_key,
            owner_id=self._run_id,
            lock_ttl_seconds=self._runtime.lock_ttl_seconds,
            heartbeat_interval_seconds=self._runtime.heartbeat_interval_seconds,
            logger=self._logger,
            run_while_locked=self._run_with_lock,
        )
        self._mark_finished(CompositePipelineState.COMPLETED)
        return lock_run_result

    async def _prepare_run_state(self) -> CompositeCheckpointState:
        """Load checkpoint state and apply resume semantics when configured."""
        state = await prepare_run_state(
            checkpoint_manager=self._checkpoint_manager,
            runtime=self._runtime,
            fsm=self._fsm,
            clock=self._clock,
        )
        self._original_run_id = resolve_original_run_id(
            runtime=self._runtime,
            state=state,
            current_run_id=self._run_id_str,
        )
        return state

    async def _extract_enrichment_keys(self) -> pl.DataFrame:
        """Extract seed keys once the seed phase has completed."""
        enrichment_key_result = await extract_enrichment_keys(
            key_extractor=self._key_extractor,
            logger=self._logger,
            request=CompositeEnrichmentKeyContext(
                composite_name=self._config.name,
                silver_table=self._config.seed.silver_table,
                output_keys=tuple(self._config.seed.output_keys),
            ),
        )
        return enrichment_key_result.keys_df

    async def _execute_locked_run_phases(
        self,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, CompositeExecutionContext]:
        """Execute composite phases in the canonical lock-held order."""
        locked_phase_result = await execute_locked_run_phases(
            self,  # pyright: ignore[reportArgumentType]
            CompositeLockedExecutionContext(state=state),
        )
        return locked_phase_result.state, locked_phase_result.execution_context

    async def _complete_successful_run(
        self,
        state: CompositeCheckpointState,
        execution_context: CompositeExecutionContext,
    ) -> CompositeResult:
        """Finalize state and emit canonical terminal success artifacts."""
        return await complete_successful_run(self, state, execution_context)

    async def _run_with_lock(self) -> CompositeResult:
        """Execute pipeline stages while lock is held."""
        state = await self._prepare_run_state()
        state, execution_context = await self._execute_locked_run_phases(state)
        return await self._complete_successful_run(state, execution_context)
