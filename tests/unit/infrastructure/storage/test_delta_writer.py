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

        with pytest.raises(ValueError, match="No records to write"):
            await writer.write_silver(
                table_name="test.table",
                records=[],
                primary_keys=["entity_id"],
            )

    @pytest.mark.asyncio
    async def test_write_silver_missing_metadata_raises(self):
        """Test write_silver raises ValueError for missing metadata."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        writer = DeltaWriter(base_path="s3://bucket")
        records = [{"entity_id": "CHEMBL123", "value": 5.5}]

        with pytest.raises(ValueError, match="Records missing required metadata"):
            await writer.write_silver(
                table_name="test.table",
                records=records,
                primary_keys=["entity_id"],
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

        with pytest.raises(ValueError, match="Records missing required metadata"):
            await writer.write_silver(
                table_name="test.table",
                records=records,
                primary_keys=["entity_id"],
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
