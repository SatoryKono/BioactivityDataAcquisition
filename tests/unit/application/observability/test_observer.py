"""Unit tests for PipelineObserver."""

from unittest.mock import MagicMock

import pytest
from bioetl.application.core.shutdown import PipelineShutdownError
from bioetl.application.observability.observer import PipelineObserver


@pytest.fixture
def metrics_mock():
    return MagicMock()


@pytest.fixture
def logger_mock():
    return MagicMock()


def test_pipeline_observer_success(metrics_mock, logger_mock):
    """Test successful pipeline execution."""
    observer = PipelineObserver(
        metrics=metrics_mock,
        logger=logger_mock,
        pipeline_name="test_pipeline",
        run_type="incremental",
        tags={"custom": "tag"},
    )

    with observer:
        pass  # Successful execution

    # Verify metrics
    metrics_mock.observe_histogram.assert_called_once()
    args, _ = metrics_mock.observe_histogram.call_args
    assert args[0] == "pipeline_duration_seconds"
    assert isinstance(args[1], float)
    assert args[2] == {
        "pipeline_name": "test_pipeline",
        "run_type": "incremental",
        "status": "success",
        "custom": "tag",
    }

    # Verify logs: 2 info calls - start and completion
    assert logger_mock.info.call_count == 2
    # First call is "Starting pipeline: ..."
    assert "Starting pipeline" in logger_mock.info.call_args_list[0][0][0]
    # Second call is "Pipeline completed successfully"
    assert logger_mock.info.call_args_list[1][0][0] == "Pipeline completed successfully"


def test_pipeline_observer_failure(metrics_mock, logger_mock):
    """Test failed pipeline execution."""
    observer = PipelineObserver(
        metrics=metrics_mock,
        logger=logger_mock,
        pipeline_name="test_pipeline",
        run_type="incremental",
    )

    with pytest.raises(ValueError):
        with observer:
            raise ValueError("Something went wrong")

    # Verify metrics
    metrics_mock.observe_histogram.assert_called_once()
    args, _ = metrics_mock.observe_histogram.call_args
    assert args[2]["status"] == "failure"

    # On failure: 1 info call from start, 1 error call from exit
    # The "Starting pipeline" info is called, but not "Pipeline completed successfully"
    assert logger_mock.info.call_count == 1
    assert "Starting pipeline" in logger_mock.info.call_args[0][0]
    # Error is logged on failure
    logger_mock.error.assert_called_once()
    assert "Pipeline failed" in logger_mock.error.call_args[0][0]


def test_pipeline_observer_shutdown(metrics_mock, logger_mock):
    """Test pipeline execution with shutdown."""
    observer = PipelineObserver(
        metrics=metrics_mock,
        logger=logger_mock,
        pipeline_name="test_pipeline",
        run_type="incremental",
    )

    # Simulation of Runner handling shutdown
    try:
        with observer:
            raise PipelineShutdownError()
    except PipelineShutdownError:
        # Runner catches and swallows
        observer.set_status("shutdown")

    # Verify metrics
    metrics_mock.observe_histogram.assert_called_once()
    args, _ = metrics_mock.observe_histogram.call_args
    assert args[2]["status"] == "shutdown"

    # Verify logs
    logger_mock.warning.assert_called_once()
    assert logger_mock.warning.call_args[0][0] == "Pipeline shutdown"
