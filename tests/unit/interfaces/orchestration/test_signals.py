"""Unit tests for the signals module."""

from __future__ import annotations

import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.interfaces.orchestration.signals import register_signal_handlers


@pytest.mark.unit
class TestRegisterSignalHandlers:
    """Tests for register_signal_handlers function."""

    def test_sets_sigterm_handler(self):
        """Test that SIGTERM handler is set."""
        shutdown_service = MagicMock()
        shutdown_service.initiate_shutdown = AsyncMock()

        with patch.object(signal, "signal") as mock_signal:
            register_signal_handlers(shutdown_service)

            # Check SIGTERM handler was set
            sigterm_calls = [
                call
                for call in mock_signal.call_args_list
                if call[0][0] == signal.SIGTERM
            ]
            assert len(sigterm_calls) == 1

    def test_sets_sigint_handler(self):
        """Test that SIGINT handler is set."""
        shutdown_service = MagicMock()
        shutdown_service.initiate_shutdown = AsyncMock()

        with patch.object(signal, "signal") as mock_signal:
            register_signal_handlers(shutdown_service)

            # Check SIGINT handler was set
            sigint_calls = [
                call
                for call in mock_signal.call_args_list
                if call[0][0] == signal.SIGINT
            ]
            assert len(sigint_calls) == 1

    def test_handles_value_error_in_non_main_thread(self):
        """Test that ValueError is handled gracefully (non-main thread)."""
        shutdown_service = MagicMock()
        shutdown_service.initiate_shutdown = AsyncMock()

        with patch.object(signal, "signal", side_effect=ValueError("Not main thread")):
            # Should not raise
            register_signal_handlers(shutdown_service)

    def test_logs_warning_on_value_error(self):
        """Test that a warning is logged when signal setup fails."""
        shutdown_service = MagicMock()
        shutdown_service.initiate_shutdown = AsyncMock()
        mock_logger = MagicMock()

        with patch.object(signal, "signal", side_effect=ValueError("Not main thread")):
            register_signal_handlers(shutdown_service, logger=mock_logger)

            mock_logger.warning.assert_called_with(
                "Cannot set signal handlers outside main thread"
            )

    def test_works_without_logger(self):
        """Test that setup works without logger (silent mode)."""
        shutdown_service = MagicMock()
        shutdown_service.initiate_shutdown = AsyncMock()

        with patch.object(signal, "signal", side_effect=ValueError("Not main thread")):
            # Should not raise even without logger
            register_signal_handlers(shutdown_service, logger=None)
