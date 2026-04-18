"""Tests for logging helpers."""

from unittest.mock import MagicMock

from bioetl.infrastructure.observability.logging_helpers import log_debug, log_error


def test_log_error():
    """Test log_error function."""
    logger = MagicMock()
    error = "Test error"
    log_error(logger, error)
    logger.error.assert_called_once_with(f"Error occurred: {error}")


def test_log_debug():
    """Test log_debug function."""
    logger = MagicMock()
    details = "Test details"
    log_debug(logger, details)
    logger.debug.assert_called_once_with(f"Debug info: {details}")
