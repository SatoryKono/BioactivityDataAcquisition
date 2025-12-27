"""Unit tests for DeltaWriter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.exceptions import SchemaViolationError
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


@pytest.fixture
def noop_logger():
    """Provide a NoOpLogger for tests."""
    return NoOpLogger()


@pytest.fixture
def valid_records():
    """Create valid records with all required metadata."""
    return [
        {
            "entity_id": "CHEMBL123",
            "value": 5.5,
            "_run_id": "uuid-123",
            "_run_type": "incremental",
            "_source_batch_id": "batch-456",
            "_ingestion_ts": "2025-01-15T12:00:00Z",
        },
        {
            "entity_id": "CHEMBL456",
            "value": 7.2,
            "_run_id": "uuid-123",
            "_run_type": "incremental",
            "_source_batch_id": "batch-456",
            "_ingestion_ts": "2025-01-15T12:00:00Z",
        },
    ]


@pytest.mark.unit
class TestDeltaWriterInit:
    """Tests for DeltaWriter initialization."""

    def test_init_strips_trailing_slash(self, noop_logger):
        """Test that trailing slash is stripped from base_path."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket/path/", logger=noop_logger, require_lock=False)
        assert writer.base_path == "s3://bucket/path"

    def test_init_with_csv_exporter(self, noop_logger):
        """Test initialization with CSV exporter."""
        from unittest.mock import MagicMock

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_exporter = MagicMock()
        writer = DeltaWriter(
            base_path="/tmp/silver", logger=noop_logger, csv_exporter=mock_exporter, require_lock=False
        )
        assert writer.csv_exporter is mock_exporter

    def test_init_without_csv_exporter(self, noop_logger):
        """Test initialization without CSV exporter."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)
        assert writer.csv_exporter is None


@pytest.mark.unit
class TestDeltaWriterValidation:
    """Tests for DeltaWriter validation."""

    @pytest.mark.asyncio
    async def test_write_silver_invalid_mode_raises(self, noop_logger, valid_records):
        """Test write_silver raises ValueError for invalid mode."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        import pyarrow as pa

        writer = DeltaWriter(base_path="s3://bucket", logger=noop_logger, require_lock=False)
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
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        import pyarrow as pa

        writer = DeltaWriter(base_path="s3://bucket", logger=noop_logger, require_lock=False)

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
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket", logger=noop_logger, require_lock=False)
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
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket", logger=noop_logger, require_lock=False)
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
class TestDeltaWriterWriteModeEnum:
    """Tests for SilverWriteMode enum."""

    def test_silver_write_mode_values(self):
        """Test all valid SilverWriteMode values."""
        from bioetl.infrastructure.storage.delta_writer import SilverWriteMode

        assert SilverWriteMode.MERGE.value == "merge"
        assert SilverWriteMode.APPEND.value == "append"
        assert SilverWriteMode.DELETE.value == "delete"

    def test_silver_write_mode_from_string(self):
        """Test creating SilverWriteMode from string."""
        from bioetl.infrastructure.storage.delta_writer import SilverWriteMode

        assert SilverWriteMode("merge") == SilverWriteMode.MERGE
        assert SilverWriteMode("append") == SilverWriteMode.APPEND
        assert SilverWriteMode("delete") == SilverWriteMode.DELETE

    def test_silver_write_mode_invalid_raises(self):
        """Test invalid mode string raises ValueError."""
        from bioetl.infrastructure.storage.delta_writer import SilverWriteMode

        with pytest.raises(ValueError):
            SilverWriteMode("invalid")

        with pytest.raises(ValueError):
            SilverWriteMode("MERGE")  # Case sensitive

    def test_validate_write_mode_method(self, noop_logger):
        """Test _validate_write_mode returns correct enum."""
        from bioetl.infrastructure.storage.delta_writer import (
            DeltaWriter,
            SilverWriteMode,
        )

        writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)

        assert writer._validate_write_mode("merge") == SilverWriteMode.MERGE
        assert writer._validate_write_mode("append") == SilverWriteMode.APPEND
        assert writer._validate_write_mode("delete") == SilverWriteMode.DELETE

        with pytest.raises(ValueError, match="Invalid Silver write mode 'invalid'"):
            writer._validate_write_mode("invalid")

        with pytest.raises(ValueError, match="Allowed"):
            writer._validate_write_mode("overwrite")  # Valid for Gold, not Silver


@pytest.mark.unit
class TestDeltaWriterTablePath:
    """Tests for table path construction."""

    def test_table_path_construction(self, noop_logger):
        """Test table path is constructed correctly."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)

        # Access internal path construction
        table_name = "chembl.activity"
        expected_path = "s3://bucket/silver/chembl/activity"
        actual_path = f"{writer.base_path}/{table_name.replace('.', '/')}"

        assert actual_path == expected_path

    def test_table_path_with_nested_name(self, noop_logger):
        """Test table path with nested table name."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)

        table_name = "provider.schema.table"
        expected_path = "s3://bucket/silver/provider/schema/table"
        actual_path = f"{writer.base_path}/{table_name.replace('.', '/')}"

        assert actual_path == expected_path


@pytest.mark.unit
class TestDeltaWriterMergePredicate:
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


@pytest.mark.unit
class TestDeltaWriterVacuum:
    """Tests for DeltaWriter vacuum operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_vacuum_returns_deleted_files(self, mock_delta_table, noop_logger):
        """Test vacuum returns list of deleted files."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_table_instance.vacuum.return_value = [
            "file1.parquet",
            "file2.parquet",
        ]

        writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)
        result = await writer.vacuum("test.table", retention_hours=168)

        assert len(result) == 2
        mock_table_instance.vacuum.assert_called_once_with(
            retention_hours=168, dry_run=False
        )

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_vacuum_dry_run(self, mock_delta_table, noop_logger):
        """Test vacuum dry run."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_table_instance.vacuum.return_value = ["file1.parquet"]

        writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)
        await writer.vacuum("test.table", retention_hours=24, dry_run=True)

        mock_table_instance.vacuum.assert_called_once_with(
            retention_hours=24, dry_run=True
        )

    @pytest.mark.asyncio
    async def test_vacuum_table_not_found(self, noop_logger):
        """Test vacuum raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)

            with pytest.raises(TableNotFoundError):
                await writer.vacuum("nonexistent.table")


@pytest.mark.unit
class TestDeltaWriterOptimize:
    """Tests for DeltaWriter optimize operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_optimize_returns_metrics(self, mock_delta_table, noop_logger):
        """Test optimize returns compaction metrics."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_optimize = MagicMock()
        mock_table_instance.optimize = mock_optimize
        mock_optimize.compact.return_value = {
            "numFilesAdded": 1,
            "numFilesRemoved": 5,
        }

        writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)
        result = await writer.optimize("test.table")

        assert result["numFilesRemoved"] == 5
        mock_optimize.compact.assert_called_once()

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_optimize_with_partition_filters(self, mock_delta_table, noop_logger):
        """Test optimize with partition filters."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_optimize = MagicMock()
        mock_table_instance.optimize = mock_optimize
        mock_optimize.compact.return_value = {}

        writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)
        await writer.optimize("test.table", partition_filters=[("year", "=", 2025)])

        mock_optimize.compact.assert_called_once_with(
            partition_filters=[("year", "=", 2025)]
        )

    @pytest.mark.asyncio
    async def test_optimize_table_not_found(self, noop_logger):
        """Test optimize raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)

            with pytest.raises(TableNotFoundError):
                await writer.optimize("nonexistent.table")


@pytest.mark.unit
class TestDeltaWriterGetTableInfo:
    """Tests for DeltaWriter get_table_info operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_get_table_info_returns_metadata(self, mock_delta_table, noop_logger):
        """Test get_table_info returns table metadata."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_table_instance.version.return_value = 10
        mock_table_instance.files.return_value = ["file1.parquet", "file2.parquet"]
        mock_schema = MagicMock()
        mock_schema.to_arrow.return_value = {"fields": []}
        mock_table_instance.schema.return_value = mock_schema
        mock_table_instance.metadata.return_value = {"id": "test-table"}

        writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)
        result = await writer.get_table_info("test.table")

        assert result["version"] == 10
        assert result["num_files"] == 2

    @pytest.mark.asyncio
    async def test_get_table_info_table_not_found(self, noop_logger):
        """Test get_table_info raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)

            with pytest.raises(TableNotFoundError):
                await writer.get_table_info("nonexistent.table")


@pytest.mark.unit
class TestDeltaWriterTimeTravel:
    """Tests for DeltaWriter time_travel operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_time_travel_by_version(self, mock_delta_table, noop_logger):
        """Test time_travel by version number."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)
        result = await writer.time_travel("test.table", version=5)

        assert result == mock_table_instance
        mock_delta_table.assert_called_once()

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_time_travel_by_timestamp(self, mock_delta_table, noop_logger):
        """Test time_travel by timestamp."""
        from datetime import datetime

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)
        ts = datetime(2025, 1, 1, 12, 0, 0)
        result = await writer.time_travel("test.table", timestamp=ts)

        assert result == mock_table_instance

    @pytest.mark.asyncio
    async def test_time_travel_both_version_and_timestamp_raises(self, noop_logger):
        """Test time_travel raises ValueError when both version and timestamp given."""
        from datetime import datetime

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)

        with pytest.raises(ValueError, match="Specify either version or timestamp"):
            await writer.time_travel(
                "test.table", version=5, timestamp=datetime(2025, 1, 1)
            )

    @pytest.mark.asyncio
    async def test_time_travel_neither_version_nor_timestamp_raises(self, noop_logger):
        """Test time_travel raises ValueError when neither version nor timestamp given."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)

        with pytest.raises(
            ValueError, match="Must specify either version or timestamp"
        ):
            await writer.time_travel("test.table")

    @pytest.mark.asyncio
    async def test_time_travel_table_not_found(self, noop_logger):
        """Test time_travel raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)

            with pytest.raises(TableNotFoundError):
                await writer.time_travel("nonexistent.table", version=1)


@pytest.mark.unit
class TestDeltaWriterErrorHandling:
    """Tests for error handling in DeltaWriter."""

    @pytest.mark.asyncio
    async def test_write_silver_schema_mismatch_error(self, valid_records, noop_logger):
        """Test write_silver raises SchemaViolationError for schema mismatch."""
        from unittest.mock import patch

        import pyarrow as pa
        from deltalake.exceptions import SchemaMismatchError
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

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

        # First call (schema check) returns TableNotFoundError (new table)
        # Second call (write) raises SchemaMismatchError
        delta_table_mock = MagicMock(
            side_effect=[
                DeltaTableNotFoundError("Not found"),  # Schema check
                SchemaMismatchError("Schema mismatch"),  # Write attempt
            ]
        )

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            delta_table_mock,
        ):
            writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)

            with pytest.raises(SchemaViolationError):
                await writer.write_silver(
                    table_name="test.table",
                    records=valid_records,
                    primary_keys=["entity_id"],
                    schema=schema,
                )

    @pytest.mark.asyncio
    async def test_write_silver_merge_conflict_error(self, valid_records, noop_logger):
        """Test write_silver raises MergeConflictError for merge conflicts."""
        from unittest.mock import MagicMock, patch

        import pyarrow as pa
        from deltalake.exceptions import DeltaError
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import MergeConflictError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

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

        mock_table = MagicMock()
        mock_merge = MagicMock()
        mock_table.merge.return_value = mock_merge
        mock_merge.when_matched_update_all.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge
        mock_merge.execute.side_effect = DeltaError("Merge-conflict detected")

        # First call (schema check) returns TableNotFoundError (new table)
        # Second call (write merge) returns mock_table
        delta_table_mock = MagicMock(
            side_effect=[
                DeltaTableNotFoundError("Not found"),  # Schema check
                mock_table,  # Write attempt
            ]
        )

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            delta_table_mock,
        ):
            writer = DeltaWriter(base_path="s3://bucket/silver", logger=noop_logger, require_lock=False)

            with pytest.raises(MergeConflictError):
                await writer.write_silver(
                    table_name="test.table",
                    records=valid_records,
                    primary_keys=["entity_id"],
                    schema=schema,
                )


@pytest.mark.unit
class TestDeltaWriterSchemaDrift:
    """Tests for schema drift detection and handling."""

    @pytest.mark.asyncio
    async def test_get_table_schema_returns_none_for_missing_table(self, noop_logger):
        """Test _get_table_schema returns None when table doesn't exist."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)
            result = await writer._get_table_schema("test.table")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_table_schema_returns_schema_for_existing_table(
        self, noop_logger
    ):
        """Test _get_table_schema returns schema for existing table."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        expected_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = expected_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)
            result = await writer._get_table_schema("test.table")
            assert result == expected_schema

    @pytest.mark.asyncio
    async def test_schema_drift_raises_error_on_new_fields(
        self, valid_records, noop_logger
    ):
        """Test schema drift detection raises error when new fields detected."""
        import pyarrow as pa

        from bioetl.domain.exceptions import SchemaEvolutionError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        # Existing schema has fewer fields than incoming records
        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)

            with pytest.raises(SchemaEvolutionError) as exc_info:
                await writer._check_schema_drift("test.table", valid_records, "error")

            assert "value" in exc_info.value.new_fields
            assert exc_info.value.table == "test.table"

    @pytest.mark.asyncio
    async def test_schema_drift_raises_error_on_removed_fields(self, noop_logger):
        """Test schema drift detection raises error when fields are removed."""
        import pyarrow as pa

        from bioetl.domain.exceptions import SchemaEvolutionError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        # Existing schema has more fields than incoming records
        existing_schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("extra_field", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        records = [
            {
                "entity_id": "CHEMBL123",
                "_run_id": "uuid-123",
                "_run_type": "incremental",
                "_source_batch_id": "batch-456",
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            }
        ]

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)

            with pytest.raises(SchemaEvolutionError) as exc_info:
                await writer._check_schema_drift("test.table", records, "error")

            assert "extra_field" in exc_info.value.removed_fields
            assert exc_info.value.table == "test.table"

    @pytest.mark.asyncio
    async def test_schema_drift_evolve_mode_does_not_raise(
        self, valid_records, noop_logger
    ):
        """Test schema drift with evolve mode proceeds without error."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)

            # Should not raise
            await writer._check_schema_drift("test.table", valid_records, "evolve")

    @pytest.mark.asyncio
    async def test_schema_drift_ignore_mode_does_not_raise(
        self, valid_records, noop_logger
    ):
        """Test schema drift with ignore mode proceeds without error."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)

            # Should not raise
            await writer._check_schema_drift("test.table", valid_records, "ignore")

    @pytest.mark.asyncio
    async def test_schema_drift_no_error_when_no_drift(
        self, valid_records, noop_logger
    ):
        """Test no error raised when schema matches."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        # Schema matches incoming records exactly
        existing_schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)

            # Should not raise even in error mode
            await writer._check_schema_drift("test.table", valid_records, "error")

    @pytest.mark.asyncio
    async def test_schema_drift_skipped_for_new_table(self, valid_records, noop_logger):
        """Test schema drift check is skipped for new tables."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)

            # Should not raise for new table
            await writer._check_schema_drift("test.table", valid_records, "error")

    @pytest.mark.asyncio
    async def test_schema_drift_skipped_for_empty_records(self, noop_logger):
        """Test schema drift check is skipped for empty records."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)

            # Should not raise for empty records
            await writer._check_schema_drift("test.table", [], "error")

    @pytest.mark.asyncio
    async def test_schema_drift_error_mode(self, valid_records, noop_logger):
        """Test schema drift error mode raises SchemaEvolutionError via write_silver.

        Acceptance criterion for M4: Schema Drift Handling.
        When on_schema_mismatch='error' is set and schema drift is detected,
        write_silver must raise SchemaEvolutionError before writing.
        """
        import pyarrow as pa

        from bioetl.domain.exceptions import SchemaEvolutionError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        # Schema for incoming records
        incoming_schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        # Existing table has a different schema (missing 'value' field)
        existing_table_schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_table_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)

            # write_silver with on_schema_mismatch="error" should raise
            with pytest.raises(SchemaEvolutionError) as exc_info:
                await writer.write_silver(
                    table_name="test.table",
                    records=valid_records,
                    primary_keys=["entity_id"],
                    schema=incoming_schema,
                    mode="merge",
                    on_schema_mismatch="error",
                )

            # Verify error details
            assert "value" in exc_info.value.new_fields
            assert exc_info.value.table == "test.table"


@pytest.mark.unit
class TestDeltaWriterWriteModePolicy:
    """Tests for WriteModePolicy integration in DeltaWriter."""

    def test_init_with_default_policy(self, noop_logger):
        """Test DeltaWriter creates default WriteModePolicy when not provided."""
        from bioetl.domain.medallion import WriteModePolicy
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)
        assert isinstance(writer._write_policy, WriteModePolicy)

    def test_init_with_custom_policy(self, noop_logger):
        """Test DeltaWriter accepts custom WriteModePolicy."""
        from bioetl.domain.medallion import WriteModePolicy
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        custom_policy = WriteModePolicy()
        writer = DeltaWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            write_policy=custom_policy,
            require_lock=False,
        )
        assert writer._write_policy is custom_policy

    def test_init_with_metrics_port(self, noop_logger):
        """Test DeltaWriter accepts optional MetricsPort."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_metrics = MagicMock()
        writer = DeltaWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            metrics=mock_metrics,
            require_lock=False,
        )
        assert writer._metrics is mock_metrics

    def test_to_policy_write_mode_merge(self, noop_logger):
        """Test MERGE mode maps correctly."""
        from bioetl.domain.medallion import WriteMode
        from bioetl.infrastructure.storage.delta_writer import (
            DeltaWriter,
            SilverWriteMode,
        )

        writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)
        result = writer._to_policy_write_mode(SilverWriteMode.MERGE)
        assert result == WriteMode.MERGE

    def test_to_policy_write_mode_append(self, noop_logger):
        """Test APPEND mode maps correctly."""
        from bioetl.domain.medallion import WriteMode
        from bioetl.infrastructure.storage.delta_writer import (
            DeltaWriter,
            SilverWriteMode,
        )

        writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)
        result = writer._to_policy_write_mode(SilverWriteMode.APPEND)
        assert result == WriteMode.APPEND

    def test_to_policy_write_mode_delete_maps_to_overwrite(self, noop_logger):
        """Test DELETE mode maps to OVERWRITE (critical for policy enforcement)."""
        from bioetl.domain.medallion import WriteMode
        from bioetl.infrastructure.storage.delta_writer import (
            DeltaWriter,
            SilverWriteMode,
        )

        writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)
        result = writer._to_policy_write_mode(SilverWriteMode.DELETE)
        assert result == WriteMode.OVERWRITE

    def test_enforce_write_policy_allows_merge(self, noop_logger):
        """Test policy enforcement allows MERGE mode for Silver."""
        from bioetl.infrastructure.storage.delta_writer import (
            DeltaWriter,
            SilverWriteMode,
        )

        writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)
        # Should not raise
        writer._enforce_write_policy(SilverWriteMode.MERGE, "test.table")

    def test_enforce_write_policy_allows_append(self, noop_logger):
        """Test policy enforcement allows APPEND mode for Silver."""
        from bioetl.infrastructure.storage.delta_writer import (
            DeltaWriter,
            SilverWriteMode,
        )

        writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)
        # Should not raise
        writer._enforce_write_policy(SilverWriteMode.APPEND, "test.table")

    def test_enforce_write_policy_rejects_delete(self, noop_logger):
        """Test policy enforcement rejects DELETE mode for Silver (maps to OVERWRITE)."""
        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.delta_writer import (
            DeltaWriter,
            SilverWriteMode,
        )

        writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)
        with pytest.raises(PolicyViolationError) as exc_info:
            writer._enforce_write_policy(SilverWriteMode.DELETE, "test.table")
        assert "silver does not allow overwrite" in str(exc_info.value)

    def test_enforce_write_policy_increments_metric_on_violation(self, noop_logger):
        """Test policy violation increments policy_violations_total metric."""
        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.delta_writer import (
            DeltaWriter,
            SilverWriteMode,
        )

        mock_metrics = MagicMock()
        writer = DeltaWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            metrics=mock_metrics,
            require_lock=False,
        )

        with pytest.raises(PolicyViolationError):
            writer._enforce_write_policy(SilverWriteMode.DELETE, "test.table")

        mock_metrics.increment_counter.assert_called_once_with(
            "policy_violations_total",
            1,
            {"layer": "silver", "mode": "overwrite"},
        )

    def test_enforce_write_policy_logs_error_on_violation(self, noop_logger):
        """Test policy violation logs error with context."""
        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.delta_writer import (
            DeltaWriter,
            SilverWriteMode,
        )

        mock_logger = MagicMock()
        writer = DeltaWriter(base_path="/tmp/silver", logger=mock_logger, require_lock=False)

        with pytest.raises(PolicyViolationError):
            writer._enforce_write_policy(SilverWriteMode.DELETE, "test.table")

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "Write mode policy violation"
        assert call_args[1]["layer"] == "silver"
        assert call_args[1]["mode"] == "delete"
        assert call_args[1]["policy_mode"] == "overwrite"
        assert call_args[1]["table"] == "test.table"

    @pytest.mark.asyncio
    async def test_write_silver_delete_mode_raises_policy_violation(
        self, valid_records, noop_logger
    ):
        """Test write_silver with delete mode raises PolicyViolationError.

        This is the critical acceptance criterion: write_silver(mode="delete")
        must raise PolicyViolationError because DELETE maps to OVERWRITE
        which is not allowed for Silver layer.
        """
        import pyarrow as pa

        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

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

        writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)

        with pytest.raises(PolicyViolationError) as exc_info:
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="delete",
            )
        assert "silver does not allow overwrite" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_write_silver_merge_mode_passes_policy(
        self, valid_records, noop_logger
    ):
        """Test write_silver with merge mode passes policy validation."""
        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

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

        with (
            patch(
                "bioetl.infrastructure.storage.delta_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch(
                "bioetl.infrastructure.storage.delta_writer.write_deltalake"
            ) as mock_write,
        ):
            writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)

            # Should not raise PolicyViolationError
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="merge",
            )

            # Verify write was called (policy passed)
            mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_silver_append_mode_passes_policy(
        self, valid_records, noop_logger
    ):
        """Test write_silver with append mode passes policy validation."""
        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

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

        with (
            patch(
                "bioetl.infrastructure.storage.delta_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch(
                "bioetl.infrastructure.storage.delta_writer.write_deltalake"
            ) as mock_write,
        ):
            writer = DeltaWriter(base_path="/tmp/silver", logger=noop_logger, require_lock=False)

            # Should not raise PolicyViolationError
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="append",
            )

            # Verify write was called (policy passed)
            mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_silver_delete_mode_increments_metric(
        self, valid_records, noop_logger
    ):
        """Test write_silver with delete mode increments policy_violations_total."""
        import pyarrow as pa

        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

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

        mock_metrics = MagicMock()
        writer = DeltaWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            metrics=mock_metrics,
            require_lock=False,
        )

        with pytest.raises(PolicyViolationError):
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="delete",
            )

        mock_metrics.increment_counter.assert_called_once_with(
            "policy_violations_total",
            1,
            {"layer": "silver", "mode": "overwrite"},
        )
