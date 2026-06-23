"""Tests for publication Value Objects.

Tests for OpenAlexId, SemanticScholarId, ISSN, and ORCID Value Objects.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from bioetl.domain.value_objects import (
    ISSN,
    ORCID,
    OpenAlexId,
    SemanticScholarId,
)

LEGACY_HTTP_ORCID = "http" + "://orcid.org/0000-0002-1825-0097"


class TestOpenAlexId:
    """Tests for OpenAlexId Value Object."""

    def test_valid_openalex_id(self) -> None:
        """Test creation with valid OpenAlex ID."""
        oid = OpenAlexId("W2741809807")
        assert oid.value == "W2741809807"
        assert oid.numeric_id == 2741809807

    def test_open_alex_id__normalizes_case__90ee9781(self) -> None:
        """Test case normalization to uppercase."""
        oid = OpenAlexId("w2741809807")
        assert oid.value == "W2741809807"

    def test_open_alex_id__strips_whitespace__3dc896e5(self) -> None:
        """Test whitespace stripping."""
        oid = OpenAlexId("  W2741809807  ")
        assert oid.value == "W2741809807"

    def test_open_alex_id__extracts_from_url__9e695384(self) -> None:
        """Test extraction from OpenAlex URL."""
        oid = OpenAlexId("https://openalex.org/W2741809807")
        assert oid.value == "W2741809807"

    def test_url_case_insensitive(self) -> None:
        """Test URL prefix extraction is case insensitive."""
        oid = OpenAlexId("HTTPS://OPENALEX.ORG/W2741809807")
        assert oid.value == "W2741809807"

    def test_open_alex_id__url_property__b596dd3f(self) -> None:
        """Test url property returns full URL."""
        oid = OpenAlexId("W2741809807")
        assert oid.url == "https://openalex.org/W2741809807"

    def test_open_alex_id__numeric_id_property__bbeb2bc1(self) -> None:
        """Test numeric_id property."""
        oid = OpenAlexId("W123456")
        assert oid.numeric_id == 123456

    def test_open_alex_id__empty_raises__524a10da(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            OpenAlexId("")

    def test_open_alex_id__only_raises__a9417d71(self) -> None:
        """Test whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            OpenAlexId("   ")

    def test_open_alex_id__format_raises__71cd12c8(self) -> None:
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid OpenAlex ID format"):
            OpenAlexId("X2741809807")

    def test_no_digits_raises(self) -> None:
        """Test ID without digits raises ValueError."""
        with pytest.raises(ValueError, match="Invalid OpenAlex ID format"):
            OpenAlexId("W")

    def test_open_alex_id__non_string_raises__436f009f(self) -> None:
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be str"):
            OpenAlexId(123)  # type: ignore[arg-type]

    def test_open_alex_id__immutability__0ca928af(self) -> None:
        """Test Value Object is immutable."""
        oid = OpenAlexId("W2741809807")
        with pytest.raises(AttributeError, match="immutable"):
            oid._value = "W999999"  # type: ignore[misc]

    def test_open_alex_id__equality_by_value__435629f2(self) -> None:
        """Test equality is based on value, not identity."""
        oid1 = OpenAlexId("W2741809807")
        oid2 = OpenAlexId("w2741809807")
        assert oid1 == oid2
        assert oid1 is not oid2

    def test_equality_with_url(self) -> None:
        """Test equality between plain ID and URL format."""
        oid1 = OpenAlexId("W2741809807")
        oid2 = OpenAlexId("https://openalex.org/W2741809807")
        assert oid1 == oid2

    def test_open_alex_id__hash_consistency__2e3fac70(self) -> None:
        """Test hash is consistent with equality."""
        oid1 = OpenAlexId("W2741809807")
        oid2 = OpenAlexId("w2741809807")
        assert hash(oid1) == hash(oid2)

    def test_open_alex_id__can_be_used_in_set__72596f6b(self) -> None:
        """Test Value Object can be used in set."""
        ids = {OpenAlexId("W111"), OpenAlexId("w111"), OpenAlexId("W222")}
        assert len(ids) == 2

    def test_open_alex_id__be_used_as_dict_key__65f6c5bc(self) -> None:
        """Test Value Object can be used as dict key."""
        d = {OpenAlexId("W2741809807"): "paper"}
        assert d[OpenAlexId("w2741809807")] == "paper"

    def test_open_alex_id__repr__0e171dfb(self) -> None:
        """Test string representation."""
        oid = OpenAlexId("W2741809807")
        assert repr(oid) == "OpenAlexId('W2741809807')"

    def test_open_alex_id__str__34327b1d(self) -> None:
        """Test string conversion."""
        oid = OpenAlexId("W2741809807")
        assert str(oid) == "W2741809807"

    def test_open_alex_id__from_raw_valid__7394e77b(self) -> None:
        """Test from_raw with valid OpenAlex ID."""
        oid = OpenAlexId.from_raw("W2741809807")
        assert oid is not None
        assert oid.value == "W2741809807"

    def test_from_raw_url(self) -> None:
        """Test from_raw with URL format."""
        oid = OpenAlexId.from_raw("https://openalex.org/W2741809807")
        assert oid is not None
        assert oid.value == "W2741809807"

    def test_open_alex_id__from_raw_none__0eaeb0f3(self) -> None:
        """Test from_raw with None."""
        assert OpenAlexId.from_raw(None) is None

    def test_open_alex_id__from_raw_empty__349047d1(self) -> None:
        """Test from_raw with empty string."""
        assert OpenAlexId.from_raw("") is None
        assert OpenAlexId.from_raw("   ") is None

    def test_open_alex_id__from_raw_invalid__1a5bd4bb(self) -> None:
        """Test from_raw with invalid value returns None."""
        assert OpenAlexId.from_raw("invalid") is None
        assert OpenAlexId.from_raw("X123") is None


class TestSemanticScholarId:
    """Tests for SemanticScholarId Value Object."""

    def test_valid_semantic_scholar_id(self) -> None:
        """Test creation with valid Semantic Scholar ID."""
        s2id = SemanticScholarId("649def34f8be52c8b66281af98ae884c09aef38b")
        assert s2id.value == "649def34f8be52c8b66281af98ae884c09aef38b"

    def test_semantic_scholar_id__normalizes_case__bf49e6f8(self) -> None:
        """Test case normalization to lowercase."""
        s2id = SemanticScholarId("649DEF34F8BE52C8B66281AF98AE884C09AEF38B")
        assert s2id.value == "649def34f8be52c8b66281af98ae884c09aef38b"

    def test_semantic_scholar_id__strips_whitespace__74c76426(self) -> None:
        """Test whitespace stripping."""
        s2id = SemanticScholarId("  649def34f8be52c8b66281af98ae884c09aef38b  ")
        assert s2id.value == "649def34f8be52c8b66281af98ae884c09aef38b"

    def test_semantic_scholar_id__empty_raises__fd3248e0(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SemanticScholarId("")

    def test_semantic_scholar_id__only_raises__d129a7d7(self) -> None:
        """Test whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SemanticScholarId("   ")

    def test_semantic_scholar_id__too_short_raises__57d7cdb2(self) -> None:
        """Test too short ID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid Semantic Scholar ID format"):
            SemanticScholarId("649def34f8be52c8b66281af98ae884c09aef38")  # 39 chars

    def test_too_long_raises(self) -> None:
        """Test too long ID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid Semantic Scholar ID format"):
            SemanticScholarId("649def34f8be52c8b66281af98ae884c09aef38ba")  # 41 chars

    def test_semantic_scholar_id__non_hex_raises__06bcfb6a(self) -> None:
        """Test non-hexadecimal characters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid Semantic Scholar ID format"):
            SemanticScholarId("649def34f8be52c8b66281af98ae884c09aef38g")  # 'g' invalid

    def test_semantic_scholar_id__non_string_raises__477b33ae(self) -> None:
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be str"):
            SemanticScholarId(123)  # type: ignore[arg-type]

    def test_semantic_scholar_id__immutability__a7f6a034(self) -> None:
        """Test Value Object is immutable."""
        s2id = SemanticScholarId("649def34f8be52c8b66281af98ae884c09aef38b")
        with pytest.raises(AttributeError, match="immutable"):
            s2id._value = "0" * 40  # type: ignore[misc]

    def test_semantic_scholar_id__equality_by_value__da12d012(self) -> None:
        """Test equality is based on value, not identity."""
        s2id1 = SemanticScholarId("649def34f8be52c8b66281af98ae884c09aef38b")
        s2id2 = SemanticScholarId("649DEF34F8BE52C8B66281AF98AE884C09AEF38B")
        assert s2id1 == s2id2
        assert s2id1 is not s2id2

    def test_semantic_scholar_id__hash_consistency__e42d06fc(self) -> None:
        """Test hash is consistent with equality."""
        s2id1 = SemanticScholarId("649def34f8be52c8b66281af98ae884c09aef38b")
        s2id2 = SemanticScholarId("649DEF34F8BE52C8B66281AF98AE884C09AEF38B")
        assert hash(s2id1) == hash(s2id2)

    def test_semantic_scholar_id__can_be_used_in_set__3b397b85(self) -> None:
        """Test Value Object can be used in set."""
        ids = {
            SemanticScholarId("649def34f8be52c8b66281af98ae884c09aef38b"),
            SemanticScholarId("649DEF34F8BE52C8B66281AF98AE884C09AEF38B"),
            SemanticScholarId("0" * 40),
        }
        assert len(ids) == 2

    def test_semantic_scholar_id__repr__eec104b4(self) -> None:
        """Test string representation."""
        s2id = SemanticScholarId("649def34f8be52c8b66281af98ae884c09aef38b")
        assert (
            repr(s2id)
            == "SemanticScholarId('649def34f8be52c8b66281af98ae884c09aef38b')"
        )

    def test_semantic_scholar_id__str__5d8cbb08(self) -> None:
        """Test string conversion."""
        s2id = SemanticScholarId("649def34f8be52c8b66281af98ae884c09aef38b")
        assert str(s2id) == "649def34f8be52c8b66281af98ae884c09aef38b"

    def test_semantic_scholar_id__from_raw_valid__c79520a8(self) -> None:
        """Test from_raw with valid Semantic Scholar ID."""
        s2id = SemanticScholarId.from_raw("649def34f8be52c8b66281af98ae884c09aef38b")
        assert s2id is not None
        assert s2id.value == "649def34f8be52c8b66281af98ae884c09aef38b"

    def test_semantic_scholar_id__from_raw_none__4a2245e7(self) -> None:
        """Test from_raw with None."""
        assert SemanticScholarId.from_raw(None) is None

    def test_semantic_scholar_id__from_raw_empty__8fc28539(self) -> None:
        """Test from_raw with empty string."""
        assert SemanticScholarId.from_raw("") is None
        assert SemanticScholarId.from_raw("   ") is None

    def test_semantic_scholar_id__from_raw_invalid__01bde41d(self) -> None:
        """Test from_raw with invalid value returns None."""
        assert SemanticScholarId.from_raw("invalid") is None
        assert SemanticScholarId.from_raw("649def34") is None  # Too short


class TestISSN:
    """Tests for ISSN Value Object."""

    def test_valid_issn_with_hyphen(self) -> None:
        """Test creation with valid ISSN with hyphen."""
        issn = ISSN("0378-5955")
        assert issn.value == "0378-5955"

    def test_valid_issn_without_hyphen(self) -> None:
        """Test creation with valid ISSN without hyphen."""
        issn = ISSN("03785955")
        assert issn.value == "0378-5955"

    def test_valid_issn_with_x_check_digit(self) -> None:
        """Test ISSN with X check digit."""
        issn = ISSN("0317-847X")
        assert issn.value == "0317-847X"

    def test_normalizes_lowercase_x(self) -> None:
        """Test lowercase x is normalized to uppercase."""
        issn = ISSN("0317-847x")
        assert issn.value == "0317-847X"

    def test_compact_without_x(self) -> None:
        """Test compact format without hyphen."""
        issn = ISSN("0317847x")
        assert issn.value == "0317-847X"

    def test_publications_i_s_s_n__strips_whitespace__dc5aa477(self) -> None:
        """Test whitespace stripping."""
        issn = ISSN("  0378-5955  ")
        assert issn.value == "0378-5955"

    def test_publications_i_s_s_n__compact_property__5234d470(self) -> None:
        """Test compact property returns ISSN without hyphen."""
        issn = ISSN("0378-5955")
        assert issn.compact == "03785955"

    def test_compact_property_with_x(self) -> None:
        """Test compact property with X check digit."""
        issn = ISSN("0317-847X")
        assert issn.compact == "0317847X"

    def test_publications_i_s_s_n__empty_raises__e6b44f0d(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ISSN("")

    def test_publications_i_s_s_n__only_raises__3b166b43(self) -> None:
        """Test whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ISSN("   ")

    def test_publications_i_s_s_n__too_short_raises__1770e17b(self) -> None:
        """Test too short ISSN raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ISSN format"):
            ISSN("0378-595")

    def test_publications_i_s_s_n__too_long_raises__0e5cb3e5(self) -> None:
        """Test too long ISSN raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ISSN format"):
            ISSN("0378-59555")

    def test_publications_i_s_s_n__characters_raises__8b9023c3(self) -> None:
        """Test invalid characters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid ISSN format"):
            ISSN("0378-595A")

    def test_x_in_wrong_position_raises(self) -> None:
        """Test X not in last position raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ISSN format"):
            ISSN("037X-5955")

    def test_publications_i_s_s_n__non_string_raises__fba6ce9a(self) -> None:
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be str"):
            ISSN(12345678)  # type: ignore[arg-type]

    def test_publications_i_s_s_n__immutability__e3c7357d(self) -> None:
        """Test Value Object is immutable."""
        issn = ISSN("0378-5955")
        with pytest.raises(AttributeError, match="immutable"):
            issn._value = "0000-0000"  # type: ignore[misc]

    def test_publications_i_s_s_n__equality_by_value__edc82ac2(self) -> None:
        """Test equality is based on value, not identity."""
        issn1 = ISSN("0378-5955")
        issn2 = ISSN("03785955")
        assert issn1 == issn2
        assert issn1 is not issn2

    def test_equality_with_x(self) -> None:
        """Test equality with X check digit."""
        issn1 = ISSN("0317-847X")
        issn2 = ISSN("0317847x")
        assert issn1 == issn2

    def test_publications_i_s_s_n__hash_consistency__27fcd130(self) -> None:
        """Test hash is consistent with equality."""
        issn1 = ISSN("0378-5955")
        issn2 = ISSN("03785955")
        assert hash(issn1) == hash(issn2)

    def test_publications_i_s_s_n__can_be_used_in_set__3a6713cd(self) -> None:
        """Test Value Object can be used in set."""
        issns = {ISSN("0378-5955"), ISSN("03785955"), ISSN("2049-3630")}
        assert len(issns) == 2

    def test_publications_i_s_s_n__repr__4934bffb(self) -> None:
        """Test string representation."""
        issn = ISSN("0378-5955")
        assert repr(issn) == "ISSN('0378-5955')"

    def test_publications_i_s_s_n__str__ee65679f(self) -> None:
        """Test string conversion."""
        issn = ISSN("0378-5955")
        assert str(issn) == "0378-5955"

    def test_publications_i_s_s_n__from_raw_valid__620c0df2(self) -> None:
        """Test from_raw with valid ISSN."""
        issn = ISSN.from_raw("0378-5955")
        assert issn is not None
        assert issn.value == "0378-5955"

    def test_from_raw_compact(self) -> None:
        """Test from_raw with compact format."""
        issn = ISSN.from_raw("03785955")
        assert issn is not None
        assert issn.value == "0378-5955"

    def test_publications_i_s_s_n__from_raw_none__892dd827(self) -> None:
        """Test from_raw with None."""
        assert ISSN.from_raw(None) is None

    def test_publications_i_s_s_n__from_raw_empty__4ee456cf(self) -> None:
        """Test from_raw with empty string."""
        assert ISSN.from_raw("") is None
        assert ISSN.from_raw("   ") is None

    def test_publications_i_s_s_n__from_raw_invalid__392aaddf(self) -> None:
        """Test from_raw with invalid value returns None."""
        assert ISSN.from_raw("invalid") is None
        assert ISSN.from_raw("0378-595") is None


class TestORCID:
    """Tests for ORCID Value Object."""

    def test_valid_orcid_with_hyphens(self) -> None:
        """Test creation with valid ORCID with hyphens."""
        orcid = ORCID("0000-0002-1825-0097")
        assert orcid.value == "0000-0002-1825-0097"

    def test_valid_orcid_without_hyphens(self) -> None:
        """Test creation with valid ORCID without hyphens."""
        orcid = ORCID("0000000218250097")
        assert orcid.value == "0000-0002-1825-0097"

    def test_valid_orcid_with_x_check_digit(self) -> None:
        """Test ORCID with X check digit."""
        orcid = ORCID("0000-0001-5109-370X")
        assert orcid.value == "0000-0001-5109-370X"

    def test_publications_o_r_c_i_d__lowercase_x__4c21276a(self) -> None:
        """Test lowercase x is normalized to uppercase."""
        orcid = ORCID("0000-0001-5109-370x")
        assert orcid.value == "0000-0001-5109-370X"

    def test_compact_without_x__test_o_r_c_i_d_domain_value_objects_test_publications_436(
        self,
    ) -> None:
        """Test compact format without hyphens."""
        orcid = ORCID("0000000151093700")
        assert orcid.value == "0000-0001-5109-3700"

    def test_publications_o_r_c_i_d__strips_whitespace__c6109fa3(self) -> None:
        """Test whitespace stripping."""
        orcid = ORCID("  0000-0002-1825-0097  ")
        assert orcid.value == "0000-0002-1825-0097"

    def test_extracts_from_https_url(self) -> None:
        """Test extraction from HTTPS URL."""
        orcid = ORCID("https://orcid.org/0000-0002-1825-0097")
        assert orcid.value == "0000-0002-1825-0097"

    def test_extracts_from_http_url(self) -> None:
        """Test extraction from HTTP URL."""
        orcid = ORCID(LEGACY_HTTP_ORCID)
        assert orcid.value == "0000-0002-1825-0097"

    def test_extracts_from_bare_url(self) -> None:
        """Test extraction from bare URL (no protocol)."""
        orcid = ORCID("orcid.org/0000-0002-1825-0097")
        assert orcid.value == "0000-0002-1825-0097"

    def test_publications_o_r_c_i_d__url_case_insensitive__bbc9e967(self) -> None:
        """Test URL prefix extraction is case insensitive."""
        orcid = ORCID("HTTPS://ORCID.ORG/0000-0002-1825-0097")
        assert orcid.value == "0000-0002-1825-0097"

    def test_publications_o_r_c_i_d__url_property__3c3fb10c(self) -> None:
        """Test url property returns full URL."""
        orcid = ORCID("0000-0002-1825-0097")
        assert orcid.url == "https://orcid.org/0000-0002-1825-0097"

    def test_publications_o_r_c_i_d__compact_property__72aef308(self) -> None:
        """Test compact property returns ORCID without hyphens."""
        orcid = ORCID("0000-0002-1825-0097")
        assert orcid.compact == "0000000218250097"

    def test_compact_property_with_x__test_o_r_c_i_d_domain_value_objects_test_publications_476(
        self,
    ) -> None:
        """Test compact property with X check digit."""
        orcid = ORCID("0000-0001-5109-370X")
        assert orcid.compact == "000000015109370X"

    def test_publications_o_r_c_i_d__empty_raises__9573bbf2(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ORCID("")

    def test_publications_o_r_c_i_d__only_raises__b6d58a1b(self) -> None:
        """Test whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ORCID("   ")

    def test_publications_o_r_c_i_d__too_short_raises__221e3512(self) -> None:
        """Test too short ORCID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ORCID format"):
            ORCID("0000-0002-1825-009")

    def test_publications_o_r_c_i_d__too_long_raises__302df9c8(self) -> None:
        """Test too long ORCID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ORCID format"):
            ORCID("0000-0002-1825-00977")

    def test_publications_o_r_c_i_d__characters_raises__88c2138c(self) -> None:
        """Test invalid characters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid ORCID format"):
            ORCID("0000-0002-1825-009A")

    def test_publications_o_r_c_i_d__position_raises__e118f0fa(self) -> None:
        """Test X not in last position raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ORCID format"):
            ORCID("000X-0002-1825-0097")

    def test_publications_o_r_c_i_d__non_string_raises__45d50f50(self) -> None:
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be str"):
            ORCID(1234567890123456)  # type: ignore[arg-type]

    def test_publications_o_r_c_i_d__immutability__3de718d6(self) -> None:
        """Test Value Object is immutable."""
        orcid = ORCID("0000-0002-1825-0097")
        with pytest.raises(AttributeError, match="immutable"):
            orcid._value = "0000-0000-0000-0000"  # type: ignore[misc]

    def test_publications_o_r_c_i_d__equality_by_value__10f88c61(self) -> None:
        """Test equality is based on value, not identity."""
        orcid1 = ORCID("0000-0002-1825-0097")
        orcid2 = ORCID("0000000218250097")
        assert orcid1 == orcid2
        assert orcid1 is not orcid2

    def test_publications_o_r_c_i_d__equality_with_url__27a43c18(self) -> None:
        """Test equality between plain ID and URL format."""
        orcid1 = ORCID("0000-0002-1825-0097")
        orcid2 = ORCID("https://orcid.org/0000-0002-1825-0097")
        assert orcid1 == orcid2

    def test_publications_o_r_c_i_d__equality_with_x__4089e581(self) -> None:
        """Test equality with X check digit."""
        orcid1 = ORCID("0000-0001-5109-370X")
        orcid2 = ORCID("0000-0001-5109-370x")
        assert orcid1 == orcid2

    def test_publications_o_r_c_i_d__hash_consistency__22142f1e(self) -> None:
        """Test hash is consistent with equality."""
        orcid1 = ORCID("0000-0002-1825-0097")
        orcid2 = ORCID("0000000218250097")
        assert hash(orcid1) == hash(orcid2)

    def test_publications_o_r_c_i_d__can_be_used_in_set__b499ea84(self) -> None:
        """Test Value Object can be used in set."""
        orcid_ids = {
            ORCID("0000-0002-1825-0097"),
            ORCID("0000000218250097"),
            ORCID("0000-0001-5109-3700"),
        }
        assert len(orcid_ids) == 2

    def test_publications_o_r_c_i_d__be_used_as_dict_key__e0fe2abd(self) -> None:
        """Test Value Object can be used as dict key."""
        d = {ORCID("0000-0002-1825-0097"): "researcher"}
        assert d[ORCID("0000000218250097")] == "researcher"

    def test_publications_o_r_c_i_d__repr__e0a10f0c(self) -> None:
        """Test string representation."""
        orcid = ORCID("0000-0002-1825-0097")
        assert repr(orcid) == "ORCID('0000-0002-1825-0097')"

    def test_publications_o_r_c_i_d__str__b7c8bcf6(self) -> None:
        """Test string conversion."""
        orcid = ORCID("0000-0002-1825-0097")
        assert str(orcid) == "0000-0002-1825-0097"

    def test_publications_o_r_c_i_d__from_raw_valid__542dbb3b(self) -> None:
        """Test from_raw with valid ORCID."""
        orcid = ORCID.from_raw("0000-0002-1825-0097")
        assert orcid is not None
        assert orcid.value == "0000-0002-1825-0097"

    def test_publications_o_r_c_i_d__from_raw_url__e1085028(self) -> None:
        """Test from_raw with URL format."""
        orcid = ORCID.from_raw("https://orcid.org/0000-0002-1825-0097")
        assert orcid is not None
        assert orcid.value == "0000-0002-1825-0097"

    def test_publications_o_r_c_i_d__from_raw_compact__acc1347d(self) -> None:
        """Test from_raw with compact format."""
        orcid = ORCID.from_raw("0000000218250097")
        assert orcid is not None
        assert orcid.value == "0000-0002-1825-0097"

    def test_publications_o_r_c_i_d__from_raw_none__56289ae5(self) -> None:
        """Test from_raw with None."""
        assert ORCID.from_raw(None) is None

    def test_publications_o_r_c_i_d__from_raw_empty__57442cf7(self) -> None:
        """Test from_raw with empty string."""
        assert ORCID.from_raw("") is None
        assert ORCID.from_raw("   ") is None

    def test_publications_o_r_c_i_d__from_raw_invalid__4e194562(self) -> None:
        """Test from_raw with invalid value returns None."""
        assert ORCID.from_raw("invalid") is None
        assert ORCID.from_raw("0000-0002-1825") is None
