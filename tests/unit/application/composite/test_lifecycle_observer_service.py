"""Focused tests for composite lifecycle publication service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.domain.events import PipelineEvent


class _FakeSpanHandle:
    def __init__(self, name: str, attributes: dict[str, object]) -> None:
        self.name = name
        self.entered = 0
        self.exited = 0
        self.attributes = dict(attributes)
        self.recorded_exceptions: list[Exception] = []

    def __enter__(self) -> object:
        self.entered += 1
        return object()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        self.exited += 1
        return None

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def record_exception(self, exception: Exception) -> None:
        self.recorded_exceptions.append(exception)


class _FakeOtelTracer:
    def __init__(self) -> None:
        self.started_spans: list[_FakeSpanHandle] = []

    def start_as_current_span(
        self,
        name: str,
        *,
        attributes: dict[str, object] | None = None,
    ) -> _FakeSpanHandle:
        span = _FakeSpanHandle(name, attributes or {})
        self.started_spans.append(span)
        return span


class _FakeTracingPort:
    is_noop = False

    def __init__(self) -> None:
        self.tracer = _FakeOtelTracer()
        self.flush_calls = 0

    def get_tracer(self, name: str) -> _FakeOtelTracer:
        assert name == "bioetl.pipeline"
        return self.tracer

    def close(self) -> None:
        return None

    def flush(self) -> None:
        self.flush_calls += 1


@pytest.mark.unit
def test_emit_phase_started_preserves_correlation_details() -> None:
    logger = MagicMock()
    observer = CompositeLifecycleObserverService(logger=logger)

    observer.emit_phase_started(
        composite_name="test_composite",
        run_id="run-123",
        phase_name="preflight_validation",
        details={
            "composite": "test_composite",
            "run_id": "run-123",
            "composite_run_id": "run-123",
            "field_count": 3,
        },
    )

    logger.info.assert_called_once()
    event_name = logger.info.call_args.args[0]
    log_kwargs = logger.info.call_args.kwargs
    assert event_name == PipelineEvent.phase_started("preflight_validation")
    assert log_kwargs["composite"] == "test_composite"
    assert log_kwargs["run_id"] == "run-123"
    assert log_kwargs["composite_run_id"] == "run-123"
    assert log_kwargs["field_count"] == 3
    assert log_kwargs["pipeline"] == "composite:test_composite"
    assert log_kwargs["provider"] == "composite"
    assert log_kwargs["run_type"] == "composite"
    assert log_kwargs["phase"] == "preflight_validation"
    assert log_kwargs["entity"] == "test_composite"
    assert "event" not in log_kwargs


@pytest.mark.unit
def test_emit_run_completed_marks_warning_status_when_present() -> None:
    logger = MagicMock()
    observer = CompositeLifecycleObserverService(logger=logger)

    observer.emit_run_completed(
        composite_name="test_composite",
        run_id="run-123",
        duration_seconds=12.5,
        had_warnings=True,
    )

    logger.info.assert_called_once()
    event_name = logger.info.call_args.args[0]
    log_kwargs = logger.info.call_args.kwargs
    assert event_name == PipelineEvent.COMPLETE
    assert log_kwargs["composite"] == "test_composite"
    assert log_kwargs["run_id"] == "run-123"
    assert log_kwargs["duration_seconds"] == pytest.approx(12.5)
    assert log_kwargs["status"] == "completed_with_warnings"
    assert log_kwargs["had_warnings"] is True
    assert log_kwargs["phase"] == "cleanup"
    assert log_kwargs["pipeline"] == "composite:test_composite"
    assert log_kwargs["provider"] == "composite"
    assert log_kwargs["run_type"] == "composite"


@pytest.mark.unit
def test_composite_lifecycle_tracing_records_run_and_phase_spans() -> None:
    logger = MagicMock()
    metrics = MagicMock()
    tracer = _FakeTracingPort()
    observer = CompositeLifecycleObserverService(
        logger=logger,
        metrics=metrics,
        tracer=tracer,
    )

    observer.emit_run_started(
        composite_name="test_composite",
        run_id="run-123",
    )
    observer.emit_phase_started(
        composite_name="test_composite",
        run_id="run-123",
        phase_name="merge",
    )
    observer.emit_phase_completed(
        composite_name="test_composite",
        run_id="run-123",
        phase_name="merge",
    )
    observer.emit_run_completed(
        composite_name="test_composite",
        run_id="run-123",
        duration_seconds=12.5,
        had_warnings=False,
    )

    traced_calls = [
        call
        for call in metrics.increment_counter.call_args_list
        if call.args and call.args[0] == "bioetl_traced_runs_total"
    ]
    assert len(traced_calls) == 1
    assert traced_calls[0].kwargs["labels"] == {
        "pipeline": "composite:test_composite",
        "run_type": "composite",
    }
    assert [span.name for span in tracer.tracer.started_spans] == [
        "pipeline.composite:test_composite",
        "pipeline.composite:test_composite.merge",
    ]
    run_span, phase_span = tracer.tracer.started_spans
    assert run_span.exited == 1
    assert phase_span.exited == 1
    assert run_span.attributes["bioetl.status"] == "success"
    assert phase_span.attributes["bioetl.status"] == "success"
    assert tracer.flush_calls == 1


@pytest.mark.unit
def test_composite_lifecycle_tracing_records_exceptions_on_failed_run() -> None:
    logger = MagicMock()
    tracer = _FakeTracingPort()
    observer = CompositeLifecycleObserverService(
        logger=logger,
        tracer=tracer,
    )

    observer.emit_run_started(
        composite_name="test_composite",
        run_id="run-123",
    )
    observer.emit_phase_started(
        composite_name="test_composite",
        run_id="run-123",
        phase_name="merge",
    )
    error = RuntimeError("boom")
    observer.emit_run_failed(
        composite_name="test_composite",
        run_id="run-123",
        error=error,
        reason_code="composite_failed",
        stage="merge",
    )

    run_span, phase_span = tracer.tracer.started_spans
    assert run_span.exited == 1
    assert phase_span.exited == 1
    assert run_span.recorded_exceptions == [error]
    assert phase_span.recorded_exceptions == [error]
    assert run_span.attributes["bioetl.status"] == "failed"
    assert phase_span.attributes["bioetl.status"] == "failed"
    assert tracer.flush_calls == 1


@pytest.mark.unit
def test_emit_run_shutdown_emits_shutdown_event() -> None:
    """Test emit_run_shutdown emits shutdown event with proper context."""
    logger = MagicMock()
    observer = CompositeLifecycleObserverService(logger=logger)

    error = KeyboardInterrupt("User interrupted")
    observer.emit_run_shutdown(
        composite_name="test_composite",
        run_id="run-123",
        error=error,
        reason="User requested shutdown",
        reason_code="user_interrupted",
    )

    logger.warning.assert_called_once()
    call_args = logger.warning.call_args
    assert call_args.args[0] == PipelineEvent.SHUTDOWN
    assert call_args.kwargs["composite"] == "test_composite"
    assert call_args.kwargs["run_id"] == "run-123"
    assert call_args.kwargs["error"] == "User interrupted"
    assert call_args.kwargs["error_type"] == "KeyboardInterrupt"
    assert call_args.kwargs["reason"] == "User requested shutdown"
    assert call_args.kwargs["reason_code"] == "user_interrupted"
    assert call_args.kwargs["phase"] == "cleanup"


@pytest.mark.unit
def test_emit_phase_completed_with_duration() -> None:
    """Test emit_phase_completed records duration when start_time exists."""
    logger = MagicMock()
    observer = CompositeLifecycleObserverService(logger=logger)

    observer.emit_phase_started(
        composite_name="test_composite",
        run_id="run-123",
        phase_name="merge",
    )
    observer.emit_phase_completed(
        composite_name="test_composite",
        run_id="run-123",
        phase_name="merge",
    )

    logger.info.assert_called_once()
    call_args = logger.info.call_args
    assert "duration_seconds" in call_args.kwargs
    assert call_args.kwargs["duration_seconds"] > 0


@pytest.mark.unit
def test_emit_phase_completed_without_start_time() -> None:
    """Test emit_phase_completed handles missing start_time gracefully."""
    logger = MagicMock()
    observer = CompositeLifecycleObserverService(logger=logger)

    observer.emit_phase_completed(
        composite_name="test_composite",
        run_id="run-123",
        phase_name="merge",
    )

    logger.info.assert_called_once()
    call_args = logger.info.call_args
    assert call_args.kwargs["status"] == "success"
    # duration_seconds should not be present if start_time is None
    assert "duration_seconds" not in call_args.kwargs
