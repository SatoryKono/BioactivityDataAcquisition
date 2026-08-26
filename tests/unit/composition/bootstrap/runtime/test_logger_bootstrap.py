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
"""Unit tests for logger bootstrap helpers.

Tests bootstrap_logger and its deprecated alias bootstrap_logger,
verifying correct DI wiring and UUID generation.
"""

from __future__ import annotations

from itertools import count
from unittest.mock import MagicMock
from uuid import NAMESPACE_OID, UUID, uuid5

from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.composition.bootstrap.runtime import (
    logger_bootstrap as logger_bootstrap_module,
)
from bioetl.composition.bootstrap.runtime.logger_bootstrap import (
    bootstrap_logger,
)
from bioetl.domain.ports import LoggerPort


@pytest.mark.unit
class TestBootstrapLoggerPort:
    """Tests for bootstrap_logger."""

    def test_returns_logger_port(self) -> None:
        """Should return an object implementing LoggerPort."""
        mock_logger = MagicMock(spec=LoggerPort)
        factory = MagicMock(return_value=mock_logger)

        result = bootstrap_logger(
            pipeline="test_pipeline",
            logger_factory=factory,
        )

        assert result is mock_logger

    def test_passes_pipeline_name_to_factory(self) -> None:
        """Factory should receive the pipeline name."""
        mock_logger = MagicMock(spec=LoggerPort)
        factory = MagicMock(return_value=mock_logger)

        bootstrap_logger(
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

        bootstrap_logger(
            pipeline="test",
            run_id=None,
            logger_factory=capture_factory,
        )

        assert len(captured_run_ids) == 1
        assert isinstance(captured_run_ids[0], UUID)

    def test_uses_provided_run_id(self) -> None:
        """Should use the provided run_id, not generate a new one."""
        provided_run_id = deterministic_uuid_from_callsite("test_logger_bootstrap")
        captured_run_ids: list[UUID] = []

        def capture_factory(pipeline: str, run_id: UUID, log_level: str) -> LoggerPort:
            captured_run_ids.append(run_id)
            return MagicMock(spec=LoggerPort)

        bootstrap_logger(
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

        bootstrap_logger(
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

        bootstrap_logger(
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

        bootstrap_logger(pipeline="test", run_id=None, logger_factory=capture_factory)
        bootstrap_logger(pipeline="test", run_id=None, logger_factory=capture_factory)

        assert captured_run_ids[0] != captured_run_ids[1]

    def test_fallback_run_id_uses_pipeline_and_occurrence_without_pid(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Fallback correlation is reproducible from governed inputs only."""
        monkeypatch.setattr(
            logger_bootstrap_module,
            "_FALLBACK_LOG_RUN_ID_COUNTER",
            count(7),
        )
        captured_run_ids: list[UUID] = []

        def capture_factory(pipeline: str, run_id: UUID, log_level: str) -> LoggerPort:
            captured_run_ids.append(run_id)
            return MagicMock(spec=LoggerPort)

        bootstrap_logger(
            pipeline="chembl_activity",
            run_id=None,
            logger_factory=capture_factory,
        )

        assert captured_run_ids == [
            uuid5(
                NAMESPACE_OID,
                "bioetl.logger_bootstrap:chembl_activity:7",
            )
        ]
