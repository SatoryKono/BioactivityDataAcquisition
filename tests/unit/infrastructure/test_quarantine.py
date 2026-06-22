"""Unit tests for quarantine."""

from __future__ import annotations

from tests.helpers.synthetic_paths import synthetic_test_root
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID

import pytest

from bioetl.domain.types import BatchID
from bioetl.infrastructure.quarantine.unified import UnifiedQuarantineAdapter

# Fixed timestamp for test reproducibility
TEST_INGESTION_TS = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
TEST_ROOT = synthetic_test_root("bioetl-quarantine")
QUARANTINE_ROOT = str(TEST_ROOT / "quarantine")


def _extract_record_from_call(mock_call) -> dict:
    """Extract the first record from a write_deltalake mock call.

    The data is passed as a RecordBatchReader, so we need to read it
    and convert to a dict.
    """
    call_kwargs = mock_call.call_args.kwargs
    data = call_kwargs["data"]
    # data is a RecordBatchReader
    table = data.read_all()
    return table.to_pylist()[0]


@pytest.fixture
def mock_deltalake():
    """Fixture for mocking deltalake functions."""
    with patch(
        "bioetl.infrastructure.quarantine.unified.write_deltalake"
    ) as mock_write_deltalake:
        yield mock_write_deltalake


@pytest.mark.unit
class TestUnifiedQuarantine:
    """Test UnifiedQuarantineAdapter functionality."""

    def test_unified_quarantine_initialization(self):
        """Test UnifiedQuarantineAdapter can be initialized."""
        quarantine = UnifiedQuarantineAdapter(base_path=QUARANTINE_ROOT)
        assert quarantine.base_path == QUARANTINE_ROOT

    @pytest.mark.asyncio
    async def test_write_calls_write_deltalake(self, mock_deltalake):
        """Test that write calls write_deltalake with correct data."""
        quarantine = UnifiedQuarantineAdapter(base_path=QUARANTINE_ROOT)
        pipeline = "test_pipeline"
        error_code = "INVALID_DATA"
        payload = {"id": 1, "value": "a"}
        bronze_batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        error_details = {"message": "Invalid value"}

        await quarantine.write(
            pipeline=pipeline,
            error_code=error_code,
            payload=payload,
            bronze_batch_id=bronze_batch_id,
            metadata={"error_details": error_details},
            ingestion_ts=TEST_INGESTION_TS,
        )

        mock_deltalake.assert_called_once()
        _args, kwargs = mock_deltalake.call_args
        assert kwargs["mode"] == "append"
        # Data is passed as a RecordBatchReader
        record = _extract_record_from_call(mock_deltalake)
        assert record["pipeline"] == pipeline
        assert record["error_code"] == error_code
        # Compact JSON format (no spaces) per centralized serialization
        assert record["payload"] == '{"id":1,"value":"a"}'
        assert record["bronze_batch_id"] == str(bronze_batch_id)
        assert record["error_details"] == '{"message":"Invalid value"}'
        assert record["metadata"] == '{"error_details":{"message":"Invalid value"}}'

    async def test_payload_truncation(self, mock_deltalake):
        """Test that large payloads are truncated at 64KB."""
        quarantine = UnifiedQuarantineAdapter(base_path=QUARANTINE_ROOT)
        # Create a payload larger than 64KB
        large_value = "a" * (70 * 1024)  # 70KB
        payload = {"key": large_value}

        await quarantine.write(
            pipeline="test",
            error_code="INVALID_DATA",
            payload=payload,
            bronze_batch_id=BatchID(UUID("12345678-1234-5678-1234-567812345678")),
            ingestion_ts=TEST_INGESTION_TS,
        )

        mock_deltalake.assert_called_once()
        record = _extract_record_from_call(mock_deltalake)
        # Payload should be truncated to MAX_PAYLOAD_SIZE (64KB)
        assert len(record["payload"]) <= UnifiedQuarantineAdapter.MAX_PAYLOAD_SIZE
        assert record["payload_truncated"] is True
