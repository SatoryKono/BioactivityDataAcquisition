"""Unit tests for EnrichmentCoordinator fallback strategies.

Tests verify that fallback strategies (SKIP, FAIL) are respected
regardless of the 'required' flag.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from bioetl.application.composite.coordinator import EnrichmentCoordinator
from bioetl.domain.composite.strategy import FallbackStrategy


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock LoggerPort."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def mock_dq_config() -> MagicMock:
    """Create a mock CompositeDQConfig."""
    config = MagicMock()
    config.get_enricher_hard_threshold = MagicMock(return_value=0.20)
    return config


@pytest.fixture
def sample_keys() -> pl.DataFrame:
    """Create sample keys DataFrame."""
    return pl.DataFrame(
        {
            "chembl_id": ["CHEMBL1", "CHEMBL2"],
            "doi": ["10.1000/abc", "10.1000/def"],
        }
    )


@pytest.fixture
def coordinator(mock_logger, mock_dq_config) -> EnrichmentCoordinator:
    """Create EnrichmentCoordinator instance."""
    return EnrichmentCoordinator(
        logger=mock_logger,
        dq_config=mock_dq_config,
        max_concurrency=4,
    )


@pytest.mark.unit
class TestCoordinatorFallbackStrategy:
    """Tests for fallback strategy application."""

    @pytest.mark.asyncio
    async def test_fallback_fail_strategy_raises_error_for_optional_enricher(
        self, coordinator, mock_logger, sample_keys
    ) -> None:
        """Test that fallback_strategy=FAIL raises exception even if required=False."""
        enricher_config = MagicMock()
        enricher_config.pipeline = "pubmed"
        enricher_config.required = False  # Optional
        enricher_config.fallback_strategy = FallbackStrategy.FAIL  # But strategy is FAIL
        enricher_config.timeout_seconds = 60
        enricher_config.filter_condition = None

        def failing_factory(name: str, keys: pl.DataFrame) -> MagicMock:
            runner = MagicMock()
            runner.run = AsyncMock(side_effect=RuntimeError("Critical API failure"))
            return runner

        # Should raise RuntimeError because strategy is FAIL
        # Note: run_enrichers catches exceptions via asyncio.gather(return_exceptions=True)
        # IF the exception is raised within the task.
        # But let's see how _run_single_enricher behaves.
        # If it raises, gather will catch it and return it in the list.
        # So we expect the result for this enricher to be an exception object,
        # or the coordinator might wrap it.
        # Actually, `run_enrichers` returns a dict of results.
        # If _run_single_enricher raises, `asyncio.gather` with return_exceptions=True
        # will return the Exception object.
        # Then `_process_results` converts Exception to EnrichmentResult.failed.

        # WAIT. If I want it to "Fail the composite", simply returning a failed result
        # for an optional enricher will NOT fail the composite (Runner only checks required enrichers).

        # So, if fallback_strategy=FAIL, the coordinator must ensure that the error
        # propagates in a way that the Runner sees it as a failure.
        # BUT, the Runner logic is:
        # Step 6: Check required enrichers...

        # If an optional enricher fails, the Runner ignores it.
        # Unless the Coordinator raises the exception out of `run_enrichers`.
        # But `run_enrichers` uses `gather(return_exceptions=True)`.

        # So, for `FAIL` strategy to work effectively (i.e., stop the pipeline),
        # `_process_results` needs to identify that this optional enricher FAILED with
        # a strategy that demands composite failure, and re-raise?

        # OR, `_run_single_enricher` should raise, and `run_enrichers` should NOT
        # return it as a failed result but let it bubble up?
        # No, `gather` swallows it into the result list.

        # So `_process_results` is the place where we should check:
        # "If this result is an Exception, AND the strategy was FAIL, then Re-raise."

        # However, `_process_results` currently doesn't have access to the config
        # to know the strategy.

        # Desired Behavior: It raises RuntimeError.

        with pytest.raises(RuntimeError, match="Critical API failure"):
             await coordinator.run_enrichers(
                keys=sample_keys,
                enrichers=[enricher_config],
                completed=frozenset(),
                runner_factory=failing_factory,
            )

    @pytest.mark.asyncio
    async def test_fallback_skip_strategy_suppresses_error(
        self, coordinator, mock_logger, sample_keys
    ) -> None:
        """Test that fallback_strategy=SKIP suppresses error (default behavior)."""
        enricher_config = MagicMock()
        enricher_config.pipeline = "pubmed"
        enricher_config.required = False
        enricher_config.fallback_strategy = FallbackStrategy.SKIP
        enricher_config.timeout_seconds = 60
        enricher_config.filter_condition = None

        def failing_factory(name: str, keys: pl.DataFrame) -> MagicMock:
            runner = MagicMock()
            runner.run = AsyncMock(side_effect=RuntimeError("API error"))
            return runner

        results = await coordinator.run_enrichers(
            keys=sample_keys,
            enrichers=[enricher_config],
            completed=frozenset(),
            runner_factory=failing_factory,
        )

        assert "pubmed" in results
        assert not results["pubmed"].is_success
        # Should not raise
