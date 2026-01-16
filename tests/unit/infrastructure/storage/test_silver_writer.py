"""Unit tests for SilverWriter."""

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


@pytest.mark.unit
class TestSilverWriterVacuum:
    """Tests for SilverWriter vacuum operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.retention_manager.DeltaTable")
    async def test_vacuum_returns_deleted_files(self, mock_delta_table, noop_logger):
        """Test vacuum returns list of deleted files."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_table_instance.vacuum.return_value = [
            "file1.parquet",
            "file2.parquet",
        ]

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)
        result = await writer.vacuum("test.table", retention_hours=168)

        assert len(result) == 2
        mock_table_instance.vacuum.assert_called_once_with(
            retention_hours=168, dry_run=False
        )

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.retention_manager.DeltaTable")
    async def test_vacuum_dry_run(self, mock_delta_table, noop_logger):
        """Test vacuum dry run."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_table_instance.vacuum.return_value = ["file1.parquet"]

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)
        await writer.vacuum("test.table", retention_hours=24, dry_run=True)

        mock_table_instance.vacuum.assert_called_once_with(
            retention_hours=24, dry_run=True
        )

    @pytest.mark.asyncio
    async def test_vacuum_table_not_found(self, noop_logger):
        """Test vacuum raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.retention_manager.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

            with pytest.raises(TableNotFoundError):
                await writer.vacuum("nonexistent.table")


@pytest.mark.unit
class TestSilverWriterOptimize:
    """Tests for SilverWriter optimize operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.retention_manager.DeltaTable")
    async def test_optimize_returns_metrics(self, mock_delta_table, noop_logger):
        """Test optimize returns compaction metrics."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_optimize = MagicMock()
        mock_table_instance.optimize = mock_optimize
        mock_optimize.compact.return_value = {
            "numFilesAdded": 1,
            "numFilesRemoved": 5,
        }

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)
        result = await writer.optimize("test.table")

        assert result["numFilesRemoved"] == 5
        mock_optimize.compact.assert_called_once()

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.retention_manager.DeltaTable")
    async def test_optimize_with_partition_filters(self, mock_delta_table, noop_logger):
        """Test optimize with partition filters."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_optimize = MagicMock()
        mock_table_instance.optimize = mock_optimize
        mock_optimize.compact.return_value = {}

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)
        await writer.optimize("test.table", partition_filters=[("year", "=", 2025)])

        mock_optimize.compact.assert_called_once_with(
            partition_filters=[("year", "=", 2025)]
        )

    @pytest.mark.asyncio
    async def test_optimize_table_not_found(self, noop_logger):
        """Test optimize raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.retention_manager.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

            with pytest.raises(TableNotFoundError):
                await writer.optimize("nonexistent.table")


@pytest.mark.unit
class TestSilverWriterGetTableInfo:
    """Tests for SilverWriter get_table_info operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.retention_manager.DeltaTable")
    async def test_get_table_info_returns_metadata(self, mock_delta_table, noop_logger):
        """Test get_table_info returns table metadata."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_table_instance.version.return_value = 10
        mock_table_instance.file_uris.return_value = ["file1.parquet", "file2.parquet"]
        mock_schema = MagicMock()
        mock_schema.to_arrow.return_value = {"fields": []}
        mock_table_instance.schema.return_value = mock_schema
        mock_table_instance.metadata.return_value = {"id": "test-table"}

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)
        result = await writer.get_table_info("test.table")

        assert result["version"] == 10
        assert result["num_files"] == 2

    @pytest.mark.asyncio
    async def test_get_table_info_table_not_found(self, noop_logger):
        """Test get_table_info raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.retention_manager.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

            with pytest.raises(TableNotFoundError):
                await writer.get_table_info("nonexistent.table")


@pytest.mark.unit
class TestSilverWriterTimeTravel:
    """Tests for SilverWriter time_travel operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.retention_manager.DeltaTable")
    async def test_time_travel_by_version(self, mock_delta_table, noop_logger):
        """Test time_travel by version number."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)
        result = await writer.time_travel("test.table", version=5)

        assert result == mock_table_instance
        mock_delta_table.assert_called_once()

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.retention_manager.DeltaTable")
    async def test_time_travel_by_timestamp(self, mock_delta_table, noop_logger):
        """Test time_travel by timestamp."""
        from datetime import datetime

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)
        ts = datetime(2025, 1, 1, 12, 0, 0)
        result = await writer.time_travel("test.table", timestamp=ts)

        assert result == mock_table_instance

    @pytest.mark.asyncio
    async def test_time_travel_both_version_and_timestamp_raises(self, noop_logger):
        """Test time_travel raises ValueError when both version and timestamp given."""
        from datetime import datetime

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

        with pytest.raises(ValueError, match="Specify either version or timestamp"):
            await writer.time_travel(
                "test.table", version=5, timestamp=datetime(2025, 1, 1)
            )

    @pytest.mark.asyncio
    async def test_time_travel_neither_version_nor_timestamp_raises(self, noop_logger):
        """Test time_travel raises ValueError when neither version nor timestamp given."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

        with pytest.raises(
            ValueError, match="Must specify either version or timestamp"
        ):
            await writer.time_travel("test.table")

    @pytest.mark.asyncio
    async def test_time_travel_table_not_found(self, noop_logger):
        """Test time_travel raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.retention_manager.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

            with pytest.raises(TableNotFoundError):
                await writer.time_travel("nonexistent.table", version=1)


@pytest.mark.unit
class TestSilverWriterErrorHandling:
    """Tests for error handling in SilverWriter."""

    @pytest.mark.asyncio
    async def test_write_silver_schema_mismatch_error(self, valid_records, noop_logger):
        """Test write_silver raises SchemaViolationError for schema mismatch."""
        from unittest.mock import patch

        import pyarrow as pa
        from deltalake.exceptions import SchemaMismatchError
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

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

        # Patch both modules: base_delta_writer for _get_table_schema, silver_writer for _write_merge
        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                delta_table_mock,
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                delta_table_mock,
            ),
        ):
            writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

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
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

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

        # Patch both modules: base_delta_writer for _get_table_schema, silver_writer for _write_merge
        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                delta_table_mock,
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                delta_table_mock,
            ),
        ):
            writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

            with pytest.raises(MergeConflictError):
                await writer.write_silver(
                    table_name="test.table",
                    records=valid_records,
                    primary_keys=["entity_id"],
                    schema=schema,
                )


@pytest.mark.unit
class TestSilverWriterSchemaDrift:
    """Tests for schema drift detection and handling."""

    @pytest.mark.asyncio
    async def test_get_table_schema_returns_none_for_missing_table(self, noop_logger):
        """Test _get_table_schema returns None when table doesn't exist."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._get_table_schema("test.table")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_table_schema_returns_schema_for_existing_table(
        self, noop_logger
    ):
        """Test _get_table_schema returns schema for existing table."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        expected_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = expected_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        # Patch in base_delta_writer where _get_table_schema is defined
        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._get_table_schema("test.table")
            assert result == expected_schema

    @pytest.mark.asyncio
    async def test_schema_drift_raises_error_on_new_fields(
        self, valid_records, noop_logger
    ):
        """Test schema drift detection raises error when new fields detected."""
        import pyarrow as pa

        from bioetl.domain.exceptions import SchemaEvolutionError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Existing schema has fewer fields than incoming records
        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

            with pytest.raises(SchemaEvolutionError) as exc_info:
                await writer._check_schema_drift("test.table", valid_records, "error")

            assert "value" in exc_info.value.new_fields
            assert exc_info.value.table == "test.table"

    @pytest.mark.asyncio
    async def test_schema_drift_raises_error_on_removed_fields(self, noop_logger):
        """Test schema drift detection raises error when fields are removed."""
        import pyarrow as pa

        from bioetl.domain.exceptions import SchemaEvolutionError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

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
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

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

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

            # Should not raise
            await writer._check_schema_drift("test.table", valid_records, "evolve")

    @pytest.mark.asyncio
    async def test_schema_drift_ignore_mode_does_not_raise(
        self, valid_records, noop_logger
    ):
        """Test schema drift with ignore mode proceeds without error."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

            # Should not raise
            await writer._check_schema_drift("test.table", valid_records, "ignore")

    @pytest.mark.asyncio
    async def test_schema_drift_no_error_when_no_drift(
        self, valid_records, noop_logger
    ):
        """Test no error raised when schema matches."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

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
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

            # Should not raise even in error mode
            await writer._check_schema_drift("test.table", valid_records, "error")

    @pytest.mark.asyncio
    async def test_schema_drift_skipped_for_new_table(self, valid_records, noop_logger):
        """Test schema drift check is skipped for new tables."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

            # Should not raise for new table
            await writer._check_schema_drift("test.table", valid_records, "error")

    @pytest.mark.asyncio
    async def test_schema_drift_skipped_for_empty_records(self, noop_logger):
        """Test schema drift check is skipped for empty records."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

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
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

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
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

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
class TestSilverWriterWriteModePolicy:
    """Tests for WriteModePolicy integration in SilverWriter."""

    def test_init_with_default_policy(self, noop_logger):
        """Test SilverWriter creates default WriteModePolicy when not provided."""
        from bioetl.domain.medallion import WriteModePolicy
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
        assert isinstance(writer._write_policy, WriteModePolicy)

    def test_init_with_custom_policy(self, noop_logger):
        """Test SilverWriter accepts custom WriteModePolicy."""
        from bioetl.domain.medallion import WriteModePolicy
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        custom_policy = WriteModePolicy()
        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            write_policy=custom_policy,
        )
        assert writer._write_policy is custom_policy

    def test_init_with_metrics_port(self, noop_logger):
        """Test SilverWriter accepts optional MetricsPort."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_metrics = MagicMock()
        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            metrics=mock_metrics,
        )
        assert writer._metrics is mock_metrics

    def test_to_policy_write_mode_merge(self, noop_logger):
        """Test MERGE mode maps correctly."""
        from bioetl.domain.medallion import WriteMode
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
        result = writer._to_policy_write_mode(SilverWriteMode.MERGE)
        assert result == WriteMode.MERGE

    def test_to_policy_write_mode_append(self, noop_logger):
        """Test APPEND mode maps correctly."""
        from bioetl.domain.medallion import WriteMode
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
        result = writer._to_policy_write_mode(SilverWriteMode.APPEND)
        assert result == WriteMode.APPEND

    def test_to_policy_write_mode_delete_maps_to_overwrite(self, noop_logger):
        """Test DELETE mode maps to OVERWRITE (critical for policy enforcement)."""
        from bioetl.domain.medallion import WriteMode
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
        result = writer._to_policy_write_mode(SilverWriteMode.DELETE)
        assert result == WriteMode.OVERWRITE

    def test_enforce_write_policy_allows_merge(self, noop_logger):
        """Test policy enforcement allows MERGE mode for Silver."""
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
        # Should not raise
        writer._enforce_write_policy(SilverWriteMode.MERGE, "test.table")

    def test_enforce_write_policy_allows_append(self, noop_logger):
        """Test policy enforcement allows APPEND mode for Silver."""
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
        # Should not raise
        writer._enforce_write_policy(SilverWriteMode.APPEND, "test.table")

    def test_enforce_write_policy_rejects_delete(self, noop_logger):
        """Test policy enforcement rejects DELETE mode for Silver (maps to OVERWRITE)."""
        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
        with pytest.raises(PolicyViolationError) as exc_info:
            writer._enforce_write_policy(SilverWriteMode.DELETE, "test.table")
        assert "silver does not allow overwrite" in str(exc_info.value)

    def test_enforce_write_policy_increments_metric_on_violation(self, noop_logger):
        """Test policy violation increments policy_violations_total metric."""
        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        mock_metrics = MagicMock()
        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            metrics=mock_metrics,
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
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        mock_logger = MagicMock()
        writer = SilverWriter(base_path="/tmp/silver", logger=mock_logger)

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
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

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

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

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

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

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
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.write_deltalake"
            ) as mock_write,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

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

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

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
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.write_deltalake"
            ) as mock_write,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

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
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

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
        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            metrics=mock_metrics,
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


@pytest.mark.unit
class TestSilverWriterClear:
    """Tests for SilverWriter clear operation."""

    def test_clear_nonexistent_base_path_returns_zero(self, noop_logger, tmp_path):
        """Test clear returns 0 when base_path doesn't exist."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        nonexistent = tmp_path / "nonexistent"
        writer = SilverWriter(base_path=str(nonexistent), logger=noop_logger)

        result = writer.clear()
        assert result == 0

    def test_clear_specific_table(self, noop_logger, tmp_path):
        """Test clear removes specific table directory."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Create table structure with _delta_log
        table_path = tmp_path / "chembl" / "activity"
        delta_log = table_path / "_delta_log"
        delta_log.mkdir(parents=True)
        (table_path / "part-00000.parquet").touch()

        writer = SilverWriter(base_path=str(tmp_path), logger=noop_logger)
        result = writer.clear(table_name="chembl.activity")

        assert result == 1
        assert not table_path.exists()

    def test_clear_specific_table_dry_run(self, noop_logger, tmp_path):
        """Test clear dry_run doesn't remove files."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Create table structure
        table_path = tmp_path / "chembl" / "activity"
        delta_log = table_path / "_delta_log"
        delta_log.mkdir(parents=True)

        writer = SilverWriter(base_path=str(tmp_path), logger=noop_logger)
        result = writer.clear(table_name="chembl.activity", dry_run=True)

        assert result == 1
        assert table_path.exists()  # Not deleted due to dry_run

    def test_clear_all_tables(self, noop_logger, tmp_path):
        """Test clear removes all Delta tables."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Create multiple table structures
        for name in ["table1", "table2", "table3"]:
            table_path = tmp_path / name
            (table_path / "_delta_log").mkdir(parents=True)

        writer = SilverWriter(base_path=str(tmp_path), logger=noop_logger)
        result = writer.clear()

        assert result == 3
        assert not (tmp_path / "table1").exists()
        assert not (tmp_path / "table2").exists()
        assert not (tmp_path / "table3").exists()

    def test_clear_ignores_non_delta_directories(self, noop_logger, tmp_path):
        """Test clear ignores directories without _delta_log."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Create Delta table
        delta_table = tmp_path / "delta_table"
        (delta_table / "_delta_log").mkdir(parents=True)

        # Create non-Delta directory
        non_delta = tmp_path / "non_delta"
        non_delta.mkdir()
        (non_delta / "some_file.txt").touch()

        writer = SilverWriter(base_path=str(tmp_path), logger=noop_logger)
        result = writer.clear()

        assert result == 1
        assert not delta_table.exists()
        assert non_delta.exists()  # Not deleted

    def test_get_table_path(self, noop_logger, tmp_path):
        """Test get_table_path returns correct path."""
        from pathlib import Path

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path=str(tmp_path), logger=noop_logger)
        result = writer.get_table_path("chembl.activity")

        assert result == Path(tmp_path) / "chembl" / "activity"


@pytest.mark.unit
class TestSilverWriterAudit:
    """Tests for SilverWriter audit logging."""

    @pytest.mark.asyncio
    async def test_log_silver_audit_skips_when_no_audit(self, noop_logger):
        """Test _log_silver_audit does nothing when audit is None."""
        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

        # Should not raise, just return early
        await writer._log_silver_audit(
            table_name="test.table",
            records=[{"_run_id": "uuid", "_ingestion_ts": "2025-01-01T00:00:00Z"}],
            mode=SilverWriteMode.MERGE,
        )

    @pytest.mark.asyncio
    async def test_log_silver_audit_skips_invalid_run_id(self, noop_logger):
        """Test _log_silver_audit skips when run_id is invalid UUID."""
        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_audit = MagicMock()
        writer = SilverWriter(
            base_path="/tmp/silver", logger=noop_logger, audit=mock_audit
        )

        # Invalid UUID should skip audit logging
        await writer._log_silver_audit(
            table_name="test.table",
            records=[
                {"_run_id": "not-a-uuid", "_ingestion_ts": "2025-01-01T00:00:00Z"}
            ],
            mode=SilverWriteMode.MERGE,
        )

        # Audit should NOT be called due to invalid run_id
        mock_audit.log_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_silver_audit_with_valid_data(self, noop_logger):
        """Test _log_silver_audit logs correctly with valid data."""
        from unittest.mock import AsyncMock
        from uuid import uuid4

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_audit = MagicMock()
        mock_audit.log_write = AsyncMock()

        writer = SilverWriter(
            base_path="/tmp/silver", logger=noop_logger, audit=mock_audit
        )

        valid_uuid = str(uuid4())
        await writer._log_silver_audit(
            table_name="test.table",
            records=[
                {
                    "_run_id": valid_uuid,
                    "_ingestion_ts": "2025-01-01T12:00:00",
                    "_run_type": "incremental",
                    "_source_batch_id": "batch-123",
                }
            ],
            mode=SilverWriteMode.MERGE,
        )

        mock_audit.log_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_silver_audit_with_datetime_ingestion_ts(self, noop_logger):
        """Test _log_silver_audit handles datetime ingestion_ts."""
        from datetime import UTC, datetime
        from unittest.mock import AsyncMock
        from uuid import uuid4

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_audit = MagicMock()
        mock_audit.log_write = AsyncMock()

        writer = SilverWriter(
            base_path="/tmp/silver", logger=noop_logger, audit=mock_audit
        )

        valid_uuid = str(uuid4())
        ingestion_dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        await writer._log_silver_audit(
            table_name="test.table",
            records=[
                {
                    "_run_id": valid_uuid,
                    "_ingestion_ts": ingestion_dt,  # datetime object
                    "_run_type": "backfill",
                    "_source_batch_id": "batch-456",
                }
            ],
            mode=SilverWriteMode.APPEND,
        )

        mock_audit.log_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_silver_audit_fallback_timestamp(self, noop_logger):
        """Test _log_silver_audit uses fallback when ingestion_ts is invalid type."""
        from unittest.mock import AsyncMock
        from uuid import uuid4

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_audit = MagicMock()
        mock_audit.log_write = AsyncMock()

        writer = SilverWriter(
            base_path="/tmp/silver", logger=noop_logger, audit=mock_audit
        )

        valid_uuid = str(uuid4())
        await writer._log_silver_audit(
            table_name="test.table",
            records=[
                {
                    "_run_id": valid_uuid,
                    "_ingestion_ts": 12345,  # Invalid type - will use fallback
                    "_run_type": "rebuild",
                    "_source_batch_id": "batch-789",
                }
            ],
            mode=SilverWriteMode.DELETE,
        )

        mock_audit.log_write.assert_called_once()


@pytest.mark.unit
class TestSilverWriterCsvExport:
    """Tests for SilverWriter CSV export integration."""

    @pytest.mark.asyncio
    async def test_write_silver_with_csv_exporter(self, noop_logger, valid_records):
        """Test write_silver calls CSV exporter when configured."""
        from unittest.mock import AsyncMock

        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_exporter = MagicMock()
        mock_exporter.export = AsyncMock()

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
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch("bioetl.infrastructure.storage.silver_writer.write_deltalake"),
        ):
            writer = SilverWriter(
                base_path="/tmp/silver",
                logger=noop_logger,
                csv_exporter=mock_exporter,
            )

            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="append",
            )

            mock_exporter.export.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_silver_csv_exporter_with_merge_passes_primary_keys(
        self, noop_logger, valid_records
    ):
        """Test CSV exporter receives primary_keys when mode is merge."""
        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_exporter = MagicMock()
        export_calls = []

        async def capture_export(*args, **kwargs):
            export_calls.append(kwargs)

        mock_exporter.export = capture_export

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
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch("bioetl.infrastructure.storage.silver_writer.write_deltalake"),
        ):
            writer = SilverWriter(
                base_path="/tmp/silver",
                logger=noop_logger,
                csv_exporter=mock_exporter,
            )

            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="merge",
            )

            assert len(export_calls) == 1
            assert export_calls[0]["primary_keys"] == ["entity_id"]


@pytest.mark.unit
class TestSilverWriterLineage:
    """Tests for SilverWriter lineage tracking (REQ-LINEAGE-001)."""

    @pytest.mark.asyncio
    async def test_write_silver_without_bronze_refs(self, noop_logger, valid_records):
        """Test write_silver works without bronze_refs (backward compatibility)."""
        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

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
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch("bioetl.infrastructure.storage.silver_writer.write_deltalake"),
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

            # Should not raise when bronze_refs not provided
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="merge",
            )

    @pytest.mark.asyncio
    async def test_write_silver_with_bronze_refs(self, noop_logger, valid_records):
        """Test write_silver accepts bronze_refs parameter."""
        from uuid import uuid4

        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.types import BatchID
        from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

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

        bronze_result = BronzeWriteResult(
            batch_id=BatchID(uuid4()),
            relative_path="v1/chembl/activity/2024-01-15/batch_123.jsonl.zst",
            absolute_path="/data/bronze/v1/chembl/activity/2024-01-15/batch_123.jsonl.zst",
            record_count=100,
            compressed_size=5000,
            uncompressed_size=20000,
            checksum_blake2="abc123def456",
        )

        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch("bioetl.infrastructure.storage.silver_writer.write_deltalake"),
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

            # Should not raise with bronze_refs
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="merge",
                bronze_refs=[bronze_result],
            )

    @pytest.mark.asyncio
    async def test_write_silver_metadata_includes_bronze_paths(
        self, noop_logger, valid_records
    ):
        """Test _write_silver_metadata populates bronze_paths from bronze_refs."""
        from uuid import uuid4

        from bioetl.domain.types import BatchID
        from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        bronze_result_1 = BronzeWriteResult(
            batch_id=BatchID(uuid4()),
            relative_path="v1/chembl/activity/2024-01-15/batch_001.jsonl.zst",
            absolute_path="/data/bronze/v1/chembl/activity/2024-01-15/batch_001.jsonl.zst",
            record_count=50,
            compressed_size=2500,
            uncompressed_size=10000,
            checksum_blake2="abc123",
        )

        bronze_result_2 = BronzeWriteResult(
            batch_id=BatchID(uuid4()),
            relative_path="v1/chembl/activity/2024-01-15/batch_002.jsonl.zst",
            absolute_path="/data/bronze/v1/chembl/activity/2024-01-15/batch_002.jsonl.zst",
            record_count=50,
            compressed_size=2500,
            uncompressed_size=10000,
            checksum_blake2="def456",
        )

        mock_metadata_writer = MagicMock()
        write_calls = []

        async def capture_write(table_path, metadata):
            write_calls.append({"table_path": table_path, "metadata": metadata})

        mock_metadata_writer.write_silver_metadata = capture_write

        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            metadata_writer=mock_metadata_writer,
        )

        await writer._write_silver_metadata(
            table_path="/tmp/silver/test/table",
            records=valid_records,
            primary_keys=["entity_id"],
            mode=SilverWriteMode.MERGE,
            bronze_refs=[bronze_result_1, bronze_result_2],
        )

        # Verify metadata writer was called with bronze_paths
        assert len(write_calls) == 1
        metadata = write_calls[0]["metadata"]
        lineage = metadata.lineage
        assert len(lineage.bronze_paths) == 2
        assert (
            "v1/chembl/activity/2024-01-15/batch_001.jsonl.zst" in lineage.bronze_paths
        )
        assert (
            "v1/chembl/activity/2024-01-15/batch_002.jsonl.zst" in lineage.bronze_paths
        )

    @pytest.mark.asyncio
    async def test_write_silver_metadata_empty_bronze_paths_when_no_refs(
        self, noop_logger, valid_records
    ):
        """Test _write_silver_metadata has empty bronze_paths when bronze_refs=None."""
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        mock_metadata_writer = MagicMock()
        write_calls = []

        async def capture_write(table_path, metadata):
            write_calls.append({"table_path": table_path, "metadata": metadata})

        mock_metadata_writer.write_silver_metadata = capture_write

        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            metadata_writer=mock_metadata_writer,
        )

        await writer._write_silver_metadata(
            table_path="/tmp/silver/test/table",
            records=valid_records,
            primary_keys=["entity_id"],
            mode=SilverWriteMode.MERGE,
            bronze_refs=None,  # No bronze refs
        )

        # Verify metadata writer was called with empty bronze_paths
        assert len(write_calls) == 1
        metadata = write_calls[0]["metadata"]
        lineage = metadata.lineage
        assert lineage.bronze_paths == []


@pytest.mark.unit
class TestSilverWriterDQMetrics:
    """Tests for SilverWriter DQ metrics integration (REQ-DQ-001)."""

    @pytest.mark.asyncio
    async def test_compute_dq_metrics_returns_batch_dq_metrics(
        self, noop_logger, valid_records
    ):
        """Test _compute_dq_metrics returns BatchDQMetrics."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._compute_dq_metrics("test.table", valid_records)

            assert isinstance(result, BatchDQMetrics)
            assert result.total_records == 2
            assert result.valid_records == 2
            assert result.error_records == 0

    @pytest.mark.asyncio
    async def test_compute_dq_metrics_includes_column_stats(
        self, noop_logger, valid_records
    ):
        """Test _compute_dq_metrics computes column statistics."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._compute_dq_metrics("test.table", valid_records)

            # Should have column stats for non-internal fields
            assert "entity_id" in result.column_stats
            assert "value" in result.column_stats
            # Internal fields should be excluded
            assert "_run_id" not in result.column_stats
            assert "_ingestion_ts" not in result.column_stats

    @pytest.mark.asyncio
    async def test_compute_dq_metrics_detects_schema_drift(self, noop_logger):
        """Test _compute_dq_metrics detects schema drift when table exists."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Existing table has fewer fields
        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        records = [
            {
                "entity_id": "CHEMBL123",
                "new_field": "value",  # New field
                "_run_id": "uuid-123",
                "_run_type": "incremental",
                "_source_batch_id": "batch-456",
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            }
        ]

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._compute_dq_metrics("test.table", records)

            assert result.schema_drift is not None
            assert "new_field" in result.schema_drift.new_fields

    @pytest.mark.asyncio
    async def test_compute_dq_metrics_no_drift_for_new_table(
        self, noop_logger, valid_records
    ):
        """Test _compute_dq_metrics returns no drift for new tables."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._compute_dq_metrics("test.table", valid_records)

            assert result.schema_drift is None

    @pytest.mark.asyncio
    async def test_detect_schema_drift_returns_schema_drift_info(self, noop_logger):
        """Test _detect_schema_drift returns SchemaDriftInfo."""
        import pyarrow as pa

        from bioetl.domain.value_objects.dq_metrics import SchemaDriftInfo
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        records = [{"entity_id": "CHEMBL123", "new_field": "value"}]

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._detect_schema_drift("test.table", records)

            assert isinstance(result, SchemaDriftInfo)
            assert "new_field" in result.new_fields

    @pytest.mark.asyncio
    async def test_detect_schema_drift_critical_for_missing_business_fields(
        self, noop_logger
    ):
        """Test _detect_schema_drift returns critical status for missing business fields."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Existing schema has business field that's missing in incoming records
        existing_schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("important_field", pa.string()),  # Business field
                pa.field("_run_id", pa.string()),
            ]
        )
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        # Incoming records missing 'important_field'
        records = [{"entity_id": "CHEMBL123", "_run_id": "uuid-123"}]

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._detect_schema_drift("test.table", records)

            assert result is not None
            assert result.status == "critical"
            assert "important_field" in result.missing_fields

    @pytest.mark.asyncio
    async def test_detect_schema_drift_warn_for_many_new_fields(self, noop_logger):
        """Test _detect_schema_drift returns warn status for >3 new fields."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        # >3 new fields
        records = [
            {
                "entity_id": "CHEMBL123",
                "new_field_1": "a",
                "new_field_2": "b",
                "new_field_3": "c",
                "new_field_4": "d",  # 4th new field
            }
        ]

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._detect_schema_drift("test.table", records)

            assert result is not None
            assert result.status == "warn"

    @pytest.mark.asyncio
    async def test_write_silver_metadata_with_dq_metrics(
        self, noop_logger, valid_records
    ):
        """Test _write_silver_metadata uses DQ metrics when provided."""
        from bioetl.domain.value_objects.dq_metrics import (
            BatchDQMetrics,
            ColumnStats,
            SchemaDriftInfo,
        )
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        mock_metadata_writer = MagicMock()
        write_calls = []

        async def capture_write(table_path, metadata):
            write_calls.append({"table_path": table_path, "metadata": metadata})

        mock_metadata_writer.write_silver_metadata = capture_write

        # Create DQ metrics with column stats and schema drift
        dq_metrics = BatchDQMetrics(
            total_records=100,
            valid_records=95,
            error_records=5,
            warning_records=2,
            column_stats={
                "entity_id": ColumnStats(null_rate=0.0, unique_count=95),
                "value": ColumnStats(
                    null_rate=0.05, min_value=1.0, max_value=100.0, mean_value=50.5
                ),
            },
            schema_drift=SchemaDriftInfo(
                status="warn", new_fields=("new_col",), missing_fields=()
            ),
        )

        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            metadata_writer=mock_metadata_writer,
        )

        await writer._write_silver_metadata(
            table_path="/tmp/silver/test/table",
            records=valid_records,
            primary_keys=["entity_id"],
            mode=SilverWriteMode.MERGE,
            bronze_refs=None,
            dq_metrics=dq_metrics,
        )

        # Verify DQ metrics are in metadata
        assert len(write_calls) == 1
        metadata = write_calls[0]["metadata"]
        dq_summary = metadata.dq_summary

        assert dq_summary.total_records == 100
        assert dq_summary.valid_records == 95
        assert dq_summary.error_records == 5
        assert dq_summary.warning_records == 2
        assert dq_summary.error_rate == 0.05
        assert dq_summary.validation_passed is False

        # Verify column metrics
        assert "entity_id" in dq_summary.column_metrics
        assert "value" in dq_summary.column_metrics
        assert dq_summary.column_metrics["value"].null_rate == 0.05
        assert dq_summary.column_metrics["value"].min == 1.0
        assert dq_summary.column_metrics["value"].max == 100.0

        # Verify schema drift
        assert dq_summary.schema_drift is not None
        assert dq_summary.schema_drift.status == "warn"
        assert "new_col" in dq_summary.schema_drift.new_fields

    @pytest.mark.asyncio
    async def test_write_silver_metadata_fallback_without_dq_metrics(
        self, noop_logger, valid_records
    ):
        """Test _write_silver_metadata uses fallback when dq_metrics is None."""
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        mock_metadata_writer = MagicMock()
        write_calls = []

        async def capture_write(table_path, metadata):
            write_calls.append({"table_path": table_path, "metadata": metadata})

        mock_metadata_writer.write_silver_metadata = capture_write

        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            metadata_writer=mock_metadata_writer,
        )

        await writer._write_silver_metadata(
            table_path="/tmp/silver/test/table",
            records=valid_records,
            primary_keys=["entity_id"],
            mode=SilverWriteMode.MERGE,
            bronze_refs=None,
            dq_metrics=None,  # No DQ metrics
        )

        # Verify fallback DQ summary
        assert len(write_calls) == 1
        metadata = write_calls[0]["metadata"]
        dq_summary = metadata.dq_summary

        assert dq_summary.total_records == 2  # len(valid_records)
        assert dq_summary.valid_records == 2
        assert dq_summary.error_records == 0
        assert dq_summary.column_metrics == {}  # Empty column metrics
        assert dq_summary.schema_drift is None

    @pytest.mark.asyncio
    async def test_write_silver_computes_and_passes_dq_metrics(
        self, noop_logger, valid_records
    ):
        """Test write_silver computes DQ metrics and passes to metadata."""
        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

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

        mock_metadata_writer = MagicMock()
        write_calls = []

        async def capture_write(table_path, metadata):
            write_calls.append({"table_path": table_path, "metadata": metadata})

        mock_metadata_writer.write_silver_metadata = capture_write

        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch("bioetl.infrastructure.storage.silver_writer.write_deltalake"),
        ):
            writer = SilverWriter(
                base_path="/tmp/silver",
                logger=noop_logger,
                metadata_writer=mock_metadata_writer,
            )

            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="merge",
            )

            # Verify DQ metrics were computed and passed
            assert len(write_calls) == 1
            metadata = write_calls[0]["metadata"]
            dq_summary = metadata.dq_summary

            # Should have computed column metrics
            assert "entity_id" in dq_summary.column_metrics
            assert "value" in dq_summary.column_metrics

            # value column should have numeric stats
            value_metrics = dq_summary.column_metrics["value"]
            assert value_metrics.min is not None
            assert value_metrics.max is not None
            assert value_metrics.mean is not None
