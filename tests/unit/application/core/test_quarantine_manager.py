"""Unit tests for QuarantineManagerService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    FilteredQuarantineEntry,
    QuarantineManagerService,
)
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

    @pytest.mark.asyncio
    async def test_quarantine_record_single_writes_and_increments_metric(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        """Single-record quarantine writes to port and increments metrics."""
        manager = QuarantineManagerService(
            quarantine_port=quarantine_port,
            pipeline_name="chembl_activity",
            metrics=metrics,
        )
        batch_id = BatchID(uuid4())
        ingestion_ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)

        await manager.quarantine_record(
            record={"activity_id": "1"},
            error_type=ErrorType.INVALID_DATA,
            batch_id=batch_id,
            error_details="bad value",
            ingestion_ts=ingestion_ts,
        )

        quarantine_port.write.assert_awaited_once()
        metrics.inc_quarantine_records.assert_called_once_with(
            pipeline="chembl_activity",
            reason=ErrorType.INVALID_DATA.value,
        )

    @pytest.mark.asyncio
    async def test_quarantine_records_empty_list_is_noop(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        """Empty DQ record list should not call write_many."""
        manager = QuarantineManagerService(
            quarantine_port=quarantine_port,
            pipeline_name="chembl_activity",
            metrics=metrics,
        )
        await manager.quarantine_records(
            [], BatchID(uuid4()), ingestion_ts=datetime.now(UTC)
        )
        quarantine_port.write_many.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_quarantine_filtered_records_empty_list_is_noop(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        """Empty filtered record list should not call write_many."""
        manager = QuarantineManagerService(
            quarantine_port=quarantine_port,
            pipeline_name="chembl_activity",
            metrics=metrics,
        )
        await manager.quarantine_filtered_records(
            [], BatchID(uuid4()), ingestion_ts=datetime.now(UTC)
        )
        quarantine_port.write_many.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_quarantine_record_without_metrics_does_not_fail(
        self,
        quarantine_port: MagicMock,
    ) -> None:
        """Single-record quarantine without metrics port should succeed."""
        manager = QuarantineManagerService(
            quarantine_port=quarantine_port,
            pipeline_name="test",
            metrics=None,
        )
        await manager.quarantine_record(
            record={"id": "1"},
            error_type=ErrorType.INVALID_DATA,
            batch_id=BatchID(uuid4()),
            error_details="bad",
            ingestion_ts=datetime.now(UTC),
        )
        quarantine_port.write.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_namedtuple_entries_unpack_correctly_in_bulk_write(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        """NamedTuple entries should unpack correctly in quarantine_records."""
        manager = QuarantineManagerService(
            quarantine_port=quarantine_port,
            pipeline_name="test",
            metrics=metrics,
        )
        entries = [
            DQQuarantineEntry(
                record={"id": "1"},
                error_type=ErrorType.INVALID_DATA,
                error_details="bad",
            ),
        ]
        await manager.quarantine_records(
            entries, BatchID(uuid4()), ingestion_ts=datetime.now(UTC)
        )
        quarantine_port.write_many.assert_awaited_once()
        request = quarantine_port.write_many.call_args[0][0][0]
        assert request["error_code"] == ErrorType.INVALID_DATA.value
        assert request["payload"] == {"id": "1"}
