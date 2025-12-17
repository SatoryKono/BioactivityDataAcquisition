"""Unit tests for GoldWriter."""

from unittest.mock import MagicMock, patch

import pytest
from deltalake.exceptions import TableNotFoundError
from pandera.polars import Column, DataFrameSchema

from bioetl.infrastructure.storage.gold_writer import GoldWriter


@pytest.fixture
def gold_writer():
    """Create a GoldWriter instance."""
    return GoldWriter(base_path="s3://test-bucket/gold")


@pytest.fixture
def strict_schema():
    """Create a strict Pandera schema for testing."""
    return DataFrameSchema(
        {
            "entity_id": Column(str, nullable=False),
            "value": Column(float, nullable=False),
        },
        strict=True,
    )


@pytest.fixture
def non_strict_schema():
    """Create a non-strict Pandera schema for testing."""
    return DataFrameSchema(
        {
            "entity_id": Column(str, nullable=False),
        },
        strict=False,
    )


@pytest.fixture
def valid_records():
    """Create valid records for testing."""
    return [
        {"entity_id": "CHEMBL123", "value": 5.5},
        {"entity_id": "CHEMBL456", "value": 7.2},
    ]


@pytest.mark.unit
class TestGoldWriterInit:
    """Tests for GoldWriter initialization."""

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base_path."""
        writer = GoldWriter(base_path="s3://bucket/gold/")
        assert writer.base_path == "s3://bucket/gold"

    def test_init_with_storage_options(self):
        """Test initialization with storage options."""
        opts = {"AWS_ENDPOINT_URL": "http://localhost:9000"}
        writer = GoldWriter(base_path="s3://bucket", storage_options=opts)
        assert writer.storage_options == opts

    def test_init_without_storage_options(self):
        """Test initialization without storage options."""
        writer = GoldWriter(base_path="s3://bucket")
        assert writer.storage_options == {}


@pytest.mark.unit
class TestGoldWriterValidation:
    """Tests for GoldWriter validation."""

    async def test_write_gold_empty_records_raises(self, gold_writer):
        """Test write_gold raises ValueError for empty records."""
        with pytest.raises(ValueError, match="No records to write"):
            await gold_writer.write_gold(
                table_name="test.table",
                records=[],
                mode="overwrite",
            )

    async def test_write_gold_non_strict_schema_raises(
        self, gold_writer, non_strict_schema, valid_records
    ):
        """Test write_gold raises ValueError for non-strict schema."""
        with pytest.raises(ValueError, match="strict=True"):
            await gold_writer.write_gold(
                table_name="test.table",
                records=valid_records,
                schema=non_strict_schema,
                mode="overwrite",
            )

    async def test_write_gold_invalid_mode_raises(self, gold_writer, valid_records):
        """Test write_gold raises ValueError for invalid mode."""
        with pytest.raises(ValueError, match="Invalid mode"):
            await gold_writer.write_gold(
                table_name="test.table",
                records=valid_records,
                mode="invalid",
            )

    async def test_write_gold_scd2_without_config_raises(
        self, gold_writer, valid_records
    ):
        """Test write_gold raises ValueError for SCD2 mode without config."""
        with pytest.raises(ValueError, match="scd_config required"):
            await gold_writer.write_gold(
                table_name="test.table",
                records=valid_records,
                mode="scd2",
            )


@pytest.mark.unit
class TestGoldWriterWriteSimple:
    """Tests for simple write operations."""

    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_overwrite_mode(
        self, mock_write_deltalake, gold_writer, valid_records
    ):
        """Test write_gold with overwrite mode."""
        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            mode="overwrite",
        )

        mock_write_deltalake.assert_called_once()
        call_kwargs = mock_write_deltalake.call_args[1]
        assert call_kwargs["mode"] == "overwrite"
        assert call_kwargs["table_or_uri"] == "s3://test-bucket/gold/test/table"

    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_append_mode(
        self, mock_write_deltalake, gold_writer, valid_records
    ):
        """Test write_gold with append mode."""
        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            mode="append",
        )

        mock_write_deltalake.assert_called_once()
        call_kwargs = mock_write_deltalake.call_args[1]
        assert call_kwargs["mode"] == "append"

    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_with_partitions(
        self, mock_write_deltalake, gold_writer, valid_records
    ):
        """Test write_gold with partition columns."""
        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            mode="overwrite",
            partition_cols=["year", "month"],
        )

        mock_write_deltalake.assert_called_once()
        call_kwargs = mock_write_deltalake.call_args[1]
        assert call_kwargs["partition_by"] == ["year", "month"]


@pytest.mark.unit
class TestGoldWriterSCD2:
    """Tests for SCD Type 2 operations."""

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_scd2_creates_new_table(
        self, mock_write_deltalake, mock_delta_table, gold_writer, valid_records
    ):
        """Test SCD2 write creates new table when table doesn't exist."""
        mock_delta_table.side_effect = TableNotFoundError("Not found")

        scd_config = {
            "business_key": "entity_id",
            "version_col": "version",
            "valid_from_col": "valid_from",
            "valid_to_col": "valid_to",
            "current_flag_col": "is_current",
        }

        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            mode="scd2",
            scd_config=scd_config,
        )

        mock_write_deltalake.assert_called_once()
        # Records should have SCD metadata added
        call_kwargs = mock_write_deltalake.call_args[1]
        assert call_kwargs["mode"] == "append"

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_write_gold_scd2_merge_existing_table(
        self, mock_delta_table, gold_writer, valid_records
    ):
        """Test SCD2 write merges into existing table."""
        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_merge = MagicMock()
        mock_table_instance.merge.return_value = mock_merge
        mock_merge.when_matched_update.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge

        scd_config = {
            "business_key": "entity_id",
        }

        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            mode="scd2",
            scd_config=scd_config,
        )

        mock_table_instance.merge.assert_called_once()
        mock_merge.when_matched_update.assert_called_once()
        mock_merge.when_not_matched_insert_all.assert_called_once()

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_write_gold_scd2_with_list_business_key(
        self, mock_delta_table, gold_writer, valid_records
    ):
        """Test SCD2 write with list of business keys."""
        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_merge = MagicMock()
        mock_table_instance.merge.return_value = mock_merge
        mock_merge.when_matched_update.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge

        scd_config = {
            "business_key": ["provider", "entity_id"],
        }

        records = [
            {"provider": "chembl", "entity_id": "CHEMBL123", "value": 5.5},
        ]

        await gold_writer.write_gold(
            table_name="test.table",
            records=records,
            mode="scd2",
            scd_config=scd_config,
        )

        mock_table_instance.merge.assert_called_once()


@pytest.mark.unit
class TestGoldWriterSchemaValidation:
    """Tests for schema validation."""

    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_with_valid_schema(
        self, mock_write_deltalake, gold_writer, strict_schema, valid_records
    ):
        """Test write_gold passes with valid schema."""
        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            schema=strict_schema,
            mode="overwrite",
        )

        mock_write_deltalake.assert_called_once()

    async def test_write_gold_schema_validation_failure(
        self, gold_writer, strict_schema
    ):
        """Test write_gold raises ValueError for invalid records."""
        invalid_records = [
            {"entity_id": "CHEMBL123"},  # Missing 'value'
        ]

        with pytest.raises(ValueError, match="Schema validation failed"):
            await gold_writer.write_gold(
                table_name="test.table",
                records=invalid_records,
                schema=strict_schema,
                mode="overwrite",
            )


@pytest.mark.unit
class TestGoldWriterRead:
    """Tests for read operations."""

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_read_gold_returns_records(self, mock_delta_table, gold_writer):
        """Test read_gold returns records from table."""
        import pyarrow as pa

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        # Create mock PyArrow table
        mock_arrow_table = pa.table(
            {
                "entity_id": ["CHEMBL123", "CHEMBL456"],
                "value": [5.5, 7.2],
            }
        )
        mock_table_instance.to_pyarrow_table.return_value = mock_arrow_table

        result = await gold_writer.read_gold("test.table", current_only=False)

        assert len(result) == 2
        assert result[0]["entity_id"] == "CHEMBL123"

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_read_gold_filters_current_only(self, mock_delta_table, gold_writer):
        """Test read_gold filters for current records when is_current column exists."""
        import pyarrow as pa

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        # Create mock PyArrow table with is_current column
        mock_arrow_table = pa.table(
            {
                "entity_id": ["CHEMBL123", "CHEMBL123"],
                "value": [5.5, 7.2],
                "is_current": [False, True],
            }
        )
        mock_table_instance.to_pyarrow_table.return_value = mock_arrow_table

        result = await gold_writer.read_gold("test.table", current_only=True)

        # Should only return current record
        assert len(result) == 1
        assert result[0]["value"] == 7.2


@pytest.mark.unit
class TestGoldWriterHistory:
    """Tests for history retrieval."""

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_get_history_returns_all_versions(self, mock_delta_table, gold_writer):
        """Test get_history returns all historical versions."""
        import pyarrow as pa

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        # Create mock PyArrow table with history
        mock_arrow_table = pa.table(
            {
                "entity_id": ["CHEMBL123", "CHEMBL123", "CHEMBL456"],
                "value": [5.5, 6.0, 7.2],
                "version": [1, 2, 1],
                "valid_from": ["2024-01-01", "2024-02-01", "2024-01-01"],
            }
        )
        mock_table_instance.to_pyarrow_table.return_value = mock_arrow_table

        result = await gold_writer.get_history(
            "test.table", {"entity_id": "CHEMBL123"}
        )

        # Should return both versions of CHEMBL123
        assert len(result) == 2
        assert all(r["entity_id"] == "CHEMBL123" for r in result)

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_get_history_with_multiple_keys(self, mock_delta_table, gold_writer):
        """Test get_history with multiple business key values."""
        import pyarrow as pa

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        mock_arrow_table = pa.table(
            {
                "provider": ["chembl", "chembl", "pubchem"],
                "entity_id": ["123", "123", "123"],
                "value": [5.5, 6.0, 7.2],
            }
        )
        mock_table_instance.to_pyarrow_table.return_value = mock_arrow_table

        result = await gold_writer.get_history(
            "test.table",
            {"provider": "chembl", "entity_id": "123"},
        )

        # Should return only chembl records
        assert len(result) == 2
        assert all(r["provider"] == "chembl" for r in result)
