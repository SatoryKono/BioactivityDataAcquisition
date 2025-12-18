"""Unit tests for BronzeWriter."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import zstandard as zstd

from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter


@pytest.fixture
def batch_id() -> BatchID:
    """Generate a unique batch ID."""
    return BatchID(uuid4())


@pytest.fixture
def run_id() -> RunID:
    """Generate a unique run ID."""
    return RunID(uuid4())


@pytest.fixture
def run_type() -> RunType:
    """Return default run type."""
    return RunType.INCREMENTAL


@pytest.fixture
def sample_records() -> list[bytes]:
    """Create sample records as JSONL bytes."""
    records = [
        {"id": 1, "name": "test1", "value": 100},
        {"id": 2, "name": "test2", "value": 200},
        {"id": 3, "name": "test3", "value": 300},
    ]
    return [json.dumps(r).encode("utf-8") + b"\n" for r in records]


@pytest.fixture
def temp_dir():
    """Create a temporary directory for local storage tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.mark.unit
class TestBronzeWriterInit:
    """Tests for BronzeWriter initialization."""

    def test_init_local_storage(self, temp_dir: str) -> None:
        """Test initialization for local storage."""
        writer = BronzeWriter(bucket=temp_dir)

        assert writer.bucket == temp_dir
        assert writer.is_local is True
        assert writer.endpoint_url is None
        assert writer.save_json is False

    def test_init_with_save_json(self, temp_dir: str) -> None:
        """Test initialization with JSON saving enabled."""
        writer = BronzeWriter(bucket=temp_dir, save_json=True)

        assert writer.save_json is True
        assert writer.json_path is not None

    def test_init_with_custom_json_path(self, temp_dir: str) -> None:
        """Test initialization with custom JSON path."""
        custom_path = f"{temp_dir}/custom_json"
        writer = BronzeWriter(
            bucket=temp_dir,
            save_json=True,
            json_path=custom_path,
        )

        assert writer.json_path == custom_path

    @patch("bioetl.infrastructure.storage.s3_pool.S3ClientPool")
    def test_init_s3_storage(self, mock_pool: MagicMock) -> None:
        """Test initialization for S3 storage."""
        mock_pool.get_client.return_value = MagicMock()

        writer = BronzeWriter(
            bucket="my-bucket",
            endpoint_url="http://localhost:9000",
            region="us-east-1",
            access_key="access",
            secret_key="secret",
        )

        assert writer.bucket == "my-bucket"
        assert writer.is_local is False
        assert writer.endpoint_url == "http://localhost:9000"
        mock_pool.get_client.assert_called_once()


@pytest.mark.unit
class TestBronzeWriterCompress:
    """Tests for BronzeWriter compression."""

    def test_compress_records(self, temp_dir: str, sample_records: list[bytes]) -> None:
        """Test record compression."""
        writer = BronzeWriter(bucket=temp_dir)

        compressed = writer._compress_records(iter(sample_records))

        assert compressed is not None
        assert len(compressed) > 0

        # Verify we can decompress (use streaming for robustness)
        decompressor = zstd.ZstdDecompressor()
        with decompressor.stream_reader(compressed) as reader:
            decompressed = reader.read()
        expected = b"".join(sample_records)
        assert decompressed == expected

    def test_compress_empty_records_raises(self, temp_dir: str) -> None:
        """Test that empty records raise ValueError."""
        writer = BronzeWriter(bucket=temp_dir)

        with pytest.raises(ValueError, match="No records provided"):
            writer._compress_records(iter([]))

    def test_compress_large_records(self, temp_dir: str) -> None:
        """Test compression with records larger than chunk size."""
        writer = BronzeWriter(bucket=temp_dir)

        # Create large records
        large_record = {"data": "x" * 500_000}
        records = [json.dumps(large_record).encode("utf-8") + b"\n" for _ in range(5)]

        compressed = writer._compress_records(iter(records))

        # Compression should reduce size
        original_size = sum(len(r) for r in records)
        assert len(compressed) < original_size


@pytest.mark.unit
class TestBronzeWriterWriteLocal:
    """Tests for BronzeWriter local write operations."""

    @pytest.mark.asyncio
    async def test_write_bronze_local(
        self,
        temp_dir: str,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test writing Bronze data to local storage."""
        writer = BronzeWriter(bucket=temp_dir)
        date = datetime(2024, 1, 15)

        path = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
        )

        # Verify path format (use as_posix for cross-platform compatibility)
        path_str = path.as_posix()
        assert "bronze/v1/chembl/activity/2024-01-15" in path_str
        assert str(batch_id) in path_str
        assert path_str.endswith(".jsonl.zst")

        # Verify file exists
        full_path = Path(temp_dir) / path
        assert full_path.exists()

        # Verify content (use streaming decompression for robustness)
        with open(full_path, "rb") as f:
            compressed_data = f.read()

        decompressor = zstd.ZstdDecompressor()
        with decompressor.stream_reader(compressed_data) as reader:
            decompressed = reader.read()
        expected = b"".join(sample_records)
        assert decompressed == expected

    @pytest.mark.asyncio
    async def test_write_bronze_with_json_copy(
        self,
        temp_dir: str,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test writing Bronze data with JSON copy."""
        writer = BronzeWriter(bucket=temp_dir, save_json=True)
        date = datetime(2024, 1, 15)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="pubchem",
            entity="compound",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
        )

        # Verify JSON copy exists
        json_path = Path(temp_dir) / "json" / "pubchem" / "compound"
        json_files = list(json_path.glob("*.jsonl"))
        assert len(json_files) == 1

        # Verify JSON content
        with open(json_files[0], "rb") as f:
            content = f.read()
        expected = b"".join(sample_records)
        assert content == expected

    @pytest.mark.asyncio
    async def test_write_bronze_empty_records_raises(
        self,
        temp_dir: str,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test that empty records raise ValueError."""
        writer = BronzeWriter(bucket=temp_dir)
        date = datetime(2024, 1, 15)

        with pytest.raises(ValueError, match="No records"):
            await writer.write_bronze(
                records=iter([]),
                provider="test",
                entity="test",
                date=date,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
            )


@pytest.mark.unit
class TestBronzeWriterReadLocal:
    """Tests for BronzeWriter local read operations."""

    @pytest.mark.asyncio
    async def test_read_bronze_local(
        self,
        temp_dir: str,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test reading Bronze data from local storage."""
        writer = BronzeWriter(bucket=temp_dir)
        date = datetime(2024, 1, 15)

        # Write first
        path = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
        )

        # Read back (use as_posix for cross-platform compatibility)
        records = []
        async for record in writer.read_bronze(path.as_posix()):
            records.append(record)

        assert len(records) == 3
        assert records[0]["id"] == 1
        assert records[1]["id"] == 2
        assert records[2]["id"] == 3


@pytest.mark.unit
class TestBronzeWriterListBatches:
    """Tests for BronzeWriter list operations."""

    @pytest.mark.asyncio
    async def test_list_batches_local(
        self,
        temp_dir: str,
        sample_records: list[bytes],
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test listing batches from local storage."""
        writer = BronzeWriter(bucket=temp_dir)

        # Write multiple batches
        date1 = datetime(2024, 1, 15)
        date2 = datetime(2024, 1, 16)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date1,
            batch_id=BatchID(uuid4()),
            run_id=run_id,
            run_type=run_type,
        )
        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date2,
            batch_id=BatchID(uuid4()),
            run_id=run_id,
            run_type=run_type,
        )

        # List all batches
        batches = await writer.list_batches("chembl", "activity")
        assert len(batches) == 2

    @pytest.mark.asyncio
    async def test_list_batches_with_date_filter(
        self,
        temp_dir: str,
        sample_records: list[bytes],
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test listing batches with date filter."""
        writer = BronzeWriter(bucket=temp_dir)

        date1 = datetime(2024, 1, 15)
        date2 = datetime(2024, 1, 16)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date1,
            batch_id=BatchID(uuid4()),
            run_id=run_id,
            run_type=run_type,
        )
        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date2,
            batch_id=BatchID(uuid4()),
            run_id=run_id,
            run_type=run_type,
        )

        # List with date filter
        batches = await writer.list_batches("chembl", "activity", date=date1)
        assert len(batches) == 1
        assert "2024-01-15" in batches[0]

    @pytest.mark.asyncio
    async def test_list_batches_empty(self, temp_dir: str) -> None:
        """Test listing batches when none exist."""
        writer = BronzeWriter(bucket=temp_dir)

        batches = await writer.list_batches("nonexistent", "entity")
        assert batches == []


@pytest.mark.unit
class TestBronzeWriterS3:
    """Tests for BronzeWriter S3 operations."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.s3_pool.S3ClientPool")
    async def test_write_bronze_s3(
        self,
        mock_pool: MagicMock,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test writing Bronze data to S3."""
        mock_client = MagicMock()
        mock_pool.get_client.return_value = mock_client

        writer = BronzeWriter(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
        )
        date = datetime(2024, 1, 15)

        path = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
        )

        # Verify S3 put was called
        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert "bronze/v1/chembl/activity" in call_kwargs["Key"]
        assert call_kwargs["ContentType"] == "application/zstd"
        # Verify run metadata is included in S3 object metadata
        assert call_kwargs["Metadata"]["run_id"] == str(run_id)
        assert call_kwargs["Metadata"]["run_type"] == run_type.value

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.s3_pool.S3ClientPool")
    async def test_write_bronze_s3_bucket_not_found(
        self,
        mock_pool: MagicMock,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test S3 write with missing bucket raises BucketNotFoundError."""
        from botocore.exceptions import ClientError

        from bioetl.domain.exceptions import BucketNotFoundError

        mock_client = MagicMock()
        mock_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "Bucket not found"}},
            "PutObject",
        )
        mock_pool.get_client.return_value = mock_client

        writer = BronzeWriter(
            bucket="nonexistent-bucket",
            endpoint_url="http://localhost:9000",
        )
        date = datetime(2024, 1, 15)

        with pytest.raises(BucketNotFoundError):
            await writer.write_bronze(
                records=iter(sample_records),
                provider="chembl",
                entity="activity",
                date=date,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
            )

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.s3_pool.S3ClientPool")
    async def test_write_bronze_s3_upload_error(
        self,
        mock_pool: MagicMock,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test S3 write error raises UploadError."""
        from botocore.exceptions import ClientError

        from bioetl.domain.exceptions import UploadError

        mock_client = MagicMock()
        mock_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "InternalError", "Message": "Internal error"}},
            "PutObject",
        )
        mock_pool.get_client.return_value = mock_client

        writer = BronzeWriter(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
        )
        date = datetime(2024, 1, 15)

        with pytest.raises(UploadError):
            await writer.write_bronze(
                records=iter(sample_records),
                provider="chembl",
                entity="activity",
                date=date,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
            )

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.s3_pool.S3ClientPool")
    async def test_list_batches_s3(self, mock_pool: MagicMock) -> None:
        """Test listing batches from S3."""
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "bronze/v1/chembl/activity/2024-01-15/batch_123.jsonl.zst"},
                {"Key": "bronze/v1/chembl/activity/2024-01-16/batch_456.jsonl.zst"},
            ]
        }
        mock_pool.get_client.return_value = mock_client

        writer = BronzeWriter(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
        )

        batches = await writer.list_batches("chembl", "activity")

        assert len(batches) == 2
        mock_client.list_objects_v2.assert_called_once()