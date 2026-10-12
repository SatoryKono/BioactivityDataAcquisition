# pyright: reportArgumentType=false

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.core.batch_checkpoint_save_observability import (
    close_checkpoint_save_span,
    emit_checkpoint_save_event,
    observe_checkpoint_save_duration,
    start_checkpoint_save_span,
)

pytestmark = pytest.mark.unit


def test_emit_checkpoint_save_event():
    metrics = MagicMock()
    emit_checkpoint_save_event(
        metrics,
        "pipeline1",
        operation="save",
        status="success",
    )
    metrics.increment_counter.assert_called_once_with(
        "bioetl_checkpoint_save_events_total",
        1,
        {
            "pipeline": "pipeline1",
            "operation": "save",
            "status": "success",
        },
    )

def test_emit_checkpoint_save_event_none():
    emit_checkpoint_save_event(None, "pipeline1", operation="save", status="success")
    assert True


def test_observe_checkpoint_save_duration():
    metrics = MagicMock()
    observe_checkpoint_save_duration(
        metrics,
        "pipeline1",
        operation="save",
        status="success",
        duration_seconds=1.5,
    )
    metrics.observe_histogram.assert_called_once_with(
        "bioetl_checkpoint_save_duration_seconds",
        1.5,
        {
            "pipeline": "pipeline1",
            "operation": "save",
            "status": "success",
        },
    )

def test_observe_checkpoint_save_duration_none():
    observe_checkpoint_save_duration(None, "pipeline1", operation="save", status="success", duration_seconds=1.5)
    assert True


def test_start_checkpoint_save_span():
    tracer = MagicMock()
    span = MagicMock()
    tracer.get_tracer.return_value.start_as_current_span.return_value = span

    result = start_checkpoint_save_span(
        tracer,
        "pipeline1",
        operation="save",
        records_processed=10,
    )
    assert result == span
    span.__enter__.assert_called_once()
    tracer.get_tracer.assert_called_once_with("bioetl.checkpoint")
    tracer.get_tracer.return_value.start_as_current_span.assert_called_once_with(
        "checkpoint_save",
        attributes={
            "bioetl.pipeline": "pipeline1",
            "bioetl.checkpoint.operation": "save",
            "bioetl.checkpoint.scope": "ordinary",
            "bioetl.checkpoint.records_processed": 10,
        },
    )

def test_start_checkpoint_save_span_none():
    assert start_checkpoint_save_span(None, "pipeline1", operation="save", records_processed=10) is None


def test_close_checkpoint_save_span():
    span = MagicMock()
    close_checkpoint_save_span(span, status="success")
    span.set_attribute.assert_called_once_with("bioetl.checkpoint.status", "success")
    span.__exit__.assert_called_once_with(None, None, None)

def test_close_checkpoint_save_span_error():
    span = MagicMock()
    error = ValueError("error")
    close_checkpoint_save_span(span, status="failure", error=error)
    span.set_attribute.assert_any_call("bioetl.checkpoint.status", "failure")
    span.set_attribute.assert_any_call("error", True)
    span.set_attribute.assert_any_call("error.type", "ValueError")
    span.record_exception.assert_called_once_with(error)
    span.__exit__.assert_called_once_with(None, None, None)

def test_close_checkpoint_save_span_none():
    close_checkpoint_save_span(None, status="success")
    assert True
