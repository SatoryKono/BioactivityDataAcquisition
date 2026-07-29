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
"""Unit tests for MolecularWeight Value Object."""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects import MolecularWeight


@pytest.mark.unit
class TestMolecularWeightValidation:
    """Tests for MolecularWeight creation and validation."""

    def test_valid_float_creation(self) -> None:
        mw = MolecularWeight(180.156)
        assert mw.value == pytest.approx(180.156)

    def test_valid_int_creation(self) -> None:
        mw = MolecularWeight(300)
        assert mw.value == pytest.approx(300.0)

    def test_valid_string_creation(self) -> None:
        mw = MolecularWeight("342.30")
        assert mw.value == pytest.approx(342.3)

    def test_rounds_to_precision(self) -> None:
        mw = MolecularWeight(180.15600000001)
        assert mw.value == pytest.approx(180.156)

    def test_weight_validation__nan_raises__92998f5b(self) -> None:
        with pytest.raises(ValueError, match="NaN or Inf"):
            MolecularWeight(float("nan"))

    def test_weight_validation__inf_raises__4b38f4cd(self) -> None:
        with pytest.raises(ValueError, match="NaN or Inf"):
            MolecularWeight(float("inf"))

    def test_neg_inf_raises(self) -> None:
        with pytest.raises(ValueError, match="NaN or Inf"):
            MolecularWeight(float("-inf"))

    def test_too_low_raises(self) -> None:
        with pytest.raises(ValueError, match="outside range"):
            MolecularWeight(5.0)

    def test_too_high_raises(self) -> None:
        with pytest.raises(ValueError, match="outside range"):
            MolecularWeight(15000.0)

    def test_weight_validation__string_raises__af3f3a2f(self) -> None:
        with pytest.raises(ValueError, match="Invalid molecular weight"):
            MolecularWeight("not-a-number")

    def test_boundary_just_above_min(self) -> None:
        mw = MolecularWeight(10.001)
        assert mw.value > 10.0

    def test_boundary_at_min_raises(self) -> None:
        with pytest.raises(ValueError, match="outside range"):
            MolecularWeight(10.0)

    def test_boundary_at_max_raises(self) -> None:
        with pytest.raises(ValueError, match="outside range"):
            MolecularWeight(10000.0)


@pytest.mark.unit
class TestMolecularWeightProperties:
    """Tests for MolecularWeight properties."""

    def test_min_weight(self) -> None:
        mw = MolecularWeight(180.0)
        assert mw.min_weight == pytest.approx(10.0)

    def test_max_weight(self) -> None:
        mw = MolecularWeight(180.0)
        assert mw.max_weight == pytest.approx(10000.0)


@pytest.mark.unit
class TestMolecularWeightFactoryAndEquality:
    """Tests for from_raw and equality."""

    def test_from_raw_float(self) -> None:
        result = MolecularWeight.from_raw(180.156)
        assert result is not None
        assert result.value == pytest.approx(180.156)

    def test_factory_and_equality__from_raw_string__3809d030(self) -> None:
        result = MolecularWeight.from_raw("342.30")
        assert result is not None

    def test_factory_and_equality__from_raw_none__e3418fb7(self) -> None:
        assert MolecularWeight.from_raw(None) is None

    def test_factory_and_equality__raw_empty_string__5f1c5100(self) -> None:
        assert MolecularWeight.from_raw("") is None

    def test_factory_and_equality__from_raw_invalid__b542e291(self) -> None:
        assert MolecularWeight.from_raw("abc") is None

    def test_from_raw_out_of_range(self) -> None:
        assert MolecularWeight.from_raw(1.0) is None

    def test_factory_and_equality__equality__1615451e(self) -> None:
        m1 = MolecularWeight(180.156)
        m2 = MolecularWeight(180.156)
        assert m1 == m2

    def test_factory_and_equality__inequality__ad0d56ac(self) -> None:
        m1 = MolecularWeight(180.156)
        m2 = MolecularWeight(342.3)
        assert m1 != m2

    def test_factory_and_equality__hash_equal__80f79caa(self) -> None:
        m1 = MolecularWeight(180.156)
        m2 = MolecularWeight(180.156)
        assert hash(m1) == hash(m2)
