"""Unit tests for storage writers."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import polars as pl

from bioetl.domain.types import BatchID
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter


@pytest.fixture
def mock_s3_client():
    """Fixture for a mocked S3 client."""
    with patch("boto3.client") as mock_boto_client:
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        yield mock_s3


@pytest.fixture
def mock_deltalake():
    """Fixture for mocking deltalake functions."""
    with patch("deltalake.DeltaTable") as mock_delta_table, \
         patch("deltalake.write_deltalake") as mock_write_deltalake:
        yield mock_delta_table, mock_write_deltalake


@pytest.mark.unit
class TestBronzeWriter:
    """Test BronzeWriter functionality."""

    def test_bronze_writer_initialization(self):
        """Test BronzeWriter can be initialized."""
        writer = BronzeWriter(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )
        assert writer.bucket == "test-bucket"

    def test_write_bronze_generates_correct_key(self, mock_s3_client):
        """Test that write_bronze generates the correct S3 key."""
        writer = BronzeWriter(bucket="test-bucket")
        records = [b'{"id": 1}\n']
        provider = "test_provider"
        entity = "test_entity"
        date = datetime(2023, 1, 1)
        batch_id = BatchID.from_hex("12345678123456781234567812345678")

        writer.write_bronze(
            records=iter(records),
            provider=provider,
            entity=entity,
            date=date,
            batch_id=batch_id,
        )

        expected_key = "test_provider/test_entity/2023/01/01/12345678-1234-5678-1234-567812345678.jsonl.zst"
        mock_s3_client.upload_fileobj.assert_called_once()
        args, kwargs = mock_s3_client.upload_fileobj.call_args
        assert kwargs["Bucket"] == "test-bucket"
        assert kwargs["Key"] == expected_key

    def test_write_bronze_with_no_records(self, mock_s3_client):
        """Test that write_bronze does nothing if there are no records."""
        writer = BronzeWriter(bucket="test-bucket")
        records = []
        provider = "test_provider"
        entity = "test_entity"
        date = datetime(2023, 1, 1)
        batch_id = BatchID.from_hex("12345678123456781234567812345678")

        writer.write_bronze(
            records=iter(records),
            provider=provider,
            entity=entity,
            date=date,
            batch_id=batch_id,
        )

        mock_s3_client.upload_fileobj.assert_not_called()


@pytest.mark.unit
class TestDeltaWriter:
    """Test DeltaWriter functionality."""

    def test_delta_writer_initialization(self):
        """Test DeltaWriter can be initialized."""
        writer = DeltaWriter(base_path="/tmp/delta")
        assert writer.base_path == "/tmp/delta"

    def test_write_silver_append_mode(self, mock_deltalake):
        """Test write_silver in append mode."""
        mock_delta_table, mock_write_deltalake = mock_deltalake
        writer = DeltaWriter(base_path="/tmp/delta")
        records = [{"id": 1, "value": "a"}]

        writer.write_silver(
            table_name="test_table",
            records=records,
            mode="append"
        )

        mock_write_deltalake.assert_called_once()
        args, kwargs = mock_write_deltalake.call_args
        assert kwargs["mode"] == "append"
        assert isinstance(kwargs["data"], pl.DataFrame)

    def test_write_silver_merge_mode(self, mock_deltalake):
        """Test write_silver in merge mode."""
        mock_delta_table, mock_write_deltalake = mock_deltalake
        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        writer = DeltaWriter(base_path="/tmp/delta")
        records = [{"id": 1, "value": "a"}]

        writer.write_silver(
            table_name="test_table",
            records=records,
            mode="merge",
            primary_keys=["id"]
        )

        mock_table_instance.merge.assert_called_once()

    def test_write_silver_merge_mode_no_keys_raises_error(self, mock_deltalake):
        """Test merge mode without primary keys raises an error."""
        writer = DeltaWriter(base_path="/tmp/delta")
        records = [{"id": 1, "value": "a"}]

        with pytest.raises(ValueError, match="Primary keys must be provided for merge mode"):
            writer.write_silver(
                table_name="test_table",
                records=records,
                mode="merge"
            )


@pytest.mark.unit
class TestGoldWriter:
    """Test GoldWriter functionality."""

    def test_gold_writer_initialization(self):
        """Test GoldWriter can be initialized."""
        writer = GoldWriter(base_path="/tmp/gold")
        assert writer.base_path == "/tmp/gold"

    def test_write_gold_calls_delta_writer(self, mock_deltalake):
        """Test that write_gold calls the underlying DeltaWriter."""
        mock_delta_table, mock_write_deltalake = mock_deltalake
        writer = GoldWriter(base_path="/tmp/gold")
        records = [{"id": 1, "value": "a"}]

        writer.write_gold(
            table_name="gold_table",
            records=records,
            mode="overwrite"
        )

        mock_write_deltalake.assert_called_once()
        args, kwargs = mock_write_deltalake.call_args
        assert kwargs["mode"] == "overwrite"
        assert "gold_table" in args[0]
