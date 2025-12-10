"""Unit tests for HookNotifier component."""

from unittest.mock import MagicMock

import pytest

from bioetl.application.pipelines.hook_notifier import HookNotifier
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, StageResult
from bioetl.domain.pipelines.contracts import PipelineHookABC


def _build_context() -> RunContext:
    return RunContext(entity_name="test", provider="chembl")


@pytest.mark.unit
def test_hook_notifier_registers_single_hook(mock_logger):
    """Test registering a single hook."""
    notifier = HookNotifier(logger=mock_logger)
    hook = MagicMock(spec=PipelineHookABC)

    notifier.register_hook(hook)

    assert hook in notifier.get_hooks()
    assert len(notifier.get_hooks()) == 1


@pytest.mark.unit
def test_hook_notifier_registers_multiple_hooks(mock_logger):
    """Test registering multiple hooks at once."""
    notifier = HookNotifier(logger=mock_logger)
    hook1 = MagicMock(spec=PipelineHookABC)
    hook2 = MagicMock(spec=PipelineHookABC)

    notifier.register_hooks([hook1, hook2])

    hooks = notifier.get_hooks()
    assert len(hooks) == 2
    assert hook1 in hooks
    assert hook2 in hooks


@pytest.mark.unit
def test_hook_notifier_initializes_with_hooks(mock_logger):
    """Test that hooks can be passed at init time."""
    hook = MagicMock(spec=PipelineHookABC)

    notifier = HookNotifier(logger=mock_logger, hooks=[hook])

    assert hook in notifier.get_hooks()


@pytest.mark.unit
def test_hook_notifier_notifies_stage_start(mock_logger):
    """Test that on_stage_start is called on all hooks."""
    hook1 = MagicMock(spec=PipelineHookABC)
    hook2 = MagicMock(spec=PipelineHookABC)
    notifier = HookNotifier(logger=mock_logger, hooks=[hook1, hook2])
    context = _build_context()

    notifier.notify_stage_start(
        "extract", context, provider="chembl", entity_name="test"
    )

    hook1.on_stage_start.assert_called_once_with("extract", context)
    hook2.on_stage_start.assert_called_once_with("extract", context)


@pytest.mark.unit
def test_hook_notifier_notifies_stage_end(mock_logger):
    """Test that on_stage_end is called on all hooks."""
    hook = MagicMock(spec=PipelineHookABC)
    notifier = HookNotifier(logger=mock_logger, hooks=[hook])
    result = StageResult(
        stage_name="extract",
        success=True,
        records_processed=100,
        chunks_processed=2,
        duration_sec=1.5,
        errors=[],
    )

    notifier.notify_stage_end("extract", result, provider="chembl", entity_name="test")

    hook.on_stage_end.assert_called_once_with("extract", result)


@pytest.mark.unit
def test_hook_notifier_notifies_stage_error(mock_logger):
    """Test that on_error is called on all hooks."""
    hook = MagicMock(spec=PipelineHookABC)
    notifier = HookNotifier(logger=mock_logger, hooks=[hook])
    error = PipelineStageError(
        provider="chembl",
        entity="test",
        stage="extract",
        attempt=1,
        run_id="run-123",
        cause=ValueError("test error"),
    )

    notifier.notify_stage_error("extract", error)

    hook.on_error.assert_called_once_with("extract", error)


@pytest.mark.unit
def test_hook_notifier_records_stage_start_time(mock_logger):
    """Test that stage start times are recorded."""
    notifier = HookNotifier(logger=mock_logger)
    context = _build_context()

    assert notifier.get_stage_start("extract") is None

    notifier.notify_stage_start(
        "extract", context, provider="chembl", entity_name="test"
    )

    assert notifier.get_stage_start("extract") is not None


@pytest.mark.unit
def test_hook_notifier_tracks_current_run_id(mock_logger):
    """Test that current run_id is tracked."""
    notifier = HookNotifier(logger=mock_logger)
    context = _build_context()

    assert notifier.current_run_id is None

    notifier.notify_stage_start(
        "extract", context, provider="chembl", entity_name="test"
    )

    assert notifier.current_run_id == context.run_id.value


@pytest.mark.unit
def test_hook_notifier_reset_clears_state(mock_logger):
    """Test that reset clears all accumulated state."""
    notifier = HookNotifier(logger=mock_logger)
    context = _build_context()

    notifier.notify_stage_start(
        "extract", context, provider="chembl", entity_name="test"
    )
    assert notifier.get_stage_start("extract") is not None
    assert notifier.current_run_id is not None

    notifier.reset()

    assert notifier.get_stage_start("extract") is None
    assert notifier.current_run_id is None


@pytest.mark.unit
def test_hook_notifier_logs_stage_events(mock_logger):
    """Test that stage events are logged."""
    notifier = HookNotifier(logger=mock_logger, pipeline_id="test-pipeline")
    context = _build_context()
    result = StageResult(
        stage_name="extract",
        success=True,
        records_processed=100,
        chunks_processed=2,
        duration_sec=1.5,
        errors=[],
    )

    notifier.notify_stage_start(
        "extract", context, provider="chembl", entity_name="test"
    )
    notifier.notify_stage_end("extract", result, provider="chembl", entity_name="test")

    assert mock_logger.info.call_count == 2
