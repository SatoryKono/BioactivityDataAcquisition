# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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

    def test_port_logger_port__logger_port__75b85b16(self) -> None:
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
