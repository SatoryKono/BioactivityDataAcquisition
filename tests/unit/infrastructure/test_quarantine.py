"""Unit tests for quarantine."""

from unittest.mock import patch
from uuid import UUID

import pytest

from bioetl.domain.types import BatchID
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine


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
        "bioetl.infrastructure.quarantine.unified_quarantine.write_deltalake"
    ) as mock_write_deltalake:
        yield mock_write_deltalake


@pytest.mark.unit
class TestUnifiedQuarantine:
    """Test UnifiedQuarantine functionality."""

    def test_unified_quarantine_initialization(self):
        """Test UnifiedQuarantine can be initialized."""
        quarantine = UnifiedQuarantine(base_path="/tmp/quarantine")
        assert quarantine.base_path == "/tmp/quarantine"

    async def test_write_calls_write_deltalake(self, mock_deltalake):
        """Test that write calls write_deltalake with correct data."""
        quarantine = UnifiedQuarantine(base_path="/tmp/quarantine")
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
            error_details=error_details,
        )

        mock_deltalake.assert_called_once()
        _args, kwargs = mock_deltalake.call_args
        assert kwargs["mode"] == "append"
        # Data is passed as a RecordBatchReader
        record = _extract_record_from_call(mock_deltalake)
        assert record["pipeline"] == pipeline
        assert record["error_code"] == error_code
        assert record["payload"] == '{"id": 1, "value": "a"}'
        assert record["bronze_batch_id"] == str(bronze_batch_id)
        assert record["error_details"] == '{"message": "Invalid value"}'

    async def test_payload_truncation(self, mock_deltalake):
        """Test that large payloads are truncated at 64KB."""
        quarantine = UnifiedQuarantine(base_path="/tmp/quarantine")
        # Create a payload larger than 64KB
        large_value = "a" * (70 * 1024)  # 70KB
        payload = {"key": large_value}

        await quarantine.write(
            pipeline="test",
            error_code="INVALID_DATA",
            payload=payload,
            bronze_batch_id=BatchID(UUID("12345678-1234-5678-1234-567812345678")),
            error_details={},
        )

        mock_deltalake.assert_called_once()
        record = _extract_record_from_call(mock_deltalake)
        # Payload should be truncated to MAX_PAYLOAD_SIZE (64KB)
        assert len(record["payload"]) <= UnifiedQuarantine.MAX_PAYLOAD_SIZE
        assert record["payload_truncated"] is True
