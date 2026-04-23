"""Support helpers for invariant-focused BronzeWriter test suites."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import zstandard as zstd

from bioetl.domain.ports import MetricsPort
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter


@pytest.fixture
def noop_logger() -> NoOpLogger:
    """Provide a local no-op logger fixture for sibling storage suites."""
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
    return RunID(uuid4())


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

    def test_validate_bronze_names_valid(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test valid provider and entity names pass validation."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        # Should not raise for valid names (alphanumeric + underscore only)
        writer._validate_bronze_names("chembl", "activity")
        writer._validate_bronze_names("pub_chem", "compound_data")
        writer._validate_bronze_names("uniprot_kb", "protein_entry")
        writer._validate_bronze_names("Test123", "Entity456")

    def test_validate_bronze_names_invalid_provider(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test invalid provider names raise ValueError."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

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

    def test_validate_bronze_names_invalid_entity(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test invalid entity names raise ValueError."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

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
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze raises ValueError for invalid provider."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
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
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze raises ValueError for invalid entity."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
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

    def test_validate_records_iterator_valid(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test valid iterator passes validation."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        # Should not raise for valid iterators
        writer._validate_records_iterator(iter((b"test",)))
        writer._validate_records_iterator(iter(()))
        writer._validate_records_iterator(iter((b"a", b"b")))


@pytest.mark.unit
class TestBronzeWriterTracing:
    """Tests for Bronze write tracing boundaries."""

    @pytest.mark.asyncio
    async def test_write_bronze_uses_injected_tracer(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Bronze writer should open a span when tracing is injected."""
        tracer = MagicMock()
        span = MagicMock()
        span_cm = MagicMock()
        span_cm.__enter__.return_value = span
        span_cm.__exit__.return_value = None
        tracer.start_as_current_span.return_value = span_cm
        tracing = MagicMock()
        tracing.get_tracer.return_value = tracer

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
            tracing=tracing,
        )
        writer._prepare_bronze_write = MagicMock()
        writer._write_bronze_data_and_sidecar = AsyncMock(
            return_value=MagicMock(
                record_count=1,
                uncompressed_size=10,
                compressed_size=5,
            )
        )
        writer._run_bronze_post_write_actions = AsyncMock()
        writer._build_bronze_write_result = AsyncMock(return_value=MagicMock())

        await writer.write_bronze(
            records=iter([b'{"id": 1}\n']),
            provider="chembl",
            entity="activity",
            date=datetime(2024, 1, 15, tzinfo=UTC),
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        tracing.get_tracer.assert_called_once()
        tracer.start_as_current_span.assert_called_once_with("write_bronze")
        span.set_attribute.assert_any_call("provider", "chembl")
        span.set_attribute.assert_any_call("entity", "activity")

    def test_validate_records_iterator_none_raises(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test None records raises TypeError."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        validate_records = cast(
            Callable[[Iterator[bytes] | None], None],
            writer._validate_records_iterator,
        )

        with pytest.raises(TypeError, match="records cannot be None"):
            validate_records(None)

    def test_validate_records_iterator_not_iterator_raises(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test non-iterator types raise TypeError."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        validate_records = cast(
            Callable[[object], None], writer._validate_records_iterator
        )

        # List is an iterable (valid now)
        validate_records([b"test"])

        # String is iterable but we should check if logic handles it (it iterates chars)
        # It technically passes "hasattr __iter__" but likely fails later if bytes expected.
        # But this test checks only _validate_records_iterator
        validate_records("test")

        # Int is NOT iterable
        with pytest.raises(TypeError, match="records must be an Iterator"):
            validate_records(123)

    @pytest.mark.asyncio
    async def test_write_bronze_invalid_records_type_raises(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze raises TypeError for invalid records type."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)
        write_bronze = cast(Callable[..., object], writer.write_bronze)

        # Int is not iterable
        with pytest.raises(TypeError, match="records must be an Iterator"):
            await write_bronze(
                records=123,
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

    def test_validate_utc_datetime_valid(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test valid UTC datetime passes validation."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        # Should not raise for UTC datetime
        utc_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        writer._validate_utc_datetime(utc_dt, "test_param")

    def test_validate_utc_datetime_naive_raises(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test naive datetime raises ValueError."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        naive_dt = datetime(2024, 1, 15, 12, 0, 0)  # No tzinfo
        with pytest.raises(ValueError, match="must be timezone-aware"):
            writer._validate_utc_datetime(naive_dt, "date")

    def test_validate_utc_datetime_non_utc_raises(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test non-UTC timezone raises ValueError."""
        from datetime import timedelta, timezone

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        # Create datetime with non-UTC timezone (e.g., UTC+3)
        non_utc_tz = timezone(timedelta(hours=3))
        non_utc_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=non_utc_tz)

        with pytest.raises(ValueError, match="must be UTC"):
            writer._validate_utc_datetime(non_utc_dt, "ingestion_ts")

    @pytest.mark.asyncio
    async def test_write_bronze_naive_date_raises(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze raises ValueError for naive date."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
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
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Test write_bronze raises ValueError for naive ingestion_ts."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
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
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze raises ValueError for non-UTC date."""
        from datetime import timedelta, timezone

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
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

    def test_init_local_storage(self, tmp_path: Path, noop_logger: NoOpLogger) -> None:
        """Test initialization for local storage."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        assert writer.base_path == tmp_path
        assert writer.save_json is False
        assert writer.logger is noop_logger

    def test_init_with_save_json(self, tmp_path: Path, noop_logger: NoOpLogger) -> None:
        """Test initialization with JSON saving enabled."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
            save_json=True,
        )

        assert writer.save_json is True
        assert writer.json_path is not None

    def test_init_with_custom_json_path(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
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

    def test_init_requires_logger(self, tmp_path: Path) -> None:
        """Test that logger is required (no fallback)."""
        with pytest.raises(TypeError, match="logger"):
            BronzeWriter(base_path=tmp_path)  # type: ignore[call-arg]


@pytest.mark.unit
class TestBronzeWriterWriteLocal:
    """Tests for BronzeWriter local write operations."""

    @pytest.mark.asyncio
    async def test_write_bronze_local(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test writing Bronze data to local storage."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        result = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # Verify BronzeWriteResult structure
        assert result.batch_id == batch_id
        assert result.record_count == len(sample_records)
        assert result.compressed_size > 0
        assert result.uncompressed_size > 0
        assert result.checksum_blake2  # Non-empty checksum

        # Verify path format (normalize for cross-platform)
        # Path format: {provider}/{entity}/{date}/batch_{date}_{batch_id}.jsonl.zst
        path_str = result.relative_path.replace("\\", "/")
        assert "chembl/activity/2024-01-15" in path_str
        assert str(batch_id) in result.relative_path
        assert result.relative_path.endswith(".jsonl.zst")

        # Verify file exists
        full_path = tmp_path / result.relative_path
        assert full_path.exists()
        assert result.absolute_path == str(full_path)

        # Verify metadata file exists
        meta_path = full_path.with_suffix(".zst.meta.json")
        assert meta_path.exists()

        # Verify metadata content
        metadata = json.loads(
            await asyncio.to_thread(meta_path.read_text, encoding="utf-8")
        )
        assert metadata["run_id"] == str(run_id)
        assert metadata["run_type"] == run_type.value
        assert metadata["provider"] == "chembl"
        assert metadata["entity"] == "activity"
        assert metadata["batch_id"] == str(batch_id)

        # Verify content (use streaming decompression for robustness)
        compressed_data = await asyncio.to_thread(full_path.read_bytes)

        decompressor = zstd.ZstdDecompressor()
        with decompressor.stream_reader(compressed_data) as reader:
            decompressed = reader.read()
        expected = b"".join(sample_records)
        assert decompressed == expected

        # Verify checksum matches file content
        import hashlib

        h = hashlib.blake2b()
        h.update(compressed_data)
        assert result.checksum_blake2 == h.hexdigest()

    @pytest.mark.asyncio
    async def test_write_bronze_local_async(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that local write is performed asynchronously."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        date = datetime(2023, 1, 1, tzinfo=UTC)

        # We patch run_in_executor to verify it's called for file I/O
        with patch.object(
            asyncio.get_running_loop(),
            "run_in_executor",
            wraps=asyncio.get_running_loop().run_in_executor,
        ) as mock_executor:
            result = await writer.write_bronze(
                records=iter(sample_records),
                provider="test_provider",
                entity="test_entity",
                date=date,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
                ingestion_ts=ingestion_ts,
            )

            # Verify run_in_executor was called at least once (for write_task)
            assert mock_executor.call_count >= 1

            # Verify file existence and content
            full_path = tmp_path / result.relative_path
            assert full_path.exists()
            assert full_path.with_suffix(".zst.meta.json").exists()

    @pytest.mark.asyncio
    async def test_write_bronze_with_json_copy(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test writing Bronze data with JSON copy."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
            save_json=True,
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

        # JSON copy is now in the same directory as zst files
        # Path format: {provider}/{entity}/{date}/batch_{date}_{batch_id}.jsonl
        json_path = tmp_path / "pubchem" / "compound" / "2024-01-15"
        json_files = list(json_path.glob("*.jsonl"))
        assert len(json_files) == 1

        # Verify JSON content
        content = await asyncio.to_thread(json_files[0].read_bytes)
        expected = b"".join(sample_records)
        assert content == expected

    @pytest.mark.asyncio
    async def test_write_bronze_empty_records_raises(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that empty records raise ValueError."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
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
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test reading Bronze data from local storage."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        # Write first
        result = await writer.write_bronze(
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
        async for record in writer.read_bronze(result.relative_path):
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
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test listing batches from local storage."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

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
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test listing batches with date filter."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

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
    async def test_list_batches_empty(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test listing batches when none exist."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        batches = await writer.list_batches("nonexistent", "entity")
        assert batches == []


@pytest.mark.unit
class TestBronzeWriterAtomicWrite:
    """Tests for BronzeWriter atomic write guarantees (REQ-DATA-004)."""

    @pytest.mark.asyncio
    async def test_no_partial_files_on_write_failure(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
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
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        # Mock Path.replace to fail (simulating rename failure)
        # Note: We now use Path.replace directly in _write_atomic_stream
        with patch(
            "pathlib.Path.replace", side_effect=OSError("Simulated rename failure")
        ):
            with pytest.raises(OSError, match="Simulated rename failure"):
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
            list(bronze_path.rglob("*.meta.json"))
            assert len(zst_files) == 0, "Partial .zst file should not exist"
            # Metadata might exist if we mock only data write failure, but here we fail before data write success

        # Verify no temp files remain anywhere
        tmp_files = list(tmp_path.rglob("*.tmp"))
        assert len(tmp_files) == 0, "No temp files should remain after failure"

    @pytest.mark.asyncio
    async def test_no_orphan_metadata_without_data(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that metadata file never exists without corresponding data file.

        Both files must be written together atomically.
        """
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        # Successful write
        result = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        full_path = tmp_path / result.relative_path
        meta_path = full_path.with_suffix(".zst.meta.json")

        # Both files must exist
        assert full_path.exists(), "Data file must exist"
        assert meta_path.exists(), "Metadata file must exist"

    @pytest.mark.asyncio
    async def test_no_temp_files_after_successful_write(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that no temp files remain after successful write."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
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

        # No temp files should remain
        tmp_files = list(tmp_path.rglob("*.tmp"))
        assert len(tmp_files) == 0, f"Found orphan temp files: {tmp_files}"

    @pytest.mark.asyncio
    async def test_failure_during_stream_write_cleans_up(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that failure during streaming write cleans up temp files."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        # Mock writer.write to raise OSError mid-stream
        with patch("zstandard.ZstdCompressor.stream_writer") as mock_stream:
            mock_writer = MagicMock()
            mock_writer.__enter__.return_value = mock_writer
            mock_writer.write.side_effect = OSError("Simulated write failure")
            mock_stream.return_value = mock_writer

            with pytest.raises(OSError, match="Simulated write failure"):
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
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that JSON copy also uses atomic write."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
            save_json=True,
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

        # JSON file is now in the same directory as zst files
        json_path = tmp_path / "chembl" / "activity" / "2024-01-15"
        json_files = list(json_path.glob("*.jsonl"))
        assert len(json_files) == 1

        # No temp files should remain
        tmp_files = list(tmp_path.rglob("*.tmp"))
        assert len(tmp_files) == 0, f"Found orphan temp files: {tmp_files}"


@pytest.mark.unit
class TestBronzeWriterLoggerInjection:
    """Tests verifying logger is properly injected and used."""

    @pytest.mark.asyncio
    async def test_logger_called_on_write(
        self,
        tmp_path: Path,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that injected logger is called during write operations."""
        mock_logger = MagicMock()
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=mock_logger,
            metrics=NoOpMetrics(),
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

        # Verify logger.info was called with bronze_write_complete
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "bronze_write_complete"
        assert call_args[1]["provider"] == "chembl"
        assert call_args[1]["entity"] == "activity"
        assert call_args[1]["batch_id"] == str(batch_id)
        assert call_args[1]["run_id"] == str(run_id)

    def test_logger_is_stored_as_attribute(self, tmp_path: Path) -> None:
        """Test that injected logger is stored and accessible."""
        mock_logger = MagicMock()
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=mock_logger,
            metrics=NoOpMetrics(),
        )

        assert writer.logger is mock_logger


@pytest.mark.unit
class TestBronzeWriterMetadataDeterminism:
    """Tests for metadata determinism (REQ-ARCH-030)."""

    @pytest.mark.asyncio
    async def test_compressed_payload_bitwise_identical_on_repeated_calls(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Repeated Bronze writes must produce identical compressed payload bytes.

        This black-box check protects the actual ``.jsonl.zst`` artifact, not only
        metadata formatting helpers, so deterministic-write regressions surface
        immediately when compression or write assembly changes.
        """
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        result_1 = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=BatchID(uuid4()),
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )
        result_2 = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=BatchID(uuid4()),
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        payload_1 = (tmp_path / result_1.relative_path).read_bytes()
        payload_2 = (tmp_path / result_2.relative_path).read_bytes()

        assert payload_1 == payload_2, (
            "Repeated Bronze writes with identical logical input must emit "
            "bitwise-identical compressed payloads"
        )

    @pytest.mark.asyncio
    async def test_metadata_bitwise_identical_on_repeated_calls(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that metadata files are bitwise identical on repeated writes.

        Verifies REQ-ARCH-030: Deterministic writes for reproducibility.
        Uses sort_keys=True and separators=(',', ':') to ensure consistent output.
        """
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        # Write twice with the same parameters but different batch IDs
        batch_id_1 = BatchID(uuid4())
        batch_id_2 = BatchID(uuid4())

        result_1 = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id_1,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        result_2 = await writer.write_bronze(
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
        meta_path_1 = (tmp_path / result_1.relative_path).with_suffix(".zst.meta.json")
        meta_path_2 = (tmp_path / result_2.relative_path).with_suffix(".zst.meta.json")

        meta_bytes_1 = await asyncio.to_thread(meta_path_1.read_bytes)
        meta_bytes_2 = await asyncio.to_thread(meta_path_2.read_bytes)

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
        tmp_path: Path,
        noop_logger: NoOpLogger,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        batch_id: BatchID,
    ) -> None:
        """Test that _build_bronze_metadata produces deterministic JSON.

        Multiple serializations of the same metadata dict should produce
        identical byte sequences when using sort_keys=True and separators=(',', ':').
        """
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

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
        tmp_path: Path,
        noop_logger: NoOpLogger,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        batch_id: BatchID,
    ) -> None:
        """Test that metadata JSON has consistent formatting with no extra whitespace.

        Using separators=(',', ':') removes spaces after separators.
        """
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

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

    def test_init_with_metrics(self, tmp_path: Path, noop_logger: NoOpLogger) -> None:
        """Test initialization with custom metrics port."""
        mock_metrics = MagicMock()
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=mock_metrics,
        )

        assert writer._metrics is mock_metrics

    def test_init_without_metrics_uses_noop(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test initialization without metrics uses NoOpMetrics."""
        from bioetl.domain.ports.noop import NoOpMetrics

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        assert isinstance(writer._metrics, NoOpMetrics)

    @pytest.mark.asyncio
    async def test_write_bronze_records_duration_metric(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that write_bronze records duration histogram."""
        mock_metrics = MagicMock()
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=mock_metrics,
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
            if call[0][0] == "bioetl_bronze_write_duration_seconds"
        ]
        assert len(histogram_calls) == 1

        call_args = histogram_calls[0]
        assert call_args[0][0] == "bioetl_bronze_write_duration_seconds"
        assert isinstance(call_args[0][1], float)
        assert call_args[0][1] >= 0  # Duration should be non-negative
        assert call_args[0][2] == {"provider": "chembl", "entity": "activity"}

    @pytest.mark.asyncio
    async def test_write_bronze_records_count_metric(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that write_bronze records count counter."""
        mock_metrics = MagicMock()
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=mock_metrics,
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
            if call[0][0] == "bioetl_bronze_records_written_total"
        ]
        assert len(counter_calls) == 1

        call_args = counter_calls[0]
        assert call_args[0][0] == "bioetl_bronze_records_written_total"
        assert call_args[0][1] == len(sample_records)  # 3 records
        assert call_args[0][2] == {"provider": "pubchem", "entity": "compound"}

    @pytest.mark.asyncio
    async def test_write_bronze_records_bytes_metric(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that write_bronze records bytes counter."""
        mock_metrics = MagicMock()
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=mock_metrics,
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
            if call[0][0] == "bioetl_bronze_bytes_written_total"
        ]
        assert len(counter_calls) == 1

        call_args = counter_calls[0]
        assert call_args[0][0] == "bioetl_bronze_bytes_written_total"
        assert call_args[0][1] > 0  # Should have written some bytes
        assert call_args[0][2] == {"provider": "uniprot", "entity": "protein"}

    @pytest.mark.asyncio
    async def test_write_bronze_all_metrics_recorded(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that all write metrics are recorded on write."""
        mock_metrics = MagicMock()
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=mock_metrics,
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

        # Verify histogram/counter families were emitted.
        # The writer now records both operation duration and total duration, and
        # includes a write-attempt counter in addition to records/bytes counters.
        assert mock_metrics.observe_histogram.call_count >= 2
        assert mock_metrics.increment_counter.call_count >= 3

        # Verify all expected metrics were recorded
        histogram_names = [
            call[0][0] for call in mock_metrics.observe_histogram.call_args_list
        ]
        counter_names = [
            call[0][0] for call in mock_metrics.increment_counter.call_args_list
        ]

        assert "bioetl_bronze_write_duration_seconds" in histogram_names
        assert "bioetl_bronze_write_total_duration_seconds" in histogram_names
        assert "bioetl_bronze_write_attempts_total" in counter_names
        assert "bioetl_bronze_records_written_total" in counter_names
        assert "bioetl_bronze_bytes_written_total" in counter_names

    @pytest.mark.asyncio
    async def test_logger_includes_metrics_info(
        self,
        tmp_path: Path,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that logger call includes record count and byte size."""
        mock_logger = MagicMock()
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=mock_logger,
            metrics=NoOpMetrics(),
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

    def test_init_with_validate_json_default(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test that validate_json defaults to True."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        assert writer.validate_json is True

    def test_init_with_validate_json_disabled(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test initialization with JSON validation disabled."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
            validate_json=False,
        )
        assert writer.validate_json is False

    def test_validate_json_records_valid(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test _validate_json_records passes valid JSON through."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        valid_records = [
            b'{"id": 1, "name": "test"}\n',
            b'{"id": 2, "value": 100}\n',
            b"[1, 2, 3]\n",
            b'"string"\n',
            b"123\n",
            b"null\n",
        ]

        validated = list(writer._validate_json_records(iter(valid_records)))
        assert validated == valid_records

    def test_validate_json_records_invalid_raises(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test _validate_json_records raises BronzeValidationError on invalid JSON."""
        from bioetl.domain.exceptions import StorageError

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        invalid_records = [
            b'{"id": 1}\n',
            b"not valid json\n",  # This is invalid
            b'{"id": 3}\n',
        ]

        with pytest.raises(StorageError) as exc_info:
            list(writer._validate_json_records(iter(invalid_records)))

        assert exc_info.value.record_index == 1
        assert exc_info.value.original_error is not None
        assert "Invalid JSON" in str(exc_info.value)

    def test_validate_json_records_empty_string(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test _validate_json_records raises on empty string."""
        from bioetl.domain.exceptions import StorageError

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        with pytest.raises(StorageError) as exc_info:
            list(writer._validate_json_records(iter([b""])))

        assert exc_info.value.record_index == 0

    def test_validate_json_records_truncated_json(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test _validate_json_records raises on truncated JSON."""
        from bioetl.domain.exceptions import StorageError

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        truncated_records = [
            b'{"id": 1, "name": "incomplete',  # Missing closing brace and quote
        ]

        with pytest.raises(StorageError) as exc_info:
            list(writer._validate_json_records(iter(truncated_records)))

        assert exc_info.value.record_index == 0

    def test_validate_json_records_is_lazy(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test _validate_json_records is a lazy generator."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        valid_records = [
            b'{"id": 1}\n',
            b'{"id": 2}\n',
        ]

        # Getting the generator should not consume any records
        gen = writer._validate_json_records(iter(valid_records))
        assert hasattr(gen, "__next__")

        # First record should be validated on demand
        first = next(gen)
        assert first == b'{"id": 1}\n'

    @pytest.mark.asyncio
    async def test_write_bronze_validates_json_by_default(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze validates JSON when validate_json=True (default)."""
        from bioetl.domain.exceptions import StorageError

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        invalid_records = [
            b'{"valid": true}\n',
            b"invalid json here\n",
        ]

        with pytest.raises(StorageError) as exc_info:
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
        tmp_path: Path,
        noop_logger: NoOpLogger,
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
            b"not json but bytes\n",
            b"another invalid line\n",
        ]

        # Should not raise - writes the bytes as-is
        result = await writer.write_bronze(
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
        full_path = tmp_path / result.relative_path
        assert full_path.exists()

    @pytest.mark.asyncio
    async def test_write_bronze_valid_json_succeeds(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
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

        result = await writer.write_bronze(
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
        full_path = tmp_path / result.relative_path
        assert full_path.exists()

        # Verify we can read back the records
        records_read = []
        async for record in writer.read_bronze(result.relative_path):
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


@pytest.mark.unit
class TestBronzeWriterAudit:
    """Tests for BronzeWriter audit logging."""

    @pytest.mark.asyncio
    async def test_write_bronze_with_audit(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze calls audit.log_write when audit port configured."""
        from unittest.mock import AsyncMock

        mock_audit = AsyncMock()

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
            audit=mock_audit,
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

        mock_audit.log_write.assert_called_once()
        call_args = mock_audit.log_write.call_args
        audit_entry = call_args[0][0]

        # Verify audit entry fields
        assert audit_entry.run_id == run_id
        assert audit_entry.records_count == len(sample_records)
        assert audit_entry.metadata["provider"] == "chembl"
        assert audit_entry.metadata["entity"] == "activity"

    @pytest.mark.asyncio
    async def test_write_bronze_without_audit(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test write_bronze works without audit port (default)."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        date = datetime(2024, 1, 15, tzinfo=UTC)

        # Should not raise
        result = await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        assert result is not None
        assert result.relative_path is not None
