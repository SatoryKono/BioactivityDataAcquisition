"""Unit tests for storage writers."""

import asyncio
import io
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
import zstandard as zstd

from bioetl.domain.types import BatchID
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter


def make_sync_executor(loop: asyncio.AbstractEventLoop):
    """Create a run_in_executor replacement that returns awaitable sync results."""
    async def sync_executor(_, fn, *args):
        return fn(*args)
    return sync_executor


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

    @pytest.mark.asyncio
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
        )

        mock_s3_client.put_object.assert_called_once()
        _args, kwargs = mock_s3_client.put_object.call_args
        assert kwargs["Bucket"] == "test-bucket"
        # Check key contains expected parts (new path format: {provider}/{entity}/batch_{date}_{id}.jsonl.zst)
        expected_key = "test_provider/test_entity/batch_2023-01-01_12345678-1234-5678-1234-567812345678.jsonl.zst"
        assert kwargs["Key"] == expected_key

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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
            )


@pytest.mark.unit
class TestBronzeWriterLocal:
    """Tests for BronzeWriter in local mode."""

    @pytest.mark.asyncio
    async def test_write_bronze_local_creates_file(self, tmp_path):
        """Test write_bronze creates file in local mode."""
        writer = BronzeWriter(bucket=str(tmp_path))
        writer.loop = asyncio.get_event_loop()
        writer.loop.run_in_executor = make_sync_executor(writer.loop)

        records = [b'{"id": 1, "data": "test"}\n']
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        date = datetime(2023, 1, 1)

        path = await writer.write_bronze(
            records=iter(records),
            provider="test_provider",
            entity="test_entity",
            date=date,
            batch_id=batch_id,
        )

        expected_file = tmp_path / path
        assert expected_file.exists()

    @pytest.mark.asyncio
    async def test_write_bronze_local_compresses_data(self, tmp_path):
        """Test write_bronze compresses data in local mode."""
        writer = BronzeWriter(bucket=str(tmp_path))
        writer.loop = asyncio.get_event_loop()
        writer.loop.run_in_executor = make_sync_executor(writer.loop)

        records = [b'{"id": 1, "data": "test"}\n']
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        date = datetime(2023, 1, 1)

        path = await writer.write_bronze(
            records=iter(records),
            provider="test_provider",
            entity="test_entity",
            date=date,
            batch_id=batch_id,
        )

        file_path = tmp_path / path
        with open(file_path, "rb") as f:
            compressed_data = f.read()

        # Verify zstd magic bytes
        assert compressed_data.startswith(b"\x28\xb5\x2f\xfd")

    @pytest.mark.asyncio
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

        # Create directory structure
        bronze_dir = tmp_path / "bronze" / "v1" / "test_provider" / "test_entity" / "2023-01-01"
        bronze_dir.mkdir(parents=True)
        test_file = bronze_dir / "batch_test.jsonl.zst"
        test_file.write_bytes(compressed)

        writer = BronzeWriter(bucket=str(tmp_path))
        writer.loop = asyncio.get_event_loop()
        writer.loop.run_in_executor = make_sync_executor(writer.loop)

        # Read it back
        read_records = []
        async for record in writer.read_bronze("bronze/v1/test_provider/test_entity/2023-01-01/batch_test.jsonl.zst"):
            read_records.append(record)

        assert len(read_records) == 2
        assert read_records[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_list_batches_local(self, tmp_path):
        """Test list_batches in local mode."""
        writer = BronzeWriter(bucket=str(tmp_path))
        writer.loop = asyncio.get_event_loop()
        writer.loop.run_in_executor = make_sync_executor(writer.loop)

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
            )

        batches = await writer.list_batches("test_provider", "test_entity", date)

        assert len(batches) == 2
        assert all(b.endswith(".jsonl.zst") for b in batches)

    @pytest.mark.asyncio
    async def test_list_batches_local_nonexistent(self, tmp_path):
        """Test list_batches returns empty for nonexistent path."""
        writer = BronzeWriter(bucket=str(tmp_path))
        writer.loop = asyncio.get_event_loop()
        writer.loop.run_in_executor = make_sync_executor(writer.loop)

        batches = await writer.list_batches("nonexistent", "entity", datetime.now())

        assert batches == []


@pytest.mark.unit
class TestDeltaWriter:
    """Test DeltaWriter functionality."""

    def test_delta_writer_initialization(self):
        """Test DeltaWriter can be initialized."""
        writer = DeltaWriter(base_path="/tmp/delta")
        assert writer.base_path == "/tmp/delta"

    @pytest.mark.asyncio
    async def test_write_silver_creates_new_table(self, mock_delta_writer):
        """Test write_silver creates table if not exists."""
        from deltalake.exceptions import TableNotFoundError

        mock_delta_table, mock_write_deltalake = mock_delta_writer
        mock_delta_table.side_effect = TableNotFoundError("Not found")

        writer = DeltaWriter(base_path="/tmp/delta")
        # Make run_in_executor execute synchronously for testing
        writer.loop = asyncio.get_event_loop()
        writer.loop.run_in_executor = make_sync_executor(writer.loop)

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

        await writer.write_silver(
            table_name="test_table", records=records, primary_keys=["id"]
        )

        mock_write_deltalake.assert_called_once()

    @pytest.mark.asyncio
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
        # Make run_in_executor execute synchronously for testing
        writer.loop = asyncio.get_event_loop()
        writer.loop.run_in_executor = make_sync_executor(writer.loop)

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

        await writer.write_silver(
            table_name="test_table", records=records, primary_keys=["id"]
        )

        mock_table_instance.merge.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("mock_delta_writer")
    async def test_write_silver_empty_records_raises_error(self):
        writer = DeltaWriter(base_path="/tmp/delta")
        # Make run_in_executor execute synchronously for testing
        writer.loop = asyncio.get_event_loop()
        writer.loop.run_in_executor = make_sync_executor(writer.loop)

        with pytest.raises(ValueError, match="No records to write"):
            await writer.write_silver(
                table_name="test_table", records=[], primary_keys=["id"]
            )
