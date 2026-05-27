"""Tests for academic identifier Value Objects.

Tests for OpenAlexId, SemanticScholarId, ISSN, ORCID.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from bioetl.domain.value_objects.academic_ids import (
    ISSN,
    ORCID,
    OpenAlexId,
    SemanticScholarId,
)


# ===========================================================================
# OpenAlexId tests
# ===========================================================================


class TestOpenAlexId:
    """Tests for OpenAlexId Value Object."""

    def test_valid_creation(self) -> None:
        """Test creation with valid OpenAlex ID."""
        oa_id = OpenAlexId("W2741809807")
        assert oa_id.value == "W2741809807"

    def test_normalizes_to_uppercase(self) -> None:
        """Test that lowercase 'w' prefix is normalized to uppercase."""
        oa_id = OpenAlexId("w2741809807")
        assert oa_id.value == "W2741809807"

    def test_strips_whitespace(self) -> None:
        """Test whitespace is stripped before validation."""
        oa_id = OpenAlexId("  W123456  ")
        assert oa_id.value == "W123456"

    def test_extracts_from_url(self) -> None:
        """Test extraction from full OpenAlex URL."""
        oa_id = OpenAlexId("https://openalex.org/W2741809807")
        assert oa_id.value == "W2741809807"

    def test_url_property(self) -> None:
        """Test url property returns full OpenAlex URL."""
        oa_id = OpenAlexId("W2741809807")
        assert oa_id.url == "https://openalex.org/W2741809807"

    def test_numeric_id_property(self) -> None:
        """Test numeric_id strips the W prefix and returns int."""
        oa_id = OpenAlexId("W2741809807")
        assert oa_id.numeric_id == 2741809807

    def test_empty_string_raises(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            OpenAlexId("")

    def test_wrong_prefix_raises(self) -> None:
        """Test ID without W prefix raises ValueError."""
        with pytest.raises(ValueError, match="Invalid OpenAlex ID"):
            OpenAlexId("A2741809807")

    def test_non_digits_after_w_raises(self) -> None:
        """Test ID with non-digits after W raises ValueError."""
        with pytest.raises(ValueError, match="Invalid OpenAlex ID"):
            OpenAlexId("W274abc")

    def test_non_string_raises(self) -> None:
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be str"):
            OpenAlexId(12345)  # type: ignore[arg-type]

    def test_from_raw_valid(self) -> None:
        """Test from_raw with valid value."""
        oa_id = OpenAlexId.from_raw("W123456")
        assert oa_id is not None
        assert oa_id.value == "W123456"

    def test_from_raw_none_returns_none(self) -> None:
        """Test from_raw with None returns None."""
        assert OpenAlexId.from_raw(None) is None

    def test_from_raw_empty_returns_none(self) -> None:
        """Test from_raw with empty string returns None."""
        assert OpenAlexId.from_raw("") is None
        assert OpenAlexId.from_raw("   ") is None

    def test_from_raw_invalid_returns_none(self) -> None:
        """Test from_raw with invalid value returns None (not raise)."""
        assert OpenAlexId.from_raw("INVALID") is None

    def test_immutability(self) -> None:
        """Test OpenAlexId is immutable."""
        oa_id = OpenAlexId("W100")
        with pytest.raises(AttributeError, match="immutable"):
            oa_id._value = "W200"  # type: ignore[misc]

    def test_equality(self) -> None:
        """Test equality by value."""
        assert OpenAlexId("W100") == OpenAlexId("W100")
        assert OpenAlexId("W100") != OpenAlexId("W200")

    def test_hash_consistency(self) -> None:
        """Test hash is consistent with equality."""
        a = OpenAlexId("W100")
        b = OpenAlexId("w100")
        assert a == b
        assert hash(a) == hash(b)

    def test_can_be_used_in_set(self) -> None:
        """Test OpenAlexId can be used in a set."""
        ids = {OpenAlexId("W100"), OpenAlexId("W100"), OpenAlexId("W200")}
        assert len(ids) == 2


# ===========================================================================
# SemanticScholarId tests
# ===========================================================================


class TestSemanticScholarId:
    """Tests for SemanticScholarId Value Object."""

    VALID_ID = "649def34f8be52c8b66281af98ae884c09aef38b"  # 40-char hex

    def test_valid_creation(self) -> None:
        """Test creation with valid 40-char hex ID."""
        ss_id = SemanticScholarId(self.VALID_ID)
        assert ss_id.value == self.VALID_ID

    def test_normalizes_to_lowercase(self) -> None:
        """Test uppercase hex is normalized to lowercase."""
        upper_id = self.VALID_ID.upper()
        ss_id = SemanticScholarId(upper_id)
        assert ss_id.value == self.VALID_ID

    def test_strips_whitespace(self) -> None:
        """Test leading/trailing whitespace is stripped."""
        ss_id = SemanticScholarId(f"  {self.VALID_ID}  ")
        assert ss_id.value == self.VALID_ID

    def test_empty_raises(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SemanticScholarId("")

    def test_wrong_length_raises(self) -> None:
        """Test ID with wrong length raises ValueError."""
        with pytest.raises(ValueError, match="Invalid Semantic Scholar ID"):
            SemanticScholarId("abc123")

    def test_non_hex_raises(self) -> None:
        """Test ID with non-hex characters raises ValueError."""
        non_hex = "z" * 40
        with pytest.raises(ValueError, match="Invalid Semantic Scholar ID"):
            SemanticScholarId(non_hex)

    def test_from_raw_valid(self) -> None:
        """Test from_raw with valid value."""
        ss_id = SemanticScholarId.from_raw(self.VALID_ID)
        assert ss_id is not None
        assert ss_id.value == self.VALID_ID

    def test_from_raw_none_returns_none(self) -> None:
        """Test from_raw with None returns None."""
        assert SemanticScholarId.from_raw(None) is None

    def test_from_raw_invalid_returns_none(self) -> None:
        """Test from_raw with invalid value returns None."""
        assert SemanticScholarId.from_raw("tooshort") is None

    def test_equality(self) -> None:
        """Test equality by value."""
        a = SemanticScholarId(self.VALID_ID)
        b = SemanticScholarId(self.VALID_ID.upper())
        assert a == b

    def test_repr(self) -> None:
        """Test repr includes class name and value."""
        ss_id = SemanticScholarId(self.VALID_ID)
        assert "SemanticScholarId" in repr(ss_id)


# ===========================================================================
# ISSN tests
# ===========================================================================


class TestISSN:
    """Tests for ISSN Value Object."""

    def test_valid_with_hyphen(self) -> None:
        """Test ISSN with hyphen is valid."""
        issn = ISSN("0378-5955")
        assert issn.value == "0378-5955"

    def test_valid_without_hyphen_adds_hyphen(self) -> None:
        """Test ISSN without hyphen is normalized to include hyphen."""
        issn = ISSN("03785955")
        assert issn.value == "0378-5955"

    def test_x_check_digit_normalized_uppercase(self) -> None:
        """Test X check digit is normalized to uppercase."""
        issn = ISSN("0317-847x")
        assert issn.value == "0317-847X"

    def test_compact_property(self) -> None:
        """Test compact property removes hyphen."""
        issn = ISSN("0378-5955")
        assert issn.compact == "03785955"

    def test_empty_raises(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ISSN("")

    def test_invalid_format_raises(self) -> None:
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ISSN"):
            ISSN("ABCD-1234")  # letters in first group are invalid

    def test_wrong_length_raises(self) -> None:
        """Test string too short raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ISSN"):
            ISSN("1234-56")

    def test_from_raw_valid(self) -> None:
        """Test from_raw with valid ISSN."""
        issn = ISSN.from_raw("0378-5955")
        assert issn is not None
        assert issn.value == "0378-5955"

    def test_from_raw_none_returns_none(self) -> None:
        """Test from_raw with None returns None."""
        assert ISSN.from_raw(None) is None

    def test_from_raw_empty_returns_none(self) -> None:
        """Test from_raw with empty string returns None."""
        assert ISSN.from_raw("") is None

    def test_from_raw_invalid_returns_none(self) -> None:
        """Test from_raw with invalid format returns None."""
        assert ISSN.from_raw("not-an-issn") is None

    def test_equality(self) -> None:
        """Test equality: hyphenated vs no hyphen."""
        a = ISSN("0378-5955")
        b = ISSN("03785955")
        assert a == b

    def test_immutability(self) -> None:
        """Test ISSN is immutable."""
        issn = ISSN("0378-5955")
        with pytest.raises(AttributeError, match="immutable"):
            issn._value = "1234-5678"  # type: ignore[misc]


# ===========================================================================
# ORCID tests
# ===========================================================================


class TestORCID:
    """Tests for ORCID Value Object."""

    def test_valid_with_hyphens(self) -> None:
        """Test ORCID with hyphens is valid."""
        orcid = ORCID("0000-0002-1825-0097")
        assert orcid.value == "0000-0002-1825-0097"

    def test_valid_without_hyphens_adds_hyphens(self) -> None:
        """Test ORCID without hyphens is normalized to include hyphens."""
        orcid = ORCID("0000000218250097")
        assert orcid.value == "0000-0002-1825-0097"

    def test_x_check_digit_uppercase(self) -> None:
        """Test X check digit is normalized to uppercase."""
        orcid = ORCID("0000-0001-5109-370x")
        assert orcid.value == "0000-0001-5109-370X"

    def test_url_prefix_stripped(self) -> None:
        """Test ORCID URL prefix is stripped."""
        orcid = ORCID("https://orcid.org/0000-0002-1825-0097")
        assert orcid.value == "0000-0002-1825-0097"

    def test_url_property(self) -> None:
        """Test url property returns full ORCID URL."""
        orcid = ORCID("0000-0002-1825-0097")
        assert orcid.url == "https://orcid.org/0000-0002-1825-0097"

    def test_compact_property(self) -> None:
        """Test compact property removes all hyphens."""
        orcid = ORCID("0000-0002-1825-0097")
        assert orcid.compact == "0000000218250097"

    def test_empty_raises(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ORCID("")

    def test_invalid_format_raises(self) -> None:
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ORCID"):
            ORCID("1234-5678-9012")  # too short

    def test_non_string_raises(self) -> None:
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be str"):
            ORCID(123)  # type: ignore[arg-type]

    def test_from_raw_valid(self) -> None:
        """Test from_raw with valid ORCID."""
        orcid = ORCID.from_raw("0000-0002-1825-0097")
        assert orcid is not None
        assert orcid.value == "0000-0002-1825-0097"

    def test_from_raw_none_returns_none(self) -> None:
        """Test from_raw with None returns None."""
        assert ORCID.from_raw(None) is None

    def test_from_raw_empty_returns_none(self) -> None:
        """Test from_raw with empty string returns None."""
        assert ORCID.from_raw("") is None
        assert ORCID.from_raw("   ") is None

    def test_from_raw_invalid_returns_none(self) -> None:
        """Test from_raw with invalid format returns None."""
        assert ORCID.from_raw("not-an-orcid") is None

    def test_equality(self) -> None:
        """Test equality by value."""
        a = ORCID("0000-0002-1825-0097")
        b = ORCID("0000000218250097")
        assert a == b

    def test_hash_consistency(self) -> None:
        """Test hash is consistent with equality."""
        a = ORCID("0000-0002-1825-0097")
        b = ORCID("0000000218250097")
        assert hash(a) == hash(b)

    def test_can_be_used_in_set(self) -> None:
        """Test ORCID can be used in a set."""
        orcids = {
            ORCID("0000-0002-1825-0097"),
            ORCID("0000000218250097"),
            ORCID("0000-0001-5109-3700"),
        }
        assert len(orcids) == 2

    def test_immutability(self) -> None:
        """Test ORCID is immutable."""
        orcid = ORCID("0000-0002-1825-0097")
        with pytest.raises(AttributeError, match="immutable"):
            orcid._value = "0000-0001-0000-0000"  # type: ignore[misc]
