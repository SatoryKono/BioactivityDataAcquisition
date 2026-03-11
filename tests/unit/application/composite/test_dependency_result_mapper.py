"""Unit tests for dependency result mapping helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.dependency_result_mapper import (
    DependencyResultMapper,
)
from bioetl.domain.composite.config import DependencyConfig
from bioetl.domain.composite.result import DependencyStatus


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger for mapper tests."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


def test_build_success_result_uses_runner_execution_metrics(
    mock_logger: MagicMock,
) -> None:
    """Success result should read public runner metrics view."""
    mapper = DependencyResultMapper(mock_logger)
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
    )

    assert result.status == DependencyStatus.SUCCESS
    assert result.records_extracted == 7
    assert result.records_silver == 5
    assert result.duration_seconds == 3.0
    mock_logger.info.assert_called_once()


def test_build_failed_result_uses_error_log_for_required_dependency(
    mock_logger: MagicMock,
) -> None:
    """Required dependency failure should emit error-level log."""
    mapper = DependencyResultMapper(mock_logger)
    dependency = DependencyConfig(
        pipeline="chembl_publication_term",
        join_keys=("document_chembl_id",),
        required=True,
    )
    started_at = datetime.now(tz=UTC)

    result = mapper.build_failed_result(
        dependency=dependency,
        error=RuntimeError("boom"),
        started_at=started_at,
    )

    assert result.status == DependencyStatus.FAILED
    assert "boom" in (result.error_message or "")
    mock_logger.error.assert_called_once()


def test_build_timeout_result_returns_timeout_status(
    mock_logger: MagicMock,
) -> None:
    """Timeout result should preserve dependency timeout threshold."""
    mapper = DependencyResultMapper(mock_logger)
    dependency = DependencyConfig(
        pipeline="chembl_publication_term",
        join_keys=("document_chembl_id",),
        timeout_seconds=12,
    )

    result = mapper.build_timeout_result(
        dependency=dependency,
        started_at=datetime.now(tz=UTC),
    )

    assert result.status == DependencyStatus.TIMEOUT
    assert result.duration_seconds == 12
    mock_logger.warning.assert_called_once()
