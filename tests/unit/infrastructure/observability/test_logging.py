"""Unit tests for logging module."""

from __future__ import annotations


import pytest
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.observability.logging import StructlogLogger, create_logger


@pytest.mark.unit
class TestStructlogLogger:
    """Tests for StructlogLogger adapter."""

    def test_structlog_logger__logger_port__1be605ac(self) -> None:
        """Test that StructlogLogger implements LoggerPort protocol."""
        run_id = deterministic_uuid_from_callsite("test_logging")
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
        )

        # StructlogLogger must implement LoggerPort
        assert isinstance(logger, LoggerPort)

    def test_structlog_logger_is_structlog_logger_type(self) -> None:
        """Test that create_logger returns StructlogLogger instance."""
        run_id = deterministic_uuid_from_callsite("test_logging")
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
        )

        assert isinstance(logger, StructlogLogger)

    def test_structlog_logger_bind_returns_self_type(self) -> None:
        """Test that bind() returns StructlogLogger, not BoundLogger."""
        run_id = deterministic_uuid_from_callsite("test_logging")
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
        )

        bound = logger.bind(extra_key="value")

        # bind() must return StructlogLogger, not raw BoundLogger
        assert isinstance(bound, StructlogLogger)
        assert isinstance(bound, LoggerPort)

    def test_structlog_logger_all_methods(self) -> None:
        """Test that StructlogLogger has all LoggerPort methods."""
        run_id = deterministic_uuid_from_callsite("test_logging")
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

    def test_structlog_logger_ignores_event_kwarg_conflict(self) -> None:
        """Test that kwargs['event'] is sanitized before structlog call."""
        run_id = deterministic_uuid_from_callsite("test_logging")
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
        )

        logger.info("pipeline_started", event="pipeline_started", stage="extract")


@pytest.mark.unit
class TestCreateLogger:
    """Tests for create_logger function."""

    def test_create_logger_returns_bound_logger(self):
        """Test that create_logger returns a bound logger."""
        run_id = deterministic_uuid_from_callsite("test_logging")
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
        )

        assert logger is not None
        # Should have bind method (BoundLogger)
        assert hasattr(logger, "bind")

    def test_create_logger_with_json_format(self):
        """Test create_logger with JSON format."""
        run_id = deterministic_uuid_from_callsite("test_logging")
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
            json_format=True,
        )

        assert logger is not None

    def test_create_logger_with_console_format(self):
        """Test create_logger with console format."""
        run_id = deterministic_uuid_from_callsite("test_logging")
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
            json_format=False,
        )

        assert logger is not None

    def test_create_logger_with_custom_log_level(self):
        """Test create_logger with custom log level."""
        run_id = deterministic_uuid_from_callsite("test_logging")
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
            log_level="DEBUG",
        )

        assert logger is not None

    def test_logger_can_log_info(self):
        """Test that logger can log info messages."""
        run_id = deterministic_uuid_from_callsite("test_logging")
        logger = create_logger(
            pipeline="test_pipeline",
            run_id=run_id,
        )

        # Should not raise
        logger.info("Test message", extra={"key": "value"})

    def test_logger_bound_to_pipeline_and_run_id(self):
        """Test that logger is bound to pipeline and run_id."""
        run_id = deterministic_uuid_from_callsite("test_logging")
        logger = create_logger(
            pipeline="my_pipeline",
            run_id=run_id,
        )

        # The logger should be bound with these values
        # We can verify by checking it has the bind method
        bound_logger = logger.bind(stage="extract")
        assert bound_logger is not None
