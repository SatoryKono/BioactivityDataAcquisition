"""Explicit LoggerPort contract suite."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.unified_logger import UnifiedLogger


@pytest.mark.unit
class TestLoggerPortContract:
    """Bounded contract assertions for LoggerPort implementations."""

    def test_noop_logger_implements_logger_port(self) -> None:
        assert isinstance(NoOpLogger(), LoggerPort)

    def test_bind_returns_logger_port_with_preserved_run_context(self) -> None:
        logger = UnifiedLogger(pipeline="chembl_activity", run_id="run-123")

        bound = logger.bind(dataset="chembl_activity")

        assert isinstance(bound, LoggerPort)
        assert isinstance(bound, UnifiedLogger)
        assert bound is not logger
        assert bound._pipeline == "chembl_activity"
        assert bound._run_id == "run-123"

    def test_info_emits_flat_event_with_default_stage(self) -> None:
        """LoggerPort event emission must stay flat and inject default stage."""
        logger = UnifiedLogger(pipeline="chembl_activity", run_id="run-123")
        logger._logger = MagicMock()

        logger.info("pipeline_started", dataset="chembl_activity")

        logger._logger.info.assert_called_once_with(
            "pipeline_started",
            stage="init",
            dataset="chembl_activity",
        )

    def test_explicit_kwargs_override_nested_extra_payload(self) -> None:
        """Explicit kwargs must win over compatibility `extra={...}` input."""
        logger = UnifiedLogger(pipeline="chembl_activity", run_id="run-123")
        logger._logger = MagicMock()

        logger.warning(
            "degraded_health",
            stage="validate",
            extra={"stage": "bootstrap", "component": "source", "event": "bad"},
            component="registry",
        )

        logger._logger.warning.assert_called_once_with(
            "degraded_health",
            stage="validate",
            component="registry",
        )

    def test_noop_logger_methods_are_safe_noops(self) -> None:
        logger = NoOpLogger()

        assert logger.bind(run_id="run-123") is logger
        assert logger.info("event", stage="init") is None
        assert logger.warning("event", stage="validate") is None
        assert logger.error("event", error_type="schema") is None
        assert logger.debug("event", dataset="chembl") is None
        assert logger.exception("event", error_type="runtime") is None
