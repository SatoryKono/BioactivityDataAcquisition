"""Unit tests for BaseHttpAdapter observability fallback."""

from __future__ import annotations

from unittest.mock import MagicMock

from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


def test_base_http_adapter_logger_fallback():
    """Test that BaseHttpAdapter uses NoOpLogger when no logger is provided."""
    mock_http_client = MagicMock()

    # Initialize without logger
    adapter = BaseHttpAdapter(http_client=mock_http_client)

    # Verify logger is initialized and is instance of NoOpLogger
    assert hasattr(adapter, "logger")
    assert isinstance(adapter.logger, NoOpLogger)

    # Verify we can call methods on it without error
    adapter.logger.info("Test message")
    adapter.logger.error("Error message")

def test_base_http_adapter_logger_provided():
    """Test that BaseHttpAdapter uses provided logger."""
    mock_http_client = MagicMock()
    mock_logger = MagicMock()

    # Initialize with logger
    adapter = BaseHttpAdapter(http_client=mock_http_client, logger=mock_logger)

    # Verify provided logger is used
    assert adapter.logger is mock_logger
    assert not isinstance(adapter.logger, NoOpLogger)
