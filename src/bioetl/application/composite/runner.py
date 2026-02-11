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
from bioetl.application.composite.runner_helpers import (
    add_not_run_results,
    calculate_had_warnings,
    get_mergeable_dependencies,
    get_mergeable_enrichers,
    log_enrichment_summary,
)
from bioetl.domain.composite.result import (
    CompositeResult,
    DependencyResult,
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
    from bioetl.application.composite.dependency_coordinator import (
        DependencyCoordinator,
    )
    from bioetl.application.composite.key_extractor import KeyExtractorService
    from bioetl.application.composite.merger import MergeService
    from bioetl.application.composite.preflight_validator import (
        CompositePreflightValidator,
    )
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
        use_cached_bronze: Load data from Bronze cache instead of API (master switch).
        cached_bronze_path: Explicit path to Bronze cache directory.
        cached_bronze_date: Filter Bronze cache by date (YYYY-MM-DD).
        cached_bronze_enrichers: Override cached Bronze for enrichers.
            None=follow master, True=force cache, False=force API.
        cached_bronze_dependencies: Override cached Bronze for dependencies.
            False by default — dependencies call APIs with seed-derived keys,
            so their Bronze cache is often stale or absent (e.g. uniprot_idmapping
            on first composite run). Set True to force cache if Bronze was
            pre-populated by a standalone run with identical keys.
    """

    resume: bool = False
    dry_run: bool = False
    enrich_only: tuple[str, ...] | None = None
    required_only: bool = False
    force_enricher: str | None = None
    seed_limit: int | None = None
    use_cached_bronze: bool = True
    cached_bronze_path: str | None = None
    cached_bronze_date: str | None = None
    cached_bronze_enrichers: bool | None = None
    cached_bronze_dependencies: bool = False

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
        preflight_validator: CompositePreflightValidator | None = None,
        dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
        | None = None,
        dependency_coordinator: DependencyCoordinator | None = None,
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
            preflight_validator: Optional preflight validator for field_priorities.
                If provided, validates configuration before Extract phase.
            dependencies_runner_factory: Factory to create dependency PipelineRunner.
                Takes pipeline name and keys DataFrame.
            dependency_coordinator: Coordinator for running dependencies.
        """
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
        self._finished: bool = False
        self._final_state: CompositePipelineState | None = None
        self._dq_report_service = dq_report_service
        self._preflight_validator = preflight_validator

        # Initialize FSM helper for state transition logic
        from bioetl.application.composite.fsm_helper import FSMStateHelper

        self._fsm = FSMStateHelper(
            config=config,
            logger=logger,
            run_id=self._run_id_str,
        )

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
        5. Run dependencies (if configured, to populate Silver tables)
        6. Run enrichers in parallel (fan-out)
        7. Merge results into Gold
        8. Delete checkpoint on success

        Returns:
            CompositeResult with all sub-pipeline results.

        Raises:
            CriticalError: If seed or required enricher/dependency fails.
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

        # Run preflight validation for field_priorities (BEFORE Extract phase)
        # This catches schema drift and configuration errors early
        self._run_preflight_validation()

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
            state = self._fsm.handle_resume_from_failed(state)

        # Log resume context if resuming with progress
        if self._runtime.resume and state.is_resumable:
            self._fsm.log_resume_context(state)

        # Step 1: Run seed phase
        state, seed_result = await self._execute_seed_phase(state)

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

        # Step 3: Run dependencies phase
        state, dependency_results = await self._execute_dependencies_phase(
            state, keys_df
        )

        # Step 4: Run enrichment phase
        state, enrichment_results = await self._execute_enrichment_phase(state, keys_df)

        # Step 5: Transition to ENRICHMENT_COMPLETED
        state = await self._transition_to_enrichment_completed(state)

        # Step 6: Execute merge or skip in dry run mode
        state, merge_result = await self._execute_merge_stage(
            state, enrichment_results, dependency_results
        )

        # Step 7: Finalize - set COMPLETED and cleanup checkpoint
        await self._finalize_pipeline(state)

        return self._build_composite_result(
            seed_result, dependency_results, enrichment_results, merge_result
        )

    async def _execute_seed_phase(
        self, state: CompositeCheckpointState
    ) -> tuple[CompositeCheckpointState, SeedResult]:
        """Execute the seed phase or resume from checkpoint."""
        if not state.seed_completed:
            return await self._run_seed_with_fsm(state)

        # Resume: seed already completed
        self._logger.info(
            "Seed already completed, resuming from checkpoint",
            composite=self._config.name,
            run_id=self._run_id_str,
        )
        if state.state != CompositePipelineState.SEED_COMPLETED:
            previous_state = state.state
            state = state.with_state(CompositePipelineState.SEED_COMPLETED)
            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.SEED_COMPLETED,
                stage="seed_resume",
            )
        return state, SeedResult(pipeline_name=self._config.seed.pipeline, resumed=True)

    async def _run_seed_with_fsm(
        self, state: CompositeCheckpointState
    ) -> tuple[CompositeCheckpointState, SeedResult]:
        """Run seed pipeline with FSM state transitions."""
        previous_state = state.state
        self._fsm.validate_fsm_transition(
            previous_state, CompositePipelineState.SEED_RUNNING
        )
        state = state.with_state(CompositePipelineState.SEED_RUNNING)
        self._fsm.log_fsm_transition(
            from_state=previous_state,
            to_state=CompositePipelineState.SEED_RUNNING,
            stage="seed_start",
        )
        self._logger.info(
            PipelineEvent.phase_started("seed"),
            composite=self._config.name,
            run_id=self._run_id_str,
        )
        await self._save_checkpoint_safe(state, "seed_running")

        try:
            seed_result = await self._run_seed()
        except Exception as e:
            self._logger.error(
                "Seed pipeline failed",
                composite=self._config.name,
                run_id=self._run_id_str,
                seed_pipeline=self._config.seed.pipeline,
                error=str(e),
            )
            self._fsm.log_fsm_transition(
                from_state=CompositePipelineState.SEED_RUNNING,
                to_state=CompositePipelineState.FAILED,
                stage="seed_failed",
                error=str(e),
            )
            failed_state = state.with_state(CompositePipelineState.FAILED)
            await self._save_checkpoint_safe(failed_state, "seed_failed")
            raise

        state = state.with_seed_completed(seed_result)
        self._fsm.log_fsm_transition(
            from_state=CompositePipelineState.SEED_RUNNING,
            to_state=CompositePipelineState.SEED_COMPLETED,
            stage="seed_complete",
            records_extracted=seed_result.records_extracted,
            records_silver=seed_result.records_silver,
        )
        self._logger.info(
            PipelineEvent.phase_completed("seed"),
            composite=self._config.name,
            run_id=self._run_id_str,
            records_extracted=seed_result.records_extracted,
            records_silver=seed_result.records_silver,
        )
        await self._save_checkpoint_safe(state, "seed_completed")
        return state, seed_result

    def _has_dependencies_configured(self) -> bool:
        """Check if dependencies phase is configured and ready."""
        return bool(
            self._config.dependencies
            and self._dependency_coordinator
            and self._dependencies_runner_factory
        )

    def _find_required_failures(
        self, results: dict[str, DependencyResult]
    ) -> list[str]:
        """Find required dependencies that failed."""
        failed = []
        for name, result in results.items():
            if result.is_success:
                continue
            dep_cfg = self._config.get_dependency(name)
            if dep_cfg and dep_cfg.required:
                failed.append(name)
        return failed

    async def _execute_dependencies_phase(
        self,
        state: CompositeCheckpointState,
        keys_df: pl.DataFrame,
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]:
        """Execute the dependencies phase if configured."""
        dependency_results: dict[str, DependencyResult] = {}
        if not self._has_dependencies_configured():
            return state, dependency_results

        assert self._dependency_coordinator is not None
        assert self._dependencies_runner_factory is not None

        previous_state = state.state
        self._fsm.validate_fsm_transition(
            previous_state, CompositePipelineState.DEPENDENCIES_RUNNING
        )
        state = state.with_state(CompositePipelineState.DEPENDENCIES_RUNNING)
        await self._checkpoint_manager.save(state)

        dep_pipelines = [d.pipeline for d in self._config.dependencies]
        self._fsm.log_fsm_transition(
            from_state=previous_state,
            to_state=CompositePipelineState.DEPENDENCIES_RUNNING,
            stage="dependencies_start",
            dependencies=dep_pipelines,
            count=len(dep_pipelines),
        )
        self._logger.info(
            PipelineEvent.phase_started("dependencies"),
            composite=self._config.name,
            run_id=self._run_id_str,
            dependencies=dep_pipelines,
            count=len(dep_pipelines),
        )

        dependency_results = await self._dependency_coordinator.run_dependencies(
            keys=keys_df,
            dependencies=self._config.dependencies,
            completed=state.completed_dependencies,
            runner_factory=self._dependencies_runner_factory,
            dependency_configs={d.pipeline: d for d in self._config.dependencies},
        )

        for dep_name, dep_result in dependency_results.items():
            if dep_result.is_success:
                state = state.with_dependency_completed(dep_name, dep_result)

        required_failed = self._find_required_failures(dependency_results)
        if required_failed:
            state = state.with_state(CompositePipelineState.FAILED)
            await self._checkpoint_manager.save(state)
            raise RuntimeError(f"Required dependencies failed: {required_failed}")

        previous_state = state.state
        state = state.with_state(CompositePipelineState.DEPENDENCIES_COMPLETED)
        succeeded = sum(1 for r in dependency_results.values() if r.is_success)
        failed = len(dependency_results) - succeeded
        self._fsm.log_fsm_transition(
            from_state=previous_state,
            to_state=CompositePipelineState.DEPENDENCIES_COMPLETED,
            stage="dependencies_complete",
            succeeded=succeeded,
            failed=failed,
        )
        self._logger.info(
            PipelineEvent.phase_completed("dependencies"),
            composite=self._config.name,
            run_id=self._run_id_str,
            succeeded=succeeded,
            failed=failed,
        )
        await self._checkpoint_manager.save(state)
        return state, dependency_results

    async def _execute_enrichment_phase(
        self,
        state: CompositeCheckpointState,
        keys_df: pl.DataFrame,
    ) -> tuple[CompositeCheckpointState, dict[str, EnrichmentResult]]:
        """Execute the enrichment phase."""
        enrichers_to_run = self._get_enrichers_to_run(state)
        enrichment_results: dict[str, EnrichmentResult] = {}

        if enrichers_to_run:
            enricher_names = [e.pipeline for e in enrichers_to_run]
            previous_state = state.state
            self._fsm.validate_fsm_transition(
                previous_state, CompositePipelineState.ENRICHING
            )
            state = state.with_state(CompositePipelineState.ENRICHING)
            await self._checkpoint_manager.save(state)

            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.ENRICHING,
                stage="enrichment_start",
                enrichers=enricher_names,
                count=len(enrichers_to_run),
            )
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

            for name, result in enrichment_results.items():
                if result.is_success or result.status == EnrichmentStatus.SKIPPED:
                    state = state.with_enricher_completed(name, result)
            await self._checkpoint_manager.save(state)

            log_enrichment_summary(enrichment_results, self._config.name, self._logger)
        else:
            self._logger.info(
                "No enrichers to run, skipping enrichment stage",
                composite=self._config.name,
                reason="all_completed_or_filtered",
            )

        enrichment_results.update(state.enrichment_results)

        enrichment_results = add_not_run_results(
            enrichment_results,
            enrichers_to_run,
            self._config.enrichers,
            state.completed_enrichers,
            self._runtime.required_only,
            self._config.name,
            self._logger,
        )

        # Check required enrichers with FSM FAILED transition on error
        try:
            self._check_required_enrichers(enrichment_results)
        except RuntimeError as e:
            previous_state = state.state
            state = state.with_state(CompositePipelineState.FAILED)
            self._fsm.log_fsm_transition(
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

        return state, enrichment_results

    def _build_composite_result(
        self,
        seed_result: SeedResult,
        dependency_results: dict[str, DependencyResult],
        enrichment_results: dict[str, EnrichmentResult],
        merge_result: MergeResult | None,
    ) -> CompositeResult:
        """Build the final CompositeResult."""
        completed_at = datetime.now(tz=UTC)
        started = self._started_at or completed_at
        total_duration = (completed_at - started).total_seconds()

        had_warnings = calculate_had_warnings(
            enrichment_results,
            frozenset(self._config.required_enrichers),
            self._config.name,
            self._logger,
        )

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
            dependency_results=dependency_results,
            enrichment_results=enrichment_results,
            merge_result=merge_result,
            total_duration_seconds=total_duration,
            started_at=self._started_at,
            completed_at=completed_at,
            had_warnings=had_warnings,
            _required_enrichers=frozenset(self._config.required_enrichers),
            _required_dependencies=frozenset(self._config.required_dependencies),
        )

    async def _transition_to_enrichment_completed(
        self, state: CompositeCheckpointState
    ) -> CompositeCheckpointState:
        """Transition FSM state to ENRICHMENT_COMPLETED.

        Handles the case where no enrichers were run (state is still SEED_COMPLETED
        or DEPENDENCIES_COMPLETED). Must go through ENRICHING first per FSM rules.
        """
        from bioetl.domain.composite.state import CompositePipelineState

        # Handle states that need to transition through ENRICHING first
        if state.state in (
            CompositePipelineState.SEED_COMPLETED,
            CompositePipelineState.DEPENDENCIES_COMPLETED,
        ):
            # Must go through ENRICHING first per FSM rules (no enrichers case)
            previous_state = state.state
            self._fsm.validate_fsm_transition(
                previous_state, CompositePipelineState.ENRICHING
            )
            state = state.with_state(CompositePipelineState.ENRICHING)
            self._fsm.log_fsm_transition(
                from_state=previous_state,
                to_state=CompositePipelineState.ENRICHING,
                stage="enrichment_start_empty",
                reason="no_enrichers_to_run",
            )

        if state.state == CompositePipelineState.ENRICHING:
            enriching_state: CompositePipelineState = state.state
            self._fsm.validate_fsm_transition(
                enriching_state, CompositePipelineState.ENRICHMENT_COMPLETED
            )
            state = state.with_state(CompositePipelineState.ENRICHMENT_COMPLETED)
            await self._save_checkpoint_safe(state, "enrichment_completed")

            # Log FSM transition to ENRICHMENT_COMPLETED
            self._fsm.log_fsm_transition(
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
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> tuple[CompositeCheckpointState, MergeResult | None]:
        """Execute merge stage or skip in dry run mode.

        Returns updated state and merge result (None for dry run).
        """
        from bioetl.domain.composite.state import CompositePipelineState

        merge_result: MergeResult | None = None

        if not self._runtime.dry_run:
            # Validate and transition to MERGING state
            previous_state = state.state
            self._fsm.validate_fsm_transition(
                previous_state, CompositePipelineState.MERGING
            )
            state = state.with_state(CompositePipelineState.MERGING)
            await self._save_checkpoint_safe(state, "merging")

            # Log FSM transition to MERGING
            self._fsm.log_fsm_transition(
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
                mergeable_enrichers = get_mergeable_enrichers(
                    enrichment_results, self._config.enrichers, self._logger
                )

                # Get only dependencies with data to merge
                mergeable_dependencies = get_mergeable_dependencies(
                    dependency_results or {},
                    self._config.dependencies,
                    self._logger,
                )

                merge_result = await self._merger.merge(
                    seed_table=self._config.seed.silver_table,
                    enrichers=mergeable_enrichers,
                    enrichment_results=enrichment_results,
                    run_id=self._run_id_str,
                    seed_pipeline=self._config.seed.pipeline,
                    dependencies=mergeable_dependencies,
                    dependency_results=dependency_results,
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
                self._fsm.log_fsm_transition(
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
            self._fsm.log_fsm_transition(
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
            self._fsm.validate_fsm_transition(
                previous_state, CompositePipelineState.COMPLETED
            )
            state = state.with_state(CompositePipelineState.COMPLETED)

            # Log FSM transition to COMPLETED
            self._fsm.log_fsm_transition(
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

    def _run_preflight_validation(self) -> None:
        """Run preflight validation for field_priorities configuration.

        Validates that all field_priorities reference valid fields and sources
        with compatible types BEFORE the Extract phase starts.

        This catches schema drift and configuration errors early, preventing
        failures during the merge phase where they are harder to diagnose.

        Raises:
            PreflightValidationError: If validation fails with blocking errors.
        """
        if self._preflight_validator is None:
            # No validator configured - skip preflight validation
            self._logger.debug(
                "Preflight validation skipped",
                composite=self._config.name,
                reason="preflight_validator not configured",
            )
            return

        # Check if field_priorities are configured
        if not self._config.merge.field_priorities:
            self._logger.debug(
                "Preflight validation skipped",
                composite=self._config.name,
                reason="no field_priorities configured",
            )
            return

        self._logger.info(
            PipelineEvent.phase_started("preflight_validation"),
            composite=self._config.name,
            run_id=self._run_id_str,
            field_count=len(self._config.merge.field_priorities),
        )

        # Run validation - will raise PreflightValidationError on failure
        result = self._preflight_validator.validate(
            self._config,
            fail_on_error=True,
        )

        # Log resolved field sources for auditability
        self._preflight_validator.log_resolved_field_sources(result, self._config.name)

        self._logger.info(
            PipelineEvent.phase_completed("preflight_validation"),
            composite=self._config.name,
            run_id=self._run_id_str,
            fields_validated=len(result.resolved_fields),
            warnings=len(result.warnings),
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
