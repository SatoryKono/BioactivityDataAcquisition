"""Unit tests for CompositePipelineRunner required flag handling.

Tests for:
- Optional enricher failure handling (had_warnings)
- NOT_RUN status for skipped optional enrichers (required_only mode)
- Mergeable enricher filtering
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import polars as pl
import pytest

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg import (
    CompositePipelineRunner,
    CompositeRunnerDependencies,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite.result import (
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
)
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.locking import FencingToken

_MOCK_TOKEN = FencingToken(
    sequence=1,
    key="lock:mock",
    owner_id=UUID("00000000-0000-0000-0000-000000000000"),
    issued_at=0.0,
)


@dataclass
class MockEnricherConfig:
    """Mock enricher configuration."""

    pipeline: str
    join_keys: tuple[str, ...] = ("doi",)
    required: bool = False
    filter_condition: str | None = None
    timeout_seconds: int = 600
    silver_table: str | None = None


@dataclass
class MockCompositeConfig:
    """Mock composite configuration for testing."""

    name: str = "test_composite"
    lock_key: str = "lock:test_composite"

    @dataclass
    class SeedConfig:
        pipeline: str = "chembl_activity"
        silver_table: str = "chembl_activity"
        output_keys: tuple[str, ...] = ("chembl_id", "doi")

    @dataclass
    class MergeConfig:
        output_silver_path: str = "silver/composite"
        output_gold_path: str = "gold/composite"

    @dataclass
    class DQConfig:
        soft_fail_threshold: float = 0.05
        hard_fail_threshold: float = 0.20

    seed: SeedConfig = None  # type: ignore[assignment]
    merge: MergeConfig = None  # type: ignore[assignment]
    dq: DQConfig = None  # type: ignore[assignment]
    enrichers: tuple[MockEnricherConfig, ...] = ()
    dependencies: tuple = ()

    @property
    def required_dependencies(self) -> tuple[str, ...]:
        return tuple(
            d.pipeline for d in self.dependencies if getattr(d, "required", False)
        )

    def __post_init__(self):
        if self.seed is None:
            self.seed = self.SeedConfig()
        if self.merge is None:
            self.merge = self.MergeConfig()
        if self.dq is None:
            self.dq = self.DQConfig()
        if not self.enrichers:
            # Default: one required, one optional enricher
            self.enrichers = (
                MockEnricherConfig(pipeline="crossref", required=True),
                MockEnricherConfig(pipeline="pubmed", required=False),
            )

    @property
    def required_enrichers(self) -> tuple[str, ...]:
        return tuple(e.pipeline for e in self.enrichers if e.required)


class MockPipelineRunner:
    """Mock PipelineRunner for testing."""

    def __init__(self, should_fail: bool = False, error_message: str = "Failed"):
        self._should_fail = should_fail
        self._error_message = error_message
        self.run_called = False
        self._executor = MagicMock()
        self._executor.records_fetched = 100
        self._executor.records_silver = 95

    @property
    def execution_metrics(self) -> dict[str, int]:
        return {
            "records_fetched": self._executor.records_fetched,
            "records_silver": self._executor.records_silver,
        }

    async def run(self):
        await asyncio.sleep(0)
        self.run_called = True
        if self._should_fail:
            raise RuntimeError(self._error_message)


def create_mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    return logger


def create_mock_lock() -> AsyncMock:
    """Create a mock lock."""
    lock = AsyncMock()
    lock.acquire = AsyncMock(return_value=_MOCK_TOKEN)
    lock.release = AsyncMock(return_value=True)
    return lock


def create_mock_checkpoint_manager(
    initial_state: CompositeCheckpointState | None = None,
) -> AsyncMock:
    """Create a mock checkpoint manager."""
    manager = AsyncMock()
    if initial_state is None:
        initial_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            created_at=datetime.now(tz=UTC),
        )
    manager.load = AsyncMock(return_value=initial_state)
    manager.save = AsyncMock()
    manager.delete = AsyncMock()
    return manager


def create_mock_key_extractor() -> AsyncMock:
    """Create a mock key extractor."""
    extractor = AsyncMock()
    extractor.extract = AsyncMock(
        return_value=pl.DataFrame({"chembl_id": ["CHEMBL123"], "doi": ["10.1234/test"]})
    )
    return extractor


def create_mock_coordinator(
    enrichment_results: dict[str, EnrichmentResult] | None = None,
) -> AsyncMock:
    """Create a mock enrichment coordinator."""
    coordinator = AsyncMock()
    if enrichment_results is None:
        enrichment_results = {}
    coordinator.run_enrichers = AsyncMock(return_value=enrichment_results)
    return coordinator


def create_mock_merger() -> AsyncMock:
    """Create a mock merger."""
    merger = AsyncMock()
    merger.merge = AsyncMock(
        return_value=MergeResult(
            records_merged=100,
            records_from_seed=100,
            records_enriched=0,
            records_fully_enriched=0,
            duration_seconds=1.0,
        )
    )
    return merger


def _seed_runner_factory(seed_runner: MockPipelineRunner):
    def _factory() -> MockPipelineRunner:
        return seed_runner

    return _factory


def _new_enricher_runner_factory():
    def _factory(name: str, df: object) -> MockPipelineRunner:
        return MockPipelineRunner()

    return _factory


def create_runner(
    config: MockCompositeConfig | None = None,
    seed_runner: MockPipelineRunner | None = None,
    checkpoint_manager: AsyncMock | None = None,
    coordinator: AsyncMock | None = None,
    merger: AsyncMock | None = None,
    logger: MagicMock | None = None,
    runtime: CompositeRuntimeConfig | None = None,
) -> CompositePipelineRunner:
    """Create a CompositePipelineRunner for testing."""
    if config is None:
        config = MockCompositeConfig()
    if seed_runner is None:
        seed_runner = MockPipelineRunner()
    if checkpoint_manager is None:
        checkpoint_manager = create_mock_checkpoint_manager()
    if coordinator is None:
        coordinator = create_mock_coordinator()
    if merger is None:
        merger = create_mock_merger()
    if logger is None:
        logger = create_mock_logger()
    if runtime is None:
        runtime = CompositeRuntimeConfig()

    deps = CompositeRunnerDependencies(
        seed_runner_factory=_seed_runner_factory(seed_runner),
        enricher_runner_factory=_new_enricher_runner_factory(),
        key_extractor=create_mock_key_extractor(),
        coordinator=coordinator,
        merger=merger,
        checkpoint_manager=checkpoint_manager,
        logger=logger,
        lock=create_mock_lock(),
        fsm_state_helper=MagicMock(),
    )
    return CompositePipelineRunner(
        config=config,
        runtime=runtime,
        deps=deps,
    )


class TestOptionalEnricherFailure:
    """Tests for optional enricher failure handling."""

    @pytest.mark.asyncio
    async def test_optional_failure_does_not_raise(self):
        """Pipeline should complete when optional enricher fails."""
        # Create coordinator that returns failed optional enricher
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
            "pubmed": EnrichmentResult.failed(
                enricher_name="pubmed",
                error_message="API error",
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)

        runner = create_runner(coordinator=coordinator)

        # Should not raise
        result = await runner.run()

        assert result is not None
        assert result.is_success is True

    @pytest.mark.asyncio
    async def test_optional_failure_sets_had_warnings(self):
        """had_warnings should be True when optional enricher fails."""
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
            "pubmed": EnrichmentResult.failed(
                enricher_name="pubmed",
                error_message="Connection timeout",
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)

        runner = create_runner(coordinator=coordinator)
        result = await runner.run()

        assert result.had_warnings is True

    @pytest.mark.asyncio
    async def test_no_warnings_when_all_succeed(self):
        """had_warnings should be False when all enrichers succeed."""
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
            "pubmed": EnrichmentResult.success(
                enricher_name="pubmed",
                records_input=100,
                records_enriched=80,
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)

        runner = create_runner(coordinator=coordinator)
        result = await runner.run()

        assert result.had_warnings is False

    @pytest.mark.asyncio
    async def test_required_failure_raises(self):
        """Pipeline should fail when required enricher fails."""
        enrichment_results = {
            "crossref": EnrichmentResult.failed(
                enricher_name="crossref",
                error_message="Critical failure",
            ),
            "pubmed": EnrichmentResult.success(
                enricher_name="pubmed",
                records_input=100,
                records_enriched=80,
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)

        runner = create_runner(coordinator=coordinator)

        with pytest.raises(InvalidStateError, match="crossref"):
            await runner.run()

    @pytest.mark.asyncio
    async def test_optional_timeout_sets_had_warnings(self):
        """had_warnings should be True when optional enricher times out."""
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
            "pubmed": EnrichmentResult.timeout(
                enricher_name="pubmed",
                timeout_seconds=600,
                records_input=100,
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)

        runner = create_runner(coordinator=coordinator)
        result = await runner.run()

        assert result.had_warnings is True

    @pytest.mark.asyncio
    async def test_optional_failure_logged_as_warning(self):
        """Optional enricher failure should be logged as warning."""
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
            "pubmed": EnrichmentResult.failed(
                enricher_name="pubmed",
                error_message="API error",
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)
        logger = create_mock_logger()

        runner = create_runner(coordinator=coordinator, logger=logger)
        await runner.run()

        # Check that warning was logged for optional failure
        warning_calls = [
            c
            for c in logger.warning.call_args_list
            if "Optional enricher failed" in str(c)
        ]
        assert len(warning_calls) >= 1


class TestRequiredOnlyMode:
    """Tests for required_only mode and NOT_RUN status."""

    @pytest.mark.asyncio
    async def test_optional_enrichers_not_run_in_required_only_mode(self):
        """Optional enrichers should not be executed in required_only mode."""
        # Create coordinator that returns only required enricher result
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)

        runner = create_runner(
            coordinator=coordinator,
            runtime=CompositeRuntimeConfig(required_only=True),
        )
        result = await runner.run()

        # pubmed should have NOT_RUN status
        assert "pubmed" in result.enrichment_results
        assert result.enrichment_results["pubmed"].status == EnrichmentStatus.NOT_RUN
        assert (
            "required_only" in result.enrichment_results["pubmed"].error_message.lower()
        )

    @pytest.mark.asyncio
    async def test_not_run_enrichers_in_result(self):
        """NOT_RUN enrichers should appear in enrichment_results."""
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)

        runner = create_runner(
            coordinator=coordinator,
            runtime=CompositeRuntimeConfig(required_only=True),
        )
        result = await runner.run()

        assert "pubmed" in result.not_run_enrichers


@pytest.mark.unit
class TestRuntimeEnricherSelectionPolicy:
    """Tests for runtime enricher selection rules."""

    def test_enrich_only_filters_out_non_selected_enricher(self):
        """enrich_only should select only explicitly requested enricher pipelines."""
        runner = create_runner(runtime=CompositeRuntimeConfig(enrich_only=("pubmed",)))
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            created_at=datetime.now(tz=UTC),
        )

        selected = [e.pipeline for e in runner._get_enrichers_to_run(state)]

        assert selected == ["pubmed"]

    def test_force_enricher_overrides_completed_skip(self):
        """force_enricher should rerun a completed enricher."""
        runner = create_runner(runtime=CompositeRuntimeConfig(force_enricher="pubmed"))
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            created_at=datetime.now(tz=UTC),
            completed_enrichers=frozenset({"pubmed"}),
        )
        pubmed_cfg = next(
            enricher
            for enricher in runner._config.enrichers
            if enricher.pipeline == "pubmed"
        )

        assert runner._should_run_enricher(pubmed_cfg, state) is True

    @pytest.mark.asyncio
    async def test_not_run_does_not_affect_success(self):
        """NOT_RUN enrichers should not affect pipeline success."""
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)

        runner = create_runner(
            coordinator=coordinator,
            runtime=CompositeRuntimeConfig(required_only=True),
        )
        result = await runner.run()

        assert result.is_success is True
        assert result.had_warnings is False

    @pytest.mark.asyncio
    async def test_not_run_logged_as_info(self):
        """NOT_RUN enrichers should be logged as info."""
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)
        logger = create_mock_logger()

        runner = create_runner(
            coordinator=coordinator,
            logger=logger,
            runtime=CompositeRuntimeConfig(required_only=True),
        )
        await runner.run()

        # Check that info was logged for skipped enricher
        info_calls = [
            c
            for c in logger.info.call_args_list
            if "Optional enricher not run" in str(c)
        ]
        assert len(info_calls) >= 1

    def test_required_enricher_missing_reports_failure_reason(self):
        """Required enricher validation should explain missing required result."""
        runner = create_runner()

        failure = runner._get_required_enricher_failure({})

        assert failure == "Required enricher 'crossref' did not run"

    def test_required_enricher_failed_reports_error_message(self):
        """Required enricher validation should surface the required failure reason."""
        runner = create_runner()

        failure = runner._get_required_enricher_failure(
            {
                "crossref": EnrichmentResult.failed(
                    enricher_name="crossref",
                    error_message="timeout from upstream",
                ),
            }
        )

        assert failure == "Required enricher 'crossref' failed: timeout from upstream"

    def test_finalize_enrichment_results_adds_not_run_for_optional(
        self,
    ) -> None:
        """Post-enrichment normalization should add NOT_RUN results for skipped optional enrichers."""
        runner = create_runner(runtime=CompositeRuntimeConfig(required_only=True))
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            created_at=datetime.now(tz=UTC),
        )
        context = runner._prepare_enrichment_run_context(state)

        finalized = runner._finalize_enrichment_results(
            state=state,
            context=context,
            enrichment_results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=90,
                ),
            },
        )

        assert finalized["crossref"].status == EnrichmentStatus.SUCCESS
        assert finalized["pubmed"].status == EnrichmentStatus.NOT_RUN

    @pytest.mark.asyncio
    async def test_validate_required_enrichment_results_persists_failed_state(
        self,
    ) -> None:
        """Required enrichment validation should persist FAILED state before re-raising."""
        runner = create_runner()
        runner._save_failed_enrichment_state = AsyncMock()  # type: ignore[method-assign]
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            created_at=datetime.now(tz=UTC),
        )

        with pytest.raises(InvalidStateError, match="crossref"):
            await runner._validate_required_enrichment_results(state, {})

        runner._save_failed_enrichment_state.assert_awaited_once()
        saved_state, saved_error = runner._save_failed_enrichment_state.await_args.args
        assert saved_state is state
        assert "crossref" in str(saved_error)


class TestMergeableEnrichers:
    """Tests for mergeable enricher filtering."""

    @pytest.mark.asyncio
    async def test_not_run_enrichers_excluded_from_merge(self):
        """NOT_RUN enrichers should not be passed to merger."""
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)
        merger = create_mock_merger()

        runner = create_runner(
            coordinator=coordinator,
            merger=merger,
            runtime=CompositeRuntimeConfig(required_only=True),
        )
        await runner.run()

        # Check merger.merge was called
        merger.merge.assert_called_once()
        call_kwargs = merger.merge.call_args
        passed_enrichers = call_kwargs.kwargs.get("enrichers") or call_kwargs.args[1]

        # Only crossref should be passed (pubmed is NOT_RUN)
        enricher_names = [e.pipeline for e in passed_enrichers]
        assert "crossref" in enricher_names
        assert "pubmed" not in enricher_names

    @pytest.mark.asyncio
    async def test_skipped_enrichers_excluded_from_merge(self):
        """SKIPPED enrichers should not be passed to merger."""
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
            "pubmed": EnrichmentResult.skipped(
                enricher_name="pubmed",
                reason="No pmid keys",
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)
        merger = create_mock_merger()

        runner = create_runner(
            coordinator=coordinator,
            merger=merger,
        )
        await runner.run()

        # Check merger.merge was called
        merger.merge.assert_called_once()
        call_kwargs = merger.merge.call_args
        passed_enrichers = call_kwargs.kwargs.get("enrichers") or call_kwargs.args[1]

        # Only crossref should be passed (pubmed is SKIPPED)
        enricher_names = [e.pipeline for e in passed_enrichers]
        assert "crossref" in enricher_names
        assert "pubmed" not in enricher_names

    @pytest.mark.asyncio
    async def test_failed_enrichers_still_passed_to_merge(self):
        """FAILED enrichers should still be passed to merger (may have partial data)."""
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
            "pubmed": EnrichmentResult.failed(
                enricher_name="pubmed",
                error_message="API error",
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)
        merger = create_mock_merger()

        runner = create_runner(
            coordinator=coordinator,
            merger=merger,
        )
        await runner.run()

        # Check merger.merge was called
        merger.merge.assert_called_once()
        call_kwargs = merger.merge.call_args
        passed_enrichers = call_kwargs.kwargs.get("enrichers") or call_kwargs.args[1]

        # Both should be passed (FAILED may have partial data)
        enricher_names = [e.pipeline for e in passed_enrichers]
        assert "crossref" in enricher_names
        assert "pubmed" in enricher_names


class TestCompletionLogging:
    """Tests for completion logging with warnings."""

    @pytest.mark.asyncio
    async def test_completed_with_warnings_logged(self):
        """Completion with warnings should be logged with status."""
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
            "pubmed": EnrichmentResult.failed(
                enricher_name="pubmed",
                error_message="API error",
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)
        logger = create_mock_logger()

        runner = create_runner(coordinator=coordinator, logger=logger)
        await runner.run()

        # Check that completion was logged with warnings status
        complete_calls = [
            c
            for c in logger.info.call_args_list
            if "completed_with_warnings" in str(c) or "had_warnings" in str(c)
        ]
        assert len(complete_calls) >= 1

    @pytest.mark.asyncio
    async def test_clean_completion_no_warning_status(self):
        """Clean completion should not log warning status."""
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
            "pubmed": EnrichmentResult.success(
                enricher_name="pubmed",
                records_input=100,
                records_enriched=80,
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)
        logger = create_mock_logger()

        runner = create_runner(coordinator=coordinator, logger=logger)
        await runner.run()

        # Check that "completed_with_warnings" is NOT in any log call
        all_calls_str = str(logger.info.call_args_list)
        assert "completed_with_warnings" not in all_calls_str


class TestEnrichmentSummary:
    """Tests for enrichment summary logging."""

    @pytest.mark.asyncio
    async def test_summary_includes_not_run_count(self):
        """Enrichment summary should include NOT_RUN count."""
        enrichment_results = {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=90,
            ),
        }
        coordinator = create_mock_coordinator(enrichment_results)
        logger = create_mock_logger()

        runner = create_runner(
            coordinator=coordinator,
            logger=logger,
            runtime=CompositeRuntimeConfig(required_only=True),
        )
        await runner.run()

        # Check enrichment summary includes not_run count
        # Summary may be called, check if not_run is logged somewhere
        all_info_str = str(logger.info.call_args_list)
        # NOT_RUN enrichers should be mentioned
        assert "not_run" in all_info_str.lower() or "pubmed" in all_info_str
