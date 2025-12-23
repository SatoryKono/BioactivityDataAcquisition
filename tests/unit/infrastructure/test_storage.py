"""Unit tests for storage writers."""

import io
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
import zstandard as zstd

from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter

# Default test run metadata
TEST_RUN_ID = RunID(UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))
TEST_RUN_TYPE = RunType.INCREMENTAL


@pytest.fixture
def mock_s3_client():
    """Fixture for a mocked S3 client."""
    # Patch S3ClientPool.get_client since BronzeWriter now uses the pool
    with patch(
        "bioetl.infrastructure.storage.s3_pool.S3ClientPool.get_client"
    ) as mock_get_client:
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        yield mock_s3


@pytest.fixture
def mock_delta_writer():
    """Fixture for mocking delta_writer module."""
    with (
        patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable"
        ) as mock_delta_table,
        patch(
            "bioetl.infrastructure.storage.delta_writer.write_deltalake"
        ) as mock_write_deltalake,
    ):
        yield mock_delta_table, mock_write_deltalake


@pytest.mark.unit
class TestBronzeWriter:
    """Test BronzeWriter functionality."""

    @pytest.mark.usefixtures("mock_s3_client")
    def test_bronze_writer_initialization(self):
        """Test BronzeWriter can be initialized."""
        writer = BronzeWriter(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )
        assert writer.bucket == "test-bucket"

    async def test_write_bronze_generates_correct_key(self, mock_s3_client):
        """Test that write_bronze generates the correct S3 key."""
        writer = BronzeWriter(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )

        records = [b'{"id": 1}\n']
        provider = "test_provider"
        entity = "test_entity"
        date = datetime(2023, 1, 1)
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))

        await writer.write_bronze(
            records=iter(records),
            provider=provider,
            entity=entity,
            date=date,
            batch_id=batch_id,
            run_id=TEST_RUN_ID,
            run_type=TEST_RUN_TYPE,
        )

        mock_s3_client.put_object.assert_called_once()
        _args, kwargs = mock_s3_client.put_object.call_args
        assert kwargs["Bucket"] == "test-bucket"
        # Check key contains expected parts (new path format: bronze/v1/{provider}/{entity}/{date}/batch_{id}.jsonl.zst)
        expected_key = "bronze/v1/test_provider/test_entity/2023-01-01/batch_12345678-1234-5678-1234-567812345678.jsonl.zst"
        assert kwargs["Key"] == expected_key

    async def test_write_bronze_compresses_with_zstd(self, mock_s3_client):
        """REQ-DATA-001: Test that data is compressed with zstandard."""
        writer = BronzeWriter(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )

        records = [b'{"id": 1, "data": "test"}\n']

        await writer.write_bronze(
            records=iter(records),
            provider="test",
            entity="test",
            date=datetime.now(),
            batch_id=BatchID(UUID("12345678-1234-5678-1234-567812345678")),
            run_id=TEST_RUN_ID,
            run_type=TEST_RUN_TYPE,
        )

        mock_s3_client.put_object.assert_called_once()
        _args, kwargs = mock_s3_client.put_object.call_args

        # The Body should be zstd compressed data
        compressed_data = kwargs["Body"]

        # Zstandard frames start with magic bytes 0x28, 0xB5, 0x2F, 0xFD (little-endian)
        assert compressed_data.startswith(b"\x28\xb5\x2f\xfd")

        # Decompress to verify content using stream reader
        decompressor = zstd.ZstdDecompressor()
        with decompressor.stream_reader(io.BytesIO(compressed_data)) as reader:
            decompressed_data = reader.read()

        assert decompressed_data == b'{"id": 1, "data": "test"}\n'

    async def test_write_bronze_with_no_records(self, mock_s3_client):
        """Test that write_bronze raises error if there are no records."""
        writer = BronzeWriter(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )

        records = []
        provider = "test_provider"
        entity = "test_entity"
        date = datetime(2023, 1, 1)
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))

        with pytest.raises(ValueError, match="No records"):
            await writer.write_bronze(
                records=iter(records),
                provider=provider,
                entity=entity,
                date=date,
                batch_id=batch_id,
                run_id=TEST_RUN_ID,
                run_type=TEST_RUN_TYPE,
            )

    async def test_write_bronze_save_json_copy(self, mock_s3_client):
        """Test that write_bronze saves JSON copy if save_json is True."""
        writer = BronzeWriter(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
            save_json=True,
        )

        records = [b'{"id": 1}\n']
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        date = datetime(2023, 1, 1)

        await writer.write_bronze(
            records=iter(records),
            provider="test_provider",
            entity="test_entity",
            date=date,
            batch_id=batch_id,
            run_id=TEST_RUN_ID,
            run_type=TEST_RUN_TYPE,
        )

        # Should call put_object twice: once for zstd, once for json
        assert mock_s3_client.put_object.call_count == 2

        calls = mock_s3_client.put_object.call_args_list

        # Verify JSON call
        json_call = next(c for c in calls if c[1]["Key"].endswith(".jsonl"))
        _args, kwargs = json_call
        assert kwargs["Bucket"] == "test-bucket"
        assert kwargs["Bucket"] == "test-bucket"
        assert (
            kwargs["Key"]
            == "json/test_provider/test_entity/batch_2023-01-01_12345678-1234-5678-1234-567812345678.jsonl"
        )
        assert kwargs["Body"] == b'{"id": 1}\n'
        assert kwargs["ContentType"] == "application/x-ndjson"

    async def test_write_bronze_save_json_copy_failure_logs_warning(
        self, mock_s3_client
    ):
        """Test that JSON copy failure logs warning but doesn't raise."""
        from botocore.exceptions import ClientError

        mock_logger = MagicMock()

        writer = BronzeWriter(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
            save_json=True,
            logger=mock_logger,
        )

        # First call (compressed) succeeds, second call (json) fails
        mock_s3_client.put_object.side_effect = [
            None,
            ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject"),
        ]

        records = [b'{"id": 1}\n']
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        date = datetime(2023, 1, 1)

        await writer.write_bronze(
            records=iter(records),
            provider="test_provider",
            entity="test_entity",
            date=date,
            batch_id=batch_id,
            run_id=TEST_RUN_ID,
            run_type=TEST_RUN_TYPE,
        )

        # Should log warning
        mock_logger.warning.assert_called_once()
        assert "json_copy_write_failed" in str(mock_logger.warning.call_args)


@pytest.mark.unit
class TestBronzeWriterLocal:
    """Tests for BronzeWriter in local mode."""

    async def test_write_bronze_local_creates_file(self, tmp_path):
        """Test write_bronze creates file in local mode."""
        writer = BronzeWriter(bucket=str(tmp_path))

        records = [b'{"id": 1, "data": "test"}\n']
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        date = datetime(2023, 1, 1)

        path = await writer.write_bronze(
            records=iter(records),
            provider="test_provider",
            entity="test_entity",
            date=date,
            batch_id=batch_id,
            run_id=TEST_RUN_ID,
            run_type=TEST_RUN_TYPE,
        )

        expected_file = tmp_path / path
        assert expected_file.exists()

    async def test_write_bronze_local_compresses_data(self, tmp_path):
        """Test write_bronze compresses data in local mode."""
        writer = BronzeWriter(bucket=str(tmp_path))

        records = [b'{"id": 1, "data": "test"}\n']
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        date = datetime(2023, 1, 1)

        path = await writer.write_bronze(
            records=iter(records),
            provider="test_provider",
            entity="test_entity",
            date=date,
            batch_id=batch_id,
            run_id=TEST_RUN_ID,
            run_type=TEST_RUN_TYPE,
        )

        file_path = tmp_path / path
        with open(file_path, "rb") as f:
            compressed_data = f.read()

        # Verify zstd magic bytes
        assert compressed_data.startswith(b"\x28\xb5\x2f\xfd")

    async def test_read_bronze_local(self, tmp_path):
        """Test read_bronze reads file in local mode."""
        # Create a compressed file manually for deterministic testing
        import json

        import zstandard as zstd

        records_data = [{"id": 1, "data": "test"}, {"id": 2, "data": "test2"}]
        jsonl_data = "\n".join(json.dumps(r) for r in records_data) + "\n"

        # Compress with zstd
        compressor = zstd.ZstdCompressor(level=3)
        compressed = compressor.compress(jsonl_data.encode("utf-8"))

        # Create directory structure (new path format: {provider}/{entity}/batch_*.jsonl.zst)
        bronze_dir = tmp_path / "test_provider" / "test_entity"
        bronze_dir.mkdir(parents=True)
        test_file = bronze_dir / "batch_test.jsonl.zst"
        test_file.write_bytes(compressed)

        writer = BronzeWriter(bucket=str(tmp_path))

        # Read it back
        read_records = []
        async for record in writer.read_bronze(
            "test_provider/test_entity/batch_test.jsonl.zst"
        ):
            read_records.append(record)

        assert len(read_records) == 2
        assert read_records[0]["id"] == 1

    async def test_list_batches_local(self, tmp_path):
        """Test list_batches in local mode."""
        writer = BronzeWriter(bucket=str(tmp_path))

        # Write two batches
        date = datetime(2023, 1, 1)
        for i in range(2):
            batch_id = BatchID(UUID(f"12345678-1234-5678-1234-56781234567{i}"))
            await writer.write_bronze(
                records=iter([b'{"id": 1}\n']),
                provider="test_provider",
                entity="test_entity",
                date=date,
                batch_id=batch_id,
                run_id=TEST_RUN_ID,
                run_type=TEST_RUN_TYPE,
            )

        batches = await writer.list_batches("test_provider", "test_entity", date)

        # In local mode, list_batches glob might need adjustment or the test should expect paths relative to bucket
        # Current implementation returns str(p.relative_to(self.bucket))
        # With new structure, we expect 2 files
        assert len(batches) == 2
        assert all(b.endswith(".jsonl.zst") for b in batches)

    async def test_list_batches_local_nonexistent(self, tmp_path):
        """Test list_batches returns empty for nonexistent path."""
        writer = BronzeWriter(bucket=str(tmp_path))

        batches = await writer.list_batches("nonexistent", "entity", datetime.now())

        assert batches == []


@pytest.mark.unit
class TestDeltaWriter:
    """Test DeltaWriter functionality."""

    def test_delta_writer_initialization(self):
        """Test DeltaWriter can be initialized."""
        writer = DeltaWriter(base_path="/tmp/delta")
        assert writer.base_path == "/tmp/delta"

    async def test_write_silver_creates_new_table(self, mock_delta_writer):
        """Test write_silver creates table if not exists."""
        from deltalake.exceptions import TableNotFoundError

        mock_delta_table, mock_write_deltalake = mock_delta_writer
        mock_delta_table.side_effect = TableNotFoundError("Not found")

        writer = DeltaWriter(base_path="/tmp/delta")

        records = [
            {
                "id": 1,
                "value": "a",
                "_run_id": "test-run",
                "_run_type": "incremental",
                "_source_batch_id": "batch-1",
                "_ingestion_ts": "2024-01-01T00:00:00Z",
            }
        ]

        import pyarrow as pa

        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("value", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        await writer.write_silver(
            table_name="test_table", records=records, primary_keys=["id"], schema=schema
        )

        mock_write_deltalake.assert_called_once()

    async def test_write_silver_merge_existing_table(self, mock_delta_writer):
        """Test write_silver merges into existing table."""
        mock_delta_table, _mock_write_deltalake = mock_delta_writer
        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        # Set up merge chain
        mock_merge = MagicMock()
        mock_table_instance.merge.return_value = mock_merge
        mock_merge.when_matched_update_all.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge

        writer = DeltaWriter(base_path="/tmp/delta")

        records = [
            {
                "id": 1,
                "value": "a",
                "_run_id": "test-run",
                "_run_type": "incremental",
                "_source_batch_id": "batch-1",
                "_ingestion_ts": "2024-01-01T00:00:00Z",
            }
        ]

        import pyarrow as pa

        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("value", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        await writer.write_silver(
            table_name="test_table", records=records, primary_keys=["id"], schema=schema
        )

        mock_table_instance.merge.assert_called_once()

    @pytest.mark.usefixtures("mock_delta_writer")
    async def test_write_silver_empty_records_raises_error(self):
        writer = DeltaWriter(base_path="/tmp/delta")

        with pytest.raises(ValueError, match="No records to write"):
            await writer.write_silver(
                table_name="test_table",
                records=[],
                primary_keys=["id"],
                schema=MagicMock(),
            )


@pytest.mark.unit
class TestGoldWriter:
    """Test GoldWriter functionality."""

    @pytest.fixture
    def mock_gold_writer_deps(self):
        """Fixture for mocking GoldWriter dependencies."""
        with (
            patch(
                "bioetl.infrastructure.storage.gold_writer.DeltaTable"
            ) as mock_delta_table,
            patch(
                "bioetl.infrastructure.storage.gold_writer.write_deltalake"
            ) as mock_write_deltalake,
        ):
            yield mock_delta_table, mock_write_deltalake

    async def test_gold_writer_sorts_columns(self, mock_gold_writer_deps):
        """Test that GoldWriter sorts columns alphabetically in _to_arrow_table."""
        _mock_delta_table, mock_write_deltalake = mock_gold_writer_deps

        writer = GoldWriter(base_path="/tmp/gold")

        # Records with mixed key order
        records = [
            {"b": 2, "a": 1, "c": 3},
            {"c": 30, "b": 20, "a": 10},
        ]

        await writer.write_gold(
            table_name="test_table",
            records=records,
            mode="overwrite",
        )

        # Verify write_deltalake was called
        assert mock_write_deltalake.called

        # Get the arrow table passed to write_deltalake
        call_args = mock_write_deltalake.call_args
        kwargs = call_args.kwargs

        # data might be a RecordBatchReader
        data = kwargs.get("data")
        assert data is not None

        schema = data.schema
        column_names = schema.names

        assert column_names == ["a", "b", "c"], (
            f"Expected sorted columns ['a', 'b', 'c'], got {column_names}"
        )
