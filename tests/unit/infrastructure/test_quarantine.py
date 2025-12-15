"""Unit tests for quarantine."""

from unittest.mock import MagicMock, patch

import pytest
import polars as pl

from bioetl.domain.types import BatchID, ErrorType
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine


@pytest.fixture
def mock_deltalake():
    """Fixture for mocking deltalake functions."""
    with patch("deltalake.write_deltalake") as mock_write_deltalake:
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
        error_code = ErrorType.INVALID_DATA
        payload = {"id": 1, "value": "a"}
        bronze_batch_id = BatchID.from_hex("12345678123456781234567812345678")
        error_details = {"message": "Invalid value"}

        quarantine.write(
            pipeline=pipeline,
            error_code=error_code,
            payload=payload,
            bronze_batch_id=bronze_batch_id,
            error_details=error_details,
        )

        mock_deltalake.assert_called_once()
        args, kwargs = mock_deltalake.call_args
        assert kwargs["mode"] == "append"
        assert isinstance(kwargs["data"], pl.DataFrame)
        df = kwargs["data"]
        assert df["pipeline"][0] == pipeline
        assert df["error_code"][0] == error_code.value
        assert df["payload"][0] == '{"id": 1, "value": "a"}'
        assert df["bronze_batch_id"][0] == str(bronze_batch_id)
        assert df["error_details"][0] == '{"message": "Invalid value"}'

    def test_payload_truncation(self, mock_deltalake):
        """Test that large payloads are truncated."""
        quarantine = UnifiedQuarantine(base_path="/tmp/quarantine", max_payload_size=10)
        payload = {"key": "a" * 20}

        quarantine.write(
            pipeline="test",
            error_code=ErrorType.INVALID_DATA,
            payload=payload,
            bronze_batch_id=BatchID.from_hex("12345678123456781234567812345678"),
            error_details={},
        )

        mock_deltalake.assert_called_once()
        args, kwargs = mock_deltalake.call_args
        df = kwargs["data"]
        assert len(df["payload"][0]) <= 10 + 20  # Allow for some overhead
