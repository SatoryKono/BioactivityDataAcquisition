# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for GoldWriter."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandera.pandas as pa
import pyarrow as pa_arrow
import pytest
from deltalake.exceptions import TableNotFoundError
from pandera.pandas import DataFrameSchema

from bioetl.infrastructure.storage.gold_writer import GoldWriter


pytestmark = pytest.mark.unit


@pytest.fixture
def gold_writer(noop_logger):
    return GoldWriter(base_path="s3://test-bucket/gold", logger=noop_logger)


@pytest.fixture
def valid_records():
    return [{"id": 1, "value": 10.5}, {"id": 2, "value": 20.0}]


@pytest.fixture
def strict_schema():
    return DataFrameSchema(
        {
            "id": pa.Column(int),
            "value": pa.Column(float),
        },
        strict=True,
    )


async def test_write_gold_no_records(gold_writer, strict_schema):
    """Test writing empty records raises ValueError."""
    with pytest.raises(ValueError, match="No records to write"):
        await gold_writer.write_gold("test_table", [], schema=strict_schema)


async def test_write_gold_schema_not_strict(gold_writer, valid_records):
    """Test non-strict schema raises ValueError."""
    schema = DataFrameSchema({"id": pa.Column(int)})  # strict=False by default

    with pytest.raises(ValueError, match="Gold layer requires strict=True"):
        await gold_writer.write_gold("test_table", valid_records, schema=schema)


async def test_storage_gold_writer__validation_failure__eb6c952a(
    gold_writer, strict_schema
):
    """Test schema validation failure raises ValueError."""
    invalid_records = [{"id": "not_int", "value": 10.5}]

    with pytest.raises(ValueError, match="Schema validation failed"):
        await gold_writer.write_gold(
            "test_table", invalid_records, schema=strict_schema
        )


async def test_write_gold_invalid_mode(gold_writer, valid_records, strict_schema):
    """Test invalid write mode raises ValueError."""
    with pytest.raises(ValueError, match="Invalid Gold write mode"):
        await gold_writer.write_gold(
            "test_table", valid_records, schema=strict_schema, mode="invalid"
        )


async def test_write_simple_overwrite(gold_writer, valid_records, strict_schema):
    """Test simple overwrite mode."""
    with patch(
        "bioetl.infrastructure.storage.gold_writer.write_deltalake"
    ) as mock_write:
        await gold_writer.write_gold(
            "test_table", valid_records, schema=strict_schema, mode="overwrite"
        )

        mock_write.assert_called_once()
        call_kwargs = mock_write.call_args[1]
        assert call_kwargs["mode"] == "overwrite"
        assert call_kwargs["table_or_uri"] == "s3://test-bucket/gold/test_table"

        # Convert expected data to pyarrow table for comparison
        expected_table = pa_arrow.Table.from_pylist(valid_records)
        actual_data = call_kwargs["data"]
        # Handle RecordBatchReader
        if isinstance(actual_data, pa_arrow.RecordBatchReader):
            actual_data = actual_data.read_all()
        assert actual_data.equals(expected_table)


async def test_write_simple_append(gold_writer, valid_records, strict_schema):
    """Test simple append mode."""
    with patch(
        "bioetl.infrastructure.storage.gold_writer.write_deltalake"
    ) as mock_write:
        await gold_writer.write_gold(
            "test_table", valid_records, schema=strict_schema, mode="append"
        )

        mock_write.assert_called_once()
        call_kwargs = mock_write.call_args[1]
        assert call_kwargs["mode"] == "append"


async def test_write_scd2_missing_config(gold_writer, valid_records, strict_schema):
    """Test SCD2 mode without config raises ValueError."""
    with pytest.raises(ValueError, match="scd_config required"):
        await gold_writer.write_gold(
            "test_table", valid_records, schema=strict_schema, mode="scd2"
        )


async def test_write_scd2_new_table(gold_writer, valid_records, strict_schema):
    """Test SCD2 write when table does not exist (creates new)."""
    scd_config = {"business_key": "id"}
    ingestion_ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    with (
        patch("bioetl.infrastructure.storage.gold_writer.DeltaTable") as mock_dt,
        patch(
            "bioetl.infrastructure.storage.gold_writer.write_deltalake"
        ) as mock_write,
    ):
        mock_dt.side_effect = TableNotFoundError("Table not found")

        await gold_writer.write_gold(
            "test_table",
            valid_records,
            schema=strict_schema,
            mode="scd2",
            scd_config=scd_config,
            ingestion_ts=ingestion_ts,
        )

        # Should call write_deltalake to create table
        mock_write.assert_called_once()
        call_kwargs = mock_write.call_args[1]
        assert call_kwargs["mode"] == "append"

        # Verify SCD columns added
        written_data_obj = call_kwargs["data"]
        # Handle RecordBatchReader
        if isinstance(written_data_obj, pa_arrow.RecordBatchReader):
            written_data_obj = written_data_obj.read_all()
        written_data = written_data_obj.to_pylist()
        assert "valid_from" in written_data[0]
        assert "valid_to" in written_data[0]
        assert "is_current" in written_data[0]
        assert written_data[0]["is_current"] is True
        assert written_data[0]["valid_to"] is None


async def test_write_scd2_existing_table(gold_writer, valid_records, strict_schema):
    """Test SCD2 merge with existing table."""
    scd_config = {"business_key": "id"}
    ingestion_ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    mock_dt_instance = MagicMock()
    mock_merge_builder = MagicMock()
    mock_dt_instance.merge.return_value = mock_merge_builder
    mock_merge_builder.when_matched_update.return_value = mock_merge_builder
    mock_merge_builder.when_not_matched_insert_all.return_value = mock_merge_builder

    with patch(
        "bioetl.infrastructure.storage.gold_writer.DeltaTable",
        return_value=mock_dt_instance,
    ):
        await gold_writer.write_gold(
            "test_table",
            valid_records,
            schema=strict_schema,
            mode="scd2",
            scd_config=scd_config,
            ingestion_ts=ingestion_ts,
        )

        # Should call merge
        mock_dt_instance.merge.assert_called_once()
        call_kwargs = mock_dt_instance.merge.call_args[1]
        assert "target.id = source.id" in call_kwargs["predicate"]

        # Verify execution
        mock_merge_builder.execute.assert_called_once()


async def test_read_gold(gold_writer):
    """Test reading from Gold table."""
    mock_dt_instance = MagicMock()
    mock_arrow_table = MagicMock()
    mock_arrow_table.column_names = ["id", "value", "is_current"]
    mock_arrow_table.to_pylist.return_value = [{"id": 1, "is_current": True}]

    # Setup __getitem__ to return a mock that pyarrow.compute functions will accept
    # This mocks table['column'] access
    column_mock = MagicMock()
    mock_arrow_table.__getitem__.return_value = column_mock

    mock_dt_instance.to_pyarrow_table.return_value = mock_arrow_table

    # Mock filter
    mock_arrow_table.filter.return_value = mock_arrow_table

    # We need to mock pyarrow.compute functions because they type check arguments
    with (
        patch(
            "bioetl.infrastructure.storage.gold_writer.DeltaTable",
            return_value=mock_dt_instance,
        ),
        patch("pyarrow.compute.equal") as mock_equal,
    ):
        mock_equal.return_value = MagicMock()  # Return a mask

        result = await gold_writer.read_gold("test_table", current_only=True)

        assert len(result) == 1
        assert result[0]["id"] == 1
        mock_arrow_table.filter.assert_called_once()


async def test_get_history(gold_writer):
    """Test getting history for an entity."""
    mock_dt_instance = MagicMock()
    mock_arrow_table = MagicMock()
    mock_arrow_table.column_names = ["id", "valid_from"]
    mock_arrow_table.to_pylist.return_value = [
        {"id": 1, "valid_from": "2023-01-01"},
        {"id": 1, "valid_from": "2023-01-02"},
    ]

    # Mock __getitem__ for column access
    mock_arrow_table.__getitem__.return_value = MagicMock()

    mock_dt_instance.to_pyarrow_table.return_value = mock_arrow_table
    mock_arrow_table.filter.return_value = mock_arrow_table
    mock_arrow_table.sort_by.return_value = mock_arrow_table

    with (
        patch(
            "bioetl.infrastructure.storage.gold_writer.DeltaTable",
            return_value=mock_dt_instance,
        ),
        patch("pyarrow.compute.equal") as mock_equal,
        patch("pyarrow.compute.and_") as mock_and,
    ):
        mock_equal.return_value = MagicMock()
        mock_and.return_value = MagicMock()

        history = await gold_writer.get_history("test_table", {"id": 1})

        assert len(history) == 2
        mock_arrow_table.filter.assert_called_once()
        mock_arrow_table.sort_by.assert_called_once()


async def test_write_gold_merged_no_records(gold_writer, noop_logger):
    """Test write_gold_merged handles empty records gracefully."""
    # Should not raise, just log warning
    await gold_writer.write_gold_merged(
        table_name="test_empty",
        records=[],
    )


async def test_write_gold_merged_calls_write_deltalake(
    gold_writer, valid_records, strict_schema
):
    """Test write_gold_merged writes data with overwrite mode."""
    with patch(
        "bioetl.infrastructure.storage.gold_writer.write_deltalake"
    ) as mock_write:
        await gold_writer.write_gold_merged(
            table_name="test_merged",
            records=valid_records,
            primary_keys=["id"],
            schema=strict_schema,
        )

        mock_write.assert_called_once()
        # Check positional args and kwargs
        call_args, call_kwargs = mock_write.call_args
        # First positional arg is the path
        assert call_args[0] == "s3://test-bucket/gold/test_merged"
        # Mode should be in kwargs
        assert call_kwargs["mode"] == "overwrite"


async def test_write_gold_merged_sorts_by_primary_keys(gold_writer):
    """Test write_gold_merged sorts records by primary keys."""
    records = [
        {"id": "3", "value": 30},
        {"id": "1", "value": 10},
        {"id": "2", "value": 20},
    ]

    with patch(
        "bioetl.infrastructure.storage.gold_writer.write_deltalake"
    ) as mock_write:
        schema = DataFrameSchema(
            {
                "id": pa.Column(str),
                "value": pa.Column(int),
            },
            strict=True,
        )
        await gold_writer.write_gold_merged(
            table_name="test_sorted",
            records=records,
            primary_keys=["id"],
            schema=schema,
        )

        mock_write.assert_called_once()
        # Second positional arg is the arrow table
        call_args, _call_kwargs = mock_write.call_args
        written_data = call_args[1]
        # Data should be sorted by id
        written_list = written_data.to_pylist()
        ids = [r["id"] for r in written_list]
        assert ids == ["1", "2", "3"]


async def test_write_gold_merged_strips_runtime_occurrence_fields(gold_writer):
    """Merged Gold overwrite should not persist run-scoped provenance columns."""
    records = [
        {
            "id": "1",
            "value": 10,
            "_composite_run_id": "run-1",
            "_lineage_created_at": "2024-01-01T00:00:00Z",
            "_ingestion_ts": "2024-01-01T00:00:00Z",
        }
    ]

    with patch(
        "bioetl.infrastructure.storage.gold_writer.write_deltalake"
    ) as mock_write:
        schema = DataFrameSchema(
            {
                "id": pa.Column(str),
                "value": pa.Column(int),
            },
            strict=True,
        )
        await gold_writer.write_gold_merged(
            table_name="test_runtime_contract",
            records=records,
            primary_keys=["id"],
            schema=schema,
        )

        written_data = mock_write.call_args[0][1]
        written_list = written_data.to_pylist()

        assert list(written_list[0].keys()) == ["id", "value"]
