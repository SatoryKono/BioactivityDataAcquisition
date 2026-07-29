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
"""Tests for TaxonomyId Value Object and validate_taxonomy_id helper.

Tests for NCBI Taxonomy identifier validation and normalization.
"""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects.taxonomy_id import TaxonomyId, validate_taxonomy_id

pytestmark = pytest.mark.unit


class TestTaxonomyId:
    """Tests for TaxonomyId Value Object."""

    def test_valid_integer(self) -> None:
        """Test creation from valid integer."""
        tid = TaxonomyId(9606)
        assert tid.value == 9606

    def test_id_taxonomy_id__valid_string__c7c56ccb(self) -> None:
        """Test creation from valid string."""
        tid = TaxonomyId("9606")
        assert tid.value == 9606

    def test_id_taxonomy_id__with_whitespace__c7c2bb7b(self) -> None:
        """Test whitespace is stripped before parsing."""
        tid = TaxonomyId("  9606  ")
        assert tid.value == 9606

    def test_as_str_property(self) -> None:
        """Test as_str returns string representation."""
        tid = TaxonomyId(9606)
        assert tid.as_str == "9606"
        assert isinstance(tid.as_str, str)

    def test_ncbi_url_property(self) -> None:
        """Test ncbi_url returns correct NCBI Taxonomy Browser URL."""
        tid = TaxonomyId(9606)
        assert tid.ncbi_url == (
            "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=9606"
        )

    def test_known_organisms(self) -> None:
        """Test well-known NCBI taxonomy IDs."""
        assert TaxonomyId(9606).value == 9606  # Homo sapiens
        assert TaxonomyId(10090).value == 10090  # Mus musculus
        assert TaxonomyId(562).value == 562  # E. coli

    def test_minimum_valid_value(self) -> None:
        """Test minimum valid taxonomy ID (1)."""
        tid = TaxonomyId(1)
        assert tid.value == 1

    def test_id_taxonomy_id__zero_raises__dbf7d0f3(self) -> None:
        """Test zero raises ValueError (must be >= 1)."""
        with pytest.raises(ValueError, match="must be >= 1"):
            TaxonomyId(0)

    def test_id_taxonomy_id__negative_raises__ae56e3fd(self) -> None:
        """Test negative value raises ValueError."""
        with pytest.raises(ValueError, match="must be >= 1"):
            TaxonomyId(-1)

    def test_exceeds_max_raises(self) -> None:
        """Test value >= 10_000_000 raises ValueError."""
        with pytest.raises(ValueError, match="must be <"):
            TaxonomyId(10_000_000)

    def test_id_taxonomy_id__bool_raises__ed69f171(self) -> None:
        """Test boolean input raises ValueError (bool is subclass of int)."""
        with pytest.raises(ValueError, match="bool"):
            TaxonomyId(True)  # type: ignore[arg-type]

    def test_non_numeric_string_raises(self) -> None:
        """Test non-numeric string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid TaxonomyId"):
            TaxonomyId("homo_sapiens")

    def test_id_taxonomy_id__empty_string_raises__3bba2582(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            TaxonomyId("")

    def test_from_raw_integer(self) -> None:
        """Test from_raw with integer."""
        tid = TaxonomyId.from_raw(9606)
        assert tid is not None
        assert tid.value == 9606

    def test_id_taxonomy_id__from_raw_string__34ea4765(self) -> None:
        """Test from_raw with string."""
        tid = TaxonomyId.from_raw("9606")
        assert tid is not None
        assert tid.value == 9606

    def test_id_taxonomy_id__none_returns_none__9ab3c93c(self) -> None:
        """Test from_raw with None returns None."""
        assert TaxonomyId.from_raw(None) is None

    def test_from_raw_bool_returns_none(self) -> None:
        """Test from_raw with bool returns None."""
        assert TaxonomyId.from_raw(True) is None
        assert TaxonomyId.from_raw(False) is None

    def test_from_raw_empty_string_returns_none(self) -> None:
        """Test from_raw with empty string returns None."""
        assert TaxonomyId.from_raw("") is None
        assert TaxonomyId.from_raw("   ") is None

    def test_from_raw_invalid_string_returns_none(self) -> None:
        """Test from_raw with invalid string returns None."""
        assert TaxonomyId.from_raw("invalid") is None

    def test_from_raw_zero_returns_none(self) -> None:
        """Test from_raw with 0 returns None (below minimum)."""
        assert TaxonomyId.from_raw(0) is None

    def test_equality_int_vs_string(self) -> None:
        """Test equality for int vs string-sourced IDs."""
        a = TaxonomyId(9606)
        b = TaxonomyId("9606")
        assert a == b

    def test_id_taxonomy_id__inequality__424cb181(self) -> None:
        """Test inequality for different taxonomy IDs."""
        a = TaxonomyId(9606)
        b = TaxonomyId(10090)
        assert a != b

    def test_id_taxonomy_id__hash_consistency__455ba34f(self) -> None:
        """Test hash is consistent with equality."""
        a = TaxonomyId(9606)
        b = TaxonomyId("9606")
        assert hash(a) == hash(b)

    def test_id_taxonomy_id__can_be_used_in_set__1d163dbd(self) -> None:
        """Test TaxonomyId can be used in a set."""
        ids = {TaxonomyId(9606), TaxonomyId(9606), TaxonomyId(10090)}
        assert len(ids) == 2

    def test_id_taxonomy_id__str_representation__295768af(self) -> None:
        """Test str() returns string of the value."""
        tid = TaxonomyId(9606)
        assert str(tid) == "9606"

    def test_id_taxonomy_id__repr__30740efb(self) -> None:
        """Test repr includes class name."""
        tid = TaxonomyId(9606)
        assert "TaxonomyId" in repr(tid)
        assert "9606" in repr(tid)

    def test_id_taxonomy_id__immutability__d375dd23(self) -> None:
        """Test TaxonomyId is immutable."""
        tid = TaxonomyId(9606)
        with pytest.raises(AttributeError, match="immutable"):
            tid._value = 1  # type: ignore[misc]


class TestValidateTaxonomyId:
    """Tests for validate_taxonomy_id helper function."""

    def test_valid_integer_returns_int(self) -> None:
        """Test valid integer input returns integer."""
        result = validate_taxonomy_id(9606)
        assert result == 9606
        assert isinstance(result, int)

    def test_valid_string_returns_int(self) -> None:
        """Test valid string input returns integer."""
        result = validate_taxonomy_id("9606")
        assert result == 9606

    def test_validate_taxonomy_id__none_returns_none__9dc97edb(self) -> None:
        """Test None input returns None."""
        assert validate_taxonomy_id(None) is None

    def test_validate_taxonomy_id__invalid_returns_none__80059cc7(self) -> None:
        """Test invalid input returns None."""
        assert validate_taxonomy_id("not_a_number") is None

    def test_validate_taxonomy_id__zero_returns_none__37537572(self) -> None:
        """Test zero returns None (below minimum)."""
        assert validate_taxonomy_id(0) is None

    def test_validate_taxonomy_id__bool_returns_none__57e2bea7(self) -> None:
        """Test bool input returns None."""
        assert validate_taxonomy_id(True) is None
