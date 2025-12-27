"""Unit tests for span context manager helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.observability.span_context import (
    SpanBuilder,
    traced_operation,
    traced_sync_operation,
)


@pytest.fixture
def mock_tracer():
    """Create mock TracingPort."""
    tracer = MagicMock()
    mock_otel_tracer = MagicMock()
    mock_span = MagicMock()

    # Setup chain: tracer.get_tracer().start_as_current_span() returns span
    tracer.get_tracer.return_value = mock_otel_tracer
    mock_otel_tracer.start_as_current_span.return_value = mock_span

    # Make span work as context manager
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)

    return tracer, mock_otel_tracer, mock_span


@pytest.mark.unit
class TestTracedOperation:
    """Tests for traced_operation async context manager."""

    @pytest.mark.asyncio
    async def test_none_tracer_yields_none(self):
        """Test with None tracer yields None without error."""
        async with traced_operation(None, "test_op") as span:
            assert span is None

    @pytest.mark.asyncio
    async def test_creates_span_with_name(self, mock_tracer):
        """Test span is created with correct name."""
        tracer, mock_otel_tracer, _ = mock_tracer

        async with traced_operation(tracer, "my_operation"):
            pass

        tracer.get_tracer.assert_called_once_with("bioetl")
        mock_otel_tracer.start_as_current_span.assert_called_once()
        call_args = mock_otel_tracer.start_as_current_span.call_args
        assert call_args[0][0] == "my_operation"

    @pytest.mark.asyncio
    async def test_custom_tracer_name(self, mock_tracer):
        """Test custom tracer name is used."""
        tracer, _, _ = mock_tracer

        async with traced_operation(tracer, "op", tracer_name="custom.tracer"):
            pass

        tracer.get_tracer.assert_called_once_with("custom.tracer")

    @pytest.mark.asyncio
    async def test_attributes_prefixed_with_bioetl(self, mock_tracer):
        """Test attributes are prefixed with bioetl."""
        tracer, mock_otel_tracer, _ = mock_tracer

        async with traced_operation(tracer, "op", batch_id="123", count=10):
            pass

        call_args = mock_otel_tracer.start_as_current_span.call_args
        attrs = call_args[1]["attributes"]
        assert "bioetl.batch_id" in attrs
        assert "bioetl.count" in attrs
        assert attrs["bioetl.batch_id"] == "123"
        assert attrs["bioetl.count"] == "10"

    @pytest.mark.asyncio
    async def test_yields_span_object(self, mock_tracer):
        """Test yields actual span object."""
        tracer, _, mock_span = mock_tracer

        async with traced_operation(tracer, "op") as span:
            assert span is mock_span

    @pytest.mark.asyncio
    async def test_records_duration(self, mock_tracer):
        """Test records duration_ms attribute on exit."""
        tracer, _, mock_span = mock_tracer

        async with traced_operation(tracer, "op"):
            pass

        # Check set_attribute was called with duration
        duration_calls = [
            c
            for c in mock_span.set_attribute.call_args_list
            if c[0][0] == "bioetl.duration_ms"
        ]
        assert len(duration_calls) == 1
        assert duration_calls[0][0][1] >= 0  # Duration should be non-negative

    @pytest.mark.asyncio
    async def test_records_exception_on_error(self, mock_tracer):
        """Test exception is recorded on span when error occurs."""
        tracer, _, mock_span = mock_tracer

        with pytest.raises(ValueError):
            async with traced_operation(tracer, "op"):
                raise ValueError("test error")

        mock_span.set_attribute.assert_any_call("error", True)
        mock_span.set_attribute.assert_any_call("error.type", "ValueError")
        mock_span.set_attribute.assert_any_call("error.message", "test error")
        mock_span.record_exception.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_propagates(self, mock_tracer):
        """Test exception is re-raised after recording."""
        tracer, _, _ = mock_tracer

        with pytest.raises(RuntimeError, match="original error"):
            async with traced_operation(tracer, "op"):
                raise RuntimeError("original error")


@pytest.mark.unit
class TestTracedSyncOperation:
    """Tests for traced_sync_operation sync context manager."""

    def test_none_tracer_yields_none(self):
        """Test with None tracer yields None without error."""
        with traced_sync_operation(None, "test_op") as span:
            assert span is None

    def test_creates_span_with_name(self, mock_tracer):
        """Test span is created with correct name."""
        tracer, mock_otel_tracer, _ = mock_tracer

        with traced_sync_operation(tracer, "sync_operation"):
            pass

        tracer.get_tracer.assert_called_once_with("bioetl")
        call_args = mock_otel_tracer.start_as_current_span.call_args
        assert call_args[0][0] == "sync_operation"

    def test_records_exception_on_error(self, mock_tracer):
        """Test exception is recorded on span when error occurs."""
        tracer, _, mock_span = mock_tracer

        with pytest.raises(ValueError):
            with traced_sync_operation(tracer, "op"):
                raise ValueError("sync error")

        mock_span.set_attribute.assert_any_call("error", True)
        mock_span.record_exception.assert_called_once()


@pytest.mark.unit
class TestSpanBuilder:
    """Tests for SpanBuilder class."""

    def test_with_attrs_returns_new_builder(self, mock_tracer):
        """Test with_attrs returns a new builder with combined attrs."""
        tracer, _, _ = mock_tracer
        builder = SpanBuilder(tracer)

        builder2 = builder.with_attrs(pipeline="chembl")

        # Should be different instances
        assert builder is not builder2
        # Original should not have the attrs
        assert builder._base_attrs == {}
        assert builder2._base_attrs == {"pipeline": "chembl"}

    def test_with_attrs_accumulates(self, mock_tracer):
        """Test with_attrs can be chained."""
        tracer, _, _ = mock_tracer

        builder = (
            SpanBuilder(tracer)
            .with_attrs(pipeline="chembl")
            .with_attrs(run_id="123", entity="activity")
        )

        assert builder._base_attrs == {
            "pipeline": "chembl",
            "run_id": "123",
            "entity": "activity",
        }

    @pytest.mark.asyncio
    async def test_span_includes_base_attrs(self, mock_tracer):
        """Test span() includes base attributes."""
        tracer, mock_otel_tracer, _ = mock_tracer

        builder = SpanBuilder(tracer).with_attrs(pipeline="chembl")

        async with builder.span("fetch_batch"):
            pass

        call_args = mock_otel_tracer.start_as_current_span.call_args
        attrs = call_args[1]["attributes"]
        assert "bioetl.pipeline" in attrs

    @pytest.mark.asyncio
    async def test_span_includes_extra_attrs(self, mock_tracer):
        """Test span() merges extra attributes."""
        tracer, mock_otel_tracer, _ = mock_tracer

        builder = SpanBuilder(tracer).with_attrs(pipeline="chembl")

        async with builder.span("fetch_batch", batch_id="456"):
            pass

        call_args = mock_otel_tracer.start_as_current_span.call_args
        attrs = call_args[1]["attributes"]
        assert "bioetl.pipeline" in attrs
        assert "bioetl.batch_id" in attrs

    def test_sync_span_works(self, mock_tracer):
        """Test sync_span() works correctly."""
        tracer, mock_otel_tracer, _ = mock_tracer

        builder = SpanBuilder(tracer).with_attrs(pipeline="pubchem")

        with builder.sync_span("validate"):
            pass

        call_args = mock_otel_tracer.start_as_current_span.call_args
        assert call_args[0][0] == "validate"
        attrs = call_args[1]["attributes"]
        assert "bioetl.pipeline" in attrs

    def test_none_tracer_works(self):
        """Test builder works with None tracer (no-op)."""
        builder = SpanBuilder(None).with_attrs(pipeline="test")

        with builder.sync_span("op") as span:
            assert span is None

    @pytest.mark.asyncio
    async def test_none_tracer_async_works(self):
        """Test builder async span works with None tracer."""
        builder = SpanBuilder(None).with_attrs(pipeline="test")

        async with builder.span("op") as span:
            assert span is None
