"""Unit tests for QuarantineService.

Tests the quarantine administrative service.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.quarantine_service import (
    QuarantineRecord,
    QuarantineService,
)
from bioetl.domain.types import QuarantineRecordStatus


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
    from unittest.mock import AsyncMock

    port = MagicMock()
    port.inspect = AsyncMock(return_value=[])
    port.get_stats = AsyncMock(return_value={})
    port.aclose = AsyncMock()
    # New synchronous methods
    port.replay = MagicMock(return_value=iter([]))
    port.purge = MagicMock(return_value=0)
    port.update_status = MagicMock(return_value=True)
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
    async def test_inspect_with_records(self, quarantine_service, mock_quarantine_port):
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

    def test_replay_returns_records(self, quarantine_service, mock_quarantine_port):
        """Test replay returns records from port."""
        records = [
            {"payload_hash": "hash1", "error_code": "DQ_ERROR"},
            {"payload_hash": "hash2", "error_code": "DQ_ERROR"},
        ]
        mock_quarantine_port.replay.return_value = iter(records)

        result = quarantine_service.replay("pipeline1", max_age_days=7)

        assert len(result) == 2
        assert result[0]["payload_hash"] == "hash1"
        mock_quarantine_port.replay.assert_called_once()

    def test_replay_with_error_code_filter(
        self, quarantine_service, mock_quarantine_port
    ):
        """Test replay with error code filter."""
        mock_quarantine_port.replay.return_value = iter([])

        quarantine_service.replay("pipeline1", error_code="DQ_NETWORK_ERROR")

        call_kwargs = mock_quarantine_port.replay.call_args[1]
        assert call_kwargs["error_code"] == "DQ_NETWORK_ERROR"


@pytest.mark.unit
class TestQuarantineServiceMarkAsReprocessed:
    """Test QuarantineService.mark_as_reprocessed method."""

    def test_mark_as_reprocessed(self, quarantine_service, mock_quarantine_port):
        """Test marking records as reprocessed."""
        records = [
            {"payload_hash": "hash1"},
            {"payload_hash": "hash2"},
        ]

        count = quarantine_service.mark_as_reprocessed(records)

        assert count == 2
        assert mock_quarantine_port.update_status.call_count == 2

    def test_mark_as_reprocessed_skips_missing_hash(
        self, quarantine_service, mock_quarantine_port
    ):
        """Test marking skips records without payload_hash."""
        records = [
            {"payload_hash": "hash1"},
            {"other_field": "value"},  # Missing payload_hash
        ]

        count = quarantine_service.mark_as_reprocessed(records)

        assert count == 1
        assert mock_quarantine_port.update_status.call_count == 1


@pytest.mark.unit
class TestQuarantineServicePurge:
    """Test QuarantineService.purge method."""

    def test_purge_returns_count(self, quarantine_service, mock_quarantine_port):
        """Test purge returns count from port."""
        mock_quarantine_port.purge.return_value = 50

        result = quarantine_service.purge("pipeline1", older_than_days=30)

        assert result == 50
        mock_quarantine_port.purge.assert_called_once()

    def test_purge_with_custom_retention(
        self, quarantine_service, mock_quarantine_port
    ):
        """Test purge with custom retention days."""
        quarantine_service.purge("pipeline1", older_than_days=60)

        call_kwargs = mock_quarantine_port.purge.call_args[1]
        assert call_kwargs["older_than_days"] == 60


@pytest.mark.unit
class TestQuarantineServiceUpdateStatus:
    """Test QuarantineService.update_status method."""

    def test_update_status_success(self, quarantine_service, mock_quarantine_port):
        """Test successful status update."""
        mock_quarantine_port.update_status.return_value = True

        result = quarantine_service.update_status(
            "hash123", QuarantineRecordStatus.IGNORED
        )

        assert result is True
        mock_quarantine_port.update_status.assert_called_once_with(
            "hash123", QuarantineRecordStatus.IGNORED
        )

    def test_update_status_not_found(self, quarantine_service, mock_quarantine_port):
        """Test status update when record not found."""
        mock_quarantine_port.update_status.return_value = False

        result = quarantine_service.update_status(
            "nonexistent", QuarantineRecordStatus.REPROCESSED
        )

        assert result is False


@pytest.mark.unit
class TestQuarantineServiceAclose:
    """Test QuarantineService.aclose method."""

    @pytest.mark.asyncio
    async def test_aclose(self, quarantine_service, mock_quarantine_port):
        """Test closing the service."""
        await quarantine_service.aclose()

        mock_quarantine_port.aclose.assert_called_once()
