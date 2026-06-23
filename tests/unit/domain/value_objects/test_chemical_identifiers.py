"""Unit tests for chemical structure identifier Value Objects (InChIKey, SMILES)."""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects import InChIKey, SMILES


ASPIRIN_INCHIKEY = "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
CAFFEINE_SMILES = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"


@pytest.mark.unit
class TestInChIKeyValidation:
    """Tests for InChIKey creation and validation."""

    def test_in_ch_i_key_validation__valid_creation__bf835342(self) -> None:
        key = InChIKey(ASPIRIN_INCHIKEY)
        assert key.value == ASPIRIN_INCHIKEY

    def test_in_ch_i_key_validation__to_uppercase__c522f7fc(self) -> None:
        key = InChIKey("bsynrymutxbxsq-uhfffaoysa-n")
        assert key.value == ASPIRIN_INCHIKEY

    def test_in_ch_i_key_validation__strips_whitespace__89075a37(self) -> None:
        key = InChIKey(f"  {ASPIRIN_INCHIKEY}  ")
        assert key.value == ASPIRIN_INCHIKEY

    def test_in_ch_i_key_validation__non_string_raises__e3f95df3(self) -> None:
        with pytest.raises(ValueError, match="must be str"):
            InChIKey(12345)  # type: ignore[arg-type]

    def test_in_ch_i_key_validation__empty_string_raises__bed8478d(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            InChIKey("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            InChIKey("   ")

    def test_in_ch_i_key_validation__format_raises__f37db925(self) -> None:
        with pytest.raises(ValueError, match="Invalid InChI Key format"):
            InChIKey("NOT-A-VALID-INCHIKEY")

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid InChI Key format"):
            InChIKey("ABCDEF-GHIJ-K")

    def test_connectivity_layer(self) -> None:
        key = InChIKey(ASPIRIN_INCHIKEY)
        assert key.connectivity_layer == "BSYNRYMUTXBXSQ"

    def test_stereochemistry_layer(self) -> None:
        key = InChIKey(ASPIRIN_INCHIKEY)
        assert key.stereochemistry_layer == "UHFFFAOYSA"

    def test_protonation_layer(self) -> None:
        key = InChIKey(ASPIRIN_INCHIKEY)
        assert key.protonation_layer == "N"

    def test_in_ch_i_key_validation__equality__34a1464e(self) -> None:
        k1 = InChIKey(ASPIRIN_INCHIKEY)
        k2 = InChIKey(ASPIRIN_INCHIKEY)
        assert k1 == k2

    def test_hash_equal(self) -> None:
        k1 = InChIKey(ASPIRIN_INCHIKEY)
        k2 = InChIKey(ASPIRIN_INCHIKEY)
        assert hash(k1) == hash(k2)

    def test_in_ch_i_key_validation__from_raw_valid__ff17a260(self) -> None:
        result = InChIKey.from_raw(ASPIRIN_INCHIKEY)
        assert result is not None
        assert result.value == ASPIRIN_INCHIKEY

    def test_from_raw_none(self) -> None:
        assert InChIKey.from_raw(None) is None

    def test_from_raw_empty(self) -> None:
        assert InChIKey.from_raw("") is None

    def test_from_raw_invalid(self) -> None:
        assert InChIKey.from_raw("INVALID") is None


@pytest.mark.unit
class TestSMILESValidation:
    """Tests for SMILES creation and validation."""

    def test_s_m_i_l_e_s_validation__valid_creation__de71b12f(self) -> None:
        s = SMILES(CAFFEINE_SMILES)
        assert s.value == CAFFEINE_SMILES

    def test_s_m_i_l_e_s_validation__strips_whitespace__e3141d01(self) -> None:
        s = SMILES(f"  {CAFFEINE_SMILES}  ")
        assert s.value == CAFFEINE_SMILES

    def test_s_m_i_l_e_s_validation__non_string_raises__001feb93(self) -> None:
        with pytest.raises(ValueError, match="must be str"):
            SMILES(42)  # type: ignore[arg-type]

    def test_s_m_i_l_e_s_validation__empty_raises__14aeff4c(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            SMILES("")

    def test_s_m_i_l_e_s_validation__only_raises__59324297(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            SMILES("   ")

    def test_not_canonical_by_default(self) -> None:
        s = SMILES(CAFFEINE_SMILES)
        assert s.is_canonical is False

    def test_canonical_factory(self) -> None:
        s = SMILES.canonical(CAFFEINE_SMILES)
        assert s.is_canonical is True
        assert s.value == CAFFEINE_SMILES

    def test_equality_same(self) -> None:
        s1 = SMILES(CAFFEINE_SMILES)
        s2 = SMILES(CAFFEINE_SMILES)
        assert s1 == s2

    def test_inequality_canonical_flag(self) -> None:
        s1 = SMILES(CAFFEINE_SMILES)
        s2 = SMILES.canonical(CAFFEINE_SMILES)
        assert s1 != s2

    def test_hash_same(self) -> None:
        s1 = SMILES(CAFFEINE_SMILES)
        s2 = SMILES(CAFFEINE_SMILES)
        assert hash(s1) == hash(s2)

    def test_s_m_i_l_e_s_validation__from_raw_valid__b433c74f(self) -> None:
        result = SMILES.from_raw(CAFFEINE_SMILES)
        assert result is not None
        assert result.value == CAFFEINE_SMILES

    def test_s_m_i_l_e_s_validation__from_raw_none__d6059486(self) -> None:
        assert SMILES.from_raw(None) is None

    def test_s_m_i_l_e_s_validation__from_raw_empty__f2cdb590(self) -> None:
        assert SMILES.from_raw("") is None

    def test_from_raw_canonical(self) -> None:
        result = SMILES.from_raw(CAFFEINE_SMILES, is_canonical=True)
        assert result is not None
        assert result.is_canonical is True

    def test_from_raw_soft_invalid_returns_none(self) -> None:
        assert SMILES.from_raw("invalid smiles with spaces") is None

    def test_from_raw_strict_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid SMILES format"):
            SMILES.from_raw("invalid smiles with spaces", mode="strict")

    def test_from_raw_strict_blank_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            SMILES.from_raw("   ", mode="strict")

    def test_invalid_smiles_characters_raise(self) -> None:
        with pytest.raises(ValueError, match="Invalid SMILES format"):
            SMILES("CCO🙂")

    def test_repr_basic(self) -> None:
        s = SMILES("CC")
        assert "CC" in repr(s)

    def test_repr_canonical(self) -> None:
        s = SMILES.canonical("CC")
        assert "is_canonical=True" in repr(s)
