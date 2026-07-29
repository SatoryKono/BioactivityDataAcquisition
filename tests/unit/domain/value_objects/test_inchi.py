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
"""Unit tests for InChI value object."""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects.inchi import InChI


@pytest.mark.unit
class TestInChIValidation:
    """Tests for InChI validation."""

    def test_valid_inchi_creation(self) -> None:
        """Test creating InChI with valid string."""
        inchi = InChI(
            "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)"
        )
        assert inchi.value.startswith("InChI=")

    def test_in_ch_i_validation__strips_whitespace__79f72bc5(self) -> None:
        """Test that whitespace is stripped."""
        inchi = InChI("  InChI=1S/C2H6/c1-2/h1-2H3  ")
        assert not inchi.value.startswith(" ")
        assert not inchi.value.endswith(" ")

    def test_inchi_non_string_raises_value_error(self) -> None:
        """Test that non-string raises ValueError."""
        with pytest.raises(ValueError, match="InChI must be str"):
            InChI(12345)  # type: ignore[arg-type]

    def test_inchi_empty_string_raises_value_error(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="InChI cannot be empty"):
            InChI("")

    def test_whitespace_only_raises_value_error(self) -> None:
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="InChI cannot be empty"):
            InChI("   ")

    def test_invalid_prefix_raises_value_error(self) -> None:
        """Test that string without InChI= prefix raises ValueError."""
        with pytest.raises(ValueError, match="must start with 'InChI='"):
            InChI("1S/C9H8O4")

    def test_wrong_prefix_raises_value_error(self) -> None:
        """Test that wrong prefix raises ValueError."""
        with pytest.raises(ValueError, match="must start with 'InChI='"):
            InChI("inchi=1S/C2H6")

    def test_in_ch_i_validation__equality__c49e85c9(self) -> None:
        """Test equality of InChI values."""
        inchi1 = InChI("InChI=1S/C2H6/c1-2/h1-2H3")
        inchi2 = InChI("InChI=1S/C2H6/c1-2/h1-2H3")
        assert inchi1 == inchi2

    def test_in_ch_i_validation__inequality__865506a7(self) -> None:
        """Test inequality of different InChI values."""
        inchi1 = InChI("InChI=1S/C2H6/c1-2/h1-2H3")
        inchi2 = InChI("InChI=1S/C3H8/c1-3-2/h3H2,1-2H3")
        assert inchi1 != inchi2


@pytest.mark.unit
class TestInChIFromRaw:
    """Tests for InChI.from_raw() factory method."""

    def test_inchi_in_ch_i_from_raw__none_returns_none__e7aaaf19(self) -> None:
        """Test that None returns None."""
        assert InChI.from_raw(None) is None

    def test_inchi_in_ch_i_from_raw__string_returns_none__7831e7d9(self) -> None:
        """Test that empty string returns None."""
        assert InChI.from_raw("") is None

    def test_inchi_in_ch_i_from_raw__only_returns_none__42d9aa2b(self) -> None:
        """Test that whitespace-only string returns None."""
        assert InChI.from_raw("   ") is None

    def test_invalid_format_returns_none(self) -> None:
        """Test that invalid format returns None (no exception)."""
        result = InChI.from_raw("not-an-inchi")
        assert result is None

    def test_valid_inchi_returns_instance(self) -> None:
        """Test that valid InChI returns InChI instance."""
        raw = "InChI=1S/C2H6/c1-2/h1-2H3"
        result = InChI.from_raw(raw)
        assert result is not None
        assert isinstance(result, InChI)
        assert result.value == raw

    def test_valid_inchi_with_whitespace_returned(self) -> None:
        """Test that valid InChI with whitespace is stripped and returned."""
        result = InChI.from_raw("  InChI=1S/C2H6/c1-2/h1-2H3  ")
        assert result is not None
        assert result.value == "InChI=1S/C2H6/c1-2/h1-2H3"
