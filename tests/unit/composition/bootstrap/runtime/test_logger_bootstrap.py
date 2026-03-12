"""Unit tests for logger bootstrap helpers.

Tests bootstrap_logger_port and its deprecated alias bootstrap_logger,
verifying correct DI wiring and UUID generation.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from bioetl.composition.bootstrap.runtime.logger_bootstrap import (
    bootstrap_logger,
    bootstrap_logger_port,
)
from bioetl.domain.ports import LoggerPort


@pytest.mark.unit
class TestBootstrapLoggerPort:
    """Tests for bootstrap_logger_port."""

    def test_returns_logger_port(self) -> None:
        """Should return an object implementing LoggerPort."""
        mock_logger = MagicMock(spec=LoggerPort)
        factory = MagicMock(return_value=mock_logger)

        result = bootstrap_logger_port(
            pipeline="test_pipeline",
            logger_factory=factory,
        )

        assert result is mock_logger

    def test_passes_pipeline_name_to_factory(self) -> None:
        """Factory should receive the pipeline name."""
        mock_logger = MagicMock(spec=LoggerPort)
        factory = MagicMock(return_value=mock_logger)

        bootstrap_logger_port(
            pipeline="chembl_activity",
            logger_factory=factory,
        )

        call_args = factory.call_args
        assert call_args[0][0] == "chembl_activity"

    def test_generates_run_id_when_none(self) -> None:
        """Should generate a UUID run_id when run_id is None."""
        captured_run_ids: list[UUID] = []

        def capture_factory(pipeline: str, run_id: UUID, log_level: str) -> LoggerPort:
            captured_run_ids.append(run_id)
            return MagicMock(spec=LoggerPort)

        bootstrap_logger_port(
            pipeline="test",
            run_id=None,
            logger_factory=capture_factory,
        )

        assert len(captured_run_ids) == 1
        assert isinstance(captured_run_ids[0], UUID)

    def test_uses_provided_run_id(self) -> None:
        """Should use the provided run_id, not generate a new one."""
        provided_run_id = uuid4()
        captured_run_ids: list[UUID] = []

        def capture_factory(pipeline: str, run_id: UUID, log_level: str) -> LoggerPort:
            captured_run_ids.append(run_id)
            return MagicMock(spec=LoggerPort)

        bootstrap_logger_port(
            pipeline="test",
            run_id=provided_run_id,
            logger_factory=capture_factory,
        )

        assert captured_run_ids[0] == provided_run_id

    def test_passes_log_level_to_factory(self) -> None:
        """Factory should receive the log_level argument."""
        captured_levels: list[str] = []

        def capture_factory(pipeline: str, run_id: UUID, log_level: str) -> LoggerPort:
            captured_levels.append(log_level)
            return MagicMock(spec=LoggerPort)

        bootstrap_logger_port(
            pipeline="test",
            log_level="DEBUG",
            logger_factory=capture_factory,
        )

        assert captured_levels[0] == "DEBUG"

    def test_default_log_level_is_info(self) -> None:
        """Default log_level should be 'INFO'."""
        captured_levels: list[str] = []

        def capture_factory(pipeline: str, run_id: UUID, log_level: str) -> LoggerPort:
            captured_levels.append(log_level)
            return MagicMock(spec=LoggerPort)

        bootstrap_logger_port(
            pipeline="test",
            logger_factory=capture_factory,
        )

        assert captured_levels[0] == "INFO"

    def test_each_call_with_none_run_id_generates_unique_uuid(self) -> None:
        """Two calls with run_id=None should generate different UUIDs."""
        captured_run_ids: list[UUID] = []

        def capture_factory(pipeline: str, run_id: UUID, log_level: str) -> LoggerPort:
            captured_run_ids.append(run_id)
            return MagicMock(spec=LoggerPort)

        bootstrap_logger_port(
            pipeline="test", run_id=None, logger_factory=capture_factory
        )
        bootstrap_logger_port(
            pipeline="test", run_id=None, logger_factory=capture_factory
        )

        assert captured_run_ids[0] != captured_run_ids[1]


@pytest.mark.unit
class TestBootstrapLoggerAlias:
    """Tests for bootstrap_logger (deprecated alias)."""

    def test_alias_delegates_to_port_variant(self) -> None:
        """bootstrap_logger should produce equivalent result to bootstrap_logger_port."""
        mock_logger = MagicMock(spec=LoggerPort)
        factory = MagicMock(return_value=mock_logger)

        run_id = uuid4()
        result = bootstrap_logger(
            pipeline="test_pipeline",
            run_id=run_id,
            log_level="WARNING",
            logger_factory=factory,
        )

        assert result is mock_logger
        factory.assert_called_once()

    def test_alias_passes_same_args(self) -> None:
        """Alias should pass through all arguments identically."""
        captured: list[tuple] = []

        def capture_factory(pipeline: str, run_id: UUID, log_level: str) -> LoggerPort:
            captured.append((pipeline, run_id, log_level))
            return MagicMock(spec=LoggerPort)

        run_id = uuid4()
        bootstrap_logger(
            pipeline="my_pipeline",
            run_id=run_id,
            log_level="ERROR",
            logger_factory=capture_factory,
        )

        assert captured[0] == ("my_pipeline", run_id, "ERROR")
