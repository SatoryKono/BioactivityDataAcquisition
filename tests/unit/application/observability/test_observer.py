"""Unit tests for PipelineObserver."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from bioetl.application.core.shutdown import PipelineShutdownError
from bioetl.application.observability.observer import PipelineObserver
from bioetl.domain.types import RunID, RunType


@pytest.fixture
def metrics_mock():
    return MagicMock()


@pytest.fixture
def logger_mock():
    return MagicMock()


@pytest.fixture
def run_id():
    return RunID(uuid4())


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
    args, kwargs = metrics_mock.observe_histogram.call_args
    assert args[0] == "bioetl_pipeline_duration_seconds"
    assert isinstance(args[1], float)
    expected_labels = {
        "pipeline": "test_pipeline",
        "run_type": "incremental",
        "status": "success",
    }
    assert kwargs.get("labels") == expected_labels or args[2] == expected_labels

    # Verify logs: 2 info calls - start and completion
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

    with pytest.raises(ValueError):
        with observer:
            raise ValueError("Something went wrong")

    # Verify metrics
    metrics_mock.observe_histogram.assert_called_once()
    args, kwargs = metrics_mock.observe_histogram.call_args
    labels = kwargs.get("labels") or args[2]
    assert labels["status"] == "failed"

    # On failure: 1 info call from start, 1 error call from exit
    assert logger_mock.info.call_count == 1
    # Error is logged on failure
    logger_mock.error.assert_called_once()


def test_pipeline_observer_shutdown(metrics_mock, logger_mock, run_id):
    """Test pipeline execution with shutdown."""
    observer = PipelineObserver(
        pipeline_name="test_pipeline",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        metrics=metrics_mock,
        logger=logger_mock,
    )

    # PipelineShutdownError is suppressed by observer
    with observer:
        raise PipelineShutdownError()

    # Verify metrics
    metrics_mock.observe_histogram.assert_called_once()
    args, kwargs = metrics_mock.observe_histogram.call_args
    labels = kwargs.get("labels") or args[2]
    assert labels["status"] == "shutdown"

    # Verify logs - warning is logged for shutdown
    logger_mock.warning.assert_called_once()
