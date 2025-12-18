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

    # Verify logs
    logger_mock.info.assert_called_once()
    assert logger_mock.info.call_args[0][0] == "Pipeline completed successfully"


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

    # Logger warning/error is handled by the caller or inside the loop,
    # but observer might log if we added that logic.
    # Current implementation doesn't log on generic failure in __exit__
    # because it expects the exception to bubble up.
    # We can check that SUCCESS log was NOT called.
    logger_mock.info.assert_not_called()


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
