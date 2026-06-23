"""Tests for logging helpers."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.observability.logging_helpers import log_debug, log_error


pytestmark = pytest.mark.unit


def test_log_error():
    """Test log_error function."""
    logger = MagicMock()
    error = "Test error"
    log_error(logger, error)
    logger.error.assert_called_once_with("error_occurred", error=error)


def test_log_debug():
    """Test log_debug function."""
    logger = MagicMock()
    details = "Test details"
    log_debug(logger, details)
    logger.debug.assert_called_once_with("debug_info", details=details)


def test_log_error_supports_standard_logging_logger(monkeypatch) -> None:
    logger = logging.getLogger("bioetl.test.log_error_supports_standard_logger")
    error_mock = MagicMock()
    monkeypatch.setattr(logger, "error", error_mock)

    log_error(logger, "boom")

    error_mock.assert_called_once_with("Error occurred: %s", "boom")


def test_log_debug_supports_standard_logging_logger(monkeypatch) -> None:
    logger = logging.getLogger("bioetl.test.log_debug_supports_standard_logger")
    debug_mock = MagicMock()
    monkeypatch.setattr(logger, "debug", debug_mock)

    log_debug(logger, "details")

    debug_mock.assert_called_once_with("Debug info: %s", "details")
