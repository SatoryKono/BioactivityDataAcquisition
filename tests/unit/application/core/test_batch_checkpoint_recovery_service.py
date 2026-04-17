"""Unit tests for BatchCheckpointRecoveryService.

Tests checkpoint save semantics for periodic saves, saves on exception,
saves on shutdown, immediate saves, and the total-processed calculation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.batch_checkpoint_recovery_service import (
    BatchCheckpointRecoveryService,
)
from bioetl.domain.exceptions import BioETLError


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_checkpoint_manager():
    manager = MagicMock()
    manager.save_checkpoint = AsyncMock()
    return manager


@pytest.fixture
def mock_logger():
    logger = MagicMock()
    logger.warning = MagicMock()
    logger.info = MagicMock()
    return logger


@pytest.fixture
def mock_metrics():
    metrics = MagicMock()
    metrics.increment_counter = MagicMock()
    metrics.observe_histogram = MagicMock()
    return metrics


@pytest.fixture
def mock_tracer():
    tracer = MagicMock()
    otel_tracer = MagicMock()
    span = MagicMock()
    otel_tracer.start_as_current_span.return_value = span
    tracer.get_tracer.return_value = otel_tracer
    tracer.flush = MagicMock()
    return tracer


@pytest.fixture
def service(mock_checkpoint_manager, mock_logger, mock_metrics, mock_tracer):
    return BatchCheckpointRecoveryService(
        checkpoint_manager=mock_checkpoint_manager,
        logger=mock_logger,
        metrics=mock_metrics,
        tracer=mock_tracer,
        pipeline_name="test_pipeline",
    )


# ---------------------------------------------------------------------------
# save_periodic_checkpoint
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestSavePeriodicCheckpoint:
    """Tests for BatchCheckpointRecoveryService.save_periodic_checkpoint."""

    async def test_saves_at_exact_interval_boundary(
        self, service, mock_checkpoint_manager
    ):
        """Checkpoint is saved when records_fetched % interval == 0."""
        await service.save_periodic_checkpoint(
            records_fetched=100,
            resume_offset=0,
            checkpoint_interval=100,
        )

        mock_checkpoint_manager.save_checkpoint.assert_awaited_once_with(100)

    async def test_does_not_save_before_interval(
        self, service, mock_checkpoint_manager
    ):
        """Checkpoint is NOT saved when records_fetched % interval != 0."""
        await service.save_periodic_checkpoint(
            records_fetched=50,
            resume_offset=0,
            checkpoint_interval=100,
        )

        mock_checkpoint_manager.save_checkpoint.assert_not_awaited()

    async def test_includes_resume_offset_in_total(
        self, service, mock_checkpoint_manager
    ):
        """Total passed to checkpoint includes resume_offset + records_fetched."""
        await service.save_periodic_checkpoint(
            records_fetched=200,
            resume_offset=500,
            checkpoint_interval=100,
        )

        # total = 500 + 200 = 700
        mock_checkpoint_manager.save_checkpoint.assert_awaited_once_with(700)

    async def test_saves_multiple_times_at_multiples_of_interval(
        self, service, mock_checkpoint_manager
    ):
        """Each multiple of interval triggers a save when called repeatedly."""
        intervals = [100, 200, 300, 400, 500]
        for fetched in intervals:
            await service.save_periodic_checkpoint(
                records_fetched=fetched,
                resume_offset=0,
                checkpoint_interval=100,
            )

        assert mock_checkpoint_manager.save_checkpoint.await_count == 5

    async def test_emits_metrics_when_periodic_save_succeeds(
        self, service, mock_metrics, mock_tracer
    ):
        """Periodic checkpoint saves emit success event and duration metrics."""
        await service.save_periodic_checkpoint(
            records_fetched=100,
            resume_offset=0,
            checkpoint_interval=100,
        )

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_save_events_total",
            1,
            {
                "pipeline": "test_pipeline",
                "operation": "periodic",
                "status": "succeeded",
            },
        )
        mock_metrics.observe_histogram.assert_called_once()
        mock_tracer.get_tracer.assert_called_once_with("bioetl.checkpoint")
        mock_span = (
            mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        )
        mock_span.set_attribute.assert_called_with(
            "bioetl.checkpoint.status",
            "succeeded",
        )
        mock_tracer.flush.assert_called_once()

    async def test_no_save_at_zero_records(self, service, mock_checkpoint_manager):
        """records_fetched=0 triggers save only if 0 % interval == 0 (edge)."""
        # 0 % 100 == 0 in Python, so this DOES save — documenting the behaviour
        await service.save_periodic_checkpoint(
            records_fetched=0,
            resume_offset=0,
            checkpoint_interval=100,
        )

        mock_checkpoint_manager.save_checkpoint.assert_awaited_once_with(0)


# ---------------------------------------------------------------------------
# save_checkpoint_on_exception
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestSaveCheckpointOnException:
    """Tests for BatchCheckpointRecoveryService.save_checkpoint_on_exception."""

    async def test_saves_and_logs_when_records_processed(
        self, service, mock_checkpoint_manager, mock_logger
    ):
        """Saves checkpoint and logs warning when total > 0."""
        error = RuntimeError("pipeline crashed")

        await service.save_checkpoint_on_exception(
            records_fetched=50,
            resume_offset=100,
            error=error,
        )

        mock_checkpoint_manager.save_checkpoint.assert_awaited_once_with(150)
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["records_processed"] == 150
        assert call_kwargs["error_type"] == "RuntimeError"

    async def test_does_not_save_when_total_is_zero(
        self, service, mock_checkpoint_manager, mock_logger
    ):
        """No checkpoint saved when total processed is zero."""
        await service.save_checkpoint_on_exception(
            records_fetched=0,
            resume_offset=0,
            error=ValueError("zero records"),
        )

        mock_checkpoint_manager.save_checkpoint.assert_not_awaited()
        mock_logger.warning.assert_not_called()

    async def test_does_not_save_when_total_is_negative(
        self, service, mock_checkpoint_manager, mock_logger
    ):
        """No checkpoint saved when total processed is negative (edge case)."""
        await service.save_checkpoint_on_exception(
            records_fetched=0,
            resume_offset=-5,
            error=ValueError("negative"),
        )

        mock_checkpoint_manager.save_checkpoint.assert_not_awaited()

    async def test_emits_skipped_metric_when_exception_save_has_no_progress(
        self, service, mock_checkpoint_manager, mock_metrics
    ):
        """Exception checkpoint skips emit a bounded skipped outcome."""
        await service.save_checkpoint_on_exception(
            records_fetched=0,
            resume_offset=0,
            error=ValueError("zero records"),
        )

        mock_checkpoint_manager.save_checkpoint.assert_not_awaited()
        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_save_events_total",
            1,
            {
                "pipeline": "test_pipeline",
                "operation": "exception",
                "status": "skipped",
            },
        )
        mock_metrics.observe_histogram.assert_not_called()

    async def test_logs_warning_on_checkpoint_save_failure(
        self, mock_checkpoint_manager, mock_logger
    ):
        """If checkpoint save itself fails, a warning is logged (no re-raise)."""
        mock_checkpoint_manager.save_checkpoint = AsyncMock(
            side_effect=BioETLError("checkpoint storage failed")
        )
        service = BatchCheckpointRecoveryService(
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger,
            metrics=None,
            pipeline_name="test_pipeline",
        )

        # Must not raise — failure is swallowed and logged
        await service.save_checkpoint_on_exception(
            records_fetched=100,
            resume_offset=0,
            error=RuntimeError("pipeline error"),
        )

        # Two warning calls expected: failure log
        assert mock_logger.warning.call_count >= 1
        call_kwargs = mock_logger.warning.call_args[1]
        assert "checkpoint_save_failed" in call_kwargs.get("reason", "")

    async def test_save_failure_logs_include_error_type(
        self, mock_checkpoint_manager, mock_logger
    ):
        """Checkpoint save failure log includes the checkpoint error type."""
        mock_checkpoint_manager.save_checkpoint = AsyncMock(
            side_effect=OSError("disk full")
        )
        service = BatchCheckpointRecoveryService(
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger,
            metrics=None,
            pipeline_name="test_pipeline",
        )

        await service.save_checkpoint_on_exception(
            records_fetched=50,
            resume_offset=0,
            error=RuntimeError("upstream"),
        )

        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["error_type"] == "OSError"

    async def test_reason_includes_pipeline_exception_context(
        self, service, mock_checkpoint_manager, mock_logger
    ):
        """Success log reason mentions checkpoint saved on pipeline exception."""
        await service.save_checkpoint_on_exception(
            records_fetched=10,
            resume_offset=0,
            error=KeyError("missing_key"),
        )

        call_kwargs = mock_logger.warning.call_args[1]
        assert "pipeline_exception" in call_kwargs.get("reason", "")


# ---------------------------------------------------------------------------
# save_checkpoint_on_shutdown
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestSaveCheckpointOnShutdown:
    """Tests for BatchCheckpointRecoveryService.save_checkpoint_on_shutdown."""

    async def test_saves_emergency_checkpoint_on_shutdown(
        self, service, mock_checkpoint_manager
    ):
        """Checkpoint is saved with correct total on shutdown."""
        await service.save_checkpoint_on_shutdown(
            records_fetched=300,
            resume_offset=100,
        )

        mock_checkpoint_manager.save_checkpoint.assert_awaited_once_with(400)

    async def test_does_not_raise_on_checkpoint_failure(
        self, mock_checkpoint_manager, mock_logger
    ):
        """Checkpoint failure during shutdown logs warning and does not re-raise."""
        mock_checkpoint_manager.save_checkpoint = AsyncMock(
            side_effect=RuntimeError("shutdown storage error")
        )
        service = BatchCheckpointRecoveryService(
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger,
            metrics=None,
            pipeline_name="test_pipeline",
        )

        # Must not raise
        await service.save_checkpoint_on_shutdown(
            records_fetched=50,
            resume_offset=10,
        )

        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert "shutdown" in call_kwargs.get("reason", "").lower()

    async def test_shutdown_failure_includes_error_type(
        self, mock_checkpoint_manager, mock_logger
    ):
        """Shutdown failure log includes the checkpoint error type."""
        mock_checkpoint_manager.save_checkpoint = AsyncMock(
            side_effect=ValueError("value error in shutdown")
        )
        service = BatchCheckpointRecoveryService(
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger,
            metrics=None,
            pipeline_name="test_pipeline",
        )

        await service.save_checkpoint_on_shutdown(records_fetched=20, resume_offset=5)

        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["error_type"] == "ValueError"

    async def test_shutdown_with_zero_records_still_saves(
        self, service, mock_checkpoint_manager
    ):
        """Shutdown checkpoint is saved even when records_fetched=0."""
        await service.save_checkpoint_on_shutdown(
            records_fetched=0,
            resume_offset=0,
        )

        mock_checkpoint_manager.save_checkpoint.assert_awaited_once_with(0)

    async def test_emits_failed_metrics_when_shutdown_save_fails(
        self, mock_checkpoint_manager, mock_logger, mock_metrics, mock_tracer
    ):
        """Shutdown save failures emit failed checkpoint save metrics."""
        mock_checkpoint_manager.save_checkpoint = AsyncMock(
            side_effect=RuntimeError("shutdown storage error")
        )
        service = BatchCheckpointRecoveryService(
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger,
            metrics=mock_metrics,
            tracer=mock_tracer,
            pipeline_name="test_pipeline",
        )

        await service.save_checkpoint_on_shutdown(
            records_fetched=50,
            resume_offset=10,
        )

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_save_events_total",
            1,
            {
                "pipeline": "test_pipeline",
                "operation": "shutdown",
                "status": "failed",
            },
        )
        mock_metrics.observe_histogram.assert_called_once()
        mock_span = (
            mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        )
        mock_span.set_attribute.assert_any_call("bioetl.checkpoint.status", "failed")
        mock_span.set_attribute.assert_any_call("error", True)
        mock_span.set_attribute.assert_any_call("error.type", "RuntimeError")
        mock_span.record_exception.assert_called_once()
        mock_tracer.flush.assert_called_once()


# ---------------------------------------------------------------------------
# save_checkpoint_now
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestSaveCheckpointNow:
    """Tests for BatchCheckpointRecoveryService.save_checkpoint_now."""

    async def test_saves_total_immediately(self, service, mock_checkpoint_manager):
        """save_checkpoint_now passes total directly to checkpoint manager."""
        await service.save_checkpoint_now(
            records_fetched=75,
            resume_offset=25,
        )

        mock_checkpoint_manager.save_checkpoint.assert_awaited_once_with(100)

    async def test_propagates_exception_without_swallowing(
        self, mock_checkpoint_manager, mock_logger
    ):
        """save_checkpoint_now does NOT swallow exceptions — they propagate."""
        mock_checkpoint_manager.save_checkpoint = AsyncMock(
            side_effect=BioETLError("immediate save failed")
        )
        service = BatchCheckpointRecoveryService(
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger,
            metrics=None,
            pipeline_name="test_pipeline",
        )

        with pytest.raises(BioETLError):
            await service.save_checkpoint_now(records_fetched=10, resume_offset=0)

    async def test_zero_offset_and_zero_fetched(self, service, mock_checkpoint_manager):
        """Handles zero+zero case gracefully."""
        await service.save_checkpoint_now(records_fetched=0, resume_offset=0)

        mock_checkpoint_manager.save_checkpoint.assert_awaited_once_with(0)

    async def test_emits_metrics_for_manual_checkpoint_save(
        self, service, mock_metrics
    ):
        """Immediate/manual checkpoint saves emit success metrics."""
        await service.save_checkpoint_now(records_fetched=10, resume_offset=5)

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_save_events_total",
            1,
            {
                "pipeline": "test_pipeline",
                "operation": "manual",
                "status": "succeeded",
            },
        )
        mock_metrics.observe_histogram.assert_called_once()


# ---------------------------------------------------------------------------
# _total_processed (static helper)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTotalProcessed:
    """Tests for BatchCheckpointRecoveryService._total_processed static method."""

    def test_sums_records_and_offset(self):
        """Returns sum of records_fetched and resume_offset."""
        result = BatchCheckpointRecoveryService._total_processed(300, 700)
        assert result == 1000

    def test_zero_offset(self):
        """Zero resume_offset returns records_fetched unchanged."""
        result = BatchCheckpointRecoveryService._total_processed(42, 0)
        assert result == 42

    def test_zero_records(self):
        """Zero records_fetched returns resume_offset unchanged."""
        result = BatchCheckpointRecoveryService._total_processed(0, 500)
        assert result == 500

    def test_both_zero(self):
        """Both zero returns zero."""
        result = BatchCheckpointRecoveryService._total_processed(0, 0)
        assert result == 0

    def test_large_values(self):
        """Works correctly with large record counts."""
        result = BatchCheckpointRecoveryService._total_processed(1_000_000, 5_000_000)
        assert result == 6_000_000
