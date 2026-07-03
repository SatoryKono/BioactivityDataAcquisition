"""Unit tests for BatchWriterTracingMixin.

Tests span creation, error tagging, lock validation, and error tracking
helpers extracted into BatchWriterTracingMixin.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from tests.helpers.deterministic_ids import (
    deterministic_batch_uuid_from_callsite,
    deterministic_uuid_from_callsite,
)

import pytest

from bioetl.application.core.batch_writer_tracing_mixin import BatchWriterTracingMixin
from bioetl.domain.locking import LockNotHeldError


# ---------------------------------------------------------------------------
# Concrete test double
# ---------------------------------------------------------------------------


class _TracingWriter(BatchWriterTracingMixin):
    """Minimal concrete subclass wiring required mixin attributes."""

    def __init__(
        self,
        *,
        tracer=None,
        lock_validator=None,
        provider: str = "test_prov",
        entity_type: str = "test_entity",
        error_classifier=None,
        batch_metrics=None,
        context=None,
    ) -> None:
        self._tracer = tracer
        self._lock_validator = lock_validator
        self._provider = provider
        self._entity_type = entity_type
        self._error_classifier = error_classifier or MagicMock()
        self._batch_metrics = batch_metrics or MagicMock()
        self._context = context or MagicMock()


def _make_span_mock():
    """Return a MagicMock that behaves like an OTel span context manager."""
    span = MagicMock()
    span.__enter__ = MagicMock(return_value=span)
    span.__exit__ = MagicMock(return_value=None)
    span.set_attribute = MagicMock()
    span.record_exception = MagicMock()
    return span


def _make_tracer_mock(span=None):
    """Return a complete tracer mock hierarchy."""
    if span is None:
        span = _make_span_mock()
    inner = MagicMock()
    inner.start_as_current_span = MagicMock(return_value=span)
    tracer = MagicMock()
    tracer.get_tracer = MagicMock(return_value=inner)
    return tracer, inner, span


# ---------------------------------------------------------------------------
# _validate_lock
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateLock:
    """Tests for BatchWriterTracingMixin._validate_lock."""

    async def test_no_op_when_lock_validator_is_none(self):
        """_validate_lock returns immediately when lock_validator is None."""
        writer = _TracingWriter(lock_validator=None)
        # Must not raise
        await writer._validate_lock("write_bronze")

    async def test_passes_when_lock_is_held(self):
        """_validate_lock completes without error when validator returns True."""
        validator = AsyncMock(return_value=True)
        writer = _TracingWriter(lock_validator=validator)

        await writer._validate_lock("write_silver")

        validator.assert_awaited_once()

    async def test_raises_lock_not_held_error_when_lock_lost(self):
        """LockNotHeldError raised when lock validator returns False."""
        validator = AsyncMock(return_value=False)
        mock_logger = MagicMock()
        mock_context = MagicMock()
        mock_context.logger = mock_logger
        mock_context.run_id = deterministic_uuid_from_callsite(
            "test_batch_writer_tracing_mixin"
        )

        writer = _TracingWriter(lock_validator=validator, context=mock_context)

        with pytest.raises(LockNotHeldError) as exc_info:
            await writer._validate_lock("write_gold")

        assert exc_info.value.operation == "write_gold"

    async def test_lock_lost_logs_error_with_operation_and_table(self):
        """Losing lock logs an error with operation and table context."""
        validator = AsyncMock(return_value=False)
        mock_logger = MagicMock()
        mock_context = MagicMock()
        mock_context.logger = mock_logger
        mock_context.run_id = deterministic_uuid_from_callsite(
            "test_batch_writer_tracing_mixin"
        )

        writer = _TracingWriter(
            lock_validator=validator,
            context=mock_context,
            provider="chembl",
            entity_type="activity",
        )

        with pytest.raises(LockNotHeldError):
            await writer._validate_lock("write_bronze")

        mock_logger.error.assert_called_once()
        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs["operation"] == "write_bronze"
        assert "chembl_activity" in call_kwargs["table"]

    async def test_lock_not_held_error_contains_table_name_in_key(self):
        """LockNotHeldError.expected_key contains provider_entity table name."""
        validator = AsyncMock(return_value=False)
        mock_context = MagicMock()
        mock_context.run_id = deterministic_uuid_from_callsite(
            "test_batch_writer_tracing_mixin"
        )

        writer = _TracingWriter(
            lock_validator=validator,
            context=mock_context,
            provider="pubchem",
            entity_type="compound",
        )

        with pytest.raises(LockNotHeldError) as exc_info:
            await writer._validate_lock("write_silver")

        assert "pubchem_compound" in exc_info.value.expected_key


# ---------------------------------------------------------------------------
# _start_span
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStartSpan:
    """Tests for BatchWriterTracingMixin._start_span."""

    def test_returns_none_when_no_tracer(self):
        """Returns None when _tracer is falsy."""
        writer = _TracingWriter(tracer=None)
        result = writer._start_span(
            "write_bronze",
            "bronze",
            100,
            deterministic_batch_uuid_from_callsite("test_batch_writer_tracing_mixin"),
        )

        assert result is None

    def test_creates_span_with_correct_name(self):
        """Span is created with the given operation name."""
        tracer, inner, _ = _make_tracer_mock()
        writer = _TracingWriter(tracer=tracer)

        writer._start_span("write_bronze", "bronze", 10)

        inner.start_as_current_span.assert_called_once()
        call_args = inner.start_as_current_span.call_args
        assert call_args[0][0] == "write_bronze"

    def test_span_attributes_contain_layer_and_record_count(self):
        """Span attributes include layer and record_count."""
        tracer, inner, _ = _make_tracer_mock()
        writer = _TracingWriter(
            tracer=tracer, provider="chembl", entity_type="activity"
        )

        writer._start_span("write_silver", "silver", 42)

        attrs = inner.start_as_current_span.call_args[1]["attributes"]
        assert attrs["bioetl.layer"] == "silver"
        assert attrs["bioetl.record_count"] == 42
        assert attrs["bioetl.provider"] == "chembl"
        assert attrs["bioetl.entity_type"] == "activity"

    def test_span_attributes_include_batch_id_when_provided(self):
        """batch_id attribute is set when batch_id is given."""
        tracer, inner, _ = _make_tracer_mock()
        writer = _TracingWriter(tracer=tracer)
        batch_id = deterministic_batch_uuid_from_callsite(
            "test_batch_writer_tracing_mixin"
        )

        writer._start_span("write_bronze", "bronze", 5, batch_id)

        attrs = inner.start_as_current_span.call_args[1]["attributes"]
        assert attrs["bioetl.batch_id"] == str(batch_id)

    def test_span_attributes_omit_batch_id_when_none(self):
        """batch_id attribute is absent when batch_id is None."""
        tracer, inner, _ = _make_tracer_mock()
        writer = _TracingWriter(tracer=tracer)

        writer._start_span("write_gold", "gold", 10, None)

        attrs = inner.start_as_current_span.call_args[1]["attributes"]
        assert "bioetl.batch_id" not in attrs

    def test_span_enter_is_called(self):
        """span.__enter__ is called to activate the span."""
        tracer, _, span = _make_tracer_mock()
        writer = _TracingWriter(tracer=tracer)

        writer._start_span("write_bronze", "bronze", 1)

        span.__enter__.assert_called_once()

    def test_returns_span_object(self):
        """Returns the span object (not None) when tracer is set."""
        tracer, _, span = _make_tracer_mock()
        writer = _TracingWriter(tracer=tracer)

        result = writer._start_span("write_bronze", "bronze", 1)

        assert result is span


# ---------------------------------------------------------------------------
# _end_span
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEndSpan:
    """Tests for BatchWriterTracingMixin._end_span."""

    def test_no_op_when_span_is_none(self):
        """_end_span is a no-op when span is None."""
        writer = _TracingWriter()
        # Must not raise
        writer._end_span(None)

    def test_calls_exit_without_error(self):
        """span.__exit__ is called when no error provided."""
        span = _make_span_mock()
        writer = _TracingWriter()

        writer._end_span(span)

        span.__exit__.assert_called_once_with(None, None, None)

    def test_sets_error_attribute_on_exception(self):
        """span.set_attribute("error", True) called when error is provided."""
        span = _make_span_mock()
        writer = _TracingWriter()

        error = RuntimeError("storage failure")
        writer._end_span(span, error)

        span.set_attribute.assert_called_with("error", True)

    def test_records_exception_on_error(self):
        """span.record_exception called with the error instance."""
        span = _make_span_mock()
        writer = _TracingWriter()

        error = ValueError("bad value")
        writer._end_span(span, error)

        span.record_exception.assert_called_once_with(error)

    def test_exits_span_after_recording_error(self):
        """span.__exit__ is called even after recording an error."""
        span = _make_span_mock()
        writer = _TracingWriter()

        writer._end_span(span, RuntimeError("oops"))

        span.__exit__.assert_called_once()

    def test_no_set_attribute_when_no_error(self):
        """set_attribute is NOT called when error=None."""
        span = _make_span_mock()
        writer = _TracingWriter()

        writer._end_span(span, None)

        span.set_attribute.assert_not_called()


# ---------------------------------------------------------------------------
# log_and_track_write_error
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLogAndTrackWriteError:
    """Tests for BatchWriterTracingMixin.log_and_track_write_error."""

    def test_classifies_and_logs_error(self):
        """Error is classified and logged with layer, error, and batch_id."""
        from bioetl.domain.error_classifier import ErrorClassifier

        mock_logger = MagicMock()
        mock_context = MagicMock()
        mock_context.logger = mock_logger

        mock_metrics = MagicMock()
        classifier = ErrorClassifier()

        writer = _TracingWriter(
            context=mock_context,
            error_classifier=classifier,
            batch_metrics=mock_metrics,
        )

        batch_id = deterministic_batch_uuid_from_callsite(
            "test_batch_writer_tracing_mixin"
        )
        error = ValueError("bad schema")

        writer.log_and_track_write_error("silver", error, batch_id)

        mock_logger.error.assert_called_once()
        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs["layer"] == "silver"
        assert "bad schema" in call_kwargs["error"]
        assert call_kwargs["batch_id"] == str(batch_id)

    def test_tracks_error_via_batch_metrics(self):
        """batch_metrics.track_error is called with layer and error_type."""
        from bioetl.domain.error_classifier import ErrorClassifier

        mock_context = MagicMock()
        mock_context.logger = MagicMock()

        mock_metrics = MagicMock()
        classifier = ErrorClassifier()

        writer = _TracingWriter(
            context=mock_context,
            error_classifier=classifier,
            batch_metrics=mock_metrics,
        )

        batch_id = deterministic_batch_uuid_from_callsite(
            "test_batch_writer_tracing_mixin"
        )
        writer.log_and_track_write_error("gold", OSError("disk full"), batch_id)

        mock_metrics.track_error.assert_called_once()
        call_args = mock_metrics.track_error.call_args[0]
        assert call_args[0] == "gold_write"

    def test_error_type_value_in_log(self):
        """error_type.value string is included in the log call."""
        from bioetl.domain.error_classifier import ErrorClassifier

        mock_logger = MagicMock()
        mock_context = MagicMock()
        mock_context.logger = mock_logger

        writer = _TracingWriter(
            context=mock_context,
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(),
        )

        writer.log_and_track_write_error(
            "bronze",
            RuntimeError("crash"),
            deterministic_batch_uuid_from_callsite("test_batch_writer_tracing_mixin"),
        )

        call_kwargs = mock_logger.error.call_args[1]
        # error_type value must be a non-empty string
        assert isinstance(call_kwargs["error_type"], str)
        assert len(call_kwargs["error_type"]) > 0

    def test_works_with_multiple_error_types(self):
        """log_and_track_write_error handles any supported error type without raising."""
        from bioetl.domain.error_classifier import ErrorClassifier

        mock_context = MagicMock()
        mock_context.logger = MagicMock()

        writer = _TracingWriter(
            context=mock_context,
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(),
        )

        for exc in [ValueError("v"), TypeError("t"), OSError("o"), RuntimeError("r")]:
            writer.log_and_track_write_error(
                "silver",
                exc,
                deterministic_batch_uuid_from_callsite(
                    "test_batch_writer_tracing_mixin"
                ),
            )

        # Should have been called 4 times without raising
        assert mock_context.logger.error.call_count == 4
