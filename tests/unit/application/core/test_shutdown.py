"""Unit tests for ShutdownSignal."""

import asyncio

import pytest

from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal


@pytest.mark.unit
class TestShutdownSignal:
    """Tests for ShutdownSignal class."""

    def test_initial_state(self):
        """Test that signal is not requested initially."""
        signal = ShutdownSignal()
        assert signal.is_requested is False

    def test_request_sets_flag(self):
        """Test that request() sets the flag."""
        signal = ShutdownSignal()
        signal.request()
        assert signal.is_requested is True

    def test_request_is_idempotent(self):
        """Test that multiple requests don't cause issues."""
        signal = ShutdownSignal()
        signal.request()
        signal.request()  # Second call should be safe
        assert signal.is_requested is True

    def test_reset_clears_flag(self):
        """Test that reset() clears the flag."""
        signal = ShutdownSignal()
        signal.request()
        signal.reset()
        assert signal.is_requested is False

    @pytest.mark.asyncio
    async def test_wait_returns_immediately_if_requested(self):
        """Test that wait() returns immediately if already requested."""
        signal = ShutdownSignal()
        signal.request()

        # Should return immediately
        await asyncio.wait_for(signal.wait(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_wait_blocks_until_requested(self):
        """Test that wait() blocks until request() is called."""
        signal = ShutdownSignal()

        async def request_after_delay():
            await asyncio.sleep(0.1)
            signal.request()

        # Start request task
        task = asyncio.create_task(request_after_delay())

        # Wait for signal
        await asyncio.wait_for(signal.wait(), timeout=1.0)

        assert signal.is_requested is True
        await task


@pytest.mark.unit
class TestPipelineShutdownError:
    """Tests for PipelineShutdownError exception."""

    def test_can_be_raised(self):
        """Test that exception can be raised and caught."""
        with pytest.raises(PipelineShutdownError):
            raise PipelineShutdownError()

    def test_is_exception(self):
        """Test that PipelineShutdownError is an Exception."""
        assert issubclass(PipelineShutdownError, Exception)

    def test_with_message(self):
        """Test exception with message."""
        with pytest.raises(PipelineShutdownError, match="test message"):
            raise PipelineShutdownError("test message")
