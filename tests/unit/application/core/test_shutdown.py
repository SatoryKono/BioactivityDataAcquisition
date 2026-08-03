# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for ShutdownSignal."""

from __future__ import annotations

import asyncio

import pytest

from bioetl.application.core.lifecycle.shutdown import (
    PipelineShutdownError,
    ShutdownSignal,
)


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

        result = await asyncio.wait_for(signal.wait(), timeout=1.0)

        assert result is None
        assert signal.is_requested is True

    @pytest.mark.asyncio
    async def test_wait_blocks_until_requested(self):
        """Test that wait() blocks until request() is called."""
        signal = ShutdownSignal()

        wait_task = asyncio.create_task(signal.wait())
        await asyncio.sleep(0)
        assert wait_task.done() is False

        signal.request()
        await asyncio.wait_for(wait_task, timeout=1.0)

        assert signal.is_requested is True

    def test_is_shutting_down_alias(self):
        """Test is_shutting_down() is alias for is_requested."""
        signal = ShutdownSignal()
        assert signal.is_shutting_down() is False
        signal.request()
        assert signal.is_shutting_down() is True

    @pytest.mark.asyncio
    async def test_shutdown_signal_initiate_shutdown_sets_flag(self):
        """Test initiate_shutdown() sets flag (ShutdownPort compat)."""
        signal = ShutdownSignal()
        await signal.initiate_shutdown("test reason")
        assert signal.is_requested is True
        assert signal.is_shutting_down() is True

    @pytest.mark.asyncio
    async def test_shutdown_signal_wait_for_completion_returns_false_on_timeout(self):
        """Test wait_for_completion returns False on timeout."""
        signal = ShutdownSignal()
        result = await signal.wait_for_completion(timeout_seconds=0.01)
        assert result is False

    @pytest.mark.asyncio
    async def test_shutdown_signal_wait_for_completion_returns_true_after_mark_completed(
        self,
    ):
        """Test wait_for_completion returns True when marked complete."""
        signal = ShutdownSignal()

        wait_task = asyncio.create_task(signal.wait_for_completion(timeout_seconds=1.0))
        await asyncio.sleep(0)
        assert wait_task.done() is False

        signal.mark_completed()
        result = await asyncio.wait_for(wait_task, timeout=1.0)

        assert result is True

    def test_mark_completed(self):
        """Test mark_completed sets completion event."""
        signal = ShutdownSignal()
        signal.mark_completed()
        # Completion event should be set
        assert signal._completion_event.is_set()


@pytest.mark.unit
class TestPipelineShutdownError:
    """Tests for PipelineShutdownError exception."""

    def test_pipeline_shutdown_error_can_be_raised(self):
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
