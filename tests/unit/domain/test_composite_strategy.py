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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for composite pipeline strategy enums."""

from __future__ import annotations

import pytest

from bioetl.domain.composite.strategy import (
    ConflictResolution,
    FallbackStrategy,
    MergeStrategy,
)


@pytest.mark.unit
class TestMergeStrategy:
    """Tests for MergeStrategy enum."""

    def test_enum_values(self) -> None:
        """Test that enum members have correct string values."""
        assert MergeStrategy.LEFT_OUTER == "left_outer"
        assert MergeStrategy.INNER == "inner"
        assert MergeStrategy.UNION == "union"

    def test_from_string_left_outer(self) -> None:
        """Test from_string for LEFT_OUTER."""
        result = MergeStrategy.from_string("left_outer")
        assert result == MergeStrategy.LEFT_OUTER

    def test_from_string_inner(self) -> None:
        """Test from_string for INNER."""
        result = MergeStrategy.from_string("inner")
        assert result == MergeStrategy.INNER

    def test_from_string_union(self) -> None:
        """Test from_string for UNION."""
        result = MergeStrategy.from_string("union")
        assert result == MergeStrategy.UNION

    def test_from_string_case_insensitive(self) -> None:
        """Test from_string is case-insensitive."""
        assert MergeStrategy.from_string("INNER") == MergeStrategy.INNER
        assert MergeStrategy.from_string("Left_Outer") == MergeStrategy.LEFT_OUTER

    def test_from_string_invalid_raises(self) -> None:
        """Test from_string raises ValueError for invalid values."""
        with pytest.raises(ValueError, match="Invalid merge strategy"):
            MergeStrategy.from_string("invalid_strategy")

    def test_from_string_error_includes_valid_values(self) -> None:
        """Test that error message includes valid options."""
        with pytest.raises(ValueError, match="Valid:"):
            MergeStrategy.from_string("unknown")

    @pytest.mark.parametrize("value", ["left_outer", "inner", "union"])
    def test_from_string_roundtrip(self, value: str) -> None:
        """Test that from_string is inverse of .value."""
        strategy = MergeStrategy.from_string(value)
        assert strategy.value == value


@pytest.mark.unit
class TestConflictResolution:
    """Tests for ConflictResolution enum."""

    def test_conflict_resolution__enum_values__9ffc18ff(self) -> None:
        """Test that enum members have correct string values."""
        assert ConflictResolution.SEED_PRIORITY == "seed_priority"
        assert ConflictResolution.ENRICHER_PRIORITY == "enricher"
        assert ConflictResolution.LATEST_TIMESTAMP == "latest"
        assert ConflictResolution.EXPLICIT_RULES == "explicit"
        assert ConflictResolution.COALESCE == "coalesce"

    def test_from_string_seed_priority(self) -> None:
        """Test from_string for SEED_PRIORITY."""
        result = ConflictResolution.from_string("seed_priority")
        assert result == ConflictResolution.SEED_PRIORITY

    def test_from_string_coalesce(self) -> None:
        """Test from_string for COALESCE."""
        result = ConflictResolution.from_string("coalesce")
        assert result == ConflictResolution.COALESCE

    def test_conflict_resolution__case_insensitive__4ca69dcf(self) -> None:
        """Test from_string is case-insensitive."""
        assert ConflictResolution.from_string("COALESCE") == ConflictResolution.COALESCE

    def test_conflict_resolution__invalid_raises__0de274c3(self) -> None:
        """Test from_string raises ValueError for invalid values."""
        with pytest.raises(ValueError, match="Invalid conflict resolution"):
            ConflictResolution.from_string("wrong_value")

    @pytest.mark.parametrize(
        "value",
        ["seed_priority", "enricher", "latest", "explicit", "coalesce"],
    )
    def test_conflict_resolution__string_roundtrip__133a1a41(self, value: str) -> None:
        """Test that from_string is inverse of .value."""
        resolution = ConflictResolution.from_string(value)
        assert resolution.value == value


@pytest.mark.unit
class TestFallbackStrategy:
    """Tests for FallbackStrategy enum."""

    def test_fallback_strategy__enum_values__b423ef17(self) -> None:
        """Test that enum members have correct string values."""
        assert FallbackStrategy.SKIP == "skip"
        assert FallbackStrategy.USE_CACHED == "use_cached"
        assert FallbackStrategy.FAIL == "fail"

    def test_from_string_skip(self) -> None:
        """Test from_string for SKIP."""
        result = FallbackStrategy.from_string("skip")
        assert result == FallbackStrategy.SKIP

    def test_from_string_use_cached(self) -> None:
        """Test from_string for USE_CACHED."""
        result = FallbackStrategy.from_string("use_cached")
        assert result == FallbackStrategy.USE_CACHED

    def test_from_string_fail(self) -> None:
        """Test from_string for FAIL."""
        result = FallbackStrategy.from_string("fail")
        assert result == FallbackStrategy.FAIL

    def test_fallback_strategy__case_insensitive__dd252ac3(self) -> None:
        """Test from_string is case-insensitive."""
        assert FallbackStrategy.from_string("SKIP") == FallbackStrategy.SKIP
        assert FallbackStrategy.from_string("FAIL") == FallbackStrategy.FAIL

    def test_fallback_strategy__invalid_raises__d4e90d38(self) -> None:
        """Test from_string raises ValueError for invalid values."""
        with pytest.raises(ValueError, match="Invalid fallback strategy"):
            FallbackStrategy.from_string("invalid_fallback")

    def test_fallback_strategy__valid_values__08f9cab1(self) -> None:
        """Test that error message includes valid options."""
        with pytest.raises(ValueError, match="Valid:"):
            FallbackStrategy.from_string("unknown")

    @pytest.mark.parametrize("value", ["skip", "use_cached", "fail"])
    def test_fallback_strategy__string_roundtrip__d9160f5b(self, value: str) -> None:
        """Test that from_string is inverse of .value."""
        strategy = FallbackStrategy.from_string(value)
        assert strategy.value == value
