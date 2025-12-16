"""Unit tests for the storage exception hierarchy."""

from unittest.mock import MagicMock, patch

import pytest
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.exceptions import (
    BucketNotFoundError,
    MergeConflictError,
    SchemaValidationError,
    UploadError,
)
from bioetl.infrastructure.storage.exceptions import (
    TableNotFoundError as CustomTableNotFoundError,
)
from botocore.exceptions import ClientError
from deltalake.exceptions import DeltaError, SchemaMismatchError, TableNotFoundError
from pyarrow import ArrowTypeError


@pytest.fixture
def mock_s3_client():
    """Fixture for a mocked boto3 S3 client."""
    return MagicMock()


@pytest.fixture
def bronze_writer(mock_s3_client):
    """Fixture for a BronzeWriter with a mocked S3 client."""
    with patch(
        "bioetl.infrastructure.storage.s3_pool.S3ClientPool.get_client"
    ) as mock_get_client:
        mock_get_client.return_value = mock_s3_client
        return BronzeWriter(bucket="test-bucket")


class TestBronzeWriterExceptions:
    """Tests for exception handling in BronzeWriter."""

    def test_write_bronze_raises_bucket_not_found(self, bronze_writer, mock_s3_client):
        """Test that BucketNotFoundError is raised for 'NoSuchBucket' error."""
        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket"}}, "PutObject"
        )
        with pytest.raises(BucketNotFoundError):
            bronze_writer.write_bronze(iter([b"{}"]), "p", "e", MagicMock(), "b")

    def test_write_bronze_raises_upload_error(self, bronze_writer, mock_s3_client):
        """Test that UploadError is raised for other client errors."""
        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "PutObject"
        )
        with pytest.raises(UploadError):
            bronze_writer.write_bronze(iter([b"{}"]), "p", "e", MagicMock(), "b")


@pytest.fixture
def delta_writer():
    """Fixture for a DeltaWriter."""
    return DeltaWriter(base_path="/fake/path")


class TestDeltaWriterExceptions:
    """Tests for exception handling in DeltaWriter."""

    @pytest.fixture
    def valid_record(self):
        """Valid test record with all required metadata fields."""
        return {
            "id": 1,
            "_run_id": "test-run-id",
            "_run_type": "incremental",
            "_source_batch_id": "batch-123",
            "_ingestion_ts": "2024-01-01T00:00:00Z",
        }

    @patch("deltalake.DeltaTable")
    def test_write_silver_raises_schema_validation_error_on_merge(
        self, mock_delta_table, valid_record
    ):
        """Test that SchemaValidationError is raised on merge."""
        mock_delta_table.side_effect = SchemaMismatchError("Invalid schema")
        writer = DeltaWriter(base_path="/fake/path")
        with pytest.raises(SchemaValidationError):
            writer.write_silver("test.table", [valid_record], ["id"])

    @patch("deltalake.DeltaTable")
    def test_write_silver_raises_merge_conflict_error(
        self, mock_delta_table, valid_record
    ):
        """Test that MergeConflictError is raised."""
        mock_delta_table.return_value.merge.side_effect = DeltaError("Merge-conflict")
        writer = DeltaWriter(base_path="/fake/path")
        with pytest.raises(MergeConflictError):
            writer.write_silver("test.table", [valid_record], ["id"])

    @patch("deltalake.write_deltalake")
    @patch("deltalake.DeltaTable", side_effect=TableNotFoundError)
    def test_write_silver_raises_schema_error_on_create(
        self, _mock_delta_table, mock_write_deltalake, valid_record
    ):
        """Test SchemaValidationError on table creation."""
        mock_write_deltalake.side_effect = ArrowTypeError("Arrow type error")
        writer = DeltaWriter(base_path="/fake/path")
        with pytest.raises(SchemaValidationError):
            writer.write_silver("test.table", [valid_record], ["id"])

    def test_vacuum_raises_table_not_found(self):
        """Test that vacuum raises CustomTableNotFoundError."""
        with patch("deltalake.DeltaTable", side_effect=TableNotFoundError):
            writer = DeltaWriter(base_path="/fake/path")
            with pytest.raises(CustomTableNotFoundError):
                writer.vacuum("test.table")
