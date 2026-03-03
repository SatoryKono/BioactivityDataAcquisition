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

from bioetl.application.composite.runner_constants import PIPELINE_EXECUTION_ERRORS
from bioetl.application.composite.runner_merge_stage_mixin import (
    CompositeRunnerMergeStageHelper,
)
from bioetl.application.composite.runner_stage_mixin import CompositeRunnerStageHelper
from bioetl.application.composite.runner_support_mixin import (
    CompositeRunnerSupportHelper,
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

    from bioetl.application.composite.checkpoint import CompositeCheckpointService
    from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
    from bioetl.application.composite.dependency_coordinator import (
        DependencyCoordinatorService,
    )
    from bioetl.application.composite.key_extractor import KeyExtractorService
    from bioetl.application.composite.merger import MergeService
    from bioetl.application.composite.preflight_validator import (
        CompositePreflightValidationService,
    )
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LockPort, LoggerPort, MetricsPort, QuarantinePort

__all__ = [
    "CompositePipelineRunner",
    "CompositePipelineRunnerService",
    "CompositeRuntimeConfig",
]


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
    use_cached_bronze: bool = False
    cached_bronze_path: str | None = None
    cached_bronze_date: str | None = None
    cached_bronze_enrichers: bool | None = None
    cached_bronze_dependencies: bool = False

    def __post_init__(self) -> None:
        """Convert list values into immutable tuples."""
        if isinstance(self.enrich_only, list):
            object.__setattr__(self, "enrich_only", tuple(self.enrich_only))


class CompositePipelineRunnerService(
    CompositeRunnerStageHelper,
    CompositeRunnerMergeStageHelper,
    CompositeRunnerSupportHelper,
):
    """Application-service orchestrator for composite pipeline execution."""

    def __init__(
        self,
        config: CompositeConfig,
        runtime: CompositeRuntimeConfig,
        seed_runner_factory: Callable[[], PipelineRunner],
        enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
        key_extractor: KeyExtractorService,
        coordinator: EnrichmentCoordinatorService,
        merger: MergeService,
        checkpoint_manager: CompositeCheckpointService,
        logger: LoggerPort,
        lock: LockPort,
        run_id: str | None = None,
        dq_report_service: DQReportService | None = None,
        preflight_validator: CompositePreflightValidationService | None = None,
        dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
        | None = None,
        dependency_coordinator: DependencyCoordinatorService | None = None,
        quarantine_port: QuarantinePort | None = None,
        metrics: MetricsPort | None = None,
    ) -> None:
        """Initialize runner and all stage dependencies."""
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
        self._quarantine_port = quarantine_port
        self._metrics = metrics

        from bioetl.application.composite.fsm_helper import FSMStateHelperService

        self._fsm = FSMStateHelperService(
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
        """Execute full composite pipeline lifecycle."""
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

        try:
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
                self._finished = True
                self._final_state = CompositePipelineState.COMPLETED
                return result
            finally:
                await self._lock.release(key=lock_key, owner_id=self._run_id)

        except PIPELINE_EXECUTION_ERRORS as error:
            self._finished = True
            self._final_state = CompositePipelineState.FAILED
            self._logger.error(
                PipelineEvent.FAILED,
                composite=self._config.name,
                run_id=self._run_id_str,
                error=str(error),
                error_type=type(error).__name__,
            )
            raise
        except BioETLError as error:
            self._finished = True
            self._final_state = CompositePipelineState.FAILED
            self._logger.error(
                PipelineEvent.FAILED,
                composite=self._config.name,
                run_id=self._run_id_str,
                error=str(error),
                error_type=type(error).__name__,
                reason_code="unexpected_bioetl_error",
            )
            raise

    async def _run_with_lock(self) -> CompositeResult:
        """Execute composite pipeline while lock is held."""
        state = await self._checkpoint_manager.load()

        if self._runtime.resume and state.state == CompositePipelineState.FAILED:
            state = self._fsm.handle_resume_from_failed(state)

        if self._runtime.resume and state.is_resumable:
            self._fsm.log_resume_context(state)

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
            state, enrichment_results, dependency_results
        )
        await self._finalize_pipeline(state)

        return self._build_composite_result(
            seed_result, dependency_results, enrichment_results, merge_result
        )


CompositePipelineRunner = CompositePipelineRunnerService
