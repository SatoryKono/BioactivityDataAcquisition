"""Unit tests for chemical structure identifier Value Objects (InChIKey, SMILES)."""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects import InChIKey, SMILES


ASPIRIN_INCHIKEY = "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
CAFFEINE_SMILES = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"


@pytest.mark.unit
class TestInChIKeyValidation:
    """Tests for InChIKey creation and validation."""

    def test_valid_creation(self) -> None:
        key = InChIKey(ASPIRIN_INCHIKEY)
        assert key.value == ASPIRIN_INCHIKEY

    def test_normalizes_to_uppercase(self) -> None:
        key = InChIKey("bsynrymutxbxsq-uhfffaoysa-n")
        assert key.value == ASPIRIN_INCHIKEY

    def test_strips_whitespace(self) -> None:
        key = InChIKey(f"  {ASPIRIN_INCHIKEY}  ")
        assert key.value == ASPIRIN_INCHIKEY

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must be str"):
            InChIKey(12345)  # type: ignore[arg-type]

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            InChIKey("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            InChIKey("   ")

    def test_invalid_format_raises(self) -> None:
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

    def test_equality(self) -> None:
        k1 = InChIKey(ASPIRIN_INCHIKEY)
        k2 = InChIKey(ASPIRIN_INCHIKEY)
        assert k1 == k2

    def test_hash_equal(self) -> None:
        k1 = InChIKey(ASPIRIN_INCHIKEY)
        k2 = InChIKey(ASPIRIN_INCHIKEY)
        assert hash(k1) == hash(k2)

    def test_from_raw_valid(self) -> None:
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

    def test_valid_creation(self) -> None:
        s = SMILES(CAFFEINE_SMILES)
        assert s.value == CAFFEINE_SMILES

    def test_strips_whitespace(self) -> None:
        s = SMILES(f"  {CAFFEINE_SMILES}  ")
        assert s.value == CAFFEINE_SMILES

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must be str"):
            SMILES(42)  # type: ignore[arg-type]

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            SMILES("")

    def test_whitespace_only_raises(self) -> None:
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

    def test_from_raw_valid(self) -> None:
        result = SMILES.from_raw(CAFFEINE_SMILES)
        assert result is not None
        assert result.value == CAFFEINE_SMILES

    def test_from_raw_none(self) -> None:
        assert SMILES.from_raw(None) is None

    def test_from_raw_empty(self) -> None:
        assert SMILES.from_raw("") is None

    def test_from_raw_canonical(self) -> None:
        result = SMILES.from_raw(CAFFEINE_SMILES, is_canonical=True)
        assert result is not None
        assert result.is_canonical is True

    def test_repr_basic(self) -> None:
        s = SMILES("CC")
        assert "CC" in repr(s)

    def test_repr_canonical(self) -> None:
        s = SMILES.canonical("CC")
        assert "is_canonical=True" in repr(s)
