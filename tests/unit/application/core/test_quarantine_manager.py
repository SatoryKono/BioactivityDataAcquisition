"""Unit tests for QuarantineManagerService bulk paths."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.quarantine_manager import QuarantineManagerService
from bioetl.domain.types import BatchID, ErrorType


@pytest.fixture
def quarantine_port() -> MagicMock:
    """Create a mock quarantine port."""
    port = MagicMock()
    port.write = AsyncMock()
    port.write_many = AsyncMock()
    return port


@pytest.fixture
def metrics() -> MagicMock:
    """Create a mock metrics port."""
    return MagicMock()


@pytest.mark.unit
class TestQuarantineManagerBulkWrites:
    """Tests for batch quarantine helpers."""

    @pytest.mark.asyncio
    async def test_quarantine_filtered_records_batches_writes_and_metrics(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        manager = QuarantineManagerService(
            quarantine_port=quarantine_port,
            pipeline_name="chembl_activity",
            metrics=metrics,
        )
        batch_id = BatchID(uuid4())
        ingestion_ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)

        await manager.quarantine_filtered_records(
            [
                ({"activity_id": "1"}, "filtered"),
                ({"activity_id": "2"}, "filtered"),
            ],
            batch_id,
            ingestion_ts=ingestion_ts,
        )

        quarantine_port.write_many.assert_awaited_once()
        metrics.inc_quarantine_records.assert_called_once_with(
            pipeline="chembl_activity",
            reason="FILTERED_OUT_SILVER",
            count=2,
        )

    @pytest.mark.asyncio
    async def test_quarantine_records_aggregates_metrics_by_error_type(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        manager = QuarantineManagerService(
            quarantine_port=quarantine_port,
            pipeline_name="chembl_activity",
            metrics=metrics,
        )
        batch_id = BatchID(uuid4())
        ingestion_ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)

        await manager.quarantine_records(
            [
                ({"activity_id": "1"}, ErrorType.INVALID_DATA, "bad"),
                ({"activity_id": "2"}, ErrorType.INVALID_DATA, "bad"),
                ({"activity_id": "3"}, ErrorType.MISSING_REQUIRED_FIELD, "missing"),
            ],
            batch_id,
            ingestion_ts=ingestion_ts,
        )

        quarantine_port.write_many.assert_awaited_once()
        metrics.inc_quarantine_records.assert_any_call(
            pipeline="chembl_activity",
            reason=ErrorType.INVALID_DATA.value,
            count=2,
        )
        metrics.inc_quarantine_records.assert_any_call(
            pipeline="chembl_activity",
            reason=ErrorType.MISSING_REQUIRED_FIELD.value,
            count=1,
        )
