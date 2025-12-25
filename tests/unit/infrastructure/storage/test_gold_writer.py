"""Unit tests for GoldWriter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pyarrow as pa
import pytest
from deltalake.exceptions import TableNotFoundError
from pandera import Column, DataFrameSchema

from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.gold_writer import GoldWriter


@pytest.fixture
def noop_logger():
    """Provide a NoOpLogger for tests."""
    return NoOpLogger()


@pytest.fixture
def gold_writer(noop_logger):
    """Create a GoldWriter instance."""
    return GoldWriter(base_path="s3://test-bucket/gold", logger=noop_logger)


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

    def test_init_strips_trailing_slash(self, noop_logger):
        """Test that trailing slash is stripped from base_path."""
        writer = GoldWriter(base_path="s3://bucket/gold/", logger=noop_logger)
        assert writer.base_path == "s3://bucket/gold"

    def test_init_with_csv_exporter(self, noop_logger):
        """Test initialization with CSV exporter."""
        from unittest.mock import MagicMock

        mock_exporter = MagicMock()
        writer = GoldWriter(
            base_path="/tmp/gold", logger=noop_logger, csv_exporter=mock_exporter
        )
        assert writer.csv_exporter is mock_exporter

    def test_init_without_csv_exporter(self, noop_logger):
        """Test initialization without CSV exporter."""
        writer = GoldWriter(base_path="/tmp/gold", logger=noop_logger)
        assert writer.csv_exporter is None


@pytest.mark.unit
class TestGoldWriterValidation:
    """Tests for GoldWriter validation."""

    async def test_write_gold_empty_records_raises(self, gold_writer, strict_schema):
        """Test write_gold raises ValueError for empty records."""
        with pytest.raises(ValueError, match="No records to write"):
            await gold_writer.write_gold(
                table_name="test.table",
                records=[],
                schema=strict_schema,
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

    async def test_write_gold_invalid_mode_raises(self, gold_writer, valid_records, strict_schema):
        """Test write_gold raises ValueError for invalid mode."""
        with pytest.raises(ValueError, match="Invalid Gold write mode"):
            await gold_writer.write_gold(
                table_name="test.table",
                records=valid_records,
                schema=strict_schema,
                mode="invalid",
            )

    async def test_write_gold_scd2_without_config_raises(
        self, gold_writer, valid_records, strict_schema
    ):
        """Test write_gold raises ValueError for SCD2 mode without config."""
        with pytest.raises(ValueError, match="scd_config required"):
            await gold_writer.write_gold(
                table_name="test.table",
                records=valid_records,
                schema=strict_schema,
                mode="scd2",
            )


@pytest.mark.unit
class TestGoldWriterWriteSimple:
    """Tests for simple write operations."""

    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_overwrite_mode(
        self, mock_write_deltalake, gold_writer, valid_records, strict_schema
    ):
        """Test write_gold with overwrite mode."""
        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            schema=strict_schema,
            mode="overwrite",
        )

        mock_write_deltalake.assert_called_once()
        call_kwargs = mock_write_deltalake.call_args[1]
        assert call_kwargs["mode"] == "overwrite"
        assert call_kwargs["table_or_uri"] == "s3://test-bucket/gold/test/table"

    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_append_mode(
        self, mock_write_deltalake, gold_writer, valid_records, strict_schema
    ):
        """Test write_gold with append mode."""
        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            schema=strict_schema,
            mode="append",
        )

        mock_write_deltalake.assert_called_once()
        call_kwargs = mock_write_deltalake.call_args[1]
        assert call_kwargs["mode"] == "append"

    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_with_partitions(
        self, mock_write_deltalake, gold_writer, valid_records, strict_schema
    ):
        """Test write_gold with partition columns."""
        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            schema=strict_schema,
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
        self, mock_write_deltalake, mock_delta_table, gold_writer, valid_records, strict_schema
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
            schema=strict_schema,
            mode="scd2",
            scd_config=scd_config,
        )

        mock_write_deltalake.assert_called_once()
        # Records should have SCD metadata added
        call_kwargs = mock_write_deltalake.call_args[1]
        assert call_kwargs["mode"] == "append"

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_write_gold_scd2_merge_existing_table(
        self, mock_delta_table, gold_writer, valid_records, strict_schema
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
            schema=strict_schema,
            mode="scd2",
            scd_config=scd_config,
        )

        mock_table_instance.merge.assert_called_once()
        mock_merge.when_matched_update.assert_called_once()
        mock_merge.when_not_matched_insert_all.assert_called_once()

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_write_gold_scd2_with_list_business_key(
        self, mock_delta_table, gold_writer
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

        # Create schema that matches records
        multi_key_schema = DataFrameSchema(
            {
                "provider": Column(str, nullable=False),
                "entity_id": Column(str, nullable=False),
                "value": Column(float, nullable=False),
            },
            strict=True,
        )

        await gold_writer.write_gold(
            table_name="test.table",
            records=records,
            schema=multi_key_schema,
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
    async def test_get_history_returns_all_versions(
        self, mock_delta_table, gold_writer
    ):
        """Test get_history returns all historical versions."""

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

        result = await gold_writer.get_history("test.table", {"entity_id": "CHEMBL123"})

        # Should return both versions of CHEMBL123
        assert len(result) == 2
        assert all(r["entity_id"] == "CHEMBL123" for r in result)

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_get_history_with_multiple_keys(self, mock_delta_table, gold_writer):
        """Test get_history with multiple business key values."""

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


@pytest.mark.unit
class TestGoldWriterTypeSanitization:
    """Tests for type sanitization methods."""

    def test_sanitize_null_type(self, gold_writer):
        """Test sanitization of null type to string."""

        result = gold_writer._sanitize_type_for_delta(pa.null())
        assert result == pa.string()

    def test_sanitize_list_with_null_inner(self, gold_writer):
        """Test sanitization of list<null> to list<string>."""

        null_list_type = pa.list_(pa.null())
        result = gold_writer._sanitize_type_for_delta(null_list_type)
        assert result == pa.list_(pa.string())

    def test_sanitize_large_list_type(self, gold_writer):
        """Test sanitization of large_list type."""

        large_list_type = pa.large_list(pa.null())
        result = gold_writer._sanitize_type_for_delta(large_list_type)
        assert result == pa.large_list(pa.string())

    def test_sanitize_struct_with_null_field(self, gold_writer):
        """Test sanitization of struct with null field."""

        struct_type = pa.struct(
            [pa.field("name", pa.string()), pa.field("value", pa.null())]
        )
        result = gold_writer._sanitize_type_for_delta(struct_type)

        # Check the value field is now string
        assert result[1].type == pa.string()

    def test_sanitize_map_type(self, gold_writer):
        """Test sanitization of map type."""

        map_type = pa.map_(pa.string(), pa.null())
        result = gold_writer._sanitize_type_for_delta(map_type)
        assert result.item_type == pa.string()

    def test_sanitize_non_null_type_unchanged(self, gold_writer):
        """Test that non-null types are unchanged."""

        int_type = pa.int64()
        result = gold_writer._sanitize_type_for_delta(int_type)
        assert result == pa.int64()


@pytest.mark.unit
class TestGoldWriterToArrowTable:
    """Tests for _to_arrow_table method."""

    def test_to_arrow_table_with_null_columns(self, gold_writer):
        """Test conversion when records have all-null columns."""
        records = [
            {"id": "a", "value": None},
            {"id": "b", "value": None},
        ]

        result = gold_writer._to_arrow_table(records)

        # Value column should be converted to string (or valid type)
        assert result.num_rows == 2

    def test_to_arrow_table_with_mixed_types(self, gold_writer):
        """Test conversion with various data types."""
        records = [
            {"id": "a", "count": 1, "score": 1.5, "active": True},
        ]

        result = gold_writer._to_arrow_table(records)

        assert result.num_rows == 1
