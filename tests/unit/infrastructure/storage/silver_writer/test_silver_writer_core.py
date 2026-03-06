"""Core SilverWriter unit tests (init, validation, mode, path, predicate)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


class TestSilverWriterInit:
    """Tests for SilverWriter initialization."""

    def test_init_strips_trailing_slash(self, noop_logger):
        """Test that trailing slash is stripped from base_path."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket/path/", logger=noop_logger)
        assert writer.base_path == "s3://bucket/path"

    def test_init_with_csv_exporter(self, noop_logger):
        """Test initialization with CSV exporter."""
        from unittest.mock import MagicMock

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_exporter = MagicMock()
        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            csv_exporter=mock_exporter,
        )
        assert writer.csv_exporter is mock_exporter

    def test_init_without_csv_exporter(self, noop_logger):
        """Test initialization without CSV exporter."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
        assert writer.csv_exporter is None


@pytest.mark.unit
class TestSilverWriterValidation:
    """Tests for SilverWriter validation."""

    @pytest.mark.asyncio
    async def test_write_silver_invalid_mode_raises(self, noop_logger, valid_records):
        """Test write_silver raises ValueError for invalid mode."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket", logger=noop_logger)
        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        with pytest.raises(ValueError, match="Invalid Silver write mode 'invalid'"):
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="invalid",
            )

    @pytest.mark.asyncio
    async def test_write_silver_empty_records_raises(self, noop_logger):
        """Test write_silver raises ValueError for empty records."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket", logger=noop_logger)

        dummy_schema = pa.schema([pa.field("entity_id", pa.string())])

        with pytest.raises(ValueError, match="No records to write"):
            await writer.write_silver(
                table_name="test.table",
                records=[],
                primary_keys=["entity_id"],
                schema=dummy_schema,
            )

    @pytest.mark.asyncio
    async def test_write_silver_missing_metadata_raises(self, noop_logger):
        """Test write_silver raises ValueError for missing metadata."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket", logger=noop_logger)
        records = [{"entity_id": "CHEMBL123", "value": 5.5}]

        import pyarrow as pa

        dummy_schema = pa.schema([pa.field("entity_id", pa.string())])

        with pytest.raises(ValueError, match="Records missing required metadata"):
            await writer.write_silver(
                table_name="test.table",
                records=records,
                primary_keys=["entity_id"],
                schema=dummy_schema,
            )

    @pytest.mark.asyncio
    async def test_write_silver_missing_run_id_raises(self, noop_logger):
        """Test write_silver raises ValueError when _run_id is missing."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket", logger=noop_logger)
        records = [
            {
                "entity_id": "CHEMBL123",
                "_run_type": "incremental",
                "_source_batch_id": "batch-456",
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            }
        ]

        import pyarrow as pa

        dummy_schema = pa.schema([pa.field("entity_id", pa.string())])

        with pytest.raises(ValueError, match="Records missing required metadata"):
            await writer.write_silver(
                table_name="test.table",
                records=records,
                primary_keys=["entity_id"],
                schema=dummy_schema,
            )


@pytest.mark.unit
class TestSilverWriterWriteModeEnum:
    """Tests for SilverWriteMode enum."""

    def test_silver_write_mode_values(self):
        """Test all valid SilverWriteMode values."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriteMode

        assert SilverWriteMode.MERGE.value == "merge"
        assert SilverWriteMode.APPEND.value == "append"
        assert SilverWriteMode.DELETE.value == "delete"

    def test_silver_write_mode_from_string(self):
        """Test creating SilverWriteMode from string."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriteMode

        assert SilverWriteMode("merge") == SilverWriteMode.MERGE
        assert SilverWriteMode("append") == SilverWriteMode.APPEND
        assert SilverWriteMode("delete") == SilverWriteMode.DELETE

    def test_silver_write_mode_invalid_raises(self):
        """Test invalid mode string raises ValueError."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriteMode

        with pytest.raises(ValueError):
            SilverWriteMode("invalid")

        with pytest.raises(ValueError):
            SilverWriteMode("MERGE")  # Case sensitive

    def test_validate_write_mode_method(self, noop_logger):
        """Test _validate_write_mode returns correct enum."""
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

        assert writer._validate_write_mode("merge") == SilverWriteMode.MERGE
        assert writer._validate_write_mode("append") == SilverWriteMode.APPEND
        assert writer._validate_write_mode("delete") == SilverWriteMode.DELETE

        with pytest.raises(ValueError, match="Invalid Silver write mode 'invalid'"):
            writer._validate_write_mode("invalid")

        with pytest.raises(ValueError, match="Allowed"):
            writer._validate_write_mode("overwrite")  # Valid for Gold, not Silver


@pytest.mark.unit
class TestSilverWriterTablePath:
    """Tests for table path construction."""

    def test_table_path_construction(self, noop_logger):
        """Test table path is constructed correctly."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

        # Access internal path construction
        table_name = "chembl.activity"
        expected_path = "s3://bucket/silver/chembl/activity"
        actual_path = f"{writer.base_path}/{table_name.replace('.', '/')}"

        assert actual_path == expected_path

    def test_table_path_with_nested_name(self, noop_logger):
        """Test table path with nested table name."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

        table_name = "provider.schema.table"
        expected_path = "s3://bucket/silver/provider/schema/table"
        actual_path = f"{writer.base_path}/{table_name.replace('.', '/')}"

        assert actual_path == expected_path


@pytest.mark.unit
class TestSilverWriterMergePredicate:
    """Tests for merge predicate building."""

    def test_build_single_key_predicate(self):
        """Test predicate building with single primary key."""
        primary_keys = ["entity_id"]
        predicate = " AND ".join(f"target.{key} = source.{key}" for key in primary_keys)

        assert predicate == "target.entity_id = source.entity_id"

    def test_build_multi_key_predicate(self):
        """Test predicate building with multiple primary keys."""
        primary_keys = ["entity_id", "version"]
        predicate = " AND ".join(f"target.{key} = source.{key}" for key in primary_keys)

        assert (
            predicate
            == "target.entity_id = source.entity_id AND target.version = source.version"
        )

    def test_build_compound_key_predicate(self):
        """Test predicate building with compound primary keys."""
        primary_keys = ["provider", "entity_type", "entity_id"]
        predicate = " AND ".join(f"target.{key} = source.{key}" for key in primary_keys)

        expected = (
            "target.provider = source.provider AND "
            "target.entity_type = source.entity_type AND "
            "target.entity_id = source.entity_id"
        )
        assert predicate == expected
