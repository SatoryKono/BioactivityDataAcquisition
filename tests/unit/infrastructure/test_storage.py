"""Unit tests for storage writers."""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pyarrow as pa
import pytest
import zstandard as zstd

from tests.helpers.synthetic_paths import synthetic_test_root

from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

# Default test run metadata
TEST_RUN_ID: RunID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
TEST_RUN_TYPE = RunType.INCREMENTAL
# Fixed timestamp for deterministic tests (see ADR-014)
TEST_INGESTION_TS = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
TEST_ROOT = synthetic_test_root("bioetl-storage-tests")
SILVER_DELTA_ROOT = str(TEST_ROOT / "delta")
GOLD_ROOT = str(TEST_ROOT / "gold")


@pytest.fixture
def mock_silver_writer():
    """Fixture for mocking silver_writer module."""
    with (
        patch(
            "bioetl.infrastructure.storage.silver_writer.DeltaTable"
        ) as mock_delta_table,
        patch(
            "bioetl.infrastructure.storage.silver_writer.write_deltalake"
        ) as mock_write_deltalake,
    ):
        yield mock_delta_table, mock_write_deltalake


@pytest.mark.unit
class TestBronzeWriter:
    """Test BronzeWriter functionality with local storage."""

    def test_bronze_writer_initialization(self, tmp_path, noop_logger):
        """Test BronzeWriter can be initialized."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )
        assert writer.base_path == tmp_path

    @pytest.mark.asyncio
    async def test_write_bronze_creates_file(self, tmp_path, noop_logger):
        """Test write_bronze creates file in local storage."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        records = [b'{"id": 1, "data": "test"}\n']
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        date = datetime(2023, 1, 1, tzinfo=UTC)

        result = await writer.write_bronze(
            records=iter(records),
            provider="test_provider",
            entity="test_entity",
            date=date,
            batch_id=batch_id,
            run_id=TEST_RUN_ID,
            run_type=TEST_RUN_TYPE,
            ingestion_ts=TEST_INGESTION_TS,
        )

        expected_file = tmp_path / result.relative_path
        assert expected_file.exists()

    @pytest.mark.asyncio
    async def test_write_bronze_generates_correct_key(self, tmp_path, noop_logger):
        """Test that write_bronze generates the correct path."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        records = [b'{"id": 1}\n']
        provider = "test_provider"
        entity = "test_entity"
        date = datetime(2023, 1, 1, tzinfo=UTC)
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))

        result = await writer.write_bronze(
            records=iter(records),
            provider=provider,
            entity=entity,
            date=date,
            batch_id=batch_id,
            run_id=TEST_RUN_ID,
            run_type=TEST_RUN_TYPE,
            ingestion_ts=TEST_INGESTION_TS,
        )

        # Check path contains expected parts (path format: {provider}/{entity}/{date}/batch_{date}_{id}.jsonl.zst)
        # Note: BronzeWriter returns relative path without 'bronze/' prefix (base_path already contains it)
        # Normalize path separators for cross-platform compatibility
        expected_path = "/".join(
            [
                "test_provider",
                "test_entity",
                "2023-01-01",
                "batch_2023-01-01_12345678-1234-5678-1234-567812345678.jsonl.zst",
            ]
        )
        assert result.relative_path.replace("\\", "/") == expected_path

    @pytest.mark.asyncio
    async def test_write_bronze_compresses_with_zstd(self, tmp_path, noop_logger):
        """REQ-DATA-001: Test that data is compressed with zstandard."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        records = [b'{"id": 1, "data": "test"}\n']
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        date = datetime(2023, 1, 1, tzinfo=UTC)

        result = await writer.write_bronze(
            records=iter(records),
            provider="test",
            entity="test",
            date=date,
            batch_id=batch_id,
            run_id=TEST_RUN_ID,
            run_type=TEST_RUN_TYPE,
            ingestion_ts=TEST_INGESTION_TS,
        )

        file_path = tmp_path / result.relative_path
        compressed_data = file_path.read_bytes()

        # Zstandard frames start with magic bytes 0x28, 0xB5, 0x2F, 0xFD (little-endian)
        assert compressed_data.startswith(b"\x28\xb5\x2f\xfd")

        # Decompress to verify content using stream reader
        decompressor = zstd.ZstdDecompressor()
        with decompressor.stream_reader(io.BytesIO(compressed_data)) as reader:
            decompressed_data = reader.read()

        assert decompressed_data == b'{"id": 1, "data": "test"}\n'

    @pytest.mark.asyncio
    async def test_write_bronze_with_no_records(self, tmp_path, noop_logger):
        """Test that write_bronze raises error if there are no records."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        records = []
        provider = "test_provider"
        entity = "test_entity"
        date = datetime(2023, 1, 1, tzinfo=UTC)
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
                ingestion_ts=TEST_INGESTION_TS,
            )

    @pytest.mark.asyncio
    async def test_write_bronze_save_json_copy(self, tmp_path, noop_logger):
        """Test that write_bronze saves JSON copy if save_json is True."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
            save_json=True,
        )

        records = [b'{"id": 1}\n']
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        date = datetime(2023, 1, 1, tzinfo=UTC)

        await writer.write_bronze(
            records=iter(records),
            provider="test_provider",
            entity="test_entity",
            date=date,
            batch_id=batch_id,
            run_id=TEST_RUN_ID,
            run_type=TEST_RUN_TYPE,
            ingestion_ts=TEST_INGESTION_TS,
        )

        # Check JSON file was created (now in same directory as zst files)
        json_path = (
            tmp_path
            / "test_provider"
            / "test_entity"
            / "2023-01-01"
            / "batch_2023-01-01_12345678-1234-5678-1234-567812345678.jsonl"
        )
        assert json_path.exists()
        assert json_path.read_bytes() == b'{"id": 1}\n'

    @pytest.mark.asyncio
    async def test_read_bronze(self, tmp_path, noop_logger):
        """Test read_bronze reads file."""
        # Create a compressed file manually for deterministic testing
        records_data = [{"id": 1, "data": "test"}, {"id": 2, "data": "test2"}]
        jsonl_data = "\n".join(json.dumps(r) for r in records_data) + "\n"

        # Compress with zstd
        compressor = zstd.ZstdCompressor(level=3)
        compressed = compressor.compress(jsonl_data.encode("utf-8"))

        # Create directory structure (path format: {provider}/{entity}/{date}/)
        bronze_dir = tmp_path / "test_provider" / "test_entity" / "2023-01-01"
        bronze_dir.mkdir(parents=True)
        test_file = bronze_dir / "batch_test.jsonl.zst"
        test_file.write_bytes(compressed)

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        # Read it back
        read_records = []
        async for record in writer.read_bronze(
            "test_provider/test_entity/2023-01-01/batch_test.jsonl.zst"
        ):
            read_records.append(record)

        assert len(read_records) == 2
        assert read_records[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_list_batches(self, tmp_path, noop_logger):
        """Test list_batches."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        # Write two batches
        date = datetime(2023, 1, 1, tzinfo=UTC)
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
                ingestion_ts=TEST_INGESTION_TS,
            )

        batches = await writer.list_batches("test_provider", "test_entity", date)

        assert len(batches) == 2
        assert all(b.endswith(".jsonl.zst") for b in batches)

    @pytest.mark.asyncio
    async def test_list_batches_nonexistent(self, tmp_path, noop_logger):
        """Test list_batches returns empty for nonexistent path."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        batches = await writer.list_batches(
            "nonexistent",
            "entity",
            datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )

        assert batches == []

    @pytest.mark.asyncio
    async def test_writes_metadata_file(self, tmp_path, noop_logger):
        """Test that write_bronze creates metadata file."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        records = [b'{"id": 1}\n']
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        date = datetime(2023, 1, 1, tzinfo=UTC)

        result = await writer.write_bronze(
            records=iter(records),
            provider="test_provider",
            entity="test_entity",
            date=date,
            batch_id=batch_id,
            run_id=TEST_RUN_ID,
            run_type=TEST_RUN_TYPE,
            ingestion_ts=TEST_INGESTION_TS,
        )

        # Check metadata file was created
        meta_path = (tmp_path / result.relative_path).with_suffix(".zst.meta.json")
        assert meta_path.exists()

        # Verify metadata content
        meta_content = json.loads(meta_path.read_text())
        assert meta_content["provider"] == "test_provider"
        assert meta_content["entity"] == "test_entity"
        assert meta_content["batch_id"] == "12345678-1234-5678-1234-567812345678"
        assert meta_content["run_type"] == "incremental"


@pytest.mark.unit
class TestSilverWriter:
    """Test SilverWriter functionality."""

    def test_silver_writer_initialization(self, noop_logger):
        """Test SilverWriter can be initialized."""
        writer = SilverWriter(base_path=SILVER_DELTA_ROOT, logger=noop_logger)
        # Normalize paths for cross-platform comparison (Windows uses backslashes)
        import os.path
        assert os.path.normpath(writer.base_path) == os.path.normpath(SILVER_DELTA_ROOT)

    @pytest.mark.asyncio
    async def test_write_silver_creates_new_table(
        self, mock_silver_writer, noop_logger
    ):
        """Test write_silver creates table if not exists."""
        from deltalake.exceptions import TableNotFoundError

        mock_delta_table, mock_write_deltalake = mock_silver_writer
        mock_delta_table.side_effect = TableNotFoundError("Not found")

        writer = SilverWriter(base_path=SILVER_DELTA_ROOT, logger=noop_logger)

        # Mock the _get_table_schema method to return None (no existing table)
        writer._get_table_schema = AsyncMock(return_value=None)

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

    @pytest.mark.asyncio
    async def test_write_silver_merge_existing_table(
        self, mock_silver_writer, noop_logger
    ):
        """Test write_silver merges into existing table."""
        import pyarrow as pa

        mock_delta_table, _mock_write_deltalake = mock_silver_writer
        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        # Mock schema to match records (avoid schema drift error)
        existing_schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("value", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        mock_schema = MagicMock()
        mock_schema.to_arrow.return_value = existing_schema
        mock_table_instance.schema.return_value = mock_schema

        # Set up merge chain
        mock_merge = MagicMock()
        mock_table_instance.merge.return_value = mock_merge
        mock_merge.when_matched_update_all.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge

        # Mock version() to return an integer for SilverWriteResult
        mock_table_instance.version.return_value = 1

        writer = SilverWriter(base_path=SILVER_DELTA_ROOT, logger=noop_logger)
        table_path = Path(SILVER_DELTA_ROOT) / "test_table"
        table_path.mkdir(parents=True, exist_ok=True)
        (table_path / "part-00000.parquet").write_bytes(b"parquet-marker")

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

        # Use same schema as existing_schema mock
        await writer.write_silver(
            table_name="test_table",
            records=records,
            primary_keys=["id"],
            schema=existing_schema,
        )

        mock_table_instance.merge.assert_called_once()

    @pytest.mark.usefixtures("mock_silver_writer")
    @pytest.mark.asyncio
    async def test_write_silver_empty_records_raises_error(self, noop_logger):
        writer = SilverWriter(base_path=SILVER_DELTA_ROOT, logger=noop_logger)

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

    @pytest.mark.asyncio
    async def test_gold_writer_sorts_columns(self, mock_gold_writer_deps, noop_logger):
        """Test that GoldWriter sorts columns alphabetically in _to_arrow_table."""
        from pandera.pandas import Column, DataFrameSchema

        _mock_delta_table, mock_write_deltalake = mock_gold_writer_deps

        writer = GoldWriter(base_path=GOLD_ROOT, logger=noop_logger)

        # Records with mixed key order
        records = [
            {"b": 2, "a": 1, "c": 3},
            {"c": 30, "b": 20, "a": 10},
        ]

        # Create a strict schema matching the records
        strict_schema = DataFrameSchema(
            {"a": Column(int), "b": Column(int), "c": Column(int)},
            strict=True,
        )

        await writer.write_gold(
            table_name="test_table",
            records=records,
            schema=strict_schema,
            mode="overwrite",
        )

        # Verify write_deltalake was called
        assert mock_write_deltalake.called

        # Get the arrow table passed to write_deltalake
        call_args = mock_write_deltalake.call_args
        kwargs = call_args.kwargs

        data = kwargs.get("data")
        assert data is not None
        assert isinstance(data, pa.Table)

        schema = data.schema
        column_names = schema.names

        assert column_names == [
            "a",
            "b",
            "c",
        ], f"Expected sorted columns ['a', 'b', 'c'], got {column_names}"
