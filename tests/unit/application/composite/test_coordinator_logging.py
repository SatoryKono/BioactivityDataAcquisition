"""Unit tests for EnrichmentCoordinator logging.

Tests verify that:
1. Optional enricher failures are logged as warnings
2. Required enricher failures are logged as errors
3. Enricher success is logged as info
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from bioetl.application.composite.coordinator import EnrichmentCoordinator


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
class TestCoordinatorOptionalEnricherLogging:
    """Tests for optional enricher failure logging."""

    @pytest.mark.asyncio
    async def test_logs_warning_for_optional_enricher_failure(
        self, coordinator, mock_logger, sample_keys
    ) -> None:
        """Test that optional enricher failures are logged as warnings."""
        enricher_config = MagicMock()
        enricher_config.pipeline = "pubmed"
        enricher_config.required = False
        enricher_config.timeout_seconds = 60
        enricher_config.filter_condition = None

        # Create a factory that returns a failing runner
        def failing_factory(name: str, keys: pl.DataFrame) -> MagicMock:
            runner = MagicMock()
            runner.run = AsyncMock(side_effect=RuntimeError("API error"))
            return runner

        await coordinator.run_enrichers(
            keys=sample_keys,
            enrichers=[enricher_config],
            completed=frozenset(),
            runner_factory=failing_factory,
        )

        # Verify warning was logged
        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and "Optional enricher failed" in str(c.args[0])
        ]
        assert len(warning_calls) >= 1, "Should log warning for optional enricher failure"

        # Verify warning includes required=False
        assert any(
            c.kwargs.get("required") is False for c in warning_calls
        ), "Warning should indicate required=False"

    @pytest.mark.asyncio
    async def test_does_not_log_error_for_optional_enricher_failure(
        self, coordinator, mock_logger, sample_keys
    ) -> None:
        """Test that optional enricher failures do not log errors."""
        enricher_config = MagicMock()
        enricher_config.pipeline = "pubmed"
        enricher_config.required = False
        enricher_config.timeout_seconds = 60
        enricher_config.filter_condition = None

        def failing_factory(name: str, keys: pl.DataFrame) -> MagicMock:
            runner = MagicMock()
            runner.run = AsyncMock(side_effect=RuntimeError("API error"))
            return runner

        await coordinator.run_enrichers(
            keys=sample_keys,
            enrichers=[enricher_config],
            completed=frozenset(),
            runner_factory=failing_factory,
        )

        # Verify no error was logged for optional enricher
        error_calls = [
            c
            for c in mock_logger.error.call_args_list
            if "pubmed" in str(c)
        ]
        assert len(error_calls) == 0, "Should not log error for optional enricher failure"


@pytest.mark.unit
class TestCoordinatorRequiredEnricherLogging:
    """Tests for required enricher failure logging."""

    @pytest.mark.asyncio
    async def test_logs_error_for_required_enricher_failure(
        self, coordinator, mock_logger, sample_keys
    ) -> None:
        """Test that required enricher failures are logged as errors.

        Note: asyncio.gather(return_exceptions=True) catches exceptions,
        so coordinator returns failed result instead of raising.
        The actual exception raise happens in runner's _check_required_enrichers.
        """
        enricher_config = MagicMock()
        enricher_config.pipeline = "crossref"
        enricher_config.required = True
        enricher_config.timeout_seconds = 60
        enricher_config.filter_condition = None

        def failing_factory(name: str, keys: pl.DataFrame) -> MagicMock:
            runner = MagicMock()
            runner.run = AsyncMock(side_effect=RuntimeError("API error"))
            return runner

        # Coordinator catches exceptions via asyncio.gather(return_exceptions=True)
        # and returns failed results - doesn't raise
        results = await coordinator.run_enrichers(
            keys=sample_keys,
            enrichers=[enricher_config],
            completed=frozenset(),
            runner_factory=failing_factory,
        )

        # Verify error was logged before exception was caught
        error_calls = [
            c
            for c in mock_logger.error.call_args_list
            if c.args and "Required enricher failed" in str(c.args[0])
        ]
        assert len(error_calls) >= 1, "Should log error for required enricher failure"

        # Verify error includes required=True
        assert any(
            c.kwargs.get("required") is True for c in error_calls
        ), "Error should indicate required=True"

        # Verify result is failed
        assert "crossref" in results
        assert not results["crossref"].is_success


@pytest.mark.unit
class TestCoordinatorSuccessLogging:
    """Tests for successful enricher logging."""

    @pytest.mark.asyncio
    async def test_logs_info_for_enricher_success(
        self, coordinator, mock_logger, sample_keys
    ) -> None:
        """Test that enricher success is logged as info."""
        enricher_config = MagicMock()
        enricher_config.pipeline = "crossref"
        enricher_config.required = True
        enricher_config.timeout_seconds = 60
        enricher_config.filter_condition = None

        def success_factory(name: str, keys: pl.DataFrame) -> MagicMock:
            runner = MagicMock()
            runner.run = AsyncMock()
            executor = MagicMock()
            executor.records_silver = len(keys)
            executor.records_quarantined = 0
            runner._executor = executor
            return runner

        await coordinator.run_enrichers(
            keys=sample_keys,
            enrichers=[enricher_config],
            completed=frozenset(),
            runner_factory=success_factory,
        )

        # Verify info was logged for completion
        info_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "Enricher completed" in str(c.args[0])
        ]
        assert len(info_calls) >= 1, "Should log info for enricher completion"


@pytest.mark.unit
class TestCoordinatorTimeoutLogging:
    """Tests for enricher timeout logging."""

    @pytest.mark.asyncio
    async def test_logs_warning_for_timeout(
        self, coordinator, mock_logger, sample_keys
    ) -> None:
        """Test that enricher timeout is logged as warning."""
        import asyncio

        enricher_config = MagicMock()
        enricher_config.pipeline = "slow_enricher"
        enricher_config.required = False
        enricher_config.timeout_seconds = 0.01  # Very short timeout
        enricher_config.filter_condition = None

        async def slow_run() -> None:
            await asyncio.sleep(1.0)  # Will timeout

        def slow_factory(name: str, keys: pl.DataFrame) -> MagicMock:
            runner = MagicMock()
            runner.run = slow_run
            return runner

        await coordinator.run_enrichers(
            keys=sample_keys,
            enrichers=[enricher_config],
            completed=frozenset(),
            runner_factory=slow_factory,
        )

        # Verify warning was logged for timeout
        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and "timed out" in str(c.args[0]).lower()
        ]
        assert len(warning_calls) >= 1, "Should log warning for enricher timeout"
