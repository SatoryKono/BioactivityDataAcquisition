"""Unit tests for ShutdownService."""

from __future__ import annotations

import asyncio

import pytest

from bioetl.application.services.shutdown_service import (
    PipelineShutdownError,
    ShutdownReason,
    ShutdownService,
)


class MockLogger:
    """Mock logger for testing."""

    def __init__(self) -> None:
        self.warnings: list[tuple[str, dict]] = []
        self.infos: list[tuple[str, dict]] = []

    def warning(self, msg: str, **kwargs) -> None:
        self.warnings.append((msg, kwargs))

    def info(self, msg: str, **kwargs) -> None:
        self.infos.append((msg, kwargs))


class MockMetrics:
    """Mock metrics for testing."""

    def __init__(self) -> None:
        self.increments: list[tuple[str, int, dict]] = []

    def increment_counter(
        self, name: str, value: int = 1, labels: dict | None = None
    ) -> None:
        self.increments.append((name, value, labels or {}))


@pytest.fixture
def logger() -> MockLogger:
    """Create mock logger."""
    return MockLogger()


@pytest.fixture
def metrics() -> MockMetrics:
    """Create mock metrics."""
    return MockMetrics()


@pytest.fixture
def shutdown_service(logger: MockLogger, metrics: MockMetrics) -> ShutdownService:
    """Create ShutdownService with mocks."""
    return ShutdownService(logger=logger, metrics=metrics)


@pytest.mark.unit
class TestShutdownService:
    """Tests for ShutdownService class."""

    def test_initial_state(self, shutdown_service: ShutdownService):
        """Test initial state is not shutting down."""
        assert shutdown_service.is_shutting_down() is False
        assert shutdown_service.reason == ShutdownReason.UNKNOWN

    @pytest.mark.asyncio
    async def test_initiate_shutdown_sets_flag(self, shutdown_service: ShutdownService):
        """Test initiate_shutdown sets the shutdown flag."""
        await shutdown_service.initiate_shutdown("test reason")
        assert shutdown_service.is_shutting_down() is True

    @pytest.mark.asyncio
    async def test_initiate_shutdown_is_idempotent(
        self, shutdown_service: ShutdownService
    ):
        """Test multiple shutdown calls are ignored."""
        await shutdown_service.initiate_shutdown("SIGTERM received")
        await shutdown_service.initiate_shutdown("SIGINT received")

        # Should keep first reason (SIGTERM)
        assert shutdown_service.reason == ShutdownReason.SIGNAL_SIGTERM
        assert shutdown_service.is_shutting_down() is True

    @pytest.mark.asyncio
    async def test_initiate_shutdown_logs_warning(
        self, shutdown_service: ShutdownService, logger: MockLogger
    ):
        """Test shutdown initiation logs a warning."""
        await shutdown_service.initiate_shutdown("SIGTERM received")

        assert len(logger.warnings) == 1
        assert "Shutdown initiated" in logger.warnings[0][0]
        assert logger.warnings[0][1]["reason"] == "SIGTERM received"

    @pytest.mark.asyncio
    async def test_initiate_shutdown_emits_metric(
        self, shutdown_service: ShutdownService, metrics: MockMetrics
    ):
        """Test shutdown initiation emits metric."""
        await shutdown_service.initiate_shutdown("signal 15 (SIGTERM)")

        assert len(metrics.increments) == 1
        assert metrics.increments[0][0] == "bioetl_shutdown_initiated"
        assert metrics.increments[0][1] == 1  # value
        assert metrics.increments[0][2]["reason"] == "SIGTERM"

    def test_request_synchronous(self, shutdown_service: ShutdownService):
        """Test synchronous request() for backward compatibility."""
        shutdown_service.request()
        assert shutdown_service.is_shutting_down() is True

    @pytest.mark.asyncio
    async def test_wait_blocks_until_shutdown(self, shutdown_service: ShutdownService):
        """Test wait() blocks until shutdown is initiated."""

        async def initiate_after_delay():
            await asyncio.sleep(0.05)
            await shutdown_service.initiate_shutdown("delayed shutdown")

        task = asyncio.create_task(initiate_after_delay())
        await asyncio.wait_for(shutdown_service.wait(), timeout=1.0)

        assert shutdown_service.is_shutting_down() is True
        await task

    @pytest.mark.asyncio
    async def test_wait_for_completion_timeout(self, shutdown_service: ShutdownService):
        """Test wait_for_completion returns False on timeout."""
        result = await shutdown_service.wait_for_completion(timeout_seconds=0.01)
        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_completion_success(self, shutdown_service: ShutdownService):
        """Test wait_for_completion returns True when marked complete."""

        async def mark_complete_after_delay():
            await asyncio.sleep(0.05)
            shutdown_service.mark_completed()

        task = asyncio.create_task(mark_complete_after_delay())
        result = await shutdown_service.wait_for_completion(timeout_seconds=1.0)

        assert result is True
        await task

    def test_mark_completed_emits_metric(
        self, shutdown_service: ShutdownService, metrics: MockMetrics
    ):
        """Test mark_completed emits metric."""
        shutdown_service.mark_completed()

        assert len(metrics.increments) == 1
        assert metrics.increments[0][0] == "bioetl_shutdown_completed"
        assert metrics.increments[0][1] == 1  # value

    def test_reset_clears_state(self, shutdown_service: ShutdownService):
        """Test reset clears all state."""
        shutdown_service.request()
        shutdown_service.reset()

        assert shutdown_service.is_shutting_down() is False
        assert shutdown_service.reason == ShutdownReason.UNKNOWN


@pytest.mark.unit
class TestShutdownReason:
    """Tests for ShutdownReason parsing."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "reason,expected",
        [
            ("signal 15 (SIGTERM)", ShutdownReason.SIGNAL_SIGTERM),
            ("SIGTERM received", ShutdownReason.SIGNAL_SIGTERM),
            ("signal 2 (SIGINT)", ShutdownReason.SIGNAL_SIGINT),
            ("SIGINT from user", ShutdownReason.SIGNAL_SIGINT),
            ("Lock lost during heartbeat", ShutdownReason.LOCK_LOST),
            ("lock was lost", ShutdownReason.LOCK_LOST),
            ("DQ threshold exceeded", ShutdownReason.DQ_THRESHOLD_EXCEEDED),
            ("dq_soft_threshold hit", ShutdownReason.DQ_THRESHOLD_EXCEEDED),
            ("Operation timeout", ShutdownReason.TIMEOUT),
            ("User requested stop", ShutdownReason.USER_REQUESTED),
            ("Unknown reason", ShutdownReason.UNKNOWN),
            ("", ShutdownReason.UNKNOWN),
        ],
    )
    async def test_reason_parsing(
        self, logger: MockLogger, reason: str, expected: ShutdownReason
    ):
        """Test shutdown reason is correctly parsed."""
        service = ShutdownService(logger=logger)
        await service.initiate_shutdown(reason)
        assert service.reason == expected


@pytest.mark.unit
class TestPipelineShutdownError:
    """Tests for PipelineShutdownError from shutdown_service."""

    def test_can_be_raised(self):
        """Test exception can be raised and caught."""
        with pytest.raises(PipelineShutdownError):
            raise PipelineShutdownError()

    def test_with_reason(self):
        """Test exception with reason."""
        error = PipelineShutdownError("Lock lost", reason=ShutdownReason.LOCK_LOST)
        assert error.reason == ShutdownReason.LOCK_LOST
        assert "Lock lost" in str(error)

    def test_default_reason(self):
        """Test default reason is UNKNOWN."""
        error = PipelineShutdownError()
        assert error.reason == ShutdownReason.UNKNOWN


@pytest.mark.unit
class TestShutdownServiceWithoutMetrics:
    """Test ShutdownService works without metrics."""

    @pytest.mark.asyncio
    async def test_initiate_without_metrics(self, logger: MockLogger):
        """Test shutdown works without metrics port."""
        service = ShutdownService(logger=logger, metrics=None)
        await service.initiate_shutdown("test")

        # Should not raise
        assert service.is_shutting_down() is True

    def test_mark_completed_without_metrics(self, logger: MockLogger):
        """Test mark_completed works without metrics port."""
        service = ShutdownService(logger=logger, metrics=None)
        service.mark_completed()

        # Should not raise
        assert True
