"""Unit tests for PipelineObserver."""

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
    return mock


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
