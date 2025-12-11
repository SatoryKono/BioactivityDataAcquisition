"""Unit tests for StageErrorHandler component."""

import pytest

from bioetl.application.factories.hooks_impl import (
    ContinueOnErrorPolicyImpl,
    FailFastErrorPolicyImpl,
)
from bioetl.application.pipelines.stage_error_handler import StageErrorHandler
from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext


def _build_context() -> RunContext:
    return RunContext(entity_name="test", provider="chembl")


@pytest.mark.unit
def test_error_handler_tracks_last_error(mock_logger):
    """Test that last error is tracked."""
    handler = StageErrorHandler(
        logger=mock_logger,
        provider="chembl",
        entity_name="test",
        error_policy=FailFastErrorPolicyImpl(),
        default_on_skip=lambda _: None,
    )
    context = _build_context()

    assert handler.last_error is None

    handler.handle_error("extract", ValueError("test"), context, attempt=1)

    assert handler.last_error is not None
    assert isinstance(handler.last_error, PipelineStageError)


@pytest.mark.unit
def test_error_handler_returns_fail_action(mock_logger):
    """Test that FailFast policy returns FAIL action."""
    handler = StageErrorHandler(
        logger=mock_logger,
        provider="chembl",
        entity_name="test",
        error_policy=FailFastErrorPolicyImpl(),
        default_on_skip=lambda _: None,
    )
    context = _build_context()

    action, error = handler.handle_error(
        "extract", ValueError("test"), context, attempt=1
    )

    assert action == ErrorAction.FAIL
    assert isinstance(error, PipelineStageError)


@pytest.mark.unit
def test_error_handler_returns_retry_action(mock_logger):
    """Test that ContinueOnError policy can return RETRY action."""
    handler = StageErrorHandler(
        logger=mock_logger,
        provider="chembl",
        entity_name="test",
        error_policy=ContinueOnErrorPolicyImpl(max_retries=2),
        default_on_skip=lambda _: None,
    )
    context = _build_context()

    action, _ = handler.handle_error("extract", ValueError("test"), context, attempt=1)

    assert action == ErrorAction.RETRY


@pytest.mark.unit
def test_error_handler_returns_skip_after_retries(mock_logger):
    """Test that SKIP is returned after max retries."""
    handler = StageErrorHandler(
        logger=mock_logger,
        provider="chembl",
        entity_name="test",
        error_policy=ContinueOnErrorPolicyImpl(max_retries=1),
        default_on_skip=lambda _: None,
    )
    context = _build_context()

    action, _ = handler.handle_error("extract", ValueError("test"), context, attempt=2)

    assert action == ErrorAction.SKIP


@pytest.mark.unit
def test_error_handler_should_retry(mock_logger):
    """Test should_retry method."""
    handler = StageErrorHandler(
        logger=mock_logger,
        provider="chembl",
        entity_name="test",
        error_policy=ContinueOnErrorPolicyImpl(max_retries=2),
        default_on_skip=lambda _: None,
    )

    error_attempt_1 = PipelineStageError(
        provider="chembl",
        entity="test",
        stage="extract",
        attempt=1,
        run_id="run-123",
    )
    error_attempt_3 = PipelineStageError(
        provider="chembl",
        entity="test",
        stage="extract",
        attempt=3,
        run_id="run-123",
    )

    assert handler.should_retry(error_attempt_1) is True
    assert handler.should_retry(error_attempt_3) is False


@pytest.mark.unit
def test_error_handler_logs_error(mock_logger):
    """Test that errors are logged."""
    handler = StageErrorHandler(
        logger=mock_logger,
        provider="chembl",
        entity_name="test",
        error_policy=FailFastErrorPolicyImpl(),
        default_on_skip=lambda _: None,
    )
    context = _build_context()

    handler.handle_error("extract", ValueError("test error"), context, attempt=1)

    mock_logger.error.assert_called_once()


@pytest.mark.unit
def test_error_handler_logs_skip(mock_logger):
    """Test that skips are logged as warnings."""
    handler = StageErrorHandler(
        logger=mock_logger,
        provider="chembl",
        entity_name="test",
        error_policy=ContinueOnErrorPolicyImpl(),
        default_on_skip=lambda _: None,
    )
    context = _build_context()

    handler.log_skip("extract", context, ValueError("test"))

    mock_logger.warning.assert_called_once()


@pytest.mark.unit
def test_error_handler_get_skip_value(mock_logger):
    """Test getting skip value for different stages."""
    handler = StageErrorHandler(
        logger=mock_logger,
        provider="chembl",
        entity_name="test",
        error_policy=FailFastErrorPolicyImpl(),
        default_on_skip=lambda stage: f"skipped-{stage}",
    )

    assert handler.get_skip_value("extract") == "skipped-extract"
    assert handler.get_skip_value("transform") == "skipped-transform"


@pytest.mark.unit
def test_error_handler_clears_error(mock_logger):
    """Test clearing error state."""
    handler = StageErrorHandler(
        logger=mock_logger,
        provider="chembl",
        entity_name="test",
        error_policy=FailFastErrorPolicyImpl(),
        default_on_skip=lambda _: None,
    )
    context = _build_context()

    handler.handle_error("extract", ValueError("test"), context, attempt=1)
    assert handler.last_error is not None

    handler.clear_error()

    assert handler.last_error is None


@pytest.mark.unit
def test_error_handler_tracks_last_action(mock_logger):
    """Test tracking last action per stage."""
    handler = StageErrorHandler(
        logger=mock_logger,
        provider="chembl",
        entity_name="test",
        error_policy=ContinueOnErrorPolicyImpl(),
        default_on_skip=lambda _: None,
    )
    context = _build_context()

    assert handler.get_last_action("extract") is None

    handler.handle_error("extract", ValueError("test"), context, attempt=1)

    assert handler.get_last_action("extract") == ErrorAction.SKIP


@pytest.mark.unit
def test_error_handler_get_last_error_messages(mock_logger):
    """Test getting error messages."""
    handler = StageErrorHandler(
        logger=mock_logger,
        provider="chembl",
        entity_name="test",
        error_policy=FailFastErrorPolicyImpl(),
        default_on_skip=lambda _: None,
    )
    context = _build_context()

    assert handler.get_last_error_messages() == []

    handler.handle_error("extract", ValueError("test error"), context, attempt=1)
    messages = handler.get_last_error_messages()

    assert len(messages) == 2
    assert "test error" in messages[-1]


@pytest.mark.unit
def test_error_handler_reset_clears_state(mock_logger):
    """Test that reset clears all state."""
    handler = StageErrorHandler(
        logger=mock_logger,
        provider="chembl",
        entity_name="test",
        error_policy=ContinueOnErrorPolicyImpl(),
        default_on_skip=lambda _: None,
    )
    context = _build_context()

    handler.handle_error("extract", ValueError("test"), context, attempt=1)
    assert handler.last_error is not None
    assert handler.get_last_action("extract") is not None

    handler.reset()

    assert handler.last_error is None
    assert handler.get_last_action("extract") is None


@pytest.mark.unit
def test_error_handler_set_error_policy(mock_logger):
    """Test changing error policy at runtime."""
    handler = StageErrorHandler(
        logger=mock_logger,
        provider="chembl",
        entity_name="test",
        error_policy=FailFastErrorPolicyImpl(),
        default_on_skip=lambda _: None,
    )
    context = _build_context()

    action, _ = handler.handle_error("extract", ValueError("test"), context, attempt=1)
    assert action == ErrorAction.FAIL

    handler.set_error_policy(ContinueOnErrorPolicyImpl())

    action, _ = handler.handle_error(
        "transform", ValueError("test"), context, attempt=1
    )
    assert action == ErrorAction.SKIP


@pytest.mark.unit
def test_error_handler_creates_pipeline_error_with_cause(mock_logger):
    """Test that PipelineStageError includes the original cause."""
    handler = StageErrorHandler(
        logger=mock_logger,
        provider="chembl",
        entity_name="test",
        error_policy=FailFastErrorPolicyImpl(),
        default_on_skip=lambda _: None,
    )
    context = _build_context()
    original_error = ValueError("original error")

    _, pipeline_error = handler.handle_error(
        "extract", original_error, context, attempt=2
    )

    assert pipeline_error.provider == "chembl"
    assert pipeline_error.entity == "test"
    assert pipeline_error.stage == "extract"
    assert pipeline_error.attempt == 2
    # Ensure run_id matches what's in the context
    assert str(pipeline_error.run_id) == str(context.run_id)
    assert pipeline_error.cause is original_error
