"""Unit tests for DeltaWriter."""

from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.exceptions import SchemaViolationError


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

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base_path."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket/path/")
        assert writer.base_path == "s3://bucket/path"

    def test_init_with_storage_options(self):
        """Test initialization with storage options."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        opts = {"AWS_ENDPOINT_URL": "http://localhost:9000"}
        writer = DeltaWriter(base_path="s3://bucket", storage_options=opts)
        assert writer.storage_options == opts

    def test_init_without_storage_options(self):
        """Test initialization without storage options."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket")
        assert writer.storage_options == {}


@pytest.mark.unit
class TestDeltaWriterValidation:
    """Tests for DeltaWriter validation."""

    @pytest.mark.asyncio
    async def test_write_silver_empty_records_raises(self):
        """Test write_silver raises ValueError for empty records."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket")

        import pyarrow as pa
        dummy_schema = pa.schema([pa.field("entity_id", pa.string())])

        with pytest.raises(ValueError, match="No records to write"):
            await writer.write_silver(
                table_name="test.table",
                records=[],
                primary_keys=["entity_id"],
                schema=dummy_schema,
            )

    @pytest.mark.asyncio
    async def test_write_silver_missing_metadata_raises(self):
        """Test write_silver raises ValueError for missing metadata."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket")
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
    async def test_write_silver_missing_run_id_raises(self):
        """Test write_silver raises ValueError when _run_id is missing."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket")
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
class TestDeltaWriterTablePath:
    """Tests for table path construction."""

    def test_table_path_construction(self):
        """Test table path is constructed correctly."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket/silver")

        # Access internal path construction
        table_name = "chembl.activity"
        expected_path = "s3://bucket/silver/chembl/activity"
        actual_path = f"{writer.base_path}/{table_name.replace('.', '/')}"

        assert actual_path == expected_path

    def test_table_path_with_nested_name(self):
        """Test table path with nested table name."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket/silver")

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
        predicate = " AND ".join(
            f"target.{key} = source.{key}" for key in primary_keys
        )

        assert predicate == "target.entity_id = source.entity_id"

    def test_build_multi_key_predicate(self):
        """Test predicate building with multiple primary keys."""
        primary_keys = ["entity_id", "version"]
        predicate = " AND ".join(
            f"target.{key} = source.{key}" for key in primary_keys
        )

        assert predicate == "target.entity_id = source.entity_id AND target.version = source.version"

    def test_build_compound_key_predicate(self):
        """Test predicate building with compound primary keys."""
        primary_keys = ["provider", "entity_type", "entity_id"]
        predicate = " AND ".join(
            f"target.{key} = source.{key}" for key in primary_keys
        )

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
    async def test_vacuum_returns_deleted_files(self, mock_delta_table):
        """Test vacuum returns list of deleted files."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_table_instance.vacuum.return_value = [
            "file1.parquet",
            "file2.parquet",
        ]

        writer = DeltaWriter(base_path="s3://bucket/silver")
        result = await writer.vacuum("test.table", retention_hours=168)

        assert len(result) == 2
        mock_table_instance.vacuum.assert_called_once_with(
            retention_hours=168, dry_run=False
        )

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_vacuum_dry_run(self, mock_delta_table):
        """Test vacuum dry run."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_table_instance.vacuum.return_value = ["file1.parquet"]

        writer = DeltaWriter(base_path="s3://bucket/silver")
        await writer.vacuum("test.table", retention_hours=24, dry_run=True)

        mock_table_instance.vacuum.assert_called_once_with(
            retention_hours=24, dry_run=True
        )

    @pytest.mark.asyncio
    async def test_vacuum_table_not_found(self):
        """Test vacuum raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = DeltaWriter(base_path="s3://bucket/silver")

            with pytest.raises(TableNotFoundError):
                await writer.vacuum("nonexistent.table")


@pytest.mark.unit
class TestDeltaWriterOptimize:
    """Tests for DeltaWriter optimize operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_optimize_returns_metrics(self, mock_delta_table):
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

        writer = DeltaWriter(base_path="s3://bucket/silver")
        result = await writer.optimize("test.table")

        assert result["numFilesRemoved"] == 5
        mock_optimize.compact.assert_called_once()

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_optimize_with_partition_filters(self, mock_delta_table):
        """Test optimize with partition filters."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_optimize = MagicMock()
        mock_table_instance.optimize = mock_optimize
        mock_optimize.compact.return_value = {}

        writer = DeltaWriter(base_path="s3://bucket/silver")
        await writer.optimize("test.table", partition_filters=[("year", "=", 2025)])

        mock_optimize.compact.assert_called_once_with(
            partition_filters=[("year", "=", 2025)]
        )

    @pytest.mark.asyncio
    async def test_optimize_table_not_found(self):
        """Test optimize raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = DeltaWriter(base_path="s3://bucket/silver")

            with pytest.raises(TableNotFoundError):
                await writer.optimize("nonexistent.table")


@pytest.mark.unit
class TestDeltaWriterGetTableInfo:
    """Tests for DeltaWriter get_table_info operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_get_table_info_returns_metadata(self, mock_delta_table):
        """Test get_table_info returns table metadata."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_table_instance.version.return_value = 10
        mock_table_instance.files.return_value = ["file1.parquet", "file2.parquet"]
        mock_schema = MagicMock()
        mock_schema.to_pyarrow.return_value = {"fields": []}
        mock_table_instance.schema.return_value = mock_schema
        mock_table_instance.metadata.return_value = {"id": "test-table"}

        writer = DeltaWriter(base_path="s3://bucket/silver")
        result = await writer.get_table_info("test.table")

        assert result["version"] == 10
        assert result["num_files"] == 2

    @pytest.mark.asyncio
    async def test_get_table_info_table_not_found(self):
        """Test get_table_info raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = DeltaWriter(base_path="s3://bucket/silver")

            with pytest.raises(TableNotFoundError):
                await writer.get_table_info("nonexistent.table")


@pytest.mark.unit
class TestDeltaWriterTimeTravel:
    """Tests for DeltaWriter time_travel operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_time_travel_by_version(self, mock_delta_table):
        """Test time_travel by version number."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        writer = DeltaWriter(base_path="s3://bucket/silver")
        result = await writer.time_travel("test.table", version=5)

        assert result == mock_table_instance
        mock_delta_table.assert_called_once()

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_time_travel_by_timestamp(self, mock_delta_table):
        """Test time_travel by timestamp."""
        from datetime import datetime

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        writer = DeltaWriter(base_path="s3://bucket/silver")
        ts = datetime(2025, 1, 1, 12, 0, 0)
        result = await writer.time_travel("test.table", timestamp=ts)

        assert result == mock_table_instance

    @pytest.mark.asyncio
    async def test_time_travel_both_version_and_timestamp_raises(self):
        """Test time_travel raises ValueError when both version and timestamp given."""
        from datetime import datetime

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket/silver")

        with pytest.raises(ValueError, match="Specify either version or timestamp"):
            await writer.time_travel(
                "test.table", version=5, timestamp=datetime(2025, 1, 1)
            )

    @pytest.mark.asyncio
    async def test_time_travel_neither_version_nor_timestamp_raises(self):
        """Test time_travel raises ValueError when neither version nor timestamp given."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket/silver")

        with pytest.raises(ValueError, match="Must specify either version or timestamp"):
            await writer.time_travel("test.table")

    @pytest.mark.asyncio
    async def test_time_travel_table_not_found(self):
        """Test time_travel raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = DeltaWriter(base_path="s3://bucket/silver")

            with pytest.raises(TableNotFoundError):
                await writer.time_travel("nonexistent.table", version=1)


@pytest.mark.unit
class TestDeltaWriterErrorHandling:
    """Tests for error handling in DeltaWriter."""

    @pytest.mark.asyncio
    async def test_write_silver_schema_mismatch_error(self, valid_records):
        """Test write_silver raises SchemaViolationError for schema mismatch."""
        from unittest.mock import patch

        from deltalake.exceptions import SchemaMismatchError

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        import pyarrow as pa

        schema = pa.schema([
            pa.field("entity_id", pa.string()),
            pa.field("value", pa.float64()),
            pa.field("_run_id", pa.string()),
            pa.field("_run_type", pa.string()),
            pa.field("_source_batch_id", pa.string()),
            pa.field("_ingestion_ts", pa.string()),
        ])

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            side_effect=SchemaMismatchError("Schema mismatch"),
        ):
            writer = DeltaWriter(base_path="s3://bucket/silver")

            with pytest.raises(SchemaViolationError):
                await writer.write_silver(
                    table_name="test.table",
                    records=valid_records,
                    primary_keys=["entity_id"],
                    schema=schema,
                )

    @pytest.mark.asyncio
    async def test_write_silver_merge_conflict_error(self, valid_records):
        """Test write_silver raises MergeConflictError for merge conflicts."""
        from unittest.mock import MagicMock, patch

        from deltalake.exceptions import DeltaError

        from bioetl.domain.exceptions import MergeConflictError
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        import pyarrow as pa

        schema = pa.schema([
            pa.field("entity_id", pa.string()),
            pa.field("value", pa.float64()),
            pa.field("_run_id", pa.string()),
            pa.field("_run_type", pa.string()),
            pa.field("_source_batch_id", pa.string()),
            pa.field("_ingestion_ts", pa.string()),
        ])

        mock_table = MagicMock()
        mock_merge = MagicMock()
        mock_table.merge.return_value = mock_merge
        mock_merge.when_matched_update_all.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge
        mock_merge.execute.side_effect = DeltaError("Merge-conflict detected")

        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = DeltaWriter(base_path="s3://bucket/silver")

            with pytest.raises(MergeConflictError):
                await writer.write_silver(
                    table_name="test.table",
                    records=valid_records,
                    primary_keys=["entity_id"],
                    schema=schema,
                )
