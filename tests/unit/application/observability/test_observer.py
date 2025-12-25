"""Unit tests for PipelineObserver.

Tests cover:
- O4: Observer tests for duration, errors, graceful shutdown
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.shutdown import PipelineShutdownError
from bioetl.application.observability.observer import PipelineObserver
from bioetl.domain.types import RunType


@pytest.fixture
def metrics_mock():
    mock = MagicMock()
    mock.observe_histogram = MagicMock()
    mock.increment_counter = MagicMock()
    return mock


@pytest.fixture
def logger_mock():
    mock = MagicMock()
    mock.info = MagicMock()
    mock.error = MagicMock()
    mock.warning = MagicMock()
    mock.debug = MagicMock()
    return mock


@pytest.fixture
def tracer_mock():
    """Create a mock tracer that returns a mock span."""
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=None)
    mock_span.set_attribute = MagicMock()
    mock_span.record_exception = MagicMock()

    mock_otel_tracer = MagicMock()
    mock_otel_tracer.start_as_current_span = MagicMock(return_value=mock_span)

    mock_tracer = MagicMock()
    mock_tracer.get_tracer = MagicMock(return_value=mock_otel_tracer)
    mock_tracer.close = MagicMock()

    return mock_tracer


@pytest.fixture
def run_id():
    return uuid4()


def test_pipeline_observer_success(metrics_mock, logger_mock, run_id):
    """Test successful pipeline execution."""
    observer = PipelineObserver(
        pipeline_name="test_pipeline",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        metrics=metrics_mock,
        logger=logger_mock,
    )

    with observer:
        pass  # Successful execution

    # Verify metrics
    metrics_mock.observe_histogram.assert_called_once()
    call_args = metrics_mock.observe_histogram.call_args
    assert call_args[0][0] == "bioetl_pipeline_duration_seconds"
    assert isinstance(call_args[0][1], float)
    assert call_args[1]["labels"]["status"] == "success"
    assert call_args[1]["labels"]["pipeline"] == "test_pipeline"

    # Verify counter
    metrics_mock.increment_counter.assert_called_once()

    # Verify logs: start and finish
    assert logger_mock.info.call_count == 2


def test_pipeline_observer_failure(metrics_mock, logger_mock, run_id):
    """Test failed pipeline execution."""
    observer = PipelineObserver(
        pipeline_name="test_pipeline",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        metrics=metrics_mock,
        logger=logger_mock,
    )

    with pytest.raises(ValueError), observer:
        raise ValueError("Something went wrong")

    # Verify metrics
    metrics_mock.observe_histogram.assert_called_once()
    call_args = metrics_mock.observe_histogram.call_args
    assert call_args[1]["labels"]["status"] == "failed"

    # Verify error was logged
    logger_mock.error.assert_called_once()


def test_pipeline_observer_shutdown(metrics_mock, logger_mock, run_id):
    """Test pipeline execution with shutdown signal."""
    observer = PipelineObserver(
        pipeline_name="test_pipeline",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        metrics=metrics_mock,
        logger=logger_mock,
    )

    # PipelineShutdownError should be suppressed by the observer
    with observer:
        raise PipelineShutdownError()

    # Verify metrics show shutdown status
    metrics_mock.observe_histogram.assert_called_once()
    call_args = metrics_mock.observe_histogram.call_args
    assert call_args[1]["labels"]["status"] == "shutdown"

    # Verify warning was logged
    logger_mock.warning.assert_called_once()


# ==================== O4: New Observer Tests ====================


def test_observer_records_duration(metrics_mock, logger_mock, run_id):
    """O4: Histogram records duration with correct labels."""
    observer = PipelineObserver(
        pipeline_name="chembl_activity",
        run_id=run_id,
        run_type=RunType.REBUILD,
        metrics=metrics_mock,
        logger=logger_mock,
    )

    with observer:
        pass  # Successful execution

    # Verify histogram was called with correct metric name
    metrics_mock.observe_histogram.assert_called_once()
    call_args = metrics_mock.observe_histogram.call_args

    # Check metric name
    assert call_args[0][0] == "bioetl_pipeline_duration_seconds"

    # Check duration is a positive float
    duration = call_args[0][1]
    assert isinstance(duration, float)
    assert duration >= 0

    # Check labels contain required fields
    labels = call_args[1]["labels"]
    assert labels["pipeline"] == "chembl_activity"
    assert labels["run_type"] == "rebuild"
    assert labels["status"] == "success"


def test_observer_tracks_errors(metrics_mock, logger_mock, run_id):
    """O4: Counter increments by error_type on failure."""
    observer = PipelineObserver(
        pipeline_name="test_pipeline",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        metrics=metrics_mock,
        logger=logger_mock,
    )

    with pytest.raises(RuntimeError), observer:
        raise RuntimeError("Test error")

    # Verify counter was incremented for failed status
    metrics_mock.increment_counter.assert_called_once()
    call_args = metrics_mock.increment_counter.call_args

    assert call_args[0][0] == "bioetl_pipeline_runs_total"
    assert call_args[0][1] == 1
    assert call_args[1]["labels"]["status"] == "failed"

    # Verify error was logged with error_type
    logger_mock.error.assert_called_once()
    error_call_args = logger_mock.error.call_args
    assert "error_type" in error_call_args[1]
    assert error_call_args[1]["error_type"] == "RuntimeError"


def test_observer_graceful_shutdown(metrics_mock, logger_mock, tracer_mock, run_id):
    """O4: Spans are flushed at close()."""
    observer = PipelineObserver(
        pipeline_name="test_pipeline",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        metrics=metrics_mock,
        logger=logger_mock,
        tracer=tracer_mock,
    )

    with observer:
        pass  # Successful execution

    # Verify span was created and ended properly
    tracer_mock.get_tracer.assert_called_once_with("bioetl.pipeline")

    # Verify span __enter__ and __exit__ were called
    mock_span = tracer_mock.get_tracer.return_value.start_as_current_span.return_value
    mock_span.__enter__.assert_called_once()
    mock_span.__exit__.assert_called_once()

    # Verify span attributes were set
    mock_span.set_attribute.assert_any_call("bioetl.status", "success")


def test_observer_handles_close_error(metrics_mock, logger_mock, tracer_mock, run_id):
    """O4: Error at close() doesn't fail pipeline."""
    # Configure tracer to raise error on span exit
    mock_span = tracer_mock.get_tracer.return_value.start_as_current_span.return_value
    mock_span.__exit__ = MagicMock(side_effect=Exception("Tracer close error"))

    observer = PipelineObserver(
        pipeline_name="test_pipeline",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        metrics=metrics_mock,
        logger=logger_mock,
        tracer=tracer_mock,
    )

    # Should not raise despite tracer error
    with observer:
        pass

    # Pipeline should still record success metrics
    metrics_mock.observe_histogram.assert_called_once()
    call_args = metrics_mock.observe_histogram.call_args
    assert call_args[1]["labels"]["status"] == "success"
