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

from bioetl.domain.composite.result import (
    CompositeResult,
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)
from bioetl.domain.events import PipelineEvent
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.checkpoint import (
        CompositeCheckpointManager,
        CompositeCheckpointState,
    )
    from bioetl.application.composite.coordinator import EnrichmentCoordinator
    from bioetl.application.composite.key_extractor import KeyExtractorService
    from bioetl.application.composite.merger import MergeService
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.config import CompositeConfig, EnricherConfig
    from bioetl.domain.composite.result import EnrichmentResult
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
        """
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
                return await self._run_with_lock()
            finally:
                await self._lock.release(key=lock_key, owner_id=self._run_id)

        except Exception as e:
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

        # Track results
        seed_result: SeedResult | None = None
        enrichment_results: dict[str, EnrichmentResult] = {}
        merge_result: MergeResult | None = None

        # Step 1: Run seed (if not completed)
        if not state.seed_completed:
            seed_result = await self._run_seed()
            state = state.with_seed_completed(seed_result)
            await self._checkpoint_manager.save(state)
        else:
            self._logger.info(
                "Seed already completed, resuming from checkpoint",
                composite=self._config.name,
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

        # Step 4: Run enrichers (fan-out)
        if enrichers_to_run:
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

        # Merge with previously completed enrichers
        enrichment_results.update(state.enrichment_results)

        # Step 5: Check required enrichers
        self._check_required_enrichers(enrichment_results)

        # Step 6: Merge results
        if not self._runtime.dry_run:
            merge_result = await self._merger.merge(
                seed_table=self._config.seed.silver_table,
                enrichers=self._config.enrichers,
                enrichment_results=enrichment_results,
                run_id=self._run_id_str,
            )

            self._logger.info(
                "Merge completed",
                composite=self._config.name,
                records_merged=merge_result.records_merged,
            )

            # Step 6b: Generate DQ reports if service is available
            await self._generate_dq_reports(merge_result)

        # Step 7: Cleanup checkpoint on success
        await self._checkpoint_manager.delete()

        completed_at = datetime.now(tz=UTC)
        started = self._started_at or completed_at  # Fallback if not set
        total_duration = (completed_at - started).total_seconds()

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
            _required_enrichers=frozenset(self._config.required_enrichers),
        )

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
