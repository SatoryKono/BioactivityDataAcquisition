"""Unit tests for QuarantineService.

Tests the quarantine administrative service.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.services.quarantine_service import (
    PurgeResult,
    QuarantineRecord,
    QuarantineService,
    ReplayResult,
)


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def mock_quarantine_port():
    """Create a mock quarantine port."""
    port = MagicMock()
    port.inspect = AsyncMock(return_value=[])
    port.get_stats = AsyncMock(return_value={})
    port.aclose = AsyncMock()
    return port


@pytest.fixture
def quarantine_service(mock_quarantine_port, mock_logger):
    """Create a QuarantineService instance."""
    return QuarantineService(
        quarantine_port=mock_quarantine_port,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestQuarantineRecord:
    """Test QuarantineRecord dataclass."""

    def test_quarantine_record_creation(self):
        """Test QuarantineRecord can be created."""
        now = datetime.now(UTC)
        record = QuarantineRecord(
            error_code="DQ_MISSING_FIELD",
            payload={"id": 123},
            batch_id="batch-123",
            pipeline="test_pipeline",
            ingestion_ts=now,
            metadata={"error_details": "Missing required field"},
        )

        assert record.error_code == "DQ_MISSING_FIELD"
        assert record.payload == {"id": 123}
        assert record.batch_id == "batch-123"
        assert record.pipeline == "test_pipeline"
        assert record.ingestion_ts == now


@pytest.mark.unit
class TestReplayResult:
    """Test ReplayResult dataclass."""

    def test_replay_result_creation(self):
        """Test ReplayResult can be created."""
        result = ReplayResult(
            batch_id="batch-123",
            records_replayed=10,
            records_succeeded=8,
            records_failed=2,
        )

        assert result.batch_id == "batch-123"
        assert result.records_replayed == 10
        assert result.records_succeeded == 8
        assert result.records_failed == 2


@pytest.mark.unit
class TestPurgeResult:
    """Test PurgeResult dataclass."""

    def test_purge_result_creation(self):
        """Test PurgeResult can be created."""
        result = PurgeResult(
            records_purged=100,
            pipelines_affected=["pipeline1", "pipeline2"],
        )

        assert result.records_purged == 100
        assert result.pipelines_affected == ["pipeline1", "pipeline2"]


@pytest.mark.unit
class TestQuarantineServiceInspect:
    """Test QuarantineService.inspect method."""

    @pytest.mark.asyncio
    async def test_inspect_empty(self, quarantine_service, mock_quarantine_port):
        """Test inspecting quarantine when empty."""
        mock_quarantine_port.inspect.return_value = []

        result = await quarantine_service.inspect("pipeline1", limit=10)

        assert result == []
        mock_quarantine_port.inspect.assert_called_once_with(
            pipeline="pipeline1",
            limit=10,
            error_code=None,
        )

    @pytest.mark.asyncio
    async def test_inspect_with_records(
        self, quarantine_service, mock_quarantine_port
    ):
        """Test inspecting quarantine with records."""
        now = datetime.now(UTC)
        mock_quarantine_port.inspect.return_value = [
            {
                "error_code": "DQ_MISSING_FIELD",
                "payload": {"id": 1},
                "bronze_batch_id": "batch-1",
                "ingestion_ts": now,
                "metadata": {},
            },
            {
                "error_code": "DQ_INVALID_SMILES",
                "payload": {"id": 2},
                "bronze_batch_id": "batch-2",
                "ingestion_ts": now,
                "metadata": {"error_details": "Invalid SMILES"},
            },
        ]

        result = await quarantine_service.inspect("pipeline1", limit=100)

        assert len(result) == 2
        assert result[0].error_code == "DQ_MISSING_FIELD"
        assert result[0].payload == {"id": 1}
        assert result[1].error_code == "DQ_INVALID_SMILES"

    @pytest.mark.asyncio
    async def test_inspect_with_error_code_filter(
        self, quarantine_service, mock_quarantine_port
    ):
        """Test inspecting quarantine with error code filter."""
        mock_quarantine_port.inspect.return_value = []

        await quarantine_service.inspect(
            "pipeline1", limit=10, error_code="DQ_MISSING_FIELD"
        )

        mock_quarantine_port.inspect.assert_called_once_with(
            pipeline="pipeline1",
            limit=10,
            error_code="DQ_MISSING_FIELD",
        )


@pytest.mark.unit
class TestQuarantineServiceGetStats:
    """Test QuarantineService.get_stats method."""

    @pytest.mark.asyncio
    async def test_get_stats(self, quarantine_service, mock_quarantine_port):
        """Test getting quarantine statistics."""
        mock_quarantine_port.get_stats.return_value = {
            "total_count": 100,
            "by_error_code": {
                "DQ_MISSING_FIELD": 60,
                "DQ_INVALID_SMILES": 40,
            },
        }

        result = await quarantine_service.get_stats("pipeline1")

        assert result["total_count"] == 100
        assert result["by_error_code"]["DQ_MISSING_FIELD"] == 60
        mock_quarantine_port.get_stats.assert_called_once_with("pipeline1")


@pytest.mark.unit
class TestQuarantineServiceReplay:
    """Test QuarantineService.replay method."""

    @pytest.mark.asyncio
    async def test_replay_returns_stats(
        self, quarantine_service, mock_quarantine_port
    ):
        """Test replay returns statistics (not yet implemented)."""
        batch_id = uuid4()
        mock_quarantine_port.inspect.return_value = [
            {"bronze_batch_id": str(batch_id), "payload": {"id": 1}},
            {"bronze_batch_id": str(batch_id), "payload": {"id": 2}},
        ]

        result = await quarantine_service.replay("pipeline1", batch_id)

        # Replay is not fully implemented, should return failure stats
        assert isinstance(result, ReplayResult)
        assert result.batch_id == str(batch_id)
        assert result.records_replayed == 2
        assert result.records_failed == 2  # All failed since not implemented


@pytest.mark.unit
class TestQuarantineServicePurge:
    """Test QuarantineService.purge method."""

    @pytest.mark.asyncio
    async def test_purge_returns_stats(
        self, quarantine_service, mock_quarantine_port
    ):
        """Test purge returns statistics (not yet implemented)."""
        mock_quarantine_port.inspect.return_value = []

        result = await quarantine_service.purge("pipeline1", older_than_days=30)

        # Purge is not fully implemented
        assert isinstance(result, PurgeResult)
        assert result.records_purged == 0


@pytest.mark.unit
class TestQuarantineServiceAclose:
    """Test QuarantineService.aclose method."""

    @pytest.mark.asyncio
    async def test_aclose(self, quarantine_service, mock_quarantine_port):
        """Test closing the service."""
        await quarantine_service.aclose()

        mock_quarantine_port.aclose.assert_called_once()
