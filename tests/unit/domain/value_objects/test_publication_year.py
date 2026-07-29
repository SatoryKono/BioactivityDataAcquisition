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
"""Unit tests for PublicationYear Value Object."""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects import PublicationYear


@pytest.mark.unit
class TestPublicationYearValidation:
    """Tests for PublicationYear creation and validation."""

    def test_year_validation__valid_int_creation__3c5ad67f(self) -> None:
        year = PublicationYear(2020)
        assert year.value == 2020

    def test_year_validation__string_creation__480339cb(self) -> None:
        year = PublicationYear("2020")
        assert year.value == 2020

    def test_date_string_extraction__test_publication_year_validation_domain_value_objects_test_publication_year_22(
        self,
    ) -> None:
        year = PublicationYear("2024-01-15")
        assert year.value == 2024

    def test_date_with_slash(self) -> None:
        year = PublicationYear("2024/01/15")
        assert year.value == 2024

    def test_whitespace_stripped(self) -> None:
        year = PublicationYear("  2020  ")
        assert year.value == 2020

    def test_year_validation__bool_raises__37ddc526(self) -> None:
        with pytest.raises(ValueError, match="must be int"):
            PublicationYear(True)  # type: ignore[arg-type]

    def test_below_min_raises(self) -> None:
        with pytest.raises(ValueError, match="outside valid range"):
            PublicationYear(1400)

    def test_above_max_raises(self) -> None:
        with pytest.raises(ValueError, match="outside valid range"):
            PublicationYear(2200)

    def test_year_validation__string_raises__740019a2(self) -> None:
        with pytest.raises(ValueError, match="Invalid publication year"):
            PublicationYear("not-a-year")

    def test_boundary_min(self) -> None:
        year = PublicationYear(1500)
        assert year.value == 1500

    def test_boundary_max(self) -> None:
        year = PublicationYear(2100)
        assert year.value == 2100


@pytest.mark.unit
class TestPublicationYearProperties:
    """Tests for PublicationYear derived properties."""

    def test_decade(self) -> None:
        assert PublicationYear(1953).decade == 1950

    def test_decade_exact(self) -> None:
        assert PublicationYear(2020).decade == 2020

    def test_century(self) -> None:
        assert PublicationYear(1953).century == 20

    def test_century_21st(self) -> None:
        assert PublicationYear(2020).century == 21

    def test_min_year(self) -> None:
        year = PublicationYear(2020)
        assert year.min_year == 1500

    def test_max_year(self) -> None:
        year = PublicationYear(2020)
        assert year.max_year == 2100


@pytest.mark.unit
class TestPublicationYearFactoryAndEquality:
    """Tests for from_raw and equality."""

    def test_from_raw_int(self) -> None:
        result = PublicationYear.from_raw(2020)
        assert result is not None
        assert result.value == 2020

    def test_factory_and_equality__from_raw_string__01694e12(self) -> None:
        result = PublicationYear.from_raw("2020")
        assert result is not None
        assert result.value == 2020

    def test_factory_and_equality__from_raw_date_string__205f7c03(self) -> None:
        result = PublicationYear.from_raw("2024-01-15")
        assert result is not None
        assert result.value == 2024

    def test_factory_and_equality__from_raw_none__d59a035e(self) -> None:
        assert PublicationYear.from_raw(None) is None

    def test_factory_and_equality__from_raw_empty__3d3938ef(self) -> None:
        assert PublicationYear.from_raw("") is None

    def test_factory_and_equality__from_raw_invalid__1447028a(self) -> None:
        assert PublicationYear.from_raw("abc") is None

    def test_factory_and_equality__raw_out_of_range__8830ba16(self) -> None:
        assert PublicationYear.from_raw(1200) is None

    def test_factory_and_equality__equality__c1435a4d(self) -> None:
        y1 = PublicationYear(2020)
        y2 = PublicationYear(2020)
        assert y1 == y2

    def test_factory_and_equality__inequality__6315694c(self) -> None:
        y1 = PublicationYear(2020)
        y2 = PublicationYear(2021)
        assert y1 != y2

    def test_factory_and_equality__hash_equal__30591669(self) -> None:
        y1 = PublicationYear(2020)
        y2 = PublicationYear(2020)
        assert hash(y1) == hash(y2)
