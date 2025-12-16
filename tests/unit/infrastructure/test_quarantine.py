"""Unit tests for quarantine."""

from unittest.mock import patch
from uuid import UUID

import pytest

from bioetl.domain.types import BatchID
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine


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

    def test_write_calls_write_deltalake(self, mock_deltalake):
        """Test that write calls write_deltalake with correct data."""
        quarantine = UnifiedQuarantine(base_path="/tmp/quarantine")
        pipeline = "test_pipeline"
        error_code = "INVALID_DATA"
        payload = {"id": 1, "value": "a"}
        bronze_batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        error_details = {"message": "Invalid value"}

        quarantine.write(
            pipeline=pipeline,
            error_code=error_code,
            payload=payload,
            bronze_batch_id=bronze_batch_id,
            error_details=error_details,
        )

        mock_deltalake.assert_called_once()
        _args, kwargs = mock_deltalake.call_args
        assert kwargs["mode"] == "append"
        # Data is passed as a list of dicts
        data = kwargs["data"]
        assert isinstance(data, list)
        assert len(data) == 1
        record = data[0]
        assert record["pipeline"] == pipeline
        assert record["error_code"] == error_code
        assert record["payload"] == '{"id": 1, "value": "a"}'
        assert record["bronze_batch_id"] == str(bronze_batch_id)
        assert record["error_details"] == '{"message": "Invalid value"}'

    def test_payload_truncation(self, mock_deltalake):
        """Test that large payloads are truncated at 64KB."""
        quarantine = UnifiedQuarantine(base_path="/tmp/quarantine")
        # Create a payload larger than 64KB
        large_value = "a" * (70 * 1024)  # 70KB
        payload = {"key": large_value}

        quarantine.write(
            pipeline="test",
            error_code="INVALID_DATA",
            payload=payload,
            bronze_batch_id=BatchID(UUID("12345678-1234-5678-1234-567812345678")),
            error_details={},
        )

        mock_deltalake.assert_called_once()
        _args, kwargs = mock_deltalake.call_args
        data = kwargs["data"]
        record = data[0]
        # Payload should be truncated to MAX_PAYLOAD_SIZE (64KB)
        assert len(record["payload"]) <= UnifiedQuarantine.MAX_PAYLOAD_SIZE
        assert record["payload_truncated"] is True
