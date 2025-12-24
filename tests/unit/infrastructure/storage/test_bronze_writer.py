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
from bioetl.infrastructure.storage._atomic import AtomicWriteGroup
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter


@pytest.fixture
def batch_id() -> BatchID:
    """Generate a unique batch ID."""
    return BatchID(uuid4())


@pytest.fixture
def run_id() -> RunID:
    """Generate a unique run ID."""
    return uuid4()


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


@pytest.mark.unit
class TestBronzeWriterAtomicWrite:
    """Tests for BronzeWriter atomic write guarantees (REQ-DATA-004)."""

    @pytest.mark.asyncio
    async def test_no_partial_files_on_write_failure(
        self,
        tmp_path,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test that no partial files remain if write fails mid-operation.

        Simulates a failure during the atomic write commit phase.
        Verifies REQ-DATA-004: Atomic writes.
        """
        writer = BronzeWriter(base_path=tmp_path)
        date = datetime(2024, 1, 15)

        # Mock AtomicWriteGroup.commit to fail
        original_commit = AtomicWriteGroup.commit

        def failing_commit(self):
            # Call rollback to simulate proper cleanup
            self.rollback()
            raise OSError("Simulated disk failure during commit")

        with patch.object(AtomicWriteGroup, "commit", failing_commit):
            with pytest.raises(OSError, match="Simulated disk failure"):
                await writer.write_bronze(
                    records=iter(sample_records),
                    provider="chembl",
                    entity="activity",
                    date=date,
                    batch_id=batch_id,
                    run_id=run_id,
                    run_type=run_type,
                )

        # Verify no data files exist
        bronze_path = tmp_path / "bronze" / "v1" / "chembl" / "activity"
        if bronze_path.exists():
            zst_files = list(bronze_path.rglob("*.zst"))
            meta_files = list(bronze_path.rglob("*.meta.json"))
            assert len(zst_files) == 0, "Partial .zst file should not exist"
            assert len(meta_files) == 0, "Partial .meta.json file should not exist"

        # Verify no temp files remain anywhere
        tmp_files = list(tmp_path.rglob("*.tmp"))
        assert len(tmp_files) == 0, "No temp files should remain after failure"

    @pytest.mark.asyncio
    async def test_no_orphan_metadata_without_data(
        self,
        tmp_path,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test that metadata file never exists without corresponding data file.

        Both files must be written together atomically.
        """
        writer = BronzeWriter(base_path=tmp_path)
        date = datetime(2024, 1, 15)

        # Successful write
        path = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
        )

        full_path = tmp_path / path
        meta_path = full_path.with_suffix(".zst.meta.json")

        # Both files must exist
        assert full_path.exists(), "Data file must exist"
        assert meta_path.exists(), "Metadata file must exist"

    @pytest.mark.asyncio
    async def test_no_temp_files_after_successful_write(
        self,
        tmp_path,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test that no temp files remain after successful write."""
        writer = BronzeWriter(base_path=tmp_path)
        date = datetime(2024, 1, 15)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
        )

        # No temp files should remain
        tmp_files = list(tmp_path.rglob("*.tmp"))
        assert len(tmp_files) == 0, f"Found orphan temp files: {tmp_files}"

    @pytest.mark.asyncio
    async def test_failure_during_add_cleans_up(
        self,
        tmp_path,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test that failure during AtomicWriteGroup.add cleans up temp files."""
        writer = BronzeWriter(base_path=tmp_path)
        date = datetime(2024, 1, 15)

        # Mock AtomicWriteGroup.add to fail on second call (metadata)
        original_add = AtomicWriteGroup.add
        call_count = [0]

        def failing_add(self, target, data):
            call_count[0] += 1
            if call_count[0] == 2:
                # Clean up first temp file before raising
                self.rollback()
                raise OSError("Simulated failure writing metadata")
            return original_add(self, target, data)

        with patch.object(AtomicWriteGroup, "add", failing_add):
            with pytest.raises(IOError, match="Simulated failure"):
                await writer.write_bronze(
                    records=iter(sample_records),
                    provider="chembl",
                    entity="activity",
                    date=date,
                    batch_id=batch_id,
                    run_id=run_id,
                    run_type=run_type,
                )

        # No temp files should remain
        tmp_files = list(tmp_path.rglob("*.tmp"))
        assert len(tmp_files) == 0, f"Found orphan temp files: {tmp_files}"

    @pytest.mark.asyncio
    async def test_json_copy_uses_atomic_write(
        self,
        tmp_path,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test that JSON copy also uses atomic write."""
        writer = BronzeWriter(base_path=tmp_path, save_json=True)
        date = datetime(2024, 1, 15)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
        )

        # Verify JSON file exists
        json_path = Path(writer.json_path) / "chembl" / "activity"
        json_files = list(json_path.glob("*.jsonl"))
        assert len(json_files) == 1

        # No temp files should remain
        tmp_files = list(Path(writer.json_path).rglob("*.tmp"))
        assert len(tmp_files) == 0, f"Found orphan temp files: {tmp_files}"
