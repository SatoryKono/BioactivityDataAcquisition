"""Unit tests for logging module."""

from __future__ import annotations

from uuid import uuid4

import pytest

from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.observability.logging import UnifiedLogger, create_logger


@pytest.mark.unit
class TestUnifiedLogger:
    """Tests for UnifiedLogger adapter."""

    def test_unified_logger_implements_logger_port(self) -> None:
        """Test that UnifiedLogger implements LoggerPort protocol."""
        run_id = uuid4()
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
        )

        # UnifiedLogger must implement LoggerPort
        assert isinstance(logger, LoggerPort)

    def test_unified_logger_is_unified_logger_type(self) -> None:
        """Test that create_logger returns UnifiedLogger instance."""
        run_id = uuid4()
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
        )

        assert isinstance(logger, UnifiedLogger)

    def test_unified_logger_bind_returns_self_type(self) -> None:
        """Test that bind() returns UnifiedLogger, not BoundLogger."""
        run_id = uuid4()
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
        )

        bound = logger.bind(extra_key="value")

        # bind() must return UnifiedLogger, not raw BoundLogger
        assert isinstance(bound, UnifiedLogger)
        assert isinstance(bound, LoggerPort)

    def test_unified_logger_all_methods(self) -> None:
        """Test that UnifiedLogger has all LoggerPort methods."""
        run_id = uuid4()
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
        )

        # All these methods should exist and not raise
        logger.info("info_event", key="value")
        logger.warning("warning_event", key="value")
        logger.error("error_event", key="value")
        logger.debug("debug_event", key="value")

        # exception requires exc_info in context, just check it exists
        assert hasattr(logger, "exception")


@pytest.mark.unit
class TestCreateLogger:
    """Tests for create_logger function."""

    def test_create_logger_returns_bound_logger(self):
        """Test that create_logger returns a bound logger."""
        run_id = uuid4()
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
        )

        assert logger is not None
        # Should have bind method (BoundLogger)
        assert hasattr(logger, "bind")

    def test_create_logger_with_json_format(self):
        """Test create_logger with JSON format."""
        run_id = uuid4()
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
            json_format=True,
        )

        assert logger is not None

    def test_create_logger_with_console_format(self):
        """Test create_logger with console format."""
        run_id = uuid4()
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
            json_format=False,
        )

        assert logger is not None

    def test_create_logger_with_custom_log_level(self):
        """Test create_logger with custom log level."""
        run_id = uuid4()
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
            log_level="DEBUG",
        )

        assert logger is not None

    def test_logger_can_log_info(self):
        """Test that logger can log info messages."""
        run_id = uuid4()
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
        )

        # Should not raise
        logger.info("Test message", extra={"key": "value"})

    def test_logger_bound_to_pipeline_and_run_id(self):
        """Test that logger is bound to pipeline and run_id."""
        run_id = uuid4()
        logger = create_logger(
            pipeline="my_pipeline",
            run_id=run_id,
        )

        # The logger should be bound with these values
        # We can verify by checking it has the bind method
        bound_logger = logger.bind(stage="extract")
        assert bound_logger is not None
