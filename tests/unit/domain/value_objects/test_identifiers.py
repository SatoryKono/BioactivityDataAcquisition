"""Tests for identifier Value Objects.

Tests for ChemblId, UniProtId, DOI, PubMedId, PubChemCid.
"""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects import (
    DOI,
    ChemblId,
    PubChemCid,
    PubMedId,
    UniProtId,
)


class TestChemblId:
    """Tests for ChemblId Value Object."""

    def test_valid_chembl_id(self) -> None:
        """Test creation with valid ChEMBL ID."""
        cid = ChemblId("CHEMBL25")
        assert cid.value == "CHEMBL25"
        assert cid.numeric_id == 25

    def test_large_chembl_id(self) -> None:
        """Test creation with large numeric ID."""
        cid = ChemblId("CHEMBL1234567")
        assert cid.value == "CHEMBL1234567"
        assert cid.numeric_id == 1234567

    def test_normalizes_case(self) -> None:
        """Test case normalization to uppercase."""
        cid = ChemblId("chembl123")
        assert cid.value == "CHEMBL123"

    def test_normalizes_mixed_case(self) -> None:
        """Test mixed case normalization."""
        cid = ChemblId("ChEmBl999")
        assert cid.value == "CHEMBL999"

    def test_strips_whitespace(self) -> None:
        """Test whitespace stripping."""
        cid = ChemblId("  CHEMBL100  ")
        assert cid.value == "CHEMBL100"

    def test_removes_leading_zeros(self) -> None:
        """Test leading zeros are normalized."""
        cid = ChemblId("CHEMBL0025")
        assert cid.value == "CHEMBL25"
        assert cid.numeric_id == 25

    def test_invalid_format_raises(self) -> None:
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ChEMBL ID format"):
            ChemblId("CH25")

    def test_empty_raises(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ChemblId("")

    def test_whitespace_only_raises(self) -> None:
        """Test whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ChemblId("   ")

    def test_zero_id_raises(self) -> None:
        """Test zero numeric ID raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            ChemblId("CHEMBL0")

    def test_negative_id_raises(self) -> None:
        """Test negative numeric ID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ChEMBL ID format"):
            ChemblId("CHEMBL-5")

    def test_non_string_raises(self) -> None:
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be str"):
            ChemblId(123)  # type: ignore[arg-type]

    def test_immutability(self) -> None:
        """Test Value Object is immutable."""
        cid = ChemblId("CHEMBL25")
        with pytest.raises(AttributeError, match="immutable"):
            cid._value = "CHEMBL999"  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        """Test equality is based on value, not identity."""
        cid1 = ChemblId("CHEMBL25")
        cid2 = ChemblId("chembl25")
        assert cid1 == cid2
        assert cid1 is not cid2

    def test_hash_consistency(self) -> None:
        """Test hash is consistent with equality."""
        cid1 = ChemblId("CHEMBL25")
        cid2 = ChemblId("chembl25")
        assert hash(cid1) == hash(cid2)

    def test_can_be_used_in_set(self) -> None:
        """Test Value Object can be used in set."""
        ids = {ChemblId("CHEMBL25"), ChemblId("CHEMBL25"), ChemblId("CHEMBL100")}
        assert len(ids) == 2

    def test_can_be_used_as_dict_key(self) -> None:
        """Test Value Object can be used as dict key."""
        d = {ChemblId("CHEMBL25"): "aspirin"}
        assert d[ChemblId("chembl25")] == "aspirin"

    def test_repr(self) -> None:
        """Test string representation."""
        cid = ChemblId("CHEMBL25")
        assert repr(cid) == "ChemblId('CHEMBL25')"

    def test_str(self) -> None:
        """Test string conversion."""
        cid = ChemblId("CHEMBL25")
        assert str(cid) == "CHEMBL25"

    def test_inequality_with_different_ids(self) -> None:
        """Test inequality for different IDs."""
        cid1 = ChemblId("CHEMBL25")
        cid2 = ChemblId("CHEMBL100")
        assert cid1 != cid2

    def test_inequality_with_different_types(self) -> None:
        """Test inequality with different types."""
        cid = ChemblId("CHEMBL25")
        assert cid != "CHEMBL25"
        assert cid != 25


class TestUniProtId:
    """Tests for UniProtId Value Object."""

    def test_valid_primary_accession(self) -> None:
        """Test creation with primary format (6 chars)."""
        uid = UniProtId("P12345")
        assert uid.value == "P12345"
        assert uid.is_primary_format is True

    def test_valid_secondary_accession(self) -> None:
        """Test creation with extended format (10 chars)."""
        uid = UniProtId("A0A1B2C3D4")
        assert uid.value == "A0A1B2C3D4"
        assert uid.is_primary_format is False

    def test_q_prefix_valid(self) -> None:
        """Test Q-prefixed accession (common in UniProt)."""
        uid = UniProtId("Q9Y6K9")
        assert uid.value == "Q9Y6K9"

    def test_o_prefix_valid(self) -> None:
        """Test O-prefixed accession."""
        uid = UniProtId("O15269")
        assert uid.value == "O15269"

    def test_normalizes_case(self) -> None:
        """Test case normalization."""
        uid = UniProtId("p12345")
        assert uid.value == "P12345"

    def test_strips_whitespace(self) -> None:
        """Test whitespace stripping."""
        uid = UniProtId("  P12345  ")
        assert uid.value == "P12345"

    def test_empty_raises(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            UniProtId("")

    def test_invalid_length_raises(self) -> None:
        """Test invalid length raises ValueError."""
        with pytest.raises(ValueError, match="Expected 6 or 10 characters"):
            UniProtId("P123")

    def test_invalid_format_raises(self) -> None:
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid UniProt accession format"):
            UniProtId("123456")

    def test_non_string_raises(self) -> None:
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be str"):
            UniProtId(12345)  # type: ignore[arg-type]

    def test_immutability(self) -> None:
        """Test Value Object is immutable."""
        uid = UniProtId("P12345")
        with pytest.raises(AttributeError, match="immutable"):
            uid._value = "Q99999"  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        """Test equality is based on value."""
        uid1 = UniProtId("P12345")
        uid2 = UniProtId("p12345")
        assert uid1 == uid2

    def test_hash_consistency(self) -> None:
        """Test hash is consistent with equality."""
        uid1 = UniProtId("P12345")
        uid2 = UniProtId("p12345")
        assert hash(uid1) == hash(uid2)


class TestDOI:
    """Tests for DOI Value Object."""

    def test_valid_doi(self) -> None:
        """Test creation with valid DOI."""
        doi = DOI("10.1038/nature12373")
        assert doi.value == "10.1038/nature12373"

    def test_complex_doi(self) -> None:
        """Test DOI with complex suffix."""
        doi = DOI("10.1000/xyz123.abc-def")
        assert doi.value == "10.1000/xyz123.abc-def"

    def test_long_registrant_code(self) -> None:
        """Test DOI with long registrant code."""
        doi = DOI("10.12345678/suffix")
        assert doi.value == "10.12345678/suffix"

    def test_strips_https_prefix(self) -> None:
        """Test HTTPS URL prefix is stripped."""
        doi = DOI("https://doi.org/10.1038/nature12373")
        assert doi.value == "10.1038/nature12373"

    def test_strips_http_prefix(self) -> None:
        """Test HTTP URL prefix is stripped."""
        doi = DOI("http://doi.org/10.1038/nature12373")
        assert doi.value == "10.1038/nature12373"

    def test_strips_doi_prefix(self) -> None:
        """Test doi: prefix is stripped."""
        doi = DOI("doi:10.1038/nature12373")
        assert doi.value == "10.1038/nature12373"

    def test_strips_doi_prefix_uppercase(self) -> None:
        """Test DOI: prefix is stripped."""
        doi = DOI("DOI:10.1038/nature12373")
        assert doi.value == "10.1038/nature12373"

    def test_normalizes_to_lowercase(self) -> None:
        """Test DOI is normalized to lowercase."""
        doi = DOI("10.1038/Nature12373")
        assert doi.value == "10.1038/nature12373"

    def test_url_property(self) -> None:
        """Test URL property returns full URL."""
        doi = DOI("10.1038/nature12373")
        assert doi.url == "https://doi.org/10.1038/nature12373"

    def test_registrant_code_property(self) -> None:
        """Test registrant_code property."""
        doi = DOI("10.1038/nature12373")
        assert doi.registrant_code == "1038"

    def test_empty_raises(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            DOI("")

    def test_invalid_format_raises(self) -> None:
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid DOI format"):
            DOI("not-a-doi")

    def test_missing_suffix_raises(self) -> None:
        """Test DOI without suffix raises ValueError."""
        with pytest.raises(ValueError, match="Invalid DOI format"):
            DOI("10.1038/")

    def test_short_registrant_raises(self) -> None:
        """Test too short registrant code raises ValueError."""
        with pytest.raises(ValueError, match="Invalid DOI format"):
            DOI("10.10/suffix")

    def test_non_string_raises(self) -> None:
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be str"):
            DOI(123)  # type: ignore[arg-type]

    def test_immutability(self) -> None:
        """Test Value Object is immutable."""
        doi = DOI("10.1038/nature12373")
        with pytest.raises(AttributeError, match="immutable"):
            doi._value = "10.9999/other"  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        """Test equality is based on value."""
        doi1 = DOI("10.1038/nature12373")
        doi2 = DOI("https://doi.org/10.1038/nature12373")
        assert doi1 == doi2

    def test_hash_consistency(self) -> None:
        """Test hash is consistent with equality."""
        doi1 = DOI("10.1038/nature12373")
        doi2 = DOI("DOI:10.1038/nature12373")
        assert hash(doi1) == hash(doi2)


class TestPubMedId:
    """Tests for PubMedId Value Object."""

    def test_valid_pmid(self) -> None:
        """Test creation with valid PMID."""
        pmid = PubMedId(12345)
        assert pmid.value == 12345

    def test_large_pmid(self) -> None:
        """Test creation with large PMID."""
        pmid = PubMedId(28891234)
        assert pmid.value == 28891234

    def test_string_conversion(self) -> None:
        """Test string input is converted to int."""
        pmid = PubMedId("12345")  # type: ignore[arg-type]
        assert pmid.value == 12345

    def test_string_with_whitespace(self) -> None:
        """Test string with whitespace is handled."""
        pmid = PubMedId("  12345  ")  # type: ignore[arg-type]
        assert pmid.value == 12345

    def test_zero_raises(self) -> None:
        """Test zero PMID raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            PubMedId(0)

    def test_negative_raises(self) -> None:
        """Test negative PMID raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            PubMedId(-1)

    def test_too_large_raises(self) -> None:
        """Test too large PMID raises ValueError."""
        with pytest.raises(ValueError, match="too large"):
            PubMedId(10_000_000_000)

    def test_bool_raises(self) -> None:
        """Test boolean input raises ValueError."""
        with pytest.raises(ValueError, match="must be int"):
            PubMedId(True)  # type: ignore[arg-type]

    def test_invalid_string_raises(self) -> None:
        """Test invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid PubMed ID"):
            PubMedId("not-a-number")  # type: ignore[arg-type]

    def test_float_raises(self) -> None:
        """Test float input raises ValueError."""
        with pytest.raises(ValueError, match="must be int"):
            PubMedId(12345.5)  # type: ignore[arg-type]

    def test_immutability(self) -> None:
        """Test Value Object is immutable."""
        pmid = PubMedId(12345)
        with pytest.raises(AttributeError, match="immutable"):
            pmid._value = 99999  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        """Test equality is based on value."""
        pmid1 = PubMedId(12345)
        pmid2 = PubMedId(12345)
        assert pmid1 == pmid2
        assert pmid1 is not pmid2

    def test_inequality(self) -> None:
        """Test inequality for different values."""
        pmid1 = PubMedId(12345)
        pmid2 = PubMedId(99999)
        assert pmid1 != pmid2

    def test_hash_consistency(self) -> None:
        """Test hash is consistent with equality."""
        pmid1 = PubMedId(12345)
        pmid2 = PubMedId(12345)
        assert hash(pmid1) == hash(pmid2)

    def test_str(self) -> None:
        """Test string conversion."""
        pmid = PubMedId(12345)
        assert str(pmid) == "12345"


class TestPubChemCid:
    """Tests for PubChemCid Value Object."""

    def test_valid_cid(self) -> None:
        """Test creation with valid CID."""
        cid = PubChemCid(2244)  # Aspirin
        assert cid.value == 2244

    def test_large_cid(self) -> None:
        """Test creation with large CID."""
        cid = PubChemCid(50_000_000_000)
        assert cid.value == 50_000_000_000

    def test_string_conversion(self) -> None:
        """Test string input is converted to int."""
        cid = PubChemCid("2244")  # type: ignore[arg-type]
        assert cid.value == 2244

    def test_zero_raises(self) -> None:
        """Test zero CID raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            PubChemCid(0)

    def test_negative_raises(self) -> None:
        """Test negative CID raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            PubChemCid(-1)

    def test_too_large_raises(self) -> None:
        """Test too large CID raises ValueError."""
        with pytest.raises(ValueError, match="too large"):
            PubChemCid(100_000_000_000)

    def test_bool_raises(self) -> None:
        """Test boolean input raises ValueError."""
        with pytest.raises(ValueError, match="must be int"):
            PubChemCid(True)  # type: ignore[arg-type]

    def test_immutability(self) -> None:
        """Test Value Object is immutable."""
        cid = PubChemCid(2244)
        with pytest.raises(AttributeError, match="immutable"):
            cid._value = 9999  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        """Test equality is based on value."""
        cid1 = PubChemCid(2244)
        cid2 = PubChemCid(2244)
        assert cid1 == cid2

    def test_hash_consistency(self) -> None:
        """Test hash is consistent with equality."""
        cid1 = PubChemCid(2244)
        cid2 = PubChemCid(2244)
        assert hash(cid1) == hash(cid2)

    def test_str(self) -> None:
        """Test string conversion."""
        cid = PubChemCid(2244)
        assert str(cid) == "2244"
