"""Unit tests for BronzeWriter."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch
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


@pytest.mark.unit
class TestBronzeWriterInit:
    """Tests for BronzeWriter initialization."""

    def test_init_local_storage(self, tmp_path) -> None:
        """Test initialization for local storage."""
        writer = BronzeWriter(base_path=tmp_path)

        assert writer.base_path == tmp_path
        assert writer.save_json is False

    def test_init_with_save_json(self, tmp_path) -> None:
        """Test initialization with JSON saving enabled."""
        writer = BronzeWriter(base_path=tmp_path, save_json=True)

        assert writer.save_json is True
        assert writer.json_path is not None

    def test_init_with_custom_json_path(self, tmp_path) -> None:
        """Test initialization with custom JSON path."""
        custom_path = str(tmp_path / "custom_json")
        writer = BronzeWriter(
            base_path=tmp_path,
            save_json=True,
            json_path=custom_path,
        )

        assert writer.json_path == custom_path


@pytest.mark.unit
class TestBronzeWriterCompress:
    """Tests for BronzeWriter compression."""

    def test_compress_records(self, tmp_path, sample_records: list[bytes]) -> None:
        """Test record compression."""
        writer = BronzeWriter(base_path=tmp_path)

        compressed = writer._compress_records(iter(sample_records))

        assert compressed is not None
        assert len(compressed) > 0

        # Verify we can decompress (use streaming for robustness)
        decompressor = zstd.ZstdDecompressor()
        with decompressor.stream_reader(compressed) as reader:
            decompressed = reader.read()
        expected = b"".join(sample_records)
        assert decompressed == expected

    def test_compress_empty_records_raises(self, tmp_path) -> None:
        """Test that empty records raise ValueError."""
        writer = BronzeWriter(base_path=tmp_path)

        with pytest.raises(ValueError, match="No records provided"):
            writer._compress_records(iter([]))

    def test_compress_large_records(self, tmp_path) -> None:
        """Test compression with records larger than chunk size."""
        writer = BronzeWriter(base_path=tmp_path)

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
        tmp_path,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test writing Bronze data to local storage."""
        writer = BronzeWriter(base_path=tmp_path)
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

        # Verify path format (normalize for cross-platform)
        path_str = str(path).replace("\\", "/")
        assert "bronze/v1/chembl/activity/2024-01-15" in path_str
        assert str(batch_id) in str(path)
        assert str(path).endswith(".jsonl.zst")

        # Verify file exists
        full_path = tmp_path / path
        assert full_path.exists()

        # Verify metadata file exists
        meta_path = full_path.with_suffix(".zst.meta.json")
        assert meta_path.exists()

        # Verify metadata content
        with open(meta_path) as f:
            metadata = json.load(f)
        assert metadata["run_id"] == str(run_id)
        assert metadata["run_type"] == run_type.value
        assert metadata["provider"] == "chembl"
        assert metadata["entity"] == "activity"
        assert metadata["batch_id"] == str(batch_id)

        # Verify content (use streaming decompression for robustness)
        with open(full_path, "rb") as f:
            compressed_data = f.read()

        decompressor = zstd.ZstdDecompressor()
        with decompressor.stream_reader(compressed_data) as reader:
            decompressed = reader.read()
        expected = b"".join(sample_records)
        assert decompressed == expected

    @pytest.mark.asyncio
    async def test_write_bronze_local_async(
        self,
        tmp_path,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test that local write is performed asynchronously."""
        writer = BronzeWriter(base_path=tmp_path)
        date = datetime(2023, 1, 1, tzinfo=UTC)

        # We patch run_in_executor to verify it's called for file I/O
        with patch.object(
            asyncio.get_running_loop(),
            "run_in_executor",
            wraps=asyncio.get_running_loop().run_in_executor,
        ) as mock_executor:
            path = await writer.write_bronze(
                records=iter(sample_records),
                provider="test_provider",
                entity="test_entity",
                date=date,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
            )

            # Verify run_in_executor was called at least twice (1 for compression, 1 for write)
            assert mock_executor.call_count >= 2

            # Verify file existence and content
            full_path = tmp_path / path
            assert full_path.exists()
            assert full_path.with_suffix(".zst.meta.json").exists()

    @pytest.mark.asyncio
    async def test_write_bronze_with_json_copy(
        self,
        tmp_path,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test writing Bronze data with JSON copy."""
        writer = BronzeWriter(base_path=tmp_path, save_json=True)
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
        json_path = Path(writer.json_path) / "pubchem" / "compound"
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
        tmp_path,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test that empty records raise ValueError."""
        writer = BronzeWriter(base_path=tmp_path)
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
        tmp_path,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test reading Bronze data from local storage."""
        writer = BronzeWriter(base_path=tmp_path)
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

        # Read back
        records = []
        async for record in writer.read_bronze(str(path)):
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
        tmp_path,
        sample_records: list[bytes],
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test listing batches from local storage."""
        writer = BronzeWriter(base_path=tmp_path)

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
        tmp_path,
        sample_records: list[bytes],
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test listing batches with date filter."""
        writer = BronzeWriter(base_path=tmp_path)

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
    async def test_list_batches_empty(self, tmp_path) -> None:
        """Test listing batches when none exist."""
        writer = BronzeWriter(base_path=tmp_path)

        batches = await writer.list_batches("nonexistent", "entity")
        assert batches == []
