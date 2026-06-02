"""Tests for infrastructure/adapters/adapter_error_logging.py.

These tests verify the standardized error logging utility.
"""

from __future__ import annotations

import pytest

import logging
from unittest.mock import MagicMock

from tests.helpers.adapter_error_logging import log_adapter_error


pytestmark = pytest.mark.unit


class TestLogAdapterError:
    """Tests for log_adapter_error function."""

    def test_logs_with_standard_logger(self) -> None:
        """log_adapter_error works with standard logging.Logger (structlog-style kwargs)."""
        logger = logging.getLogger("test_logger")
        logger.error = MagicMock()

        log_adapter_error(
            logger,
            provider="chembl",
            operation="fetch",
            exc_info=True,
            batch_id="batch_001",
        )

        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert call_args[0][0] == "chembl fetch failed"
        assert call_args[1]["exc_info"] is True
        # Context passed as kwargs (structlog-style), not extra
        assert call_args[1]["batch_id"] == "batch_001"

    def test_logs_with_structlog_logger(self) -> None:
        """log_adapter_error works with structlog-compatible logger."""
        mock_logger = MagicMock()

        log_adapter_error(
            mock_logger,
            provider="pubchem",
            operation="batch fetch",
            exc_info=False,
            record_count=100,
        )

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "pubchem batch fetch failed"
        assert call_args[1]["exc_info"] is False
        assert call_args[1]["record_count"] == 100

    def test_message_format(self) -> None:
        """Message follows '{provider} {operation} failed' format."""
        mock_logger = MagicMock()

        log_adapter_error(
            mock_logger,
            provider="uniprot",
            operation="health check",
        )

        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "uniprot health check failed"

    def test_default_exc_info_true(self) -> None:
        """exc_info defaults to True."""
        mock_logger = MagicMock()

        log_adapter_error(mock_logger, provider="chembl", operation="fetch")

        call_args = mock_logger.error.call_args
        assert call_args[1]["exc_info"] is True

    def test_exc_info_can_be_disabled(self) -> None:
        """exc_info can be set to False."""
        mock_logger = MagicMock()

        log_adapter_error(
            mock_logger,
            provider="chembl",
            operation="fetch",
            exc_info=False,
        )

        call_args = mock_logger.error.call_args
        assert call_args[1]["exc_info"] is False

    def test_with_multiple_context_fields(self) -> None:
        """Multiple context fields are passed through."""
        mock_logger = MagicMock()

        log_adapter_error(
            mock_logger,
            provider="pubmed",
            operation="xml parse",
            exc_info=True,
            run_id="run_123",
            record_id="PMID:456",
            error_type="ParseError",
            retry_count=2,
        )

        call_args = mock_logger.error.call_args
        assert call_args[1]["run_id"] == "run_123"
        assert call_args[1]["record_id"] == "PMID:456"
        assert call_args[1]["error_type"] == "ParseError"
        assert call_args[1]["retry_count"] == 2

    def test_with_empty_context(self) -> None:
        """Works with no additional context."""
        mock_logger = MagicMock()

        log_adapter_error(mock_logger, provider="chembl", operation="fetch")

        mock_logger.error.assert_called_once()

    def test_with_none_context_values(self) -> None:
        """Handles None values in context."""
        mock_logger = MagicMock()

        log_adapter_error(
            mock_logger,
            provider="chembl",
            operation="fetch",
            optional_field=None,
        )

        call_args = mock_logger.error.call_args
        assert call_args[1]["optional_field"] is None

    def test_standard_logger_receives_kwargs(self) -> None:
        """Standard logging.Logger receives context as kwargs (structlog-style)."""
        logger = logging.getLogger("test_standard")
        logger.error = MagicMock()

        log_adapter_error(
            logger,
            provider="chembl",
            operation="fetch",
            custom_field="value",
        )

        call_args = logger.error.call_args
        # All context passed as kwargs (structlog-style), not wrapped in extra
        assert call_args[1]["custom_field"] == "value"
        assert call_args[1]["provider"] == "chembl"

    def test_structlog_logger_receives_context_as_kwargs(self) -> None:
        """Structlog-compatible logger receives context as **kwargs."""
        mock_logger = MagicMock()

        log_adapter_error(
            mock_logger,
            provider="chembl",
            operation="fetch",
            custom_field="value",
        )

        call_args = mock_logger.error.call_args
        assert call_args[1]["custom_field"] == "value"

    def test_various_providers(self) -> None:
        """Works with various provider names."""
        providers = ["chembl", "pubchem", "uniprot", "pubmed"]
        mock_logger = MagicMock()

        for provider in providers:
            mock_logger.reset_mock()
            log_adapter_error(mock_logger, provider=provider, operation="fetch")
            call_args = mock_logger.error.call_args
            assert provider in call_args[0][0]

    def test_various_operations(self) -> None:
        """Works with various operation names."""
        operations = ["fetch", "batch fetch", "health check", "transform", "validate"]
        mock_logger = MagicMock()

        for operation in operations:
            mock_logger.reset_mock()
            log_adapter_error(mock_logger, provider="test", operation=operation)
            call_args = mock_logger.error.call_args
            assert operation in call_args[0][0]
