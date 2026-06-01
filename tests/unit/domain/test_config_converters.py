"""Unit tests for domain config converters."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from bioetl.domain.config._converters import (
    convert_write_mode,
    freeze_sequences,
    resolve_loading_strategy,
)
from bioetl.domain.medallion import GoldWriteMode, LoadingStrategy, SilverWriteMode


@pytest.mark.unit
class TestConvertWriteMode:
    """Tests for convert_write_mode function."""

    def test_silver_write_mode_pass_through(self) -> None:
        """Test that SilverWriteMode enum value is passed through unchanged."""
        mode = SilverWriteMode.MERGE
        result = convert_write_mode(mode, SilverWriteMode)
        assert result == SilverWriteMode.MERGE
        assert isinstance(result, SilverWriteMode)

    def test_silver_write_mode_from_string(self) -> None:
        """Test converting string to SilverWriteMode."""
        result = convert_write_mode("merge", SilverWriteMode)
        assert result == SilverWriteMode.MERGE

    def test_silver_write_mode_append_from_string(self) -> None:
        """Test converting 'append' string to SilverWriteMode."""
        result = convert_write_mode("append", SilverWriteMode)
        assert result == SilverWriteMode.APPEND

    def test_gold_write_mode_pass_through(self) -> None:
        """Test that GoldWriteMode enum value is passed through unchanged."""
        mode = GoldWriteMode.SCD2
        result = convert_write_mode(mode, GoldWriteMode)
        assert result == GoldWriteMode.SCD2

    def test_gold_write_mode_from_string(self) -> None:
        """Test converting string to GoldWriteMode."""
        result = convert_write_mode("scd2", GoldWriteMode)
        assert result == GoldWriteMode.SCD2

    def test_gold_write_mode_overwrite_from_string(self) -> None:
        """Test converting 'overwrite' string to GoldWriteMode."""
        result = convert_write_mode("overwrite", GoldWriteMode)
        assert result == GoldWriteMode.OVERWRITE

    def test_invalid_string_raises(self) -> None:
        """Test that invalid string raises ValueError."""
        with pytest.raises(ValueError):
            convert_write_mode("invalid_mode", SilverWriteMode)


@pytest.mark.unit
class TestResolveLoadingStrategy:
    """Tests for resolve_loading_strategy function."""

    def test_loading_strategy__none_returns_none__b04fa147(self) -> None:
        """Test that None input returns None."""
        result = resolve_loading_strategy(None)
        assert result is None

    def test_enum_value_passes_through(self) -> None:
        """Test that LoadingStrategy enum value passes through unchanged."""
        strategy = LoadingStrategy.FULL_SCAN_ONLY
        result = resolve_loading_strategy(strategy)
        assert result == LoadingStrategy.FULL_SCAN_ONLY
        assert isinstance(result, LoadingStrategy)

    def test_string_converted_to_enum(self) -> None:
        """Test that string value is converted to LoadingStrategy enum."""
        result = resolve_loading_strategy("full_scan_only")
        assert result == LoadingStrategy.FULL_SCAN_ONLY

    def test_loading_strategy__string_raises__2dcc559e(self) -> None:
        """Test that invalid string raises ValueError."""
        with pytest.raises(ValueError):
            resolve_loading_strategy("invalid_strategy")


@pytest.mark.unit
class TestFreezeSequences:
    """Tests for freeze_sequences function."""

    def test_converts_list_to_tuple(self) -> None:
        """Test that list field is converted to tuple."""

        @dataclass
        class TestObj:
            items: tuple | list

        obj = TestObj(items=["a", "b", "c"])
        freeze_sequences(obj, ("items",))
        assert isinstance(obj.items, tuple)
        assert obj.items == ("a", "b", "c")

    def test_tuple_already_tuple_unchanged(self) -> None:
        """Test that already-tuple field stays tuple."""

        @dataclass
        class TestObj:
            items: tuple | list

        obj = TestObj(items=("x", "y"))
        freeze_sequences(obj, ("items",))
        assert isinstance(obj.items, tuple)
        assert obj.items == ("x", "y")

    def test_freeze_sequences__multiple_fields__4d2879c7(self) -> None:
        """Test that multiple fields are all converted."""

        @dataclass
        class TestObj:
            field_a: tuple | list
            field_b: tuple | list

        obj = TestObj(field_a=[1, 2], field_b=[3, 4])
        freeze_sequences(obj, ("field_a", "field_b"))
        assert isinstance(obj.field_a, tuple)
        assert isinstance(obj.field_b, tuple)

    def test_empty_list_to_empty_tuple(self) -> None:
        """Test that empty list is converted to empty tuple."""

        @dataclass
        class TestObj:
            items: tuple | list

        obj = TestObj(items=[])
        freeze_sequences(obj, ("items",))
        assert obj.items == ()
