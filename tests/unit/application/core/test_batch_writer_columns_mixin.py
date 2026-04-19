"""Unit tests for BatchWriterColumnsMixin.

Tests column ordering, renaming, and type coercion helpers
extracted from BatchWriter into a dedicated mixin.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.core.batch_writer_columns_mixin import BatchWriterColumnsMixin


# ---------------------------------------------------------------------------
# Concrete test double — gives the mixin its required attributes via __init__
# ---------------------------------------------------------------------------


class _Writer(BatchWriterColumnsMixin):
    """Minimal concrete subclass that wires mixin dependencies."""

    def __init__(
        self,
        *,
        column_orderer=None,
        data_schema=None,
    ) -> None:
        self._column_orderer = column_orderer
        self._data_schema = data_schema


# ---------------------------------------------------------------------------
# _get_schema_columns
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetSchemaColumns:
    """Tests for BatchWriterColumnsMixin._get_schema_columns."""

    def test_returns_columns_from_to_schema_method(self):
        """Schema with to_schema() yields column names via conversion."""
        schema = MagicMock()
        converted = MagicMock()
        converted.columns = {"col_a": object(), "col_b": object()}
        schema.to_schema.return_value = converted

        writer = _Writer()
        result = writer._get_schema_columns(schema)

        assert result == {"col_a", "col_b"}

    def test_returns_columns_directly_when_no_to_schema(self):
        """Schema without to_schema() falls back to .columns attribute."""
        schema = MagicMock(spec=["columns"])
        schema.columns = {"x": object(), "y": object(), "z": object()}

        writer = _Writer()
        result = writer._get_schema_columns(schema)

        assert result == {"x", "y", "z"}

    def test_returns_none_when_no_columns_attribute(self):
        """Returns None when schema has no usable column source."""
        schema = MagicMock(spec=[])  # no attributes at all

        writer = _Writer()
        result = writer._get_schema_columns(schema)

        assert result is None

    def test_swallows_oserror_from_to_schema_and_falls_back(self):
        """to_schema() raising OSError falls back to .columns attribute."""
        schema = MagicMock()
        schema.to_schema.side_effect = OSError("disk error")
        schema.columns = {"fallback": object()}

        writer = _Writer()
        result = writer._get_schema_columns(schema)

        assert result == {"fallback"}

    def test_swallows_runtime_error_from_to_schema_and_falls_back(self):
        """to_schema() raising RuntimeError falls back to .columns."""
        schema = MagicMock()
        schema.to_schema.side_effect = RuntimeError("bad state")
        schema.columns = {"col": object()}

        writer = _Writer()
        result = writer._get_schema_columns(schema)

        assert result == {"col"}

    def test_swallows_value_error_from_to_schema_and_falls_back(self):
        """to_schema() raising ValueError falls back to .columns."""
        schema = MagicMock()
        schema.to_schema.side_effect = ValueError("invalid")
        schema.columns = {"vc": object()}

        writer = _Writer()
        result = writer._get_schema_columns(schema)

        assert result == {"vc"}

    def test_swallows_type_error_from_to_schema_and_falls_back(self):
        """to_schema() raising TypeError falls back to .columns."""
        schema = MagicMock()
        schema.to_schema.side_effect = TypeError("wrong type")
        schema.columns = {"tc": object()}

        writer = _Writer()
        result = writer._get_schema_columns(schema)

        assert result == {"tc"}

    def test_returns_none_when_to_schema_raises_and_no_fallback(self):
        """Returns None when to_schema() fails and no .columns exists."""
        schema = MagicMock(spec=["to_schema"])
        schema.to_schema.side_effect = RuntimeError("boom")

        writer = _Writer()
        result = writer._get_schema_columns(schema)

        assert result is None


# ---------------------------------------------------------------------------
# _collect_record_columns
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCollectRecordColumns:
    """Tests for BatchWriterColumnsMixin._collect_record_columns."""

    def test_collects_columns_in_first_seen_order(self):
        """Columns appear in stable first-seen order across all records."""
        records = [
            {"a": 1, "b": 2},
            {"b": 3, "c": 4},
            {"a": 5, "d": 6},
        ]
        writer = _Writer()
        result = writer._collect_record_columns(records)

        assert result == ["a", "b", "c", "d"]

    def test_empty_records_returns_empty_list(self):
        """Empty record list produces empty column list."""
        writer = _Writer()
        result = writer._collect_record_columns([])

        assert result == []

    def test_single_record(self):
        """Single record yields its own keys in insertion order."""
        records = [{"x": 1, "y": 2, "z": 3}]
        writer = _Writer()
        result = writer._collect_record_columns(records)

        assert result == ["x", "y", "z"]

    def test_no_duplicate_columns(self):
        """Each column name appears exactly once even across many records."""
        records = [{"id": i, "value": i * 2} for i in range(10)]
        writer = _Writer()
        result = writer._collect_record_columns(records)

        assert result == ["id", "value"]
        assert len(result) == len(set(result))


# ---------------------------------------------------------------------------
# _apply_renames_to_records
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestApplyRenamesToRecords:
    """Tests for BatchWriterColumnsMixin._apply_renames_to_records."""

    def test_renames_matching_keys(self):
        """Mapped keys are renamed; unmapped keys are preserved as-is."""
        records = [{"old_col": 1, "keep_col": 2}]
        rename_map = {"old_col": "new_col"}

        writer = _Writer()
        result = writer._apply_renames_to_records(records, rename_map)

        assert result == [{"new_col": 1, "keep_col": 2}]

    def test_empty_rename_map_returns_original_records(self):
        """Empty rename_map returns the same record list unchanged."""
        records = [{"a": 1}, {"b": 2}]
        writer = _Writer()
        result = writer._apply_renames_to_records(records, {})

        assert result is records

    def test_all_keys_renamed(self):
        """All keys renamed when every key appears in rename_map."""
        records = [{"x": 10, "y": 20}]
        rename_map = {"x": "alpha", "y": "beta"}

        writer = _Writer()
        result = writer._apply_renames_to_records(records, rename_map)

        assert result == [{"alpha": 10, "beta": 20}]

    def test_multiple_records_all_renamed(self):
        """Rename is applied consistently across all records."""
        records = [{"src": i} for i in range(5)]
        rename_map = {"src": "dst"}

        writer = _Writer()
        result = writer._apply_renames_to_records(records, rename_map)

        assert all("dst" in r and "src" not in r for r in result)

    def test_rename_map_with_unknown_key_is_ignored(self):
        """Rename map entries for absent keys don't raise errors."""
        records = [{"real_col": 42}]
        rename_map = {"ghost_col": "renamed_ghost", "real_col": "renamed_real"}

        writer = _Writer()
        result = writer._apply_renames_to_records(records, rename_map)

        assert result == [{"renamed_real": 42}]


# ---------------------------------------------------------------------------
# _get_column_order
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetColumnOrder:
    """Tests for BatchWriterColumnsMixin._get_column_order."""

    def test_returns_none_when_no_column_orderer(self):
        """Returns None when _column_orderer is falsy."""
        writer = _Writer(column_orderer=None)
        result = writer._get_column_order(["a", "b"])

        assert result is None

    def test_delegates_to_column_orderer(self):
        """Calls order_column_names on the orderer and pipes through prefix ordering."""
        orderer = MagicMock()
        # order_column_names returns same list (no system/DQ fields here)
        orderer.order_column_names.return_value = ["entity_id", "value"]

        writer = _Writer(column_orderer=orderer)
        result = writer._get_column_order(["entity_id", "value"])

        orderer.order_column_names.assert_called_once_with(["entity_id", "value"])
        # entity_id is a SYSTEM_FIELDS_PREFIX member — it must appear first
        assert result[0] == "entity_id"

    def test_system_fields_placed_first_by_apply_prefix_order(self):
        """_apply_system_prefix_order puts entity_id before business columns."""
        orderer = MagicMock()
        orderer.order_column_names.return_value = ["value", "entity_id", "content_hash"]

        writer = _Writer(column_orderer=orderer)
        result = writer._get_column_order(["value", "entity_id", "content_hash"])

        assert result.index("entity_id") < result.index("value")


# ---------------------------------------------------------------------------
# _apply_system_prefix_order
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestApplySystemPrefixOrder:
    """Tests for BatchWriterColumnsMixin._apply_system_prefix_order."""

    def test_empty_columns_returns_empty(self):
        """Empty input returns empty output."""
        writer = _Writer()
        result = writer._apply_system_prefix_order([])

        assert result == []

    def test_system_fields_come_before_business_columns(self):
        """entity_id / content_hash precede arbitrary business columns."""
        columns = ["value", "entity_id", "name", "content_hash"]
        writer = _Writer()
        result = writer._apply_system_prefix_order(columns)

        system_indices = [result.index("entity_id"), result.index("content_hash")]
        other_indices = [result.index("value"), result.index("name")]
        assert max(system_indices) < min(other_indices)

    def test_dq_fields_placed_at_end(self):
        """_dq_error and _dq_warn appear after all other columns."""
        columns = ["entity_id", "value", "_dq_error", "_dq_warn"]
        writer = _Writer()
        result = writer._apply_system_prefix_order(columns)

        assert result[-2] == "_dq_error"
        assert result[-1] == "_dq_warn"

    def test_lookup_fields_placed_after_system_before_middle(self):
        """Lookup fields (_lookup_method, _original_id) placed in prefix group."""
        columns = ["entity_id", "business_col", "_lookup_method", "_original_id"]
        writer = _Writer()
        result = writer._apply_system_prefix_order(columns)

        lookup_idx = min(result.index("_lookup_method"), result.index("_original_id"))
        business_idx = result.index("business_col")
        assert lookup_idx < business_idx

    def test_columns_without_system_fields_unchanged_order(self):
        """Columns with no system/DQ fields maintain their relative order."""
        columns = ["foo", "bar", "baz"]
        writer = _Writer()
        result = writer._apply_system_prefix_order(columns)

        assert result == ["foo", "bar", "baz"]


# ---------------------------------------------------------------------------
# _resolve_layer_columns
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveLayerColumns:
    """Tests for BatchWriterColumnsMixin._resolve_layer_columns."""

    def test_no_data_schema_returns_column_order_and_empty_renames(self):
        """Without _data_schema, returns ordered columns and empty rename map."""
        orderer = MagicMock()
        orderer.order_column_names.return_value = ["entity_id", "value"]
        writer = _Writer(column_orderer=orderer, data_schema=None)

        _, renames = writer._resolve_layer_columns(
            "silver", ["entity_id", "value"]
        )

        assert renames == {}
        orderer.order_column_names.assert_called_once()

    def test_data_schema_without_layer_config_falls_back_to_orderer(self):
        """Schema with no silver/gold attribute falls back to orderer."""
        schema = MagicMock()
        schema.silver = None

        orderer = MagicMock()
        orderer.order_column_names.return_value = ["entity_id"]

        writer = _Writer(column_orderer=orderer, data_schema=schema)
        _, renames = writer._resolve_layer_columns("silver", ["entity_id"])

        assert renames == {}

    def test_layer_config_with_columns_no_orderer(self):
        """With layer_config.columns but no orderer, filters available columns."""
        layer_config = MagicMock()
        layer_config.columns = ["entity_id", "name"]
        layer_config.rename_fields = {}

        schema = MagicMock()
        schema.silver = layer_config

        writer = _Writer(column_orderer=None, data_schema=schema)
        col_order, renames = writer._resolve_layer_columns(
            "silver", ["entity_id", "name", "extra"]
        )

        # Only columns present in available_columns are kept
        assert "entity_id" in col_order
        assert "name" in col_order
        assert "extra" not in col_order

    def test_layer_config_returns_rename_fields(self):
        """rename_fields from layer config are returned as second element."""
        layer_config = MagicMock()
        layer_config.columns = ["entity_id"]
        layer_config.rename_fields = {"old": "new"}

        schema = MagicMock()
        schema.gold = layer_config

        writer = _Writer(column_orderer=None, data_schema=schema)
        _, renames = writer._resolve_layer_columns("gold", ["entity_id", "old"])

        assert renames == {"old": "new"}

    def test_layer_config_empty_columns_no_orderer_returns_none(self):
        """Empty layer_config.columns with no orderer returns None for order."""
        layer_config = MagicMock()
        layer_config.columns = []
        layer_config.rename_fields = {}

        schema = MagicMock()
        schema.silver = layer_config

        writer = _Writer(column_orderer=None, data_schema=schema)
        col_order, _ = writer._resolve_layer_columns("silver", ["entity_id"])

        assert col_order is None

    def test_with_orderer_and_layer_config_uses_filter_by_layer_config(self):
        """When orderer + layer_config, delegates to filter_by_layer_config."""
        layer_config = MagicMock()
        layer_config.columns = ["entity_id", "value"]
        layer_config.rename_fields = {}

        schema = MagicMock()
        schema.silver = layer_config

        orderer = MagicMock()
        orderer.filter_by_layer_config.return_value = ["entity_id", "value"]

        writer = _Writer(column_orderer=orderer, data_schema=schema)
        col_order, _ = writer._resolve_layer_columns("silver", ["entity_id", "value"])

        orderer.filter_by_layer_config.assert_called_once()
        assert col_order is not None
