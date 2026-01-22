"""Composite Pipeline Runner.

Application Service that orchestrates composite pipeline execution.
Coordinates seed execution, parallel enrichment, and merge operations.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.domain.composite.result import (
    CompositeResult,
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.events import PipelineEvent
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.checkpoint import CompositeCheckpointManager
    from bioetl.application.composite.coordinator import EnrichmentCoordinator
    from bioetl.application.composite.key_extractor import KeyExtractorService
    from bioetl.application.composite.merger import MergeService
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.config import CompositeConfig, EnricherConfig
    from bioetl.domain.ports import LockPort, LoggerPort


@dataclass(frozen=True, slots=True)
class CompositeRuntimeConfig:
    """Runtime configuration for composite pipeline execution.

    Attributes:
        resume: Resume from checkpoint if available.
        dry_run: Extract and transform without writing.
        enrich_only: Run only specified enrichers (comma-separated).
        required_only: Skip optional enrichers.
        force_enricher: Force re-run of specified enricher.
        seed_limit: Optional limit for seed pipeline.
    """

    resume: bool = False
    dry_run: bool = False
    enrich_only: tuple[str, ...] | None = None
    required_only: bool = False
    force_enricher: str | None = None
    seed_limit: int | None = None

    def __post_init__(self) -> None:
        """Convert types for immutability."""
        if isinstance(self.enrich_only, list):
            object.__setattr__(self, "enrich_only", tuple(self.enrich_only))


class CompositePipelineRunner:
    """Orchestrates composite pipeline execution.

    Coordinates seed execution, parallel enrichment, and merge.
    Delegates to existing PipelineRunner for individual pipelines.

    This is an Application Service that:
    - Has no business logic (delegates to specialized services)
    - Coordinates cross-cutting concerns (locking, checkpointing)
    - Manages lifecycle of sub-pipelines

    Attributes:
        config: Composite pipeline configuration.
        runtime: Runtime options (resume, dry_run, etc.).

    Example:
        >>> runner = CompositePipelineRunner(
        ...     config=composite_config,
        ...     runtime=CompositeRuntimeConfig(resume=True),
        ...     seed_runner_factory=seed_factory,
        ...     enricher_runner_factory=enricher_factory,
        ...     key_extractor=key_extractor,
        ...     coordinator=coordinator,
        ...     merger=merger,
        ...     checkpoint_manager=checkpoint_manager,
        ...     logger=logger,
        ...     lock=lock,
        ... )
        >>> result = await runner.run()
    """

    def __init__(
        self,
        config: CompositeConfig,
        runtime: CompositeRuntimeConfig,
        seed_runner_factory: Callable[[], PipelineRunner],
        enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
        key_extractor: KeyExtractorService,
        coordinator: EnrichmentCoordinator,
        merger: MergeService,
        checkpoint_manager: CompositeCheckpointManager,
        logger: LoggerPort,
        lock: LockPort,
        run_id: str | None = None,
        dq_report_service: DQReportService | None = None,
    ) -> None:
        """Initialize composite pipeline runner.

        Args:
            config: Composite pipeline configuration.
            runtime: Runtime options.
            seed_runner_factory: Factory to create seed PipelineRunner.
            enricher_runner_factory: Factory to create enricher PipelineRunner.
                Takes pipeline name and keys DataFrame.
            key_extractor: Service to extract join keys from Silver.
            coordinator: Enrichment coordination service.
            merger: Data merge service.
            checkpoint_manager: Checkpoint manager for resume.
            logger: Structured logger.
            lock: Lock port for distributed locking.
            run_id: Optional run ID (generated if not provided).
            dq_report_service: Optional DQ report service for generating reports.
        """
        self._config = config
        self._runtime = runtime
        self._seed_runner_factory = seed_runner_factory
        self._enricher_runner_factory = enricher_runner_factory
        self._key_extractor = key_extractor
        self._coordinator = coordinator
        self._merger = merger
        self._checkpoint_manager = checkpoint_manager
        self._logger = logger
        self._lock = lock
        self._run_id_str = run_id or str(uuid4())
        self._run_id: RunID = cast(RunID, UUID(self._run_id_str))
        self._started_at: datetime | None = None
        self._finished: bool = False
        self._final_state: CompositePipelineState | None = None
        self._dq_report_service = dq_report_service

    @property
    def run_id(self) -> str:
        """Get the run ID as string."""
        return self._run_id_str

    @property
    def config(self) -> CompositeConfig:
        """Get the composite configuration."""
        return self._config

    async def run(self) -> CompositeResult:
        """Execute full composite pipeline.

        Execution flow:
        1. Acquire composite lock
        2. Load checkpoint (for resume)
        3. Run seed pipeline (if not completed)
        4. Extract join keys from seed Silver
        5. Run enrichers in parallel (fan-out)
        6. Merge results into Gold
        7. Delete checkpoint on success

        Returns:
            CompositeResult with all sub-pipeline results.

        Raises:
            CriticalError: If seed or required enricher fails.
            RunnerAlreadyExecutedError: If this Runner instance was already executed.
        """
        # Protection against double execution
        if self._finished:
            from bioetl.domain.exceptions import RunnerAlreadyExecutedError

            raise RunnerAlreadyExecutedError(
                runner_type="CompositePipelineRunner",
                run_id=self._run_id_str,
                final_state=self._final_state.value if self._final_state else None,
            )

        # Validate configuration consistency on startup
        self._validate_config_consistency()

        self._started_at = datetime.now(tz=UTC)
        self._logger.info(
            PipelineEvent.START,
            composite=self._config.name,
            run_id=self._run_id_str,
            stage="composite_start",
        )

        try:
            # Acquire composite lock
            lock_key = self._config.lock_key
            acquired = await self._lock.acquire(
                key=lock_key,
                owner_id=self._run_id,
                ttl=3600,  # 1 hour for composite
            )
            if not acquired:
                raise RuntimeError(
                    f"Could not acquire lock for composite: {self._config.name}"
                )

            try:
                result = await self._run_with_lock()
                # Mark as finished with success
                self._finished = True
                self._final_state = CompositePipelineState.COMPLETED
                return result
            finally:
                await self._lock.release(key=lock_key, owner_id=self._run_id)

        except Exception as e:
            # Mark as finished with failure
            self._finished = True
            self._final_state = CompositePipelineState.FAILED
            self._logger.error(
                PipelineEvent.FAILED,
                composite=self._config.name,
                run_id=self._run_id_str,
                error=str(e),
            )
            raise

    async def _run_with_lock(self) -> CompositeResult:
        """Execute composite pipeline with lock held."""
        # Load checkpoint (for resume)
        state = await self._checkpoint_manager.load()

        # Handle resume from FAILED state - determine correct phase to continue from
        if self._runtime.resume and state.state == CompositePipelineState.FAILED:
            state = self._handle_resume_from_failed(state)

        # Log resume context if resuming with progress
        if self._runtime.resume and state.is_resumable:
            self._log_resume_context(state)

        # Track results
        seed_result: SeedResult | None = None
        enrichment_results: dict[str, EnrichmentResult] = {}
        merge_result: MergeResult | None = None

        # Step 1: Run seed (if not completed)
        if not state.seed_completed:
            # Validate and transition to SEED_RUNNING before starting seed
            previous_state = state.state
            self._validate_fsm_transition(previous_state, CompositePipelineState.SEED_RUNNING)
            state = state.with_state(CompositePipelineState.SEED_RUNNING)
            self._log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.SEED_RUNNING,
                stage="seed_start",
            )
            # Log phase event for seed start
            self._logger.info(
                PipelineEvent.phase_started("seed"),
                composite=self._config.name,
                run_id=self._run_id_str,
            )
            await self._save_checkpoint_safe(state, "seed_running")

            # Execute seed with error handling
            try:
                seed_result = await self._run_seed()
            except Exception as e:
                # Seed failed - transition to FAILED state
                self._logger.error(
                    "Seed pipeline failed",
                    composite=self._config.name,
                    run_id=self._run_id_str,
                    seed_pipeline=self._config.seed.pipeline,
                    error=str(e),
                )
                self._log_fsm_transition(
                    from_state=CompositePipelineState.SEED_RUNNING,
                    to_state=CompositePipelineState.FAILED,
                    stage="seed_failed",
                    error=str(e),
                )
                # Save FAILED state to checkpoint for resume awareness
                failed_state = state.with_state(CompositePipelineState.FAILED)
                await self._save_checkpoint_safe(failed_state, "seed_failed")
                # Re-raise to trigger outer error handling and lock release
                raise

            # Seed succeeded - transition to SEED_COMPLETED
            state = state.with_seed_completed(seed_result)
            self._log_fsm_transition(
                from_state=CompositePipelineState.SEED_RUNNING,
                to_state=CompositePipelineState.SEED_COMPLETED,
                stage="seed_complete",
                records_extracted=seed_result.records_extracted,
                records_silver=seed_result.records_silver,
            )
            # Log phase event for seed completion
            self._logger.info(
                PipelineEvent.phase_completed("seed"),
                composite=self._config.name,
                run_id=self._run_id_str,
                records_extracted=seed_result.records_extracted,
                records_silver=seed_result.records_silver,
            )
            await self._save_checkpoint_safe(state, "seed_completed")
        else:
            # Resume: seed already completed
            self._logger.info(
                "Seed already completed, resuming from checkpoint",
                composite=self._config.name,
                run_id=self._run_id_str,
            )
            # Ensure FSM state reflects SEED_COMPLETED when resuming
            if state.state != CompositePipelineState.SEED_COMPLETED:
                previous_state = state.state
                state = state.with_state(CompositePipelineState.SEED_COMPLETED)
                self._log_fsm_transition(
                    from_state=previous_state,
                    to_state=CompositePipelineState.SEED_COMPLETED,
                    stage="seed_resume",
                )
            seed_result = SeedResult(
                pipeline_name=self._config.seed.pipeline,
                resumed=True,
            )

        # Step 2: Extract keys from seed Silver
        keys_df = await self._key_extractor.extract(
            silver_table=self._config.seed.silver_table,
            keys=self._config.seed.output_keys,
        )

        self._logger.info(
            "Extracted keys for enrichment",
            composite=self._config.name,
            keys_count=len(keys_df),
        )

        # Step 3: Determine which enrichers to run
        enrichers_to_run = self._get_enrichers_to_run(state)

        # Step 4: Run enrichers (fan-out) with FSM state management
        if enrichers_to_run:
            # Validate and transition to ENRICHING state before starting enrichments
            enricher_names = [e.pipeline for e in enrichers_to_run]
            previous_state = state.state
            self._validate_fsm_transition(previous_state, CompositePipelineState.ENRICHING)
            state = state.with_state(CompositePipelineState.ENRICHING)
            await self._checkpoint_manager.save(state)

            # Log FSM transition to ENRICHING
            self._log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.ENRICHING,
                stage="enrichment_start",
                enrichers=enricher_names,
                count=len(enrichers_to_run),
            )
            # Log phase event for enrichment start
            self._logger.info(
                PipelineEvent.phase_started("enrichment"),
                composite=self._config.name,
                run_id=self._run_id_str,
                enrichers=enricher_names,
                count=len(enrichers_to_run),
            )

            enrichment_results = await self._coordinator.run_enrichers(
                keys=keys_df,
                enrichers=enrichers_to_run,
                completed=state.completed_enrichers,
                runner_factory=self._enricher_runner_factory,
            )

            # Update checkpoint with completed enrichers
            for name, result in enrichment_results.items():
                if result.is_success or result.status == EnrichmentStatus.SKIPPED:
                    state = state.with_enricher_completed(name, result)
            await self._checkpoint_manager.save(state)

            # Log aggregated enrichment results
            self._log_enrichment_summary(enrichment_results)
        else:
            # No enrichers to run - skip enrichment stage
            self._logger.info(
                "No enrichers to run, skipping enrichment stage",
                composite=self._config.name,
                reason="all_completed_or_filtered",
            )

        # Merge with previously completed enrichers
        enrichment_results.update(state.enrichment_results)

        # Step 4b: Add NOT_RUN results for optional enrichers skipped due to required_only
        enrichment_results = self._add_not_run_results(
            enrichment_results, enrichers_to_run, state
        )

        # Step 5: Check required enrichers with FSM FAILED transition on error
        try:
            self._check_required_enrichers(enrichment_results)
        except RuntimeError as e:
            # Required enricher failed - transition to FAILED state
            previous_state = state.state
            state = state.with_state(CompositePipelineState.FAILED)

            # Log FSM transition to FAILED
            self._log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.FAILED,
                stage="required_enricher_failed",
                error=str(e),
            )

            try:
                await self._checkpoint_manager.save(state)
            except Exception as save_error:
                self._logger.warning(
                    "Failed to save FAILED state to checkpoint",
                    composite=self._config.name,
                    run_id=self._run_id_str,
                    error=str(save_error),
                )

            self._logger.error(
                "Required enricher failed, pipeline transitioning to FAILED",
                composite=self._config.name,
                run_id=self._run_id_str,
                error=str(e),
            )
            raise

        # Step 5b: Transition to ENRICHMENT_COMPLETED
        state = await self._transition_to_enrichment_completed(state)

        # Step 6: Execute merge or skip in dry run mode
        state, merge_result = await self._execute_merge_stage(state, enrichment_results)

        # Step 7: Finalize - set COMPLETED and cleanup checkpoint
        await self._finalize_pipeline(state)

        completed_at = datetime.now(tz=UTC)
        started = self._started_at or completed_at  # Fallback if not set
        total_duration = (completed_at - started).total_seconds()

        # Calculate if we had warnings from optional enricher failures
        had_warnings = self._calculate_had_warnings(enrichment_results)

        # Log completion with appropriate status
        if had_warnings:
            self._logger.info(
                PipelineEvent.COMPLETE,
                composite=self._config.name,
                run_id=self._run_id_str,
                duration_seconds=total_duration,
                status="completed_with_warnings",
                had_warnings=True,
            )
        else:
            self._logger.info(
                PipelineEvent.COMPLETE,
                composite=self._config.name,
                run_id=self._run_id_str,
                duration_seconds=total_duration,
            )

        return CompositeResult(
            composite_name=self._config.name,
            composite_run_id=self._run_id_str,
            seed_result=seed_result,
            enrichment_results=enrichment_results,
            merge_result=merge_result,
            total_duration_seconds=total_duration,
            started_at=self._started_at,
            completed_at=completed_at,
            had_warnings=had_warnings,
            _required_enrichers=frozenset(self._config.required_enrichers),
        )

    async def _transition_to_enrichment_completed(
        self, state: CompositeCheckpointState
    ) -> CompositeCheckpointState:
        """Transition FSM state to ENRICHMENT_COMPLETED.

        Handles the case where no enrichers were run (state is still SEED_COMPLETED).
        Must go through ENRICHING first per FSM rules.
        """
        from bioetl.domain.composite.state import CompositePipelineState

        if state.state == CompositePipelineState.SEED_COMPLETED:
            # Must go through ENRICHING first per FSM rules (no enrichers case)
            previous_state = state.state
            self._validate_fsm_transition(previous_state, CompositePipelineState.ENRICHING)
            state = state.with_state(CompositePipelineState.ENRICHING)
            self._log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.ENRICHING,
                stage="enrichment_start_empty",
                reason="no_enrichers_to_run",
            )

        if state.state == CompositePipelineState.ENRICHING:
            enriching_state: CompositePipelineState = state.state
            self._validate_fsm_transition(
                enriching_state, CompositePipelineState.ENRICHMENT_COMPLETED
            )
            state = state.with_state(CompositePipelineState.ENRICHMENT_COMPLETED)
            await self._save_checkpoint_safe(state, "enrichment_completed")

            # Log FSM transition to ENRICHMENT_COMPLETED
            self._log_fsm_transition(
                from_state=enriching_state,
                to_state=CompositePipelineState.ENRICHMENT_COMPLETED,
                stage="enrichment_complete",
            )
            # Log phase event for enrichment completion
            self._logger.info(
                PipelineEvent.phase_completed("enrichment"),
                composite=self._config.name,
                run_id=self._run_id_str,
            )
        return state

    async def _execute_merge_stage(
        self,
        state: CompositeCheckpointState,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> tuple[CompositeCheckpointState, MergeResult | None]:
        """Execute merge stage or skip in dry run mode.

        Returns updated state and merge result (None for dry run).
        """
        from bioetl.domain.composite.state import CompositePipelineState

        merge_result: MergeResult | None = None

        if not self._runtime.dry_run:
            # Validate and transition to MERGING state
            previous_state = state.state
            self._validate_fsm_transition(previous_state, CompositePipelineState.MERGING)
            state = state.with_state(CompositePipelineState.MERGING)
            await self._save_checkpoint_safe(state, "merging")

            # Log FSM transition to MERGING
            self._log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.MERGING,
                stage="merge_start",
            )
            # Log phase event for merge start
            self._logger.info(
                PipelineEvent.phase_started("merge"),
                composite=self._config.name,
                run_id=self._run_id_str,
            )

            try:
                # Get only enrichers with data to merge (exclude SKIPPED/NOT_RUN)
                mergeable_enrichers = self._get_mergeable_enrichers(enrichment_results)

                merge_result = await self._merger.merge(
                    seed_table=self._config.seed.silver_table,
                    enrichers=mergeable_enrichers,
                    enrichment_results=enrichment_results,
                    run_id=self._run_id_str,
                )

                # Log phase event for merge completion
                self._logger.info(
                    PipelineEvent.phase_completed("merge"),
                    composite=self._config.name,
                    run_id=self._run_id_str,
                    records_merged=merge_result.records_merged,
                )

                # Generate DQ reports if service is available
                await self._generate_dq_reports(merge_result)

            except Exception as merge_error:
                # Log FSM transition to FAILED
                self._log_fsm_transition(
                    from_state=CompositePipelineState.MERGING,
                    to_state=CompositePipelineState.FAILED,
                    stage="merge_failed",
                    error=str(merge_error),
                )
                self._logger.error(
                    "Merge failed",
                    composite=self._config.name,
                    run_id=self._run_id_str,
                    error=str(merge_error),
                )
                state = state.with_state(CompositePipelineState.FAILED)
                await self._save_checkpoint_safe(state, "merge_failed")
                raise
        else:
            # Dry run mode - skip merge, transition directly to COMPLETED
            self._log_fsm_transition(
                from_state=state.state,
                to_state=CompositePipelineState.COMPLETED,
                stage="dry_run_skip_merge",
                reason="dry_run_mode",
            )
            self._logger.info(
                "Dry run: merge skipped, pipeline completing",
                composite=self._config.name,
                run_id=self._run_id_str,
            )

        return state, merge_result

    async def _finalize_pipeline(self, state: CompositeCheckpointState) -> None:
        """Finalize pipeline - set COMPLETED state and cleanup checkpoint."""
        from bioetl.domain.composite.state import CompositePipelineState

        # Validate and transition to COMPLETED state (only if not already COMPLETED from dry run)
        if state.state != CompositePipelineState.COMPLETED:
            previous_state = state.state
            self._validate_fsm_transition(previous_state, CompositePipelineState.COMPLETED)
            state = state.with_state(CompositePipelineState.COMPLETED)

            # Log FSM transition to COMPLETED
            self._log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.COMPLETED,
                stage="pipeline_complete",
            )
        await self._save_checkpoint_safe(state, "completed")

        # Cleanup checkpoint on success
        try:
            await self._checkpoint_manager.delete()
        except Exception as delete_error:
            # Checkpoint deletion failure is non-critical
            self._logger.warning(
                "Failed to delete checkpoint",
                composite=self._config.name,
                run_id=self._run_id_str,
                error=str(delete_error),
            )

    def _log_fsm_transition(
        self,
        from_state: CompositePipelineState,
        to_state: CompositePipelineState,
        stage: str,
        **extra: object,
    ) -> None:
        """Log FSM state transition.

        Args:
            from_state: Previous FSM state.
            to_state: New FSM state.
            stage: Pipeline stage identifier (e.g., 'seed_start', 'seed_complete').
            **extra: Additional context for logging.
        """
        self._logger.info(
            "FSM state transition",
            from_state=from_state.value,
            to_state=to_state.value,
            composite=self._config.name,
            run_id=self._run_id_str,
            stage=stage,
            **extra,
        )

    def _validate_config_consistency(self) -> None:
        """Validate configuration consistency and log warnings for anomalies.

        Checks for potential issues in CompositeConfig that might indicate
        misconfiguration:
        - required_enrichers property matches actual required flags
        - All enrichers are optional warning (valid but notable)

        This is a defensive check to catch configuration errors early.
        """
        # Check required_enrichers consistency
        expected_required = frozenset(
            e.pipeline for e in self._config.enrichers if e.required
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

        # Log info if all enrichers are optional
        if not expected_required and self._config.enrichers:
            self._logger.info(
                "All enrichers are optional",
                composite=self._config.name,
                enricher_count=len(self._config.enrichers),
                note="Pipeline will succeed even if all enrichers fail",
            )

    def _validate_fsm_transition(
        self,
        from_state: CompositePipelineState,
        to_state: CompositePipelineState,
        allow_resume: bool = False,
    ) -> bool:
        """Validate FSM state transition and log warning if invalid.

        This method validates transitions according to FSM rules. Invalid transitions
        are logged as warnings rather than raising exceptions to avoid breaking
        pipeline execution. This is primarily a debug/development safety net.

        Args:
            from_state: Current FSM state.
            to_state: Target FSM state.
            allow_resume: If True, allows transitions from FAILED state (for resume).

        Returns:
            True if transition is valid, False otherwise.

        Note:
            When allow_resume=True, transitions from FAILED to any resumable state
            are permitted. This is needed for resume-from-failed functionality.
        """
        # Special case: allow resume from FAILED state
        if allow_resume and from_state == CompositePipelineState.FAILED:
            self._logger.debug(
                "FSM resume transition from FAILED",
                from_state=from_state.value,
                to_state=to_state.value,
                composite=self._config.name,
            )
            return True

        # Check if transition is valid according to FSM rules
        if not from_state.can_transition_to(to_state):
            self._logger.warning(
                "Invalid FSM transition detected",
                from_state=from_state.value,
                to_state=to_state.value,
                allowed_transitions=[s.value for s in from_state.allowed_transitions],
                composite=self._config.name,
                run_id=self._run_id_str,
                note="This may indicate a programming error in the Runner",
            )
            return False

        return True

    def _handle_resume_from_failed(
        self, state: CompositeCheckpointState
    ) -> CompositeCheckpointState:
        """Handle resuming from FAILED state by determining correct phase.

        When checkpoint has state=FAILED, we need to determine the actual phase
        to resume from based on seed_completed and completed_enrichers flags.

        Args:
            state: Checkpoint state with FAILED status.

        Returns:
            Updated state with corrected FSM state for resumption.
        """
        total_enrichers = len(self._config.enrichers)
        completed_count = len(state.completed_enrichers)

        if not state.seed_completed:
            # Seed failed - resume from NOT_STARTED (will re-run seed)
            resume_phase = CompositePipelineState.NOT_STARTED
            phase_description = "seed (seed not completed)"
        elif completed_count < total_enrichers:
            # Enrichment failed - resume from ENRICHING (will run remaining enrichers)
            resume_phase = CompositePipelineState.ENRICHING
            phase_description = (
                f"enrichment ({completed_count}/{total_enrichers} enrichers completed)"
            )
        else:
            # Merge failed - resume from ENRICHMENT_COMPLETED (will re-run merge)
            resume_phase = CompositePipelineState.ENRICHMENT_COMPLETED
            phase_description = "merge (all enrichers completed)"

        self._logger.info(
            "Checkpoint indicates previous failure, resuming from phase",
            composite=self._config.name,
            run_id=self._run_id_str,
            previous_state=state.state.value,
            resume_phase=resume_phase.value,
            phase_description=phase_description,
            seed_completed=state.seed_completed,
            completed_enrichers=completed_count,
            total_enrichers=total_enrichers,
        )

        # Validate and log FSM transition from FAILED to resume phase
        # allow_resume=True permits transitions from terminal FAILED state
        self._validate_fsm_transition(
            state.state, resume_phase, allow_resume=True
        )
        self._log_fsm_transition(
            from_state=state.state,
            to_state=resume_phase,
            stage="resume_from_failed",
            phase_description=phase_description,
        )

        return state.with_state(resume_phase)

    def _log_resume_context(self, state: CompositeCheckpointState) -> None:
        """Log detailed resume context when resuming from checkpoint.

        Provides visibility into what was completed previously and what
        will be executed in this run.

        Args:
            state: Current checkpoint state being resumed from.
        """
        total_enrichers = len(self._config.enrichers)
        completed_count = len(state.completed_enrichers)
        remaining_count = total_enrichers - completed_count

        self._logger.info(
            "Resuming from checkpoint",
            composite=self._config.name,
            run_id=self._run_id_str,
            last_state=state.state.value,
            seed_completed=state.seed_completed,
            completed_enrichers_count=completed_count,
            total_enrichers_count=total_enrichers,
            remaining_enrichers_count=remaining_count,
            completed_enrichers=list(state.completed_enrichers)
            if completed_count > 0
            else None,
        )

    async def _save_checkpoint_safe(
        self,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:
        """Save checkpoint with graceful error handling.

        Checkpoint save failures should not stop pipeline execution, but
        resume capability will be affected.

        Args:
            state: Checkpoint state to save.
            operation: Description of the operation for logging.

        Returns:
            True if save succeeded, False otherwise.
        """
        try:
            await self._checkpoint_manager.save(state)
            return True
        except Exception as e:
            self._logger.warning(
                "checkpoint_save_failed",
                composite=self._config.name,
                run_id=self._run_id_str,
                operation=operation,
                error=str(e),
                note="Resume capability may be affected",
            )
            return False

    async def _run_seed(self) -> SeedResult:
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

        # Extract stats from runner (if available)
        records_extracted = getattr(runner, "_executor", None)
        records_silver = 0
        if records_extracted:
            records_silver = getattr(records_extracted, "records_silver", 0)

        return SeedResult(
            pipeline_name=self._config.seed.pipeline,
            records_extracted=records_extracted.records_fetched
            if records_extracted
            else 0,
            records_silver=records_silver,
            keys_generated=records_silver,  # Approximate
            duration_seconds=(completed_at - started_at).total_seconds(),
            started_at=started_at,
            completed_at=completed_at,
        )

    def _get_enrichers_to_run(
        self, state: CompositeCheckpointState
    ) -> list[EnricherConfig]:
        """Determine which enrichers should be run."""
        enrichers_to_run: list[EnricherConfig] = []

        for enricher in self._config.enrichers:
            # Skip if already completed (unless forced)
            if (
                enricher.pipeline in state.completed_enrichers
                and self._runtime.force_enricher != enricher.pipeline
            ):
                continue

            # Skip optional enrichers if required_only
            if self._runtime.required_only and not enricher.required:
                continue

            # Filter to specific enrichers if enrich_only
            if (
                self._runtime.enrich_only
                and enricher.pipeline not in self._runtime.enrich_only
            ):
                continue

            enrichers_to_run.append(enricher)

        return enrichers_to_run

    def _check_required_enrichers(
        self, enrichment_results: dict[str, EnrichmentResult]
    ) -> None:
        """Check that all required enrichers succeeded."""
        for enricher_name in self._config.required_enrichers:
            result = enrichment_results.get(enricher_name)
            if result is None:
                raise RuntimeError(f"Required enricher '{enricher_name}' did not run")
            if not result.is_success:
                raise RuntimeError(
                    f"Required enricher '{enricher_name}' failed: "
                    f"{result.error_message or result.status.value}"
                )

    def _add_not_run_results(
        self,
        enrichment_results: dict[str, EnrichmentResult],
        enrichers_to_run: list[EnricherConfig],
        state: CompositeCheckpointState,
    ) -> dict[str, EnrichmentResult]:
        """Add NOT_RUN results for optional enrichers skipped due to required_only mode.

        When required_only is True, optional enrichers are not executed. This method
        adds explicit NOT_RUN results for these enrichers so they appear in the
        final enrichment_results for complete lineage tracking.

        Args:
            enrichment_results: Current enrichment results from executed enrichers.
            enrichers_to_run: List of enrichers that were actually run.
            state: Current checkpoint state.

        Returns:
            Updated enrichment_results with NOT_RUN entries for skipped optional enrichers.
        """
        if not self._runtime.required_only:
            return enrichment_results

        # Get set of enrichers that were actually run or previously completed
        run_names = {e.pipeline for e in enrichers_to_run}
        completed_names = state.completed_enrichers

        # Find optional enrichers that were skipped due to required_only
        for enricher in self._config.enrichers:
            # Only process optional enrichers
            if enricher.required:
                continue

            # Skip if this enricher was run or previously completed
            if enricher.pipeline in run_names:
                continue
            if enricher.pipeline in completed_names:
                continue

            # Skip if already in results (shouldn't happen, but defensive)
            if enricher.pipeline in enrichment_results:
                continue

            # Add NOT_RUN result for this skipped optional enricher
            enrichment_results[enricher.pipeline] = EnrichmentResult.not_run(
                enricher_name=enricher.pipeline,
                reason="Skipped due to required_only mode",
            )

            self._logger.info(
                "Optional enricher not run",
                composite=self._config.name,
                enricher=enricher.pipeline,
                reason="required_only_mode",
            )

        return enrichment_results

    def _calculate_had_warnings(
        self, enrichment_results: dict[str, EnrichmentResult]
    ) -> bool:
        """Calculate if the pipeline had warnings from optional enricher failures.

        A warning occurs when an optional (non-required) enricher fails but the
        pipeline can still complete successfully. This allows users to distinguish
        between clean completions and completions with issues.

        Args:
            enrichment_results: All enrichment results.

        Returns:
            True if any optional enricher failed (status FAILED or TIMEOUT).
        """
        required_enrichers = frozenset(self._config.required_enrichers)

        for name, result in enrichment_results.items():
            # Skip required enrichers - their failures would already have raised
            if name in required_enrichers:
                continue

            # Check for failure statuses (FAILED, TIMEOUT)
            if result.status in (EnrichmentStatus.FAILED, EnrichmentStatus.TIMEOUT):
                self._logger.warning(
                    "Optional enricher failed",
                    composite=self._config.name,
                    enricher=name,
                    status=result.status.value,
                    error_message=result.error_message,
                )
                return True

        return False

    def _get_mergeable_enrichers(
        self,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> list[EnricherConfig]:
        """Get list of enrichers that should be included in merge.

        Excludes enrichers with NOT_RUN or SKIPPED status since they have no
        data to merge. This prevents file I/O errors when trying to read
        non-existent or empty Silver tables.

        Args:
            enrichment_results: All enrichment results.

        Returns:
            List of EnricherConfig for enrichers that have data to merge.
        """
        # Statuses that indicate no data to merge
        non_mergeable_statuses = (
            EnrichmentStatus.SKIPPED,
            EnrichmentStatus.NOT_RUN,
        )

        mergeable: list[EnricherConfig] = []
        for enricher_cfg in self._config.enrichers:
            result = enrichment_results.get(enricher_cfg.pipeline)

            # If no result, don't include in merge
            if result is None:
                continue

            # If status indicates no data, don't include in merge
            if result.status in non_mergeable_statuses:
                self._logger.debug(
                    "Excluding enricher from merge",
                    enricher=enricher_cfg.pipeline,
                    status=result.status.value,
                    reason="no_data_to_merge",
                )
                continue

            mergeable.append(enricher_cfg)

        return mergeable

    def _log_enrichment_summary(
        self, enrichment_results: dict[str, EnrichmentResult]
    ) -> None:
        """Log aggregated summary of enrichment results.

        Args:
            enrichment_results: Results from enrichers.
        """
        if not enrichment_results:
            return

        # Aggregate by status
        success_count = 0
        partial_count = 0
        failed_count = 0
        skipped_count = 0
        timeout_count = 0
        not_run_count = 0

        total_records_input = 0
        total_records_enriched = 0
        total_records_errored = 0

        failed_enrichers: list[str] = []
        successful_enrichers: list[str] = []
        not_run_enrichers: list[str] = []

        for name, result in enrichment_results.items():
            total_records_input += result.records_input
            total_records_enriched += result.records_enriched
            total_records_errored += result.records_errored

            if result.status == EnrichmentStatus.SUCCESS:
                success_count += 1
                successful_enrichers.append(name)
            elif result.status == EnrichmentStatus.PARTIAL:
                partial_count += 1
                successful_enrichers.append(name)
            elif result.status == EnrichmentStatus.FAILED:
                failed_count += 1
                failed_enrichers.append(name)
            elif result.status == EnrichmentStatus.SKIPPED:
                skipped_count += 1
            elif result.status == EnrichmentStatus.TIMEOUT:
                timeout_count += 1
                failed_enrichers.append(name)
            elif result.status == EnrichmentStatus.NOT_RUN:
                not_run_count += 1
                not_run_enrichers.append(name)

        self._logger.info(
            "Enrichment summary",
            composite=self._config.name,
            total_enrichers=len(enrichment_results),
            success=success_count,
            partial=partial_count,
            failed=failed_count,
            skipped=skipped_count,
            timeout=timeout_count,
            not_run=not_run_count,
            successful_enrichers=successful_enrichers,
            failed_enrichers=failed_enrichers if failed_enrichers else None,
            not_run_enrichers=not_run_enrichers if not_run_enrichers else None,
            total_records_input=total_records_input,
            total_records_enriched=total_records_enriched,
            total_records_errored=total_records_errored,
        )

    async def _generate_dq_reports(self, merge_result: MergeResult) -> None:
        """Generate DQ reports for composite pipeline.

        Args:
            merge_result: Result of the merge operation.
        """
        if self._dq_report_service is None:
            self._logger.debug(
                "dq_reports_skipped",
                reason="DQReportService not configured",
                composite=self._config.name,
            )
            return

        try:
            from bioetl.application.services.dq_report_service import DQReportContext

            # Create DQ report context for composite
            context = DQReportContext(
                run_id=self._run_id_str,
                pipeline_name=f"composite_{self._config.name}",
                timestamp=datetime.now(tz=UTC),
                provider="composite",
                entity=self._config.name,
                # Silver context
                silver_target_table=self._config.merge.output_silver_path,
                silver_input_count=merge_result.records_from_seed,
                # Gold context
                gold_target_table=self._config.merge.output_gold_path,
                # DQ thresholds from config
                dq_soft_threshold=self._config.dq.soft_fail_threshold,
                dq_hard_threshold=self._config.dq.hard_fail_threshold,
            )

            # Generate reports (if analyzers are configured)
            await self._dq_report_service.generate_reports(context)

            self._logger.info(
                "dq_reports_generated",
                composite=self._config.name,
                run_id=self._run_id_str,
            )

        except Exception as e:
            # DQ report generation failure should not fail the pipeline
            self._logger.warning(
                "dq_reports_failed",
                composite=self._config.name,
                error=str(e),
            )
