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
"""Unit tests for dependency result service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.dependency_result_mapper import (
    DependencyResultService,
)
from bioetl.domain.composite.config import DependencyConfig
from bioetl.domain.composite.result import DependencyStatus


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger for result-service tests."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


def test_build_success_result_uses_runner_execution_metrics(
    mock_logger: MagicMock,
) -> None:
    """Success result should read public runner metrics view."""
    mapper = DependencyResultService(mock_logger)
    dependency = DependencyConfig(
        pipeline="chembl_publication_term",
        join_keys=("document_chembl_id",),
    )
    runner = MagicMock()
    runner.run = AsyncMock(return_value=None)
    runner.execution_metrics = {
        "records_fetched": 7,
        "records_silver": 5,
    }
    started_at = datetime(2026, 3, 11, 10, 0, tzinfo=UTC)
    completed_at = datetime(2026, 3, 11, 10, 0, 3, tzinfo=UTC)

    result = mapper.build_success_result(
        dependency=dependency,
        runner=runner,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=3.0,
    )

    assert result.status == DependencyStatus.SUCCESS
    assert result.records_extracted == 7
    assert result.records_silver == 5
    assert result.duration_seconds == pytest.approx(3.0)
    mock_logger.info.assert_called_once()


def test_build_success_result_requires_canonical_metric_keys(
    mock_logger: MagicMock,
) -> None:
    """Missing required runner counters should fail loudly."""
    mapper = DependencyResultService(mock_logger)
    dependency = DependencyConfig(
        pipeline="chembl_publication_term",
        join_keys=("document_chembl_id",),
    )
    runner = MagicMock()
    runner.execution_metrics = {"records_fetched": 7}

    with pytest.raises(KeyError, match="records_silver"):
        mapper.build_success_result(
            dependency=dependency,
            runner=runner,
            started_at=datetime(2026, 3, 11, 10, 0, tzinfo=UTC),
            completed_at=datetime(2026, 3, 11, 10, 0, 3, tzinfo=UTC),
            duration_seconds=3.0,
        )


def test_build_failed_result_uses_error_log_for_required_dependency(
    mock_logger: MagicMock,
) -> None:
    """Required dependency failure should emit error-level log."""
    mapper = DependencyResultService(mock_logger)
    dependency = DependencyConfig(
        pipeline="chembl_publication_term",
        join_keys=("document_chembl_id",),
        required=True,
    )
    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at

    result = mapper.build_failed_result(
        dependency=dependency,
        error=RuntimeError("boom"),
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=0.0,
    )

    assert result.status == DependencyStatus.FAILED
    assert "boom" in (result.error_message or "")
    mock_logger.error.assert_called_once()


def test_build_timeout_result_returns_timeout_status(
    mock_logger: MagicMock,
) -> None:
    """Timeout result should preserve dependency timeout threshold."""
    mapper = DependencyResultService(mock_logger)
    dependency = DependencyConfig(
        pipeline="chembl_publication_term",
        join_keys=("document_chembl_id",),
        timeout_seconds=12,
    )

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = started_at

    result = mapper.build_timeout_result(
        dependency=dependency,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=12.0,
    )

    assert result.status == DependencyStatus.TIMEOUT
    assert result.duration_seconds == 12
    mock_logger.warning.assert_called_once()
