# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for medallion write mode enums."""

from __future__ import annotations

import pytest

from bioetl.domain.medallion import (
    GoldWriteMode,
    Layer,
    SilverWriteMode,
    WriteMode,
    WriteModePolicy,
)
from bioetl.domain.exceptions import PolicyViolationError


@pytest.mark.unit
class TestSilverWriteMode:
    """Tests for SilverWriteMode enum."""

    def test_silver_write_mode__enum_values__7c9ecbf9(self) -> None:
        """Test SilverWriteMode enum has correct string values."""
        assert SilverWriteMode.MERGE == "merge"
        assert SilverWriteMode.APPEND == "append"
        assert SilverWriteMode.DELETE == "delete"

    def test_from_string_merge(self) -> None:
        """Test converting 'merge' string to SilverWriteMode."""
        result = SilverWriteMode.from_string("merge")
        assert result == SilverWriteMode.MERGE

    def test_from_string_append(self) -> None:
        """Test converting 'append' string to SilverWriteMode."""
        result = SilverWriteMode.from_string("append")
        assert result == SilverWriteMode.APPEND

    def test_from_string_delete(self) -> None:
        """Test converting 'delete' string to SilverWriteMode."""
        result = SilverWriteMode.from_string("delete")
        assert result == SilverWriteMode.DELETE

    def test_silver_write_mode__case_insensitive__05548453(self) -> None:
        """Test from_string is case-insensitive."""
        assert SilverWriteMode.from_string("MERGE") == SilverWriteMode.MERGE
        assert SilverWriteMode.from_string("Append") == SilverWriteMode.APPEND

    def test_silver_write_mode__raises_value_error__10c235aa(self) -> None:
        """Test from_string raises ValueError for invalid values."""
        with pytest.raises(ValueError, match="Invalid Silver write mode"):
            SilverWriteMode.from_string("invalid_mode")

    def test_from_string_error_includes_valid_modes(self) -> None:
        """Test that error message includes valid modes."""
        with pytest.raises(ValueError, match="Valid modes"):
            SilverWriteMode.from_string("bad_mode")

    @pytest.mark.parametrize("value", ["merge", "append", "delete"])
    def test_silver_write_mode__string_roundtrip__6511b8d4(self, value: str) -> None:
        """Test that from_string is inverse of .value."""
        mode = SilverWriteMode.from_string(value)
        assert mode.value == value


@pytest.mark.unit
class TestGoldWriteMode:
    """Tests for GoldWriteMode enum."""

    def test_modes_gold_write_mode__enum_values__6210496a(self) -> None:
        """Test GoldWriteMode enum has correct string values."""
        assert GoldWriteMode.APPEND == "append"
        assert GoldWriteMode.SCD2 == "scd2"
        assert GoldWriteMode.OVERWRITE == "overwrite"

    def test_modes_gold_write_mode__from_string_append__30486eae(self) -> None:
        """Test converting 'append' string to GoldWriteMode."""
        result = GoldWriteMode.from_string("append")
        assert result == GoldWriteMode.APPEND

    def test_from_string_scd2(self) -> None:
        """Test converting 'scd2' string to GoldWriteMode."""
        result = GoldWriteMode.from_string("scd2")
        assert result == GoldWriteMode.SCD2

    def test_from_string_overwrite(self) -> None:
        """Test converting 'overwrite' string to GoldWriteMode."""
        result = GoldWriteMode.from_string("overwrite")
        assert result == GoldWriteMode.OVERWRITE

    def test_modes_gold_write_mode__case_insensitive__aeee06b8(self) -> None:
        """Test from_string is case-insensitive."""
        assert GoldWriteMode.from_string("OVERWRITE") == GoldWriteMode.OVERWRITE
        assert GoldWriteMode.from_string("SCD2") == GoldWriteMode.SCD2

    def test_modes_gold_write_mode__raises_value_error__2ad4faf3(self) -> None:
        """Test from_string raises ValueError for invalid values."""
        with pytest.raises(ValueError, match="Invalid Gold write mode"):
            GoldWriteMode.from_string("invalid_mode")

    def test_modes_gold_write_mode__includes_valid_modes__55dfa4fa(self) -> None:
        """Test that error message includes valid modes."""
        with pytest.raises(ValueError, match="Valid modes"):
            GoldWriteMode.from_string("bad_mode")

    @pytest.mark.parametrize("value", ["append", "scd2", "overwrite"])
    def test_modes_gold_write_mode__string_roundtrip__26c2895d(
        self, value: str
    ) -> None:
        """Test that from_string is inverse of .value."""
        mode = GoldWriteMode.from_string(value)
        assert mode.value == value


@pytest.mark.unit
class TestWriteModePolicy:
    """Tests for WriteModePolicy."""

    def test_bronze_allows_only_append(self) -> None:
        """Test that Bronze layer only allows APPEND mode."""
        policy = WriteModePolicy()
        policy.validate(Layer.BRONZE, WriteMode.APPEND)
        assert policy.ALLOWED_MODES[Layer.BRONZE] == {WriteMode.APPEND}

    def test_bronze_rejects_merge(self) -> None:
        """Test that Bronze layer rejects MERGE mode."""
        policy = WriteModePolicy()
        with pytest.raises(PolicyViolationError, match="bronze"):
            policy.validate(Layer.BRONZE, WriteMode.MERGE)

    def test_bronze_rejects_overwrite(self) -> None:
        """Test that Bronze layer rejects OVERWRITE mode."""
        policy = WriteModePolicy()
        with pytest.raises(PolicyViolationError, match="bronze"):
            policy.validate(Layer.BRONZE, WriteMode.OVERWRITE)

    def test_silver_allows_merge(self) -> None:
        """Test that Silver layer allows MERGE mode."""
        policy = WriteModePolicy()
        policy.validate(Layer.SILVER, WriteMode.MERGE)
        assert WriteMode.MERGE in policy.ALLOWED_MODES[Layer.SILVER]

    def test_silver_allows_append(self) -> None:
        """Test that Silver layer allows APPEND mode."""
        policy = WriteModePolicy()
        policy.validate(Layer.SILVER, WriteMode.APPEND)
        assert WriteMode.APPEND in policy.ALLOWED_MODES[Layer.SILVER]

    def test_silver_rejects_overwrite(self) -> None:
        """Test that Silver layer rejects OVERWRITE mode."""
        policy = WriteModePolicy()
        with pytest.raises(PolicyViolationError, match="silver"):
            policy.validate(Layer.SILVER, WriteMode.OVERWRITE)

    def test_gold_rejects_merge(self) -> None:
        """Test that Gold layer rejects MERGE mode."""
        policy = WriteModePolicy()
        with pytest.raises(PolicyViolationError, match="gold"):
            policy.validate(Layer.GOLD, WriteMode.MERGE)
        assert WriteMode.MERGE not in policy.ALLOWED_MODES[Layer.GOLD]

    def test_gold_allows_overwrite(self) -> None:
        """Test that Gold layer allows OVERWRITE mode."""
        policy = WriteModePolicy()
        policy.validate(Layer.GOLD, WriteMode.OVERWRITE)
        assert WriteMode.OVERWRITE in policy.ALLOWED_MODES[Layer.GOLD]

    def test_gold_allows_append(self) -> None:
        """Test that Gold layer allows APPEND mode."""
        policy = WriteModePolicy()
        policy.validate(Layer.GOLD, WriteMode.APPEND)
        assert WriteMode.APPEND in policy.ALLOWED_MODES[Layer.GOLD]

    def test_error_message_includes_allowed_modes(self) -> None:
        """Test that error message includes the allowed modes."""
        policy = WriteModePolicy()
        with pytest.raises(PolicyViolationError, match="Allowed:"):
            policy.validate(Layer.BRONZE, WriteMode.MERGE)
