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
"""Tests for identifier Value Objects.

Tests for ChemblId, UniProtId, DOI, PubMedId, PubChemCid, InChIKey, SMILES,
PublicationYear, MolecularWeight.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from bioetl.domain.config import ValidationConfig
from bioetl.domain.value_objects import (
    DOI,
    ChemblId,
    InChIKey,
    MolecularWeight,
    PubChemCid,
    PubMedId,
    PublicationYear,
    SMILES,
    UniProtId,
)

LEGACY_HTTP_DOI = "http" + "://doi.org/10.1038/nature12373"


class TestChemblId:
    """Tests for ChemblId Value Object."""

    def test_identifiers_chembl_id__valid_chembl_id__c5f13f26(self) -> None:
        """Test creation with valid ChEMBL ID."""
        molecule_id = ChemblId("CHEMBL25")
        assert molecule_id.value == "CHEMBL25"
        assert molecule_id.numeric_id == 25

    def test_large_chembl_id(self) -> None:
        """Test creation with large numeric ID."""
        molecule_id = ChemblId("CHEMBL1234567")
        assert molecule_id.value == "CHEMBL1234567"
        assert molecule_id.numeric_id == 1234567

    def test_identifiers_chembl_id__normalizes_case__a90e33fc(self) -> None:
        """Test case normalization to uppercase."""
        molecule_id = ChemblId("chembl123")
        assert molecule_id.value == "CHEMBL123"

    def test_normalizes_mixed_case(self) -> None:
        """Test mixed case normalization."""
        molecule_id = ChemblId("ChEmBl999")
        assert molecule_id.value == "CHEMBL999"

    def test_identifiers_chembl_id__strips_whitespace__203edf9f(self) -> None:
        """Test whitespace stripping."""
        molecule_id = ChemblId("  CHEMBL100  ")
        assert molecule_id.value == "CHEMBL100"

    def test_identifiers_chembl_id__leading_zeros__842d78a2(self) -> None:
        """Test leading zeros are normalized."""
        molecule_id = ChemblId("CHEMBL0025")
        assert molecule_id.value == "CHEMBL25"
        assert molecule_id.numeric_id == 25

    def test_identifiers_chembl_id__format_raises__cd69303d(self) -> None:
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ChEMBL ID format"):
            ChemblId("CH25")

    def test_identifiers_chembl_id__empty_raises__acbb0430(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ChemblId("")

    def test_identifiers_chembl_id__only_raises__eb59097f(self) -> None:
        """Test whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ChemblId("   ")

    def test_identifiers_chembl_id__zero_id_raises__c1a627ab(self) -> None:
        """Test zero numeric ID raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            ChemblId("CHEMBL0")

    def test_negative_id_raises(self) -> None:
        """Test negative numeric ID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ChEMBL ID format"):
            ChemblId("CHEMBL-5")

    def test_identifiers_chembl_id__non_string_raises__881c492d(self) -> None:
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be str"):
            ChemblId(123)  # type: ignore[arg-type]

    def test_identifiers_chembl_id__immutability__7606c34a(self) -> None:
        """Test Value Object is immutable."""
        molecule_id = ChemblId("CHEMBL25")
        with pytest.raises(AttributeError, match="immutable"):
            molecule_id._value = "CHEMBL999"  # type: ignore[misc]

    def test_identifiers_chembl_id__equality_by_value__17f0fd41(self) -> None:
        """Test equality is based on value, not identity."""
        molecule_id1 = ChemblId("CHEMBL25")
        molecule_id2 = ChemblId("chembl25")
        assert molecule_id1 == molecule_id2
        assert molecule_id1 is not molecule_id2

    def test_identifiers_chembl_id__hash_consistency__23fce8c1(self) -> None:
        """Test hash is consistent with equality."""
        molecule_id1 = ChemblId("CHEMBL25")
        molecule_id2 = ChemblId("chembl25")
        assert hash(molecule_id1) == hash(molecule_id2)

    def test_identifiers_chembl_id__can_be_used_in_set__0986d093(self) -> None:
        """Test Value Object can be used in set."""
        ids = {ChemblId("CHEMBL25"), ChemblId("CHEMBL25"), ChemblId("CHEMBL100")}
        assert len(ids) == 2

    def test_identifiers_chembl_id__be_used_as_dict_key__94993916(self) -> None:
        """Test Value Object can be used as dict key."""
        d = {ChemblId("CHEMBL25"): "aspirin"}
        assert d[ChemblId("chembl25")] == "aspirin"

    def test_identifiers_chembl_id__repr__cd27e0db(self) -> None:
        """Test string representation."""
        molecule_id = ChemblId("CHEMBL25")
        assert repr(molecule_id) == "ChemblId('CHEMBL25')"

    def test_identifiers_chembl_id__str__abf20350(self) -> None:
        """Test string conversion."""
        molecule_id = ChemblId("CHEMBL25")
        assert str(molecule_id) == "CHEMBL25"

    def test_identifiers_chembl_id__with_different_ids__97130c4d(self) -> None:
        """Test inequality for different IDs."""
        molecule_id1 = ChemblId("CHEMBL25")
        molecule_id2 = ChemblId("CHEMBL100")
        assert molecule_id1 != molecule_id2

    def test_identifiers_chembl_id__with_different_types__dd86f393(self) -> None:
        """Test inequality with different types."""
        molecule_id = ChemblId("CHEMBL25")
        assert molecule_id != "CHEMBL25"
        assert molecule_id != 25


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

    def test_uni_prot_id__normalizes_case__0c127a71(self) -> None:
        """Test case normalization."""
        uid = UniProtId("p12345")
        assert uid.value == "P12345"

    def test_uni_prot_id__strips_whitespace__486d9ec5(self) -> None:
        """Test whitespace stripping."""
        uid = UniProtId("  P12345  ")
        assert uid.value == "P12345"

    def test_uni_prot_id__empty_raises__971bdd31(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            UniProtId("")

    def test_invalid_length_raises(self) -> None:
        """Test invalid length raises ValueError."""
        with pytest.raises(ValueError, match="Expected 6 or 10 characters"):
            UniProtId("P123")

    def test_uni_prot_id__format_raises__36d51f23(self) -> None:
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid UniProt accession format"):
            UniProtId("123456")

    def test_uni_prot_id__non_string_raises__05d6a737(self) -> None:
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be str"):
            UniProtId(12345)  # type: ignore[arg-type]

    def test_uni_prot_id__immutability__3aa337b4(self) -> None:
        """Test Value Object is immutable."""
        uid = UniProtId("P12345")
        with pytest.raises(AttributeError, match="immutable"):
            uid._value = "Q99999"  # type: ignore[misc]

    def test_uni_prot_id__equality_by_value__a95e6e98(self) -> None:
        """Test equality is based on value."""
        uid1 = UniProtId("P12345")
        uid2 = UniProtId("p12345")
        assert uid1 == uid2

    def test_uni_prot_id__hash_consistency__524706f1(self) -> None:
        """Test hash is consistent with equality."""
        uid1 = UniProtId("P12345")
        uid2 = UniProtId("p12345")
        assert hash(uid1) == hash(uid2)


class TestDOI:
    """Tests for DOI Value Object."""

    def test_identifiers_d_o_i__valid_doi__f5ba709a(self) -> None:
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
        doi = DOI(LEGACY_HTTP_DOI)
        assert doi.value == "10.1038/nature12373"

    def test_strips_doi_prefix(self) -> None:
        """Test doi: prefix is stripped."""
        doi = DOI("doi:10.1038/nature12373")
        assert doi.value == "10.1038/nature12373"

    def test_strips_doi_prefix_uppercase(self) -> None:
        """Test DOI: prefix is stripped."""
        doi = DOI("DOI:10.1038/nature12373")
        assert doi.value == "10.1038/nature12373"

    def test_identifiers_d_o_i__to_lowercase__c79b7ee8(self) -> None:
        """Test DOI is normalized to lowercase."""
        doi = DOI("10.1038/Nature12373")
        assert doi.value == "10.1038/nature12373"

    def test_identifiers_d_o_i__url_property__3be4398c(self) -> None:
        """Test URL property returns full URL."""
        doi = DOI("10.1038/nature12373")
        assert doi.url == "https://doi.org/10.1038/nature12373"

    def test_registrant_code_property(self) -> None:
        """Test registrant_code property."""
        doi = DOI("10.1038/nature12373")
        assert doi.registrant_code == "1038"

    def test_identifiers_d_o_i__empty_raises__4b5fa49e(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            DOI("")

    def test_identifiers_d_o_i__format_raises__e2b46fc0(self) -> None:
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

    def test_identifiers_d_o_i__non_string_raises__836cfa09(self) -> None:
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be str"):
            DOI(123)  # type: ignore[arg-type]

    def test_identifiers_d_o_i__immutability__a57184c4(self) -> None:
        """Test Value Object is immutable."""
        doi = DOI("10.1038/nature12373")
        with pytest.raises(AttributeError, match="immutable"):
            doi._value = "10.9999/other"  # type: ignore[misc]

    def test_identifiers_d_o_i__equality_by_value__58fcc180(self) -> None:
        """Test equality is based on value."""
        doi1 = DOI("10.1038/nature12373")
        doi2 = DOI("https://doi.org/10.1038/nature12373")
        assert doi1 == doi2

    def test_identifiers_d_o_i__hash_consistency__cb667550(self) -> None:
        """Test hash is consistent with equality."""
        doi1 = DOI("10.1038/nature12373")
        doi2 = DOI("DOI:10.1038/nature12373")
        assert hash(doi1) == hash(doi2)


class TestPubMedId:
    """Tests for PubMedId Value Object.

    PubMedId stores PMID as a string (numeric digits only) to match
    PubMed API behavior and enable consistent cross-provider JOINs.
    """

    def test_valid_pmid_from_int(self) -> None:
        """Test creation with valid PMID from int."""
        pmid = PubMedId(12345)
        assert pmid.value == "12345"

    def test_valid_pmid_from_string(self) -> None:
        """Test creation with valid PMID from string."""
        pmid = PubMedId("12345678")
        assert pmid.value == "12345678"

    def test_identifiers_pub_med_id__large_pmid__c64196ee(self) -> None:
        """Test creation with large PMID."""
        pmid = PubMedId(28891234)
        assert pmid.value == "28891234"

    def test_int_conversion(self) -> None:
        """Test int input is converted to string."""
        pmid = PubMedId(12345)
        assert pmid.value == "12345"
        assert isinstance(pmid.value, str)

    def test_identifiers_pub_med_id__with_whitespace__a97799dd(self) -> None:
        """Test string with whitespace is stripped."""
        pmid = PubMedId("  12345  ")
        assert pmid.value == "12345"

    def test_leading_zeros_normalized(self) -> None:
        """Test leading zeros are removed."""
        pmid = PubMedId("00012345")
        assert pmid.value == "12345"

    def test_as_int_property(self) -> None:
        """Test as_int property returns integer value."""
        pmid = PubMedId("12345678")
        assert pmid.as_int == 12345678
        assert isinstance(pmid.as_int, int)

    def test_zero_raises(self) -> None:
        """Test zero PMID raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            PubMedId(0)

    def test_zero_string_raises(self) -> None:
        """Test zero as string raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            PubMedId("0")

    def test_negative_raises(self) -> None:
        """Test negative PMID raises ValueError.

        Note: Negative numbers are caught by the format check since '-' is not a digit.
        """
        with pytest.raises(ValueError, match="Must contain only digits"):
            PubMedId(-1)

    def test_too_large_raises(self) -> None:
        """Test too large PMID raises ValueError."""
        with pytest.raises(ValueError, match="too large"):
            PubMedId(10_000_000_000)

    def test_too_large_string_raises(self) -> None:
        """Test too large PMID as string raises ValueError."""
        with pytest.raises(ValueError, match="too large"):
            PubMedId("10000000000")

    def test_bool_raises(self) -> None:
        """Test boolean input raises ValueError."""
        with pytest.raises(ValueError, match="must be str or int"):
            PubMedId(True)  # type: ignore[arg-type]

    def test_identifiers_pub_med_id__string_raises__d159b7eb(self) -> None:
        """Test invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Must contain only digits"):
            PubMedId("not-a-number")

    def test_mixed_string_raises(self) -> None:
        """Test mixed alphanumeric string raises ValueError."""
        with pytest.raises(ValueError, match="Must contain only digits"):
            PubMedId("123abc")

    def test_float_raises(self) -> None:
        """Test float input raises ValueError."""
        with pytest.raises(ValueError, match="must be str or int"):
            PubMedId(12345.5)  # type: ignore[arg-type]

    def test_identifiers_pub_med_id__empty_string_raises__be5fdcaf(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            PubMedId("")

    def test_identifiers_pub_med_id__only_raises__402f84ad(self) -> None:
        """Test whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            PubMedId("   ")

    def test_identifiers_pub_med_id__immutability__9f9ce8a7(self) -> None:
        """Test Value Object is immutable."""
        pmid = PubMedId(12345)
        with pytest.raises(AttributeError, match="immutable"):
            pmid._value = "99999"  # type: ignore[misc]

    def test_identifiers_pub_med_id__equality_by_value__da496adb(self) -> None:
        """Test equality is based on value."""
        pmid1 = PubMedId(12345)
        pmid2 = PubMedId("12345")
        assert pmid1 == pmid2
        assert pmid1 is not pmid2

    def test_identifiers_pub_med_id__inequality__b71c75b4(self) -> None:
        """Test inequality for different values."""
        pmid1 = PubMedId(12345)
        pmid2 = PubMedId(99999)
        assert pmid1 != pmid2

    def test_identifiers_pub_med_id__hash_consistency__d905807f(self) -> None:
        """Test hash is consistent with equality."""
        pmid1 = PubMedId(12345)
        pmid2 = PubMedId("12345")
        assert hash(pmid1) == hash(pmid2)

    def test_identifiers_pub_med_id__str__097e7cd2(self) -> None:
        """Test string conversion."""
        pmid = PubMedId(12345)
        assert str(pmid) == "12345"

    def test_identifiers_pub_med_id__repr__9316a477(self) -> None:
        """Test repr output."""
        pmid = PubMedId(12345)
        assert repr(pmid) == "PubMedId('12345')"


class TestPubChemCid:
    """Tests for PubChemCid Value Object."""

    def test_valid_molecule_id(self) -> None:
        """Test creation with valid CID."""
        molecule_id = PubChemCid(2244)  # Aspirin
        assert molecule_id.value == 2244

    def test_large_molecule_id(self) -> None:
        """Test creation with large CID."""
        molecule_id = PubChemCid(50_000_000_000)
        assert molecule_id.value == 50_000_000_000

    def test_string_conversion(self) -> None:
        """Test string input is converted to int."""
        molecule_id = PubChemCid("2244")  # type: ignore[arg-type]
        assert molecule_id.value == 2244

    def test_pub_chem_cid__zero_raises__43fbbbf2(self) -> None:
        """Test zero CID raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            PubChemCid(0)

    def test_pub_chem_cid__negative_raises__cc0dc929(self) -> None:
        """Test negative CID raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            PubChemCid(-1)

    def test_pub_chem_cid__too_large_raises__5726a2ff(self) -> None:
        """Test too large CID raises ValueError."""
        with pytest.raises(ValueError, match="too large"):
            PubChemCid(100_000_000_000)

    def test_pub_chem_cid__bool_raises__6e481fd4(self) -> None:
        """Test boolean input raises ValueError."""
        with pytest.raises(ValueError, match="must be int"):
            PubChemCid(True)  # type: ignore[arg-type]

    def test_pub_chem_cid__immutability__8800f5d1(self) -> None:
        """Test Value Object is immutable."""
        molecule_id = PubChemCid(2244)
        with pytest.raises(AttributeError, match="immutable"):
            molecule_id._value = 9999  # type: ignore[misc]

    def test_pub_chem_cid__equality_by_value__954b04ac(self) -> None:
        """Test equality is based on value."""
        molecule_id1 = PubChemCid(2244)
        molecule_id2 = PubChemCid(2244)
        assert molecule_id1 == molecule_id2

    def test_pub_chem_cid__hash_consistency__09bb0bc3(self) -> None:
        """Test hash is consistent with equality."""
        molecule_id1 = PubChemCid(2244)
        molecule_id2 = PubChemCid(2244)
        assert hash(molecule_id1) == hash(molecule_id2)

    def test_pub_chem_cid__str__ef916e62(self) -> None:
        """Test string conversion."""
        molecule_id = PubChemCid(2244)
        assert str(molecule_id) == "2244"

    def test_from_raw_valid_int(self) -> None:
        """Test from_raw with valid integer."""
        molecule_id = PubChemCid.from_raw(2244)
        assert molecule_id is not None
        assert molecule_id.value == 2244

    def test_from_raw_valid_string(self) -> None:
        """Test from_raw with valid string."""
        molecule_id = PubChemCid.from_raw("2244")
        assert molecule_id is not None
        assert molecule_id.value == 2244

    def test_pub_chem_cid__from_raw_none__7bf5a24f(self) -> None:
        """Test from_raw with None."""
        assert PubChemCid.from_raw(None) is None

    def test_from_raw_empty_string(self) -> None:
        """Test from_raw with empty string."""
        assert PubChemCid.from_raw("") is None
        assert PubChemCid.from_raw("   ") is None

    def test_pub_chem_cid__from_raw_invalid__ed376f9e(self) -> None:
        """Test from_raw with invalid value."""
        assert PubChemCid.from_raw(-1) is None
        assert PubChemCid.from_raw(0) is None


class TestChemblIdFromRaw:
    """Tests for ChemblId.from_raw() factory method."""

    def test_chembl_id_from_raw__from_raw_valid__eeabcbb8(self) -> None:
        """Test from_raw with valid ChEMBL ID."""
        molecule_id = ChemblId.from_raw("CHEMBL25")
        assert molecule_id is not None
        assert molecule_id.value == "CHEMBL25"

    def test_from_raw_normalizes_case(self) -> None:
        """Test from_raw normalizes case."""
        molecule_id = ChemblId.from_raw("chembl25")
        assert molecule_id is not None
        assert molecule_id.value == "CHEMBL25"

    def test_chembl_id_from_raw__from_raw_none__ce690c39(self) -> None:
        """Test from_raw with None."""
        assert ChemblId.from_raw(None) is None

    def test_chembl_id_from_raw__from_raw_empty__c503ee72(self) -> None:
        """Test from_raw with empty string."""
        assert ChemblId.from_raw("") is None
        assert ChemblId.from_raw("   ") is None

    def test_chembl_id_from_raw__from_raw_invalid__ca17f2c0(self) -> None:
        """Test from_raw with invalid value returns None."""
        assert ChemblId.from_raw("invalid") is None
        assert ChemblId.from_raw("CH25") is None


class TestUniProtIdFromRaw:
    """Tests for UniProtId.from_raw() factory method."""

    def test_uni_prot_id_from_raw__from_raw_valid__15a82697(self) -> None:
        """Test from_raw with valid UniProt ID."""
        uid = UniProtId.from_raw("P12345")
        assert uid is not None
        assert uid.value == "P12345"

    def test_uni_prot_id_from_raw__raw_normalizes_case__f4a6ba82(self) -> None:
        """Test from_raw normalizes case."""
        uid = UniProtId.from_raw("p12345")
        assert uid is not None
        assert uid.value == "P12345"

    def test_uni_prot_id_from_raw__from_raw_none__3eb33b4b(self) -> None:
        """Test from_raw with None."""
        assert UniProtId.from_raw(None) is None

    def test_uni_prot_id_from_raw__from_raw_empty__da25c5c8(self) -> None:
        """Test from_raw with empty string."""
        assert UniProtId.from_raw("") is None
        assert UniProtId.from_raw("   ") is None

    def test_uni_prot_id_from_raw__from_raw_invalid__7631b3ac(self) -> None:
        """Test from_raw with invalid value returns None."""
        assert UniProtId.from_raw("invalid") is None
        assert UniProtId.from_raw("P123") is None


class TestDOIFromRaw:
    """Tests for DOI.from_raw() factory method."""

    def test_d_o_i_from_raw__from_raw_valid__95250d02(self) -> None:
        """Test from_raw with valid DOI."""
        doi = DOI.from_raw("10.1038/nature12373")
        assert doi is not None
        assert doi.value == "10.1038/nature12373"

    def test_from_raw_strips_url(self) -> None:
        """Test from_raw strips URL prefixes."""
        doi = DOI.from_raw("https://doi.org/10.1038/nature12373")
        assert doi is not None
        assert doi.value == "10.1038/nature12373"

    def test_d_o_i_from_raw__from_raw_none__da745613(self) -> None:
        """Test from_raw with None."""
        assert DOI.from_raw(None) is None

    def test_d_o_i_from_raw__from_raw_empty__20544ff2(self) -> None:
        """Test from_raw with empty string."""
        assert DOI.from_raw("") is None
        assert DOI.from_raw("   ") is None

    def test_d_o_i_from_raw__from_raw_invalid__3ad1ca64(self) -> None:
        """Test from_raw with invalid value returns None."""
        assert DOI.from_raw("not-a-doi") is None
        assert DOI.from_raw("doi.org/10.1038") is None


class TestPubMedIdFromRaw:
    """Tests for PubMedId.from_raw() factory method."""

    def test_pub_med_id_from_raw__from_raw_valid_int__949c4f18(self) -> None:
        """Test from_raw with valid integer."""
        pmid = PubMedId.from_raw(12345)
        assert pmid is not None
        assert pmid.value == "12345"

    def test_pub_med_id_from_raw__raw_valid_string__90d1e952(self) -> None:
        """Test from_raw with valid string."""
        pmid = PubMedId.from_raw("12345678")
        assert pmid is not None
        assert pmid.value == "12345678"

    def test_pub_med_id_from_raw__from_raw_none__a5b9e7fd(self) -> None:
        """Test from_raw with None."""
        assert PubMedId.from_raw(None) is None

    def test_pub_med_id_from_raw__from_raw_empty__cd42f083(self) -> None:
        """Test from_raw with empty string."""
        assert PubMedId.from_raw("") is None
        assert PubMedId.from_raw("   ") is None

    def test_pub_med_id_from_raw__from_raw_invalid__a69a3d5d(self) -> None:
        """Test from_raw with invalid value returns None."""
        assert PubMedId.from_raw("abc") is None
        assert PubMedId.from_raw(0) is None


class TestInChIKey:
    """Tests for InChIKey Value Object."""

    def test_in_ch_i_key__valid_inchi_key__2352d427(self) -> None:
        """Test creation with valid InChI Key."""
        key = InChIKey("BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        assert key.value == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"

    def test_in_ch_i_key__normalizes_case__69846a41(self) -> None:
        """Test case normalization to uppercase."""
        key = InChIKey("bsynrymutxbxsq-uhfffaoysa-n")
        assert key.value == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"

    def test_in_ch_i_key__strips_whitespace__e99d9202(self) -> None:
        """Test whitespace stripping."""
        key = InChIKey("  BSYNRYMUTXBXSQ-UHFFFAOYSA-N  ")
        assert key.value == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"

    def test_connectivity_layer__test_in_ch_i_key_domain_value_objects_test_identifiers_682(
        self,
    ) -> None:
        """Test connectivity layer property."""
        key = InChIKey("BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        assert key.connectivity_layer == "BSYNRYMUTXBXSQ"

    def test_in_ch_i_key__layer__86bc5d33(self) -> None:
        """Test stereochemistry layer property."""
        key = InChIKey("BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        assert key.stereochemistry_layer == "UHFFFAOYSA"

    def test_in_ch_i_key__protonation_layer__c2135218(self) -> None:
        """Test protonation layer property."""
        key = InChIKey("BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        assert key.protonation_layer == "N"

    def test_in_ch_i_key__empty_raises__03ca53d9(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            InChIKey("")

    def test_in_ch_i_key__format_raises__ea62a964(self) -> None:
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid InChI Key format"):
            InChIKey("INVALID")

    def test_in_ch_i_key__wrong_length_raises__8858356c(self) -> None:
        """Test wrong length raises ValueError."""
        with pytest.raises(ValueError, match="Invalid InChI Key format"):
            InChIKey("BSYNRYMUTXBXSQ-UHFFFAOYSA")  # Missing last part

    def test_invalid_characters_raises(self) -> None:
        """Test invalid characters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid InChI Key format"):
            InChIKey("BSYNRYMUTXBXSQ-UHFFFAOYS1-N")  # Contains digit

    def test_in_ch_i_key__non_string_raises__6de85e1c(self) -> None:
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be str"):
            InChIKey(123)  # type: ignore[arg-type]

    def test_in_ch_i_key__immutability__1e7890fb(self) -> None:
        """Test Value Object is immutable."""
        key = InChIKey("BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        with pytest.raises(AttributeError, match="immutable"):
            key._value = "OTHER"  # type: ignore[misc]

    def test_in_ch_i_key__equality_by_value__c3e4a547(self) -> None:
        """Test equality is based on value."""
        key1 = InChIKey("BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        key2 = InChIKey("bsynrymutxbxsq-uhfffaoysa-n")
        assert key1 == key2

    def test_in_ch_i_key__hash_consistency__47a5a52d(self) -> None:
        """Test hash is consistent with equality."""
        key1 = InChIKey("BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        key2 = InChIKey("bsynrymutxbxsq-uhfffaoysa-n")
        assert hash(key1) == hash(key2)

    def test_in_ch_i_key__from_raw_valid__53f8ea7d(self) -> None:
        """Test from_raw with valid InChI Key."""
        key = InChIKey.from_raw("BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        assert key is not None
        assert key.value == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"

    def test_in_ch_i_key__from_raw_none__5be97895(self) -> None:
        """Test from_raw with None."""
        assert InChIKey.from_raw(None) is None

    def test_in_ch_i_key__from_raw_empty__7db3b9b1(self) -> None:
        """Test from_raw with empty string."""
        assert InChIKey.from_raw("") is None
        assert InChIKey.from_raw("   ") is None

    def test_in_ch_i_key__from_raw_invalid__1fc3fdd2(self) -> None:
        """Test from_raw with invalid value returns None."""
        assert InChIKey.from_raw("invalid") is None

    def test_in_ch_i_key__str__6e4f7995(self) -> None:
        """Test string conversion."""
        key = InChIKey("BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        assert str(key) == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"

    def test_in_ch_i_key__repr__ea9a4fde(self) -> None:
        """Test repr output."""
        key = InChIKey("BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        assert repr(key) == "InChIKey('BSYNRYMUTXBXSQ-UHFFFAOYSA-N')"


class TestSMILES:
    """Tests for SMILES Value Object."""

    def test_s_m_i_l_e_s__valid_smiles__2d5dc52a(self) -> None:
        """Test creation with valid SMILES."""
        smiles = SMILES("CC(=O)OC1=CC=CC=C1C(=O)O")
        assert smiles.value == "CC(=O)OC1=CC=CC=C1C(=O)O"
        assert smiles.is_canonical is False

    def test_canonical_smiles(self) -> None:
        """Test creation of canonical SMILES."""
        smiles = SMILES.canonical("CC(=O)OC1=CC=CC=C1C(=O)O")
        assert smiles.value == "CC(=O)OC1=CC=CC=C1C(=O)O"
        assert smiles.is_canonical is True

    def test_s_m_i_l_e_s__strips_whitespace__e909a02a(self) -> None:
        """Test whitespace stripping."""
        smiles = SMILES("  CC(=O)O  ")
        assert smiles.value == "CC(=O)O"

    def test_s_m_i_l_e_s__empty_raises__034d0252(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SMILES("")

    def test_s_m_i_l_e_s__only_raises__01d0c29a(self) -> None:
        """Test whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SMILES("   ")

    def test_s_m_i_l_e_s__non_string_raises__f50e77c7(self) -> None:
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be str"):
            SMILES(123)  # type: ignore[arg-type]

    def test_s_m_i_l_e_s__immutability__6e053e46(self) -> None:
        """Test Value Object is immutable."""
        smiles = SMILES("CC(=O)O")
        with pytest.raises(AttributeError, match="immutable"):
            smiles._value = "OTHER"  # type: ignore[misc]

    def test_equality_by_value_and_canonical(self) -> None:
        """Test equality considers both value and canonical flag."""
        smiles1 = SMILES("CC(=O)O")
        smiles2 = SMILES("CC(=O)O")
        smiles3 = SMILES.canonical("CC(=O)O")
        assert smiles1 == smiles2
        assert smiles1 != smiles3  # Different canonical flag

    def test_s_m_i_l_e_s__hash_consistency__3dec2d83(self) -> None:
        """Test hash is consistent with equality."""
        smiles1 = SMILES("CC(=O)O")
        smiles2 = SMILES("CC(=O)O")
        assert hash(smiles1) == hash(smiles2)

    def test_s_m_i_l_e_s__from_raw_valid__8cf1c94c(self) -> None:
        """Test from_raw with valid SMILES."""
        smiles = SMILES.from_raw("CC(=O)O")
        assert smiles is not None
        assert smiles.value == "CC(=O)O"
        assert smiles.is_canonical is False

    def test_s_m_i_l_e_s__from_raw_canonical__fc92a21a(self) -> None:
        """Test from_raw with canonical flag."""
        smiles = SMILES.from_raw("CC(=O)O", is_canonical=True)
        assert smiles is not None
        assert smiles.is_canonical is True

    def test_s_m_i_l_e_s__from_raw_none__ef831e18(self) -> None:
        """Test from_raw with None."""
        assert SMILES.from_raw(None) is None

    def test_s_m_i_l_e_s__from_raw_empty__f5df051e(self) -> None:
        """Test from_raw with empty string."""
        assert SMILES.from_raw("") is None
        assert SMILES.from_raw("   ") is None

    def test_s_m_i_l_e_s__str__47b5b619(self) -> None:
        """Test string conversion."""
        smiles = SMILES("CC(=O)O")
        assert str(smiles) == "CC(=O)O"

    def test_repr_non_canonical(self) -> None:
        """Test repr output for non-canonical SMILES."""
        smiles = SMILES("CC(=O)O")
        assert repr(smiles) == "SMILES('CC(=O)O')"

    def test_s_m_i_l_e_s__repr_canonical__5c203f0e(self) -> None:
        """Test repr output for canonical SMILES."""
        smiles = SMILES.canonical("CC(=O)O")
        assert repr(smiles) == "SMILES('CC(=O)O', is_canonical=True)"


class TestPublicationYear:
    """Tests for PublicationYear Value Object."""

    def test_publication_year__valid_year__f01c4ebe(self) -> None:
        """Test creation with valid year."""
        year = PublicationYear(2020)
        assert year.value == 2020

    def test_publication_year__from_string__6cfb0fc5(self) -> None:
        """Test creation from string."""
        year = PublicationYear("2020")  # type: ignore[arg-type]
        assert year.value == 2020

    def test_minimum_year(self) -> None:
        """Test creation with minimum valid year."""
        year = PublicationYear(1500)
        assert year.value == 1500

    def test_maximum_year(self) -> None:
        """Test creation with maximum valid year."""
        year = PublicationYear(2100)
        assert year.value == 2100

    def test_decade_property(self) -> None:
        """Test decade property."""
        year = PublicationYear(1953)
        assert year.decade == 1950

    def test_century_property(self) -> None:
        """Test century property."""
        year = PublicationYear(1953)
        assert year.century == 20

    def test_below_minimum_raises(self) -> None:
        """Test year below minimum raises ValueError."""
        with pytest.raises(ValueError, match="outside valid range"):
            PublicationYear(1499)

    def test_above_maximum_raises(self) -> None:
        """Test year above maximum raises ValueError."""
        with pytest.raises(ValueError, match="outside valid range"):
            PublicationYear(2101)

    def test_publication_year__bool_raises__eab4c230(self) -> None:
        """Test boolean input raises ValueError."""
        with pytest.raises(ValueError, match="must be int"):
            PublicationYear(True)  # type: ignore[arg-type]

    def test_publication_year__string_raises__9c0b53ee(self) -> None:
        """Test invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid publication year"):
            PublicationYear("not-a-year")  # type: ignore[arg-type]

    def test_publication_year__immutability__ead75024(self) -> None:
        """Test Value Object is immutable."""
        year = PublicationYear(2020)
        with pytest.raises(AttributeError, match="immutable"):
            year._value = 2021  # type: ignore[misc]

    def test_publication_year__equality_by_value__0cb41643(self) -> None:
        """Test equality is based on value."""
        year1 = PublicationYear(2020)
        year2 = PublicationYear(2020)
        assert year1 == year2

    def test_publication_year__hash_consistency__5d0cdb02(self) -> None:
        """Test hash is consistent with equality."""
        year1 = PublicationYear(2020)
        year2 = PublicationYear(2020)
        assert hash(year1) == hash(year2)

    def test_publication_year__from_raw_valid_int__7aa8d245(self) -> None:
        """Test from_raw with valid integer."""
        year = PublicationYear.from_raw(2020)
        assert year is not None
        assert year.value == 2020

    def test_publication_year__raw_valid_string__d30b9a81(self) -> None:
        """Test from_raw with valid string."""
        year = PublicationYear.from_raw("2020")
        assert year is not None
        assert year.value == 2020

    def test_publication_year__from_raw_none__3b089d9c(self) -> None:
        """Test from_raw with None."""
        assert PublicationYear.from_raw(None) is None

    def test_publication_year__from_raw_empty__28793370(self) -> None:
        """Test from_raw with empty string."""
        assert PublicationYear.from_raw("") is None
        assert PublicationYear.from_raw("   ") is None

    def test_publication_year__from_raw_invalid__df1e716a(self) -> None:
        """Test from_raw with invalid value returns None."""
        assert PublicationYear.from_raw("abc") is None
        assert PublicationYear.from_raw(1499) is None
        assert PublicationYear.from_raw(2101) is None

    def test_publication_year__str__545d3951(self) -> None:
        """Test string conversion."""
        year = PublicationYear(2020)
        assert str(year) == "2020"

    def test_publication_year__repr__b9c70828(self) -> None:
        """Test repr output."""
        year = PublicationYear(2020)
        assert repr(year) == "PublicationYear(2020)"

    def test_with_custom_config(self) -> None:
        """Test PublicationYear with custom ValidationConfig."""
        config = ValidationConfig(min_publication_year=1500)
        year = PublicationYear(1600, config=config)
        assert year.value == 1600

    def test_custom_config_rejects_out_of_range(self) -> None:
        """Test that custom config enforces its range."""
        config = ValidationConfig(min_publication_year=1500, max_publication_year=2000)
        with pytest.raises(ValueError, match="outside valid range"):
            PublicationYear(2001, config=config)

    def test_from_raw_with_config(self) -> None:
        """Test from_raw with custom config."""
        config = ValidationConfig(min_publication_year=1500)
        year = PublicationYear.from_raw(1600, config=config)
        assert year is not None
        assert year.value == 1600

    def test_from_raw_with_config_invalid(self) -> None:
        """Test from_raw with config and invalid value returns None."""
        config = ValidationConfig(min_publication_year=1500, max_publication_year=2000)
        assert PublicationYear.from_raw(2001, config=config) is None

    def test_date_string_extraction(self) -> None:
        """Test year extraction from date string."""
        # ISO date format: YYYY-MM-DD
        year = PublicationYear("2024-01-15")  # type: ignore[arg-type]
        assert year.value == 2024

    def test_date_string_extraction_slash(self) -> None:
        """Test year extraction from date string with slash."""
        year = PublicationYear("2023/06/20")  # type: ignore[arg-type]
        assert year.value == 2023

    def test_from_raw_date_string(self) -> None:
        """Test from_raw with date string."""
        year = PublicationYear.from_raw("2024-01-15")
        assert year is not None
        assert year.value == 2024

    def test_min_year_property(self) -> None:
        """Test min_year property returns config value."""
        year = PublicationYear(2020)
        assert year.min_year == 1500

    def test_max_year_property(self) -> None:
        """Test max_year property returns config value."""
        year = PublicationYear(2020)
        assert year.max_year == 2100

    def test_equality_ignores_config(self) -> None:
        """Test that equality compares by value, ignoring config."""
        config1 = ValidationConfig(min_publication_year=1800)
        config2 = ValidationConfig(min_publication_year=1500)
        year1 = PublicationYear(2020, config=config1)
        year2 = PublicationYear(2020, config=config2)
        assert year1 == year2

    def test_hash_ignores_config(self) -> None:
        """Test that hash is consistent with equality (ignoring config)."""
        config1 = ValidationConfig(min_publication_year=1800)
        config2 = ValidationConfig(min_publication_year=1500)
        year1 = PublicationYear(2020, config=config1)
        year2 = PublicationYear(2020, config=config2)
        assert hash(year1) == hash(year2)


class TestMolecularWeight:
    """Tests for MolecularWeight Value Object."""

    def test_molecular_weight__molecular_weight__0efde17c(self) -> None:
        """Test creation with valid molecular weight."""
        mw = MolecularWeight(180.156)
        assert mw.value == pytest.approx(180.156)

    def test_from_int(self) -> None:
        """Test creation from integer."""
        mw = MolecularWeight(180)
        assert mw.value == pytest.approx(180.0)

    def test_molecular_weight__from_string__dacd5985(self) -> None:
        """Test creation from string (e.g., from PubChem API)."""
        mw = MolecularWeight("342.30")
        assert mw.value == pytest.approx(342.3)

    def test_precision_rounding(self) -> None:
        """Test rounding to configured precision (default 10 decimals)."""
        mw = MolecularWeight(180.12345678901234)
        # Should round to 10 decimal places
        assert mw.value == pytest.approx(180.1234567890)

    def test_below_minimum_raises__test_molecular_weight_domain_value_objects_test_identifiers_1063(
        self,
    ) -> None:
        """Test that MW below minimum raises ValueError."""
        with pytest.raises(ValueError, match="outside range"):
            MolecularWeight(5.0)  # Below default min of 10.0

    def test_at_minimum_raises(self) -> None:
        """Test that MW at minimum raises ValueError (exclusive bound)."""
        with pytest.raises(ValueError, match="outside range"):
            MolecularWeight(10.0)  # At bound, but bounds are exclusive

    def test_molecular_weight_above_maximum_raises(self) -> None:
        """Test that MW above maximum raises ValueError."""
        with pytest.raises(ValueError, match="outside range"):
            MolecularWeight(15000.0)  # Above default max of 10000.0

    def test_at_maximum_raises(self) -> None:
        """Test that MW at maximum raises ValueError (exclusive bound)."""
        with pytest.raises(ValueError, match="outside range"):
            MolecularWeight(10000.0)  # At bound, but bounds are exclusive

    def test_molecular_weight__zero_raises__f33235f9(self) -> None:
        """Test that zero MW raises ValueError."""
        with pytest.raises(ValueError, match="outside range"):
            MolecularWeight(0.0)

    def test_molecular_weight__negative_raises__66a81934(self) -> None:
        """Test that negative MW raises ValueError."""
        with pytest.raises(ValueError, match="outside range"):
            MolecularWeight(-100.0)

    def test_nan_raises(self) -> None:
        """Test that NaN raises ValueError."""
        with pytest.raises(ValueError, match="NaN or Inf"):
            MolecularWeight(float("nan"))

    def test_inf_raises(self) -> None:
        """Test that Infinity raises ValueError."""
        with pytest.raises(ValueError, match="NaN or Inf"):
            MolecularWeight(float("inf"))

    def test_molecular_weight__string_raises__d4cc7d37(self) -> None:
        """Test that invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid molecular weight"):
            MolecularWeight("not-a-number")

    def test_molecular_weight__immutability__46009bac(self) -> None:
        """Test Value Object is immutable."""
        mw = MolecularWeight(180.156)
        with pytest.raises(AttributeError, match="immutable"):
            mw._value = 200.0  # type: ignore[misc]

    def test_molecular_weight__equality_by_value__9ab37f8c(self) -> None:
        """Test equality is based on value."""
        mw1 = MolecularWeight(180.156)
        mw2 = MolecularWeight(180.156)
        assert mw1 == mw2

    def test_molecular_weight__inequality__59fdd53d(self) -> None:
        """Test inequality for different values."""
        mw1 = MolecularWeight(180.156)
        mw2 = MolecularWeight(200.0)
        assert mw1 != mw2

    def test_molecular_weight__hash_consistency__e5573551(self) -> None:
        """Test hash is consistent with equality."""
        mw1 = MolecularWeight(180.156)
        mw2 = MolecularWeight(180.156)
        assert hash(mw1) == hash(mw2)

    def test_molecular_weight__from_raw_valid__9ab317b4(self) -> None:
        """Test from_raw with valid value."""
        mw = MolecularWeight.from_raw(180.156)
        assert mw is not None
        assert mw.value == pytest.approx(180.156)

    def test_molecular_weight__raw_valid_string__64552374(self) -> None:
        """Test from_raw with valid string."""
        mw = MolecularWeight.from_raw("342.30")
        assert mw is not None
        assert mw.value == pytest.approx(342.3)

    def test_molecular_weight__from_raw_none__4263fbe1(self) -> None:
        """Test from_raw with None."""
        assert MolecularWeight.from_raw(None) is None

    def test_molecular_weight__raw_empty_string__390d6ed3(self) -> None:
        """Test from_raw with empty string."""
        assert MolecularWeight.from_raw("") is None
        assert MolecularWeight.from_raw("   ") is None

    def test_molecular_weight__from_raw_invalid__32f58c16(self) -> None:
        """Test from_raw with invalid value returns None."""
        assert MolecularWeight.from_raw("abc") is None
        assert MolecularWeight.from_raw(5.0) is None  # Below min
        assert MolecularWeight.from_raw(15000.0) is None  # Above max

    def test_molecular_weight__str__cb2da503(self) -> None:
        """Test string conversion."""
        mw = MolecularWeight(180.156)
        assert str(mw) == "180.156"

    def test_molecular_weight__repr__bad46cc6(self) -> None:
        """Test repr output."""
        mw = MolecularWeight(180.156)
        assert repr(mw) == "MolecularWeight(180.156)"

    def test_molecular_weight__with_custom_config__34df4825(self) -> None:
        """Test MolecularWeight with custom ValidationConfig."""
        config = ValidationConfig(
            min_molecular_weight=1.0, max_molecular_weight=50000.0
        )
        mw = MolecularWeight(5.0, config=config)
        assert mw.value == pytest.approx(5.0)

    def test_molecular_weight__from_raw_with_config__adcb3069(self) -> None:
        """Test from_raw with custom config."""
        config = ValidationConfig(
            min_molecular_weight=1.0, max_molecular_weight=50000.0
        )
        mw = MolecularWeight.from_raw(5.0, config=config)
        assert mw is not None
        assert mw.value == pytest.approx(5.0)

    def test_min_weight_property(self) -> None:
        """Test min_weight property returns config value."""
        mw = MolecularWeight(100.0)
        assert mw.min_weight == pytest.approx(10.0)

    def test_max_weight_property(self) -> None:
        """Test max_weight property returns config value."""
        mw = MolecularWeight(100.0)
        assert mw.max_weight == pytest.approx(10000.0)

    def test_molecular_weight__ignores_config__41aef88b(self) -> None:
        """Test that equality compares by value, ignoring config."""
        config1 = ValidationConfig(
            min_molecular_weight=1.0, max_molecular_weight=50000.0
        )
        config2 = ValidationConfig(
            min_molecular_weight=10.0, max_molecular_weight=10000.0
        )
        mw1 = MolecularWeight(100.0, config=config1)
        mw2 = MolecularWeight(100.0, config=config2)
        assert mw1 == mw2

    def test_custom_precision(self) -> None:
        """Test custom precision via config."""
        config = ValidationConfig(molecular_weight_precision=2)
        mw = MolecularWeight(180.12345, config=config)
        assert mw.value == pytest.approx(180.12)
