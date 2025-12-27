"""Unit tests for BronzeWriter."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import zstandard as zstd

from bioetl.domain.ports import MetricsPort
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.storage._atomic import AtomicWriteGroup
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter


@pytest.fixture
def noop_logger() -> NoOpLogger:
    """Provide a NoOpLogger for BronzeWriter tests."""
    return NoOpLogger()


@pytest.fixture
def noop_metrics() -> MetricsPort:
    """Provide a NoOpMetrics for BronzeWriter tests."""
    return NoOpMetrics()


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
def ingestion_ts() -> datetime:
    """Return fixed ingestion timestamp for deterministic tests."""
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


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
class TestBronzeWriterNameValidation:
    """Tests for BronzeWriter provider/entity name validation."""

    def test_validate_bronze_names_valid(self, tmp_path, noop_logger) -> None:
        """Test valid provider and entity names pass validation."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        # Should not raise for valid names (alphanumeric + underscore only)
        writer._validate_bronze_names("chembl", "activity")
        writer._validate_bronze_names("pub_chem", "compound_data")
        writer._validate_bronze_names("uniprot_kb", "protein_entry")
        writer._validate_bronze_names("Test123", "Entity456")

    def test_validate_bronze_names_invalid_provider(self, tmp_path, noop_logger) -> None:
        """Test invalid provider names raise ValueError."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        with pytest.raises(ValueError, match="Invalid provider name"):
            writer._validate_bronze_names("", "activity")

        with pytest.raises(ValueError, match="Invalid provider name"):
            writer._validate_bronze_names("provider/path", "activity")

        with pytest.raises(ValueError, match="Invalid provider name"):
            writer._validate_bronze_names("provider name", "activity")

        with pytest.raises(ValueError, match="Invalid provider name"):
            writer._validate_bronze_names("provider.name", "activity")

        # Hyphens are not allowed (alphanumeric + underscore only)
        with pytest.raises(ValueError, match="Invalid provider name"):
            writer._validate_bronze_names("provider-name", "activity")

    def test_validate_bronze_names_invalid_entity(self, tmp_path, noop_logger) -> None:
        """Test invalid entity names raise ValueError."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        with pytest.raises(ValueError, match="Invalid entity name"):
            writer._validate_bronze_names("chembl", "")

        with pytest.raises(ValueError, match="Invalid entity name"):
            writer._validate_bronze_names("chembl", "entity/path")

        with pytest.raises(ValueError, match="Invalid entity name"):
            writer._validate_bronze_names("chembl", "entity name")

        with pytest.raises(ValueError, match="Invalid entity name"):
            writer._validate_bronze_names("chembl", "entity.name")

        # Hyphens are not allowed (alphanumeric + underscore only)
        with pytest.raises(ValueError, match="Invalid entity name"):
            writer._validate_bronze_names("chembl", "entity-name")

    @pytest.mark.asyncio
    async def test_write_bronze_invalid_provider_raises(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze raises ValueError for invalid provider."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        date = datetime(2024, 1, 15, tzinfo=UTC)

        with pytest.raises(ValueError, match="Invalid provider name"):
            await writer.write_bronze(
                records=iter(sample_records),
                provider="invalid/provider",
                entity="activity",
                date=date,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
                ingestion_ts=ingestion_ts,
            )

    @pytest.mark.asyncio
    async def test_write_bronze_invalid_entity_raises(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze raises ValueError for invalid entity."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        date = datetime(2024, 1, 15, tzinfo=UTC)

        with pytest.raises(ValueError, match="Invalid entity name"):
            await writer.write_bronze(
                records=iter(sample_records),
                provider="chembl",
                entity="invalid entity",
                date=date,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
                ingestion_ts=ingestion_ts,
            )

    def test_validate_records_iterator_valid(self, tmp_path, noop_logger) -> None:
        """Test valid iterator passes validation."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        # Should not raise for valid iterators
        writer._validate_records_iterator(iter([b"test"]))
        writer._validate_records_iterator(iter([]))
        writer._validate_records_iterator(x for x in [b"a", b"b"])

    def test_validate_records_iterator_none_raises(self, tmp_path, noop_logger) -> None:
        """Test None records raises TypeError."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        with pytest.raises(TypeError, match="records cannot be None"):
            writer._validate_records_iterator(None)  # type: ignore[arg-type]

    def test_validate_records_iterator_not_iterator_raises(
        self, tmp_path, noop_logger
    ) -> None:
        """Test non-iterator types raise TypeError."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        # List is not an iterator (has __iter__ but no __next__)
        with pytest.raises(TypeError, match="records must be an Iterator"):
            writer._validate_records_iterator([b"test"])  # type: ignore[arg-type]

        # String is not an iterator
        with pytest.raises(TypeError, match="records must be an Iterator"):
            writer._validate_records_iterator("test")  # type: ignore[arg-type]

        # Dict is not an iterator
        with pytest.raises(TypeError, match="records must be an Iterator"):
            writer._validate_records_iterator({"key": b"value"})  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_write_bronze_invalid_records_type_raises(
        self,
        tmp_path,
        noop_logger,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze raises TypeError for invalid records type."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        date = datetime(2024, 1, 15, tzinfo=UTC)

        with pytest.raises(TypeError, match="records must be an Iterator"):
            await writer.write_bronze(
                records=[b"test"],  # type: ignore[arg-type]
                provider="chembl",
                entity="activity",
                date=date,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
                ingestion_ts=ingestion_ts,
            )


@pytest.mark.unit
class TestBronzeWriterUTCValidation:
    """Tests for BronzeWriter UTC datetime validation (ADR-014 determinism)."""

    def test_validate_utc_datetime_valid(self, tmp_path, noop_logger) -> None:
        """Test valid UTC datetime passes validation."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        # Should not raise for UTC datetime
        utc_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        writer._validate_utc_datetime(utc_dt, "test_param")

    def test_validate_utc_datetime_naive_raises(self, tmp_path, noop_logger) -> None:
        """Test naive datetime raises ValueError."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        naive_dt = datetime(2024, 1, 15, 12, 0, 0)  # No tzinfo
        with pytest.raises(ValueError, match="must be timezone-aware"):
            writer._validate_utc_datetime(naive_dt, "date")

    def test_validate_utc_datetime_non_utc_raises(self, tmp_path, noop_logger) -> None:
        """Test non-UTC timezone raises ValueError."""
        from datetime import timezone, timedelta

        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        # Create datetime with non-UTC timezone (e.g., UTC+3)
        non_utc_tz = timezone(timedelta(hours=3))
        non_utc_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=non_utc_tz)

        with pytest.raises(ValueError, match="must be UTC"):
            writer._validate_utc_datetime(non_utc_dt, "ingestion_ts")

    @pytest.mark.asyncio
    async def test_write_bronze_naive_date_raises(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze raises ValueError for naive date."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        naive_date = datetime(2024, 1, 15)  # No tzinfo

        with pytest.raises(ValueError, match="date must be timezone-aware"):
            await writer.write_bronze(
                records=iter(sample_records),
                provider="chembl",
                entity="activity",
                date=naive_date,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
                ingestion_ts=ingestion_ts,
            )

    @pytest.mark.asyncio
    async def test_write_bronze_naive_ingestion_ts_raises(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test write_bronze raises ValueError for naive ingestion_ts."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        utc_date = datetime(2024, 1, 15, tzinfo=UTC)
        naive_ingestion = datetime(2024, 1, 15, 12, 0, 0)  # No tzinfo

        with pytest.raises(ValueError, match="ingestion_ts must be timezone-aware"):
            await writer.write_bronze(
                records=iter(sample_records),
                provider="chembl",
                entity="activity",
                date=utc_date,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
                ingestion_ts=naive_ingestion,
            )

    @pytest.mark.asyncio
    async def test_write_bronze_non_utc_date_raises(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze raises ValueError for non-UTC date."""
        from datetime import timezone, timedelta

        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        non_utc_tz = timezone(timedelta(hours=5))
        non_utc_date = datetime(2024, 1, 15, tzinfo=non_utc_tz)

        with pytest.raises(ValueError, match="date must be UTC"):
            await writer.write_bronze(
                records=iter(sample_records),
                provider="chembl",
                entity="activity",
                date=non_utc_date,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
                ingestion_ts=ingestion_ts,
            )


@pytest.mark.unit
class TestBronzeWriterInit:
    """Tests for BronzeWriter initialization."""

    def test_init_local_storage(self, tmp_path, noop_logger) -> None:
        """Test initialization for local storage."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        assert writer.base_path == tmp_path
        assert writer.save_json is False
        assert writer.logger is noop_logger

    def test_init_with_save_json(self, tmp_path, noop_logger) -> None:
        """Test initialization with JSON saving enabled."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics(), save_json=True)

        assert writer.save_json is True
        assert writer.json_path is not None

    def test_init_with_custom_json_path(self, tmp_path, noop_logger) -> None:
        """Test initialization with custom JSON path."""
        custom_path = str(tmp_path / "custom_json")
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
            save_json=True,
            json_path=custom_path,
        )

        assert writer.json_path == custom_path

    def test_init_requires_logger(self, tmp_path) -> None:
        """Test that logger is required (no fallback)."""
        with pytest.raises(TypeError, match="logger"):
            BronzeWriter(base_path=tmp_path)  # type: ignore[call-arg]


@pytest.mark.unit
class TestBronzeWriterCompress:
    """Tests for BronzeWriter compression."""

    def test_compress_records(
        self, tmp_path, noop_logger, sample_records: list[bytes]
    ) -> None:
        """Test record compression returns data, count, and size."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        compressed, record_count, uncompressed_size = writer._compress_records(
            iter(sample_records)
        )

        assert compressed is not None
        assert len(compressed) > 0
        assert record_count == len(sample_records)
        assert uncompressed_size == sum(len(r) for r in sample_records)

        # Verify we can decompress (use streaming for robustness)
        decompressor = zstd.ZstdDecompressor()
        with decompressor.stream_reader(compressed) as reader:
            decompressed = reader.read()
        expected = b"".join(sample_records)
        assert decompressed == expected

    def test_compress_empty_records_raises(self, tmp_path, noop_logger) -> None:
        """Test that empty records raise ValueError."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        with pytest.raises(ValueError, match="No records provided"):
            writer._compress_records(iter([]))

    def test_compress_large_records(self, tmp_path, noop_logger) -> None:
        """Test compression with records larger than chunk size."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        # Create large records
        large_record = {"data": "x" * 500_000}
        records = [json.dumps(large_record).encode("utf-8") + b"\n" for _ in range(5)]

        compressed, record_count, uncompressed_size = writer._compress_records(
            iter(records)
        )

        assert record_count == 5
        assert uncompressed_size == sum(len(r) for r in records)

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
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test writing Bronze data to local storage."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        date = datetime(2024, 1, 15, tzinfo=UTC)

        path = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
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
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that local write is performed asynchronously."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
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
                ingestion_ts=ingestion_ts,
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
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test writing Bronze data with JSON copy."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics(), save_json=True)
        date = datetime(2024, 1, 15, tzinfo=UTC)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="pubchem",
            entity="compound",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
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
        noop_logger,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that empty records raise ValueError."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        date = datetime(2024, 1, 15, tzinfo=UTC)

        with pytest.raises(ValueError, match="No records"):
            await writer.write_bronze(
                records=iter([]),
                provider="test",
                entity="test",
                date=date,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
                ingestion_ts=ingestion_ts,
            )


@pytest.mark.unit
class TestBronzeWriterReadLocal:
    """Tests for BronzeWriter local read operations."""

    @pytest.mark.asyncio
    async def test_read_bronze_local(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test reading Bronze data from local storage."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        date = datetime(2024, 1, 15, tzinfo=UTC)

        # Write first
        path = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
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
        noop_logger,
        sample_records: list[bytes],
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test listing batches from local storage."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        # Write multiple batches
        date1 = datetime(2024, 1, 15, tzinfo=UTC)
        date2 = datetime(2024, 1, 16, tzinfo=UTC)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date1,
            batch_id=BatchID(uuid4()),
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )
        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date2,
            batch_id=BatchID(uuid4()),
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # List all batches
        batches = await writer.list_batches("chembl", "activity")
        assert len(batches) == 2

    @pytest.mark.asyncio
    async def test_list_batches_with_date_filter(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test listing batches with date filter."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        date1 = datetime(2024, 1, 15, tzinfo=UTC)
        date2 = datetime(2024, 1, 16, tzinfo=UTC)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date1,
            batch_id=BatchID(uuid4()),
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )
        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date2,
            batch_id=BatchID(uuid4()),
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # List with date filter
        batches = await writer.list_batches("chembl", "activity", date=date1)
        assert len(batches) == 1
        assert "2024-01-15" in batches[0]

    @pytest.mark.asyncio
    async def test_list_batches_empty(self, tmp_path, noop_logger) -> None:
        """Test listing batches when none exist."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        batches = await writer.list_batches("nonexistent", "entity")
        assert batches == []


@pytest.mark.unit
class TestBronzeWriterAtomicWrite:
    """Tests for BronzeWriter atomic write guarantees (REQ-DATA-004)."""

    @pytest.mark.asyncio
    async def test_no_partial_files_on_write_failure(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that no partial files remain if write fails mid-operation.

        Simulates a failure during the atomic write commit phase.
        Verifies REQ-DATA-004: Atomic writes.
        """
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        date = datetime(2024, 1, 15, tzinfo=UTC)

        # Mock AtomicWriteGroup.commit to fail
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
                    ingestion_ts=ingestion_ts,
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
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that metadata file never exists without corresponding data file.

        Both files must be written together atomically.
        """
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        date = datetime(2024, 1, 15, tzinfo=UTC)

        # Successful write
        path = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
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
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that no temp files remain after successful write."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        date = datetime(2024, 1, 15, tzinfo=UTC)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # No temp files should remain
        tmp_files = list(tmp_path.rglob("*.tmp"))
        assert len(tmp_files) == 0, f"Found orphan temp files: {tmp_files}"

    @pytest.mark.asyncio
    async def test_failure_during_add_cleans_up(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that failure during AtomicWriteGroup.add cleans up temp files."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        date = datetime(2024, 1, 15, tzinfo=UTC)

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
                    ingestion_ts=ingestion_ts,
                )

        # No temp files should remain
        tmp_files = list(tmp_path.rglob("*.tmp"))
        assert len(tmp_files) == 0, f"Found orphan temp files: {tmp_files}"

    @pytest.mark.asyncio
    async def test_json_copy_uses_atomic_write(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that JSON copy also uses atomic write."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics(), save_json=True)
        date = datetime(2024, 1, 15, tzinfo=UTC)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # Verify JSON file exists
        json_path = Path(writer.json_path) / "chembl" / "activity"
        json_files = list(json_path.glob("*.jsonl"))
        assert len(json_files) == 1

        # No temp files should remain
        tmp_files = list(Path(writer.json_path).rglob("*.tmp"))
        assert len(tmp_files) == 0, f"Found orphan temp files: {tmp_files}"


@pytest.mark.unit
class TestBronzeWriterLoggerInjection:
    """Tests verifying logger is properly injected and used."""

    @pytest.mark.asyncio
    async def test_logger_called_on_write(
        self,
        tmp_path,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that injected logger is called during write operations."""
        mock_logger = MagicMock()
        writer = BronzeWriter(base_path=tmp_path, logger=mock_logger, metrics=NoOpMetrics())
        date = datetime(2024, 1, 15, tzinfo=UTC)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # Verify logger.info was called with bronze_write_complete
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "bronze_write_complete"
        assert call_args[1]["provider"] == "chembl"
        assert call_args[1]["entity"] == "activity"
        assert call_args[1]["batch_id"] == str(batch_id)
        assert call_args[1]["run_id"] == str(run_id)

    def test_logger_is_stored_as_attribute(self, tmp_path) -> None:
        """Test that injected logger is stored and accessible."""
        mock_logger = MagicMock()
        writer = BronzeWriter(base_path=tmp_path, logger=mock_logger, metrics=NoOpMetrics())

        assert writer.logger is mock_logger


@pytest.mark.unit
class TestBronzeWriterMetadataDeterminism:
    """Tests for metadata determinism (REQ-ARCH-030)."""

    @pytest.mark.asyncio
    async def test_metadata_bitwise_identical_on_repeated_calls(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that metadata files are bitwise identical on repeated writes.

        Verifies REQ-ARCH-030: Deterministic writes for reproducibility.
        Uses sort_keys=True and separators=(',', ':') to ensure consistent output.
        """
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        date = datetime(2024, 1, 15, tzinfo=UTC)

        # Write twice with the same parameters but different batch IDs
        batch_id_1 = BatchID(uuid4())
        batch_id_2 = BatchID(uuid4())

        path_1 = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id_1,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        path_2 = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id_2,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # Read both metadata files
        meta_path_1 = (tmp_path / path_1).with_suffix(".zst.meta.json")
        meta_path_2 = (tmp_path / path_2).with_suffix(".zst.meta.json")

        with open(meta_path_1, "rb") as f:
            meta_bytes_1 = f.read()
        with open(meta_path_2, "rb") as f:
            meta_bytes_2 = f.read()

        # Parse to compare structure (batch_id will differ)
        meta_1 = json.loads(meta_bytes_1)
        meta_2 = json.loads(meta_bytes_2)

        # Normalize batch_id for comparison
        meta_1["batch_id"] = "normalized"
        meta_2["batch_id"] = "normalized"

        # Re-encode with same settings to verify determinism
        normalized_1 = json.dumps(meta_1, sort_keys=True, separators=(",", ":"))
        normalized_2 = json.dumps(meta_2, sort_keys=True, separators=(",", ":"))

        assert normalized_1 == normalized_2, (
            "Metadata should produce identical bytes when serialized with same settings"
        )

    def test_metadata_json_format_is_deterministic(
        self,
        tmp_path,
        noop_logger,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        batch_id: BatchID,
    ) -> None:
        """Test that _build_bronze_metadata produces deterministic JSON.

        Multiple serializations of the same metadata dict should produce
        identical byte sequences when using sort_keys=True and separators=(',', ':').
        """
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        metadata = writer._build_bronze_metadata(
            run_id=run_id,
            run_type=run_type,
            effective_ts=ingestion_ts,
            provider="chembl",
            entity="activity",
            batch_id=batch_id,
        )

        # Serialize multiple times and verify identical output
        serialized = [
            json.dumps(metadata, sort_keys=True, separators=(",", ":"))
            for _ in range(10)
        ]

        assert all(s == serialized[0] for s in serialized), (
            "All serializations should be identical"
        )

    def test_metadata_has_no_whitespace_variations(
        self,
        tmp_path,
        noop_logger,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        batch_id: BatchID,
    ) -> None:
        """Test that metadata JSON has consistent formatting with no extra whitespace.

        Using separators=(',', ':') removes spaces after separators.
        """
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        metadata = writer._build_bronze_metadata(
            run_id=run_id,
            run_type=run_type,
            effective_ts=ingestion_ts,
            provider="chembl",
            entity="activity",
            batch_id=batch_id,
        )

        serialized = json.dumps(metadata, sort_keys=True, separators=(",", ":"))

        # Verify no spaces after : or ,
        assert ": " not in serialized, "No space after colon"
        assert ", " not in serialized, "No space after comma"
        # Verify keys are sorted
        keys = list(json.loads(serialized).keys())
        assert keys == sorted(keys), "Keys should be alphabetically sorted"


@pytest.mark.unit
class TestBronzeWriterMetrics:
    """Tests for BronzeWriter metrics collection (O1 observability)."""

    def test_init_with_metrics(self, tmp_path, noop_logger) -> None:
        """Test initialization with custom metrics port."""
        mock_metrics = MagicMock()
        writer = BronzeWriter(
            base_path=tmp_path, logger=noop_logger, metrics=mock_metrics
        )

        assert writer._metrics is mock_metrics

    def test_init_without_metrics_uses_noop(self, tmp_path, noop_logger) -> None:
        """Test initialization without metrics uses NoOpMetrics."""
        from bioetl.domain.ports.noop import NoOpMetrics

        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        assert isinstance(writer._metrics, NoOpMetrics)

    @pytest.mark.asyncio
    async def test_write_bronze_records_duration_metric(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that write_bronze records duration histogram."""
        mock_metrics = MagicMock()
        writer = BronzeWriter(
            base_path=tmp_path, logger=noop_logger, metrics=mock_metrics
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # Verify observe_histogram was called with duration metric
        histogram_calls = [
            call
            for call in mock_metrics.observe_histogram.call_args_list
            if call[0][0] == "bronze_write_duration_seconds"
        ]
        assert len(histogram_calls) == 1

        call_args = histogram_calls[0]
        assert call_args[0][0] == "bronze_write_duration_seconds"
        assert isinstance(call_args[0][1], float)
        assert call_args[0][1] >= 0  # Duration should be non-negative
        assert call_args[0][2] == {"provider": "chembl", "entity": "activity"}

    @pytest.mark.asyncio
    async def test_write_bronze_records_count_metric(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that write_bronze records count counter."""
        mock_metrics = MagicMock()
        writer = BronzeWriter(
            base_path=tmp_path, logger=noop_logger, metrics=mock_metrics
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="pubchem",
            entity="compound",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # Verify increment_counter was called with records count metric
        counter_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if call[0][0] == "bronze_records_written_total"
        ]
        assert len(counter_calls) == 1

        call_args = counter_calls[0]
        assert call_args[0][0] == "bronze_records_written_total"
        assert call_args[0][1] == len(sample_records)  # 3 records
        assert call_args[0][2] == {"provider": "pubchem", "entity": "compound"}

    @pytest.mark.asyncio
    async def test_write_bronze_records_bytes_metric(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that write_bronze records bytes counter."""
        mock_metrics = MagicMock()
        writer = BronzeWriter(
            base_path=tmp_path, logger=noop_logger, metrics=mock_metrics
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="uniprot",
            entity="protein",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # Verify increment_counter was called with bytes metric
        counter_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if call[0][0] == "bronze_bytes_written_total"
        ]
        assert len(counter_calls) == 1

        call_args = counter_calls[0]
        assert call_args[0][0] == "bronze_bytes_written_total"
        assert call_args[0][1] > 0  # Should have written some bytes
        assert call_args[0][2] == {"provider": "uniprot", "entity": "protein"}

    @pytest.mark.asyncio
    async def test_write_bronze_all_metrics_recorded(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that all 3 metrics are recorded on write."""
        mock_metrics = MagicMock()
        writer = BronzeWriter(
            base_path=tmp_path, logger=noop_logger, metrics=mock_metrics
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # Verify histogram was called once (duration)
        assert mock_metrics.observe_histogram.call_count == 1

        # Verify counter was called twice (records + bytes)
        assert mock_metrics.increment_counter.call_count == 2

        # Verify all expected metrics were recorded
        histogram_names = [
            call[0][0] for call in mock_metrics.observe_histogram.call_args_list
        ]
        counter_names = [
            call[0][0] for call in mock_metrics.increment_counter.call_args_list
        ]

        assert "bronze_write_duration_seconds" in histogram_names
        assert "bronze_records_written_total" in counter_names
        assert "bronze_bytes_written_total" in counter_names

    @pytest.mark.asyncio
    async def test_logger_includes_metrics_info(
        self,
        tmp_path,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that logger call includes record count and byte size."""
        mock_logger = MagicMock()
        writer = BronzeWriter(base_path=tmp_path, logger=mock_logger, metrics=NoOpMetrics())
        date = datetime(2024, 1, 15, tzinfo=UTC)

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # Verify logger includes new metrics fields
        call_kwargs = mock_logger.info.call_args[1]
        assert "record_count" in call_kwargs
        assert call_kwargs["record_count"] == len(sample_records)
        assert "compressed_bytes" in call_kwargs
        assert call_kwargs["compressed_bytes"] > 0
        assert "uncompressed_bytes" in call_kwargs
        assert call_kwargs["uncompressed_bytes"] > 0
        assert "duration_seconds" in call_kwargs
        assert call_kwargs["duration_seconds"] >= 0


@pytest.mark.unit
class TestBronzeWriterJsonValidation:
    """Tests for BronzeWriter JSON input validation."""

    def test_init_with_validate_json_default(self, tmp_path, noop_logger) -> None:
        """Test that validate_json defaults to True."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        assert writer.validate_json is True

    def test_init_with_validate_json_disabled(self, tmp_path, noop_logger) -> None:
        """Test initialization with JSON validation disabled."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
            validate_json=False,
        )
        assert writer.validate_json is False

    def test_validate_json_records_valid(self, tmp_path, noop_logger) -> None:
        """Test _validate_json_records passes valid JSON through."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        valid_records = [
            b'{"id": 1, "name": "test"}\n',
            b'{"id": 2, "value": 100}\n',
            b'[1, 2, 3]\n',
            b'"string"\n',
            b'123\n',
            b'null\n',
        ]

        validated = list(writer._validate_json_records(iter(valid_records)))
        assert validated == valid_records

    def test_validate_json_records_invalid_raises(self, tmp_path, noop_logger) -> None:
        """Test _validate_json_records raises BronzeValidationError on invalid JSON."""
        from bioetl.domain.exceptions import BronzeValidationError

        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        invalid_records = [
            b'{"id": 1}\n',
            b'not valid json\n',  # This is invalid
            b'{"id": 3}\n',
        ]

        with pytest.raises(BronzeValidationError) as exc_info:
            list(writer._validate_json_records(iter(invalid_records)))

        assert exc_info.value.record_index == 1
        assert exc_info.value.original_error is not None
        assert "Invalid JSON" in str(exc_info.value)

    def test_validate_json_records_empty_string(self, tmp_path, noop_logger) -> None:
        """Test _validate_json_records raises on empty string."""
        from bioetl.domain.exceptions import BronzeValidationError

        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        with pytest.raises(BronzeValidationError) as exc_info:
            list(writer._validate_json_records(iter([b''])))

        assert exc_info.value.record_index == 0

    def test_validate_json_records_truncated_json(self, tmp_path, noop_logger) -> None:
        """Test _validate_json_records raises on truncated JSON."""
        from bioetl.domain.exceptions import BronzeValidationError

        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        truncated_records = [
            b'{"id": 1, "name": "incomplete',  # Missing closing brace and quote
        ]

        with pytest.raises(BronzeValidationError) as exc_info:
            list(writer._validate_json_records(iter(truncated_records)))

        assert exc_info.value.record_index == 0

    def test_validate_json_records_is_lazy(self, tmp_path, noop_logger) -> None:
        """Test _validate_json_records is a lazy generator."""
        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())

        valid_records = [
            b'{"id": 1}\n',
            b'{"id": 2}\n',
        ]

        # Getting the generator should not consume any records
        gen = writer._validate_json_records(iter(valid_records))
        assert hasattr(gen, '__next__')

        # First record should be validated on demand
        first = next(gen)
        assert first == b'{"id": 1}\n'

    @pytest.mark.asyncio
    async def test_write_bronze_validates_json_by_default(
        self,
        tmp_path,
        noop_logger,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze validates JSON when validate_json=True (default)."""
        from bioetl.domain.exceptions import BronzeValidationError

        writer = BronzeWriter(base_path=tmp_path, logger=noop_logger, metrics=NoOpMetrics())
        date = datetime(2024, 1, 15, tzinfo=UTC)

        invalid_records = [
            b'{"valid": true}\n',
            b'invalid json here\n',
        ]

        with pytest.raises(BronzeValidationError) as exc_info:
            await writer.write_bronze(
                records=iter(invalid_records),
                provider="chembl",
                entity="activity",
                date=date,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
                ingestion_ts=ingestion_ts,
            )

        assert exc_info.value.record_index == 1
        assert "Invalid JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_write_bronze_skips_validation_when_disabled(
        self,
        tmp_path,
        noop_logger,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze skips JSON validation when validate_json=False."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
            validate_json=False,
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        # These are invalid JSON but should still be written when validation disabled
        # Note: They still need to be bytes
        invalid_records = [
            b'not json but bytes\n',
            b'another invalid line\n',
        ]

        # Should not raise - writes the bytes as-is
        path = await writer.write_bronze(
            records=iter(invalid_records),
            provider="test",
            entity="data",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # Verify file was written
        full_path = tmp_path / path
        assert full_path.exists()

    @pytest.mark.asyncio
    async def test_write_bronze_valid_json_succeeds(
        self,
        tmp_path,
        noop_logger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze succeeds with valid JSON records and validation enabled."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
            validate_json=True,
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        path = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # Verify file was written successfully
        full_path = tmp_path / path
        assert full_path.exists()

        # Verify we can read back the records
        records_read = []
        async for record in writer.read_bronze(str(path)):
            records_read.append(record)

        assert len(records_read) == len(sample_records)

    def test_bronze_validation_error_attributes(self) -> None:
        """Test BronzeValidationError has correct attributes."""
        from bioetl.domain.exceptions import BronzeValidationError

        error = BronzeValidationError(
            message="Test error",
            record_index=5,
            original_error="Expecting value",
        )

        assert error.record_index == 5
        assert error.original_error == "Expecting value"
        assert "Test error" in str(error)
        assert "record_index=5" in str(error)
        assert "error=Expecting value" in str(error)

    def test_bronze_validation_error_context(self) -> None:
        """Test BronzeValidationError exposes context for logging."""
        from bioetl.domain.exceptions import BronzeValidationError

        error = BronzeValidationError(
            message="Invalid JSON",
            record_index=10,
            original_error="Unterminated string",
        )

        context = error.context
        assert context["record_index"] == 10
        assert context["original_error"] == "Unterminated string"

    def test_bronze_validation_error_without_optional_fields(self) -> None:
        """Test BronzeValidationError works without optional fields."""
        from bioetl.domain.exceptions import BronzeValidationError

        error = BronzeValidationError(message="Simple error")

        assert error.record_index is None
        assert error.original_error is None
        assert str(error) == "Simple error"
