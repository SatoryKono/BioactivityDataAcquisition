"""Tests for span helper utilities."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from bioetl.application.observability.span_helpers import (
    traced_async_operation,
    traced_operation,
)


@pytest.fixture
def mock_tracer():
    """Create mock tracer with span tracking."""
    span = MagicMock()
    span.__enter__ = MagicMock(return_value=span)
    span.__exit__ = MagicMock(return_value=None)
    span.set_attribute = MagicMock()
    span.record_exception = MagicMock()

    otel_tracer = MagicMock()
    otel_tracer.start_as_current_span = MagicMock(return_value=span)

    tracer = MagicMock()
    tracer.get_tracer = MagicMock(return_value=otel_tracer)
    tracer.flush = MagicMock()

    return tracer, otel_tracer, span


@pytest.mark.unit
class TestTracedOperation:
    """Tests for synchronous traced_operation context manager."""

    def test_creates_span_with_name_and_attributes(self, mock_tracer):
        """Test span is created with correct name and attributes."""
        tracer, otel_tracer, span = mock_tracer

        with traced_operation(tracer, "test_op", {"key": "value"}) as active_span:
            assert active_span is span

        tracer.get_tracer.assert_called_once_with("bioetl")
        otel_tracer.start_as_current_span.assert_called_once_with(
            "test_op", attributes={"key": "value"}
        )

    def test_span_enter_and_exit_called(self, mock_tracer):
        """Test span __enter__ and __exit__ are called."""
        tracer, _, span = mock_tracer

        with traced_operation(tracer, "test_op") as active_span:
            assert active_span is span

        span.__enter__.assert_called_once()
        span.__exit__.assert_called_once_with(None, None, None)
        tracer.flush.assert_called_once()

    def test_span_closed_on_exception(self, mock_tracer):
        """Test span is closed even when exception occurs."""
        tracer, _, span = mock_tracer

        with pytest.raises(ValueError):
            with traced_operation(tracer, "test_op"):
                raise ValueError("test error")

        span.__exit__.assert_called_once_with(None, None, None)

    def test_exception_recorded_on_span(self, mock_tracer):
        """Test exception is recorded on span."""
        tracer, _, span = mock_tracer

        with pytest.raises(ValueError):
            with traced_operation(tracer, "test_op"):
                raise ValueError("test error")

        span.set_attribute.assert_any_call("error", True)
        span.set_attribute.assert_any_call("error.type", "ValueError")
        span.record_exception.assert_called_once()

    def test_can_set_attributes_inside_context(self, mock_tracer):
        """Test attributes can be set inside context."""
        tracer, _, span = mock_tracer

        with traced_operation(tracer, "test_op") as s:
            s.set_attribute("result", "success")

        span.set_attribute.assert_called_with("result", "success")

    def test_custom_tracer_name(self, mock_tracer):
        """Test custom tracer name is used."""
        tracer, _, span = mock_tracer

        with traced_operation(
            tracer, "test_op", tracer_name="custom.tracer"
        ) as active_span:
            assert active_span is span

        tracer.get_tracer.assert_called_once_with("custom.tracer")

    def test_empty_attributes_default(self, mock_tracer):
        """Test empty dict used when no attributes provided."""
        tracer, otel_tracer, span = mock_tracer

        with traced_operation(tracer, "test_op") as active_span:
            assert active_span is span

        otel_tracer.start_as_current_span.assert_called_once_with(
            "test_op", attributes={}
        )


@pytest.mark.unit
class TestTracedAsyncOperation:
    """Tests for async traced_async_operation context manager."""

    @pytest.mark.asyncio
    async def test_operation_observability_span_helpers_121__0a437a1e(
        self, mock_tracer
    ):
        """Test span is created with correct name and attributes."""
        tracer, otel_tracer, _ = mock_tracer

        async with traced_async_operation(tracer, "async_op", {"key": "value"}):
            await asyncio.sleep(0)

        tracer.get_tracer.assert_called_once_with("bioetl")
        otel_tracer.start_as_current_span.assert_called_once_with(
            "async_op", attributes={"key": "value"}
        )

    @pytest.mark.asyncio
    async def test_traced_async_operation__and_exit_called__940c3059(self, mock_tracer):
        """Test span __enter__ and __exit__ are called."""
        tracer, _, span = mock_tracer

        async with traced_async_operation(tracer, "async_op"):
            await asyncio.sleep(0)

        span.__enter__.assert_called_once()
        span.__exit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_traced_async_operation__closed_on_exception__bcb1033f(
        self, mock_tracer
    ):
        """Test span is closed even when exception occurs."""
        tracer, _, span = mock_tracer

        with pytest.raises(RuntimeError):
            async with traced_async_operation(tracer, "async_op"):
                raise RuntimeError("async error")

        span.__exit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_traced_async_operation__recorded_on_span__0b8459ca(
        self, mock_tracer
    ):
        """Test exception is recorded on span."""
        tracer, _, span = mock_tracer

        with pytest.raises(RuntimeError):
            async with traced_async_operation(tracer, "async_op"):
                raise RuntimeError("async error")

        span.set_attribute.assert_any_call("error", True)
        span.set_attribute.assert_any_call("error.type", "RuntimeError")
        span.record_exception.assert_called_once()

    @pytest.mark.asyncio
    async def test_operation_observability_span_helpers_169__24868df6(
        self, mock_tracer
    ):
        """Test attributes can be set inside async context."""
        tracer, _, span = mock_tracer

        async with traced_async_operation(tracer, "async_op") as s:
            s.set_attribute("async_result", "done")

        span.set_attribute.assert_called_with("async_result", "done")

    @pytest.mark.asyncio
    async def test_custom_tracer_name__test_traced_async_operation_application_observability_test_span_helpers_179(
        self, mock_tracer
    ):
        """Test custom tracer name is used in async context."""
        tracer, _, _ = mock_tracer

        async with traced_async_operation(
            tracer, "async_op", tracer_name="async.tracer"
        ):
            await asyncio.sleep(0)

        tracer.get_tracer.assert_called_once_with("async.tracer")
