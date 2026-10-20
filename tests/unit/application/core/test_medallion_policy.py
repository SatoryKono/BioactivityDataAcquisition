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
"""Unit tests for WriteModePolicy write mode validation.

Tests the generic write policy per RULES.md §3 (Medallion Architecture):
- Bronze: APPEND only
- Silver: APPEND or MERGE
- Gold: use GoldWriteMode, not generic WriteModePolicy
"""

from __future__ import annotations

import pytest

from bioetl.domain.exceptions import PolicyViolationError
from bioetl.domain.medallion import Layer, WriteMode, WriteModePolicy


@pytest.mark.unit
class TestLayer:
    """Tests for Layer enum."""

    def test_bronze_value(self):
        """Test Bronze layer value."""
        assert Layer.BRONZE.value == "bronze"

    def test_silver_value(self):
        """Test Silver layer value."""
        assert Layer.SILVER.value == "silver"

    def test_gold_value(self):
        """Test Gold layer value."""
        assert Layer.GOLD.value == "gold"

    def test_all_layers_defined(self):
        """Test that all expected layers are defined."""
        layers = {layer.value for layer in Layer}
        assert layers == {"bronze", "silver", "gold"}


@pytest.mark.unit
class TestWriteMode:
    """Tests for WriteMode enum."""

    def test_append_value(self):
        """Test APPEND mode value."""
        assert WriteMode.APPEND.value == "append"

    def test_merge_value(self):
        """Test MERGE mode value."""
        assert WriteMode.MERGE.value == "merge"

    def test_overwrite_value(self):
        """Test OVERWRITE mode value."""
        assert WriteMode.OVERWRITE.value == "overwrite"

    def test_all_modes_defined(self):
        """Test that all expected modes are defined."""
        modes = {mode.value for mode in WriteMode}
        assert modes == {"append", "merge", "overwrite"}


@pytest.mark.unit
class TestWriteModePolicyAllowedModes:
    """Tests for WriteModePolicy.ALLOWED_MODES configuration."""

    def test_bronze_allowed_modes(self):
        """Test Bronze layer allows only APPEND."""
        assert WriteModePolicy.ALLOWED_MODES[Layer.BRONZE] == {WriteMode.APPEND}

    def test_silver_allowed_modes(self):
        """Test Silver layer allows only APPEND and MERGE."""
        assert WriteModePolicy.ALLOWED_MODES[Layer.SILVER] == {
            WriteMode.APPEND,
            WriteMode.MERGE,
        }

    def test_generic_policy_covers_only_bronze_and_silver(self):
        """Gold writes are governed separately by GoldWriteMode."""
        defined_layers = set(WriteModePolicy.ALLOWED_MODES.keys())
        assert defined_layers == {Layer.BRONZE, Layer.SILVER}


@pytest.mark.unit
class TestWriteModePolicyValidateBronze:
    """Tests for Bronze layer validation."""

    def test_validate_bronze_accepts_append_mode(self):
        """Test Bronze APPEND is allowed."""
        policy = WriteModePolicy()
        assert policy.validate(Layer.BRONZE, WriteMode.APPEND) is None

    def test_bronze_merge_rejected(self):
        """Test Bronze MERGE is rejected."""
        policy = WriteModePolicy()
        with pytest.raises(PolicyViolationError) as exc_info:
            policy.validate(Layer.BRONZE, WriteMode.MERGE)
        assert "bronze does not allow merge" in str(exc_info.value)
        assert "append" in str(exc_info.value)

    def test_bronze_overwrite_rejected(self):
        """Test Bronze OVERWRITE is rejected (critical criterion)."""
        policy = WriteModePolicy()
        with pytest.raises(PolicyViolationError) as exc_info:
            policy.validate(Layer.BRONZE, WriteMode.OVERWRITE)
        assert "bronze does not allow overwrite" in str(exc_info.value)
        assert "append" in str(exc_info.value)


@pytest.mark.unit
class TestWriteModePolicyValidateSilver:
    """Tests for Silver layer validation."""

    def test_validate_silver_accepts_append_mode(self):
        """Test Silver APPEND is allowed."""
        policy = WriteModePolicy()
        assert policy.validate(Layer.SILVER, WriteMode.APPEND) is None

    def test_validate_silver_accepts_merge_mode(self):
        """Test Silver MERGE is allowed."""
        policy = WriteModePolicy()
        assert policy.validate(Layer.SILVER, WriteMode.MERGE) is None

    def test_silver_overwrite_rejected(self):
        """Test Silver OVERWRITE is rejected."""
        policy = WriteModePolicy()
        with pytest.raises(PolicyViolationError) as exc_info:
            policy.validate(Layer.SILVER, WriteMode.OVERWRITE)
        assert "silver does not allow overwrite" in str(exc_info.value)


@pytest.mark.unit
class TestWriteModePolicyValidateGold:
    """Tests that generic policy rejects Gold in favor of GoldWriteMode."""

    @pytest.mark.parametrize(
        "mode", [WriteMode.APPEND, WriteMode.MERGE, WriteMode.OVERWRITE]
    )
    def test_validate_gold_rejects_generic_modes(self, mode: WriteMode):
        """Every generic mode is rejected for Gold with a domain error."""
        policy = WriteModePolicy()
        with pytest.raises(PolicyViolationError, match="GoldWriteMode"):
            policy.validate(Layer.GOLD, mode)


@pytest.mark.unit
class TestWriteModePolicyValidateAllCombinations:
    """Parametrized tests for all layer/mode combinations."""

    @pytest.mark.parametrize(
        ("layer", "mode"),
        [
            (Layer.BRONZE, WriteMode.APPEND),
            (Layer.SILVER, WriteMode.APPEND),
            (Layer.SILVER, WriteMode.MERGE),
        ],
    )
    def test_validate_accepts_each_allowed_layer_mode_pair(
        self, layer: Layer, mode: WriteMode
    ):
        """Test all allowed layer/mode combinations."""
        policy = WriteModePolicy()
        assert policy.validate(layer, mode) is None

    @pytest.mark.parametrize(
        ("layer", "mode"),
        [
            (Layer.BRONZE, WriteMode.MERGE),
            (Layer.BRONZE, WriteMode.OVERWRITE),
            (Layer.SILVER, WriteMode.OVERWRITE),
            (Layer.GOLD, WriteMode.APPEND),
            (Layer.GOLD, WriteMode.MERGE),
            (Layer.GOLD, WriteMode.OVERWRITE),
        ],
    )
    def test_disallowed_combinations(self, layer: Layer, mode: WriteMode):
        """Test all disallowed layer/mode combinations."""
        policy = WriteModePolicy()
        with pytest.raises(PolicyViolationError):
            policy.validate(layer, mode)


@pytest.mark.unit
class TestPolicyViolationErrorMessage:
    """Tests for error message formatting."""

    def test_error_message_contains_layer_name(self):
        """Test error message contains layer name."""
        policy = WriteModePolicy()
        with pytest.raises(PolicyViolationError) as exc_info:
            policy.validate(Layer.BRONZE, WriteMode.OVERWRITE)
        assert "bronze" in str(exc_info.value)

    def test_error_message_contains_mode_name(self):
        """Test error message contains mode name."""
        policy = WriteModePolicy()
        with pytest.raises(PolicyViolationError) as exc_info:
            policy.validate(Layer.BRONZE, WriteMode.OVERWRITE)
        assert "overwrite" in str(exc_info.value)

    def test_error_message_contains_allowed_modes(self):
        """Test error message contains allowed modes."""
        policy = WriteModePolicy()
        with pytest.raises(PolicyViolationError) as exc_info:
            policy.validate(Layer.BRONZE, WriteMode.OVERWRITE)
        # Bronze only allows append
        assert "append" in str(exc_info.value)

    def test_error_is_critical_error(self):
        """Test that PolicyViolationError is a CriticalError."""
        from bioetl.domain.exceptions.base import CriticalError

        assert issubclass(PolicyViolationError, CriticalError)
