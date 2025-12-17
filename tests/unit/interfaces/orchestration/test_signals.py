"""Unit tests for the signals module."""

import signal
from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.core.shutdown import ShutdownSignal
from bioetl.interfaces.orchestration.signals import setup_shutdown_handlers


@pytest.mark.unit
class TestSetupShutdownHandlers:
    """Tests for setup_shutdown_handlers function."""

    def test_sets_sigterm_handler(self):
        """Test that SIGTERM handler is set."""
        shutdown_signal = ShutdownSignal()

        with patch.object(signal, "signal") as mock_signal:
            setup_shutdown_handlers(shutdown_signal)

            # Check SIGTERM handler was set
            sigterm_calls = [
                call for call in mock_signal.call_args_list
                if call[0][0] == signal.SIGTERM
            ]
            assert len(sigterm_calls) == 1

    def test_sets_sigint_handler(self):
        """Test that SIGINT handler is set."""
        shutdown_signal = ShutdownSignal()

        with patch.object(signal, "signal") as mock_signal:
            setup_shutdown_handlers(shutdown_signal)

            # Check SIGINT handler was set
            sigint_calls = [
                call for call in mock_signal.call_args_list
                if call[0][0] == signal.SIGINT
            ]
            assert len(sigint_calls) == 1

    def test_signal_handler_requests_shutdown(self):
        """Test that the signal handler triggers shutdown signal."""
        shutdown_signal = ShutdownSignal()
        captured_handler = None

        def capture_handler(signum, handler):
            nonlocal captured_handler
            if signum == signal.SIGTERM:
                captured_handler = handler

        with patch.object(signal, "signal", side_effect=capture_handler):
            setup_shutdown_handlers(shutdown_signal)

        assert captured_handler is not None
        assert shutdown_signal.is_requested is False

        # Call the captured handler
        captured_handler(signal.SIGTERM, None)

        assert shutdown_signal.is_requested is True

    def test_handles_value_error_in_non_main_thread(self):
        """Test that ValueError is handled gracefully (non-main thread)."""
        shutdown_signal = ShutdownSignal()

        with patch.object(signal, "signal", side_effect=ValueError("Not main thread")):
            # Should not raise
            setup_shutdown_handlers(shutdown_signal)

    def test_logs_warning_on_value_error(self):
        """Test that a warning is logged when signal setup fails."""
        shutdown_signal = ShutdownSignal()

        with patch.object(signal, "signal", side_effect=ValueError("Not main thread")):
            with patch("bioetl.interfaces.orchestration.signals.structlog") as mock_structlog:
                mock_logger = MagicMock()
                mock_structlog.get_logger.return_value = mock_logger

                setup_shutdown_handlers(shutdown_signal)

                mock_logger.warning.assert_called()
