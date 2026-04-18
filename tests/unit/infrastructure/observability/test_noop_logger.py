"""Unit tests for NoOpLogger (Null Object pattern)."""

from __future__ import annotations

import pytest

from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


@pytest.mark.unit
class TestNoOpLogger:
    """Tests for NoOpLogger implementation."""

    def test_implements_logger_port(self) -> None:
        """NoOpLogger should satisfy LoggerPort protocol."""
        logger = NoOpLogger()
        assert isinstance(logger, LoggerPort)

    def test_info_accepts_context_without_error(self) -> None:
        """info() should silently accept arbitrary context."""
        logger = NoOpLogger()
        logger.info("test message", key="value")

    def test_warning_accepts_context_without_error(self) -> None:
        """warning() should silently accept arbitrary context."""
        logger = NoOpLogger()
        logger.warning("test warning", key="value")

    def test_error_accepts_context_without_error(self) -> None:
        """error() should silently accept arbitrary context."""
        logger = NoOpLogger()
        logger.error("test error", key="value")

    def test_debug_accepts_context_without_error(self) -> None:
        """debug() should silently accept arbitrary context."""
        logger = NoOpLogger()
        logger.debug("test debug", key="value")

    def test_exception_accepts_context_without_error(self) -> None:
        """exception() should silently accept arbitrary context."""
        logger = NoOpLogger()
        logger.exception("test exception", key="value")

    def test_bind_returns_self(self) -> None:
        """bind() should return self (no new instance)."""
        logger = NoOpLogger()
        bound = logger.bind(run_id="123", pipeline="test")
        assert bound is logger

    def test_bind_chaining(self) -> None:
        """bind() should support chaining."""
        logger = NoOpLogger()
        bound = logger.bind(run_id="123").bind(stage="extract")
        assert bound is logger

    def test_info_with_no_kwargs(self) -> None:
        """info() should work with event-only call."""
        logger = NoOpLogger()
        logger.info("bare event")

    def test_all_exports(self) -> None:
        """__all__ should contain NoOpLogger."""
        from bioetl.infrastructure.observability import noop_logger

        assert "NoOpLogger" in noop_logger.__all__
