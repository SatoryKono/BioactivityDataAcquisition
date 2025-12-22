"""Unit tests for the storage exception hierarchy."""

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from botocore.exceptions import ClientError
from deltalake.exceptions import DeltaError, SchemaMismatchError, TableNotFoundError
from pyarrow import ArrowTypeError

from bioetl.domain.exceptions import (
    BucketNotFoundError,
    MergeConflictError,
    SchemaViolationError,
    UploadError,
)
from bioetl.domain.exceptions import (
    TableNotFoundError as CustomTableNotFoundError,
)
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter

# Default test run metadata
TEST_RUN_ID = RunID(UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))
TEST_RUN_TYPE = RunType.INCREMENTAL


def make_sync_executor(loop: asyncio.AbstractEventLoop):
    """Create a run_in_executor replacement that returns awaitable sync results."""

    async def sync_executor(_, fn, *args):
        return fn(*args)

    return sync_executor


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
        writer = BronzeWriter(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )
        # Inject the mock client directly to ensure it's used during tests
        writer.s3_client = mock_s3_client
        yield writer


class TestBronzeWriterExceptions:
    """Tests for exception handling in BronzeWriter."""

    @pytest.mark.asyncio
    async def test_write_bronze_raises_bucket_not_found(
        self, bronze_writer, mock_s3_client
    ):
        """Test that BucketNotFoundError is raised for 'NoSuchBucket' error."""
        # Make run_in_executor execute synchronously for testing
        bronze_writer.loop = asyncio.get_event_loop()
        bronze_writer.loop.run_in_executor = make_sync_executor(bronze_writer.loop)

        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket"}}, "PutObject"
        )
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))
        with pytest.raises(BucketNotFoundError):
            await bronze_writer.write_bronze(
                iter([b"{}"]),
                "p",
                "e",
                datetime.now(),
                batch_id,
                run_id=run_id,
                run_type=RunType.INCREMENTAL,
            )

    @pytest.mark.asyncio
    async def test_write_bronze_raises_upload_error(
        self, bronze_writer, mock_s3_client
    ):
        """Test that UploadError is raised for other client errors."""
        # Make run_in_executor execute synchronously for testing
        bronze_writer.loop = asyncio.get_event_loop()
        bronze_writer.loop.run_in_executor = make_sync_executor(bronze_writer.loop)

        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "PutObject"
        )
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))
        with pytest.raises(UploadError):
            await bronze_writer.write_bronze(
                iter([b"{}"]),
                "p",
                "e",
                datetime.now(),
                batch_id,
                run_id=run_id,
                run_type=RunType.INCREMENTAL,
            )


@pytest.fixture
def delta_writer():
    """Fixture for a DeltaWriter."""
    return DeltaWriter(base_path="/fake/path")


@pytest.fixture
def valid_record():
    """Valid test record with all required metadata fields."""
    return {
        "id": 1,
        "_run_id": "test-run-id",
        "_run_type": "incremental",
        "_source_batch_id": "batch-123",
        "_ingestion_ts": "2024-01-01T00:00:00Z",
    }


class TestDeltaWriterExceptions:
    """Tests for exception handling in DeltaWriter."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_write_silver_raises_schema_violation_error_on_merge(
        self, mock_delta_table, valid_record
    ):
        """Test that SchemaViolationError is raised on merge."""
        mock_delta_table.side_effect = SchemaMismatchError("Invalid schema")
        writer = DeltaWriter(base_path="/fake/path")
        # Make run_in_executor execute synchronously for testing
        writer.loop = asyncio.get_event_loop()
        writer.loop.run_in_executor = make_sync_executor(writer.loop)

        import pyarrow as pa

        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        with pytest.raises(SchemaViolationError):
            await writer.write_silver(
                "test.table", [valid_record], ["id"], schema=schema
            )

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_write_silver_raises_merge_conflict_error(
        self, mock_delta_table, valid_record
    ):
        """Test that MergeConflictError is raised."""
        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_merge = MagicMock()
        mock_table_instance.merge.return_value = mock_merge
        mock_merge.when_matched_update_all.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge
        mock_merge.execute.side_effect = DeltaError("Merge-conflict")

        writer = DeltaWriter(base_path="/fake/path")
        # Make run_in_executor execute synchronously for testing
        writer.loop = asyncio.get_event_loop()
        writer.loop.run_in_executor = make_sync_executor(writer.loop)

        import pyarrow as pa

        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        with pytest.raises(MergeConflictError):
            await writer.write_silver(
                "test.table", [valid_record], ["id"], schema=schema
            )

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.write_deltalake")
    @patch(
        "bioetl.infrastructure.storage.delta_writer.DeltaTable",
        side_effect=TableNotFoundError,
    )
    async def test_write_silver_raises_schema_error_on_create(
        self, _mock_delta_table, mock_write_deltalake, valid_record
    ):
        """Test SchemaViolationError on table creation."""
        mock_write_deltalake.side_effect = ArrowTypeError("Arrow type error")
        writer = DeltaWriter(base_path="/fake/path")
        # Make run_in_executor execute synchronously for testing
        writer.loop = asyncio.get_event_loop()
        writer.loop.run_in_executor = make_sync_executor(writer.loop)

        import pyarrow as pa

        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        with pytest.raises(SchemaViolationError):
            await writer.write_silver(
                "test.table", [valid_record], ["id"], schema=schema
            )

    @pytest.mark.asyncio
    async def test_vacuum_raises_table_not_found(self):
        """Test that vacuum raises CustomTableNotFoundError."""
        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            side_effect=TableNotFoundError,
        ):
            writer = DeltaWriter(base_path="/fake/path")
            # Make run_in_executor execute synchronously for testing
            writer.loop = asyncio.get_event_loop()
            writer.loop.run_in_executor = make_sync_executor(writer.loop)

            with pytest.raises(CustomTableNotFoundError):
                await writer.vacuum("test.table")
