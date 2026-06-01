"""Tests for compound identifier Value Objects.

Tests for CompoundId, CompoundSource, AssayId.
"""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects import (
    AssayId,
    ChemblId,
    CompoundId,
    CompoundSource,
    PubChemCid,
)

pytestmark = pytest.mark.unit


class TestCompoundSource:
    """Tests for CompoundSource enum."""

    def test_chembl_source(self) -> None:
        """Test ChEMBL source value."""
        assert CompoundSource.CHEMBL.value == "chembl"

    def test_pubchem_source(self) -> None:
        """Test PubChem source value."""
        assert CompoundSource.PUBCHEM.value == "pubchem"


class TestCompoundId:
    """Tests for CompoundId Value Object."""

    def test_from_chembl_valid(self) -> None:
        """Test creation from valid ChEMBL ID."""
        molecule_id = CompoundId.from_chembl("CHEMBL25")
        assert molecule_id.value == "CHEMBL25"
        assert molecule_id.source == CompoundSource.CHEMBL
        assert molecule_id.is_chembl is True
        assert molecule_id.is_pubchem is False

    def test_from_chembl_normalizes_case(self) -> None:
        """Test ChEMBL ID case normalization."""
        molecule_id = CompoundId.from_chembl("chembl123")
        assert molecule_id.value == "CHEMBL123"

    def test_from_chembl_removes_leading_zeros(self) -> None:
        """Test ChEMBL ID leading zero removal."""
        molecule_id = CompoundId.from_chembl("CHEMBL0025")
        assert molecule_id.value == "CHEMBL25"

    def test_from_pubchem_int_valid(self) -> None:
        """Test creation from PubChem CID integer."""
        molecule_id = CompoundId.from_pubchem(2244)
        assert molecule_id.value == "2244"
        assert molecule_id.source == CompoundSource.PUBCHEM
        assert molecule_id.is_pubchem is True
        assert molecule_id.is_chembl is False

    def test_from_pubchem_string_valid(self) -> None:
        """Test creation from PubChem CID string."""
        molecule_id = CompoundId.from_pubchem("2244")
        assert molecule_id.value == "2244"
        assert molecule_id.source == CompoundSource.PUBCHEM

    def test_from_raw_chembl(self) -> None:
        """Test from_raw with ChEMBL source."""
        molecule_id = CompoundId.from_raw("CHEMBL100", "chembl")
        assert molecule_id.value == "CHEMBL100"
        assert molecule_id.source == CompoundSource.CHEMBL

    def test_from_raw_pubchem(self) -> None:
        """Test from_raw with PubChem source."""
        molecule_id = CompoundId.from_raw(5988, "pubchem")
        assert molecule_id.value == "5988"
        assert molecule_id.source == CompoundSource.PUBCHEM

    def test_from_raw_with_enum_source(self) -> None:
        """Test from_raw with enum source."""
        molecule_id = CompoundId.from_raw("CHEMBL50", CompoundSource.CHEMBL)
        assert molecule_id.source == CompoundSource.CHEMBL

    def test_numeric_id_chembl(self) -> None:
        """Test numeric_id property for ChEMBL."""
        molecule_id = CompoundId.from_chembl("CHEMBL25")
        assert molecule_id.numeric_id == 25

    def test_numeric_id_pubchem(self) -> None:
        """Test numeric_id property for PubChem."""
        molecule_id = CompoundId.from_pubchem(2244)
        assert molecule_id.numeric_id == 2244

    def test_as_chembl_id_when_chembl(self) -> None:
        """Test as_chembl_id when source is ChEMBL."""
        molecule_id = CompoundId.from_chembl("CHEMBL25")
        chembl = molecule_id.as_chembl_id
        assert chembl is not None
        assert isinstance(chembl, ChemblId)
        assert chembl.value == "CHEMBL25"

    def test_as_chembl_id_when_pubchem(self) -> None:
        """Test as_chembl_id when source is PubChem returns None."""
        molecule_id = CompoundId.from_pubchem(2244)
        assert molecule_id.as_chembl_id is None

    def test_as_pubchem_molecule_id_when_pubchem(self) -> None:
        """Test as_pubchem_molecule_id when source is PubChem."""
        molecule_id = CompoundId.from_pubchem(2244)
        pubchem = molecule_id.as_pubchem_molecule_id
        assert pubchem is not None
        assert isinstance(pubchem, PubChemCid)
        assert pubchem.value == 2244

    def test_as_pubchem_molecule_id_when_chembl(self) -> None:
        """Test as_pubchem_molecule_id when source is ChEMBL returns None."""
        molecule_id = CompoundId.from_chembl("CHEMBL25")
        assert molecule_id.as_pubchem_molecule_id is None

    def test_invalid_chembl_format_raises(self) -> None:
        """Test invalid ChEMBL format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ChEMBL ID"):
            CompoundId.from_chembl("INVALID")

    def test_invalid_pubchem_raises(self) -> None:
        """Test invalid PubChem CID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid PubChem CID"):
            CompoundId.from_pubchem("not-a-number")

    def test_zero_pubchem_raises(self) -> None:
        """Test zero PubChem CID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid PubChem CID"):
            CompoundId.from_pubchem(0)

    def test_invalid_source_raises(self) -> None:
        """Test invalid source raises ValueError."""
        with pytest.raises(ValueError):
            CompoundId.from_raw("123", "invalid_source")  # type: ignore[arg-type]

    def test_immutability(self) -> None:
        """Test CompoundId is immutable (frozen dataclass)."""
        molecule_id = CompoundId.from_chembl("CHEMBL25")
        with pytest.raises(Exception):  # FrozenInstanceError
            molecule_id.value = "CHEMBL100"  # type: ignore[misc]

    def test_equality_same_source(self) -> None:
        """Test equality for same source."""
        molecule_id1 = CompoundId.from_chembl("CHEMBL25")
        molecule_id2 = CompoundId.from_chembl("chembl25")
        assert molecule_id1 == molecule_id2

    def test_inequality_different_sources(self) -> None:
        """Test inequality for different sources."""
        molecule_id1 = CompoundId.from_chembl("CHEMBL25")
        molecule_id2 = CompoundId.from_pubchem(25)
        assert molecule_id1 != molecule_id2

    def test_inequality_different_values(self) -> None:
        """Test inequality for different values."""
        molecule_id1 = CompoundId.from_chembl("CHEMBL25")
        molecule_id2 = CompoundId.from_chembl("CHEMBL100")
        assert molecule_id1 != molecule_id2

    def test_hash_consistency(self) -> None:
        """Test hash is consistent with equality."""
        molecule_id1 = CompoundId.from_chembl("CHEMBL25")
        molecule_id2 = CompoundId.from_chembl("chembl25")
        assert hash(molecule_id1) == hash(molecule_id2)

    def test_str(self) -> None:
        """Test string representation includes source."""
        molecule_id = CompoundId.from_chembl("CHEMBL25")
        assert str(molecule_id) == "chembl:CHEMBL25"

        molecule_id2 = CompoundId.from_pubchem(2244)
        assert str(molecule_id2) == "pubchem:2244"

    def test_can_be_used_in_set(self) -> None:
        """Test CompoundId can be used in set."""
        ids = {
            CompoundId.from_chembl("CHEMBL25"),
            CompoundId.from_chembl("CHEMBL25"),
            CompoundId.from_pubchem(2244),
        }
        assert len(ids) == 2

    def test_can_be_used_as_dict_key(self) -> None:
        """Test CompoundId can be used as dict key."""
        d = {CompoundId.from_chembl("CHEMBL25"): "aspirin"}
        assert d[CompoundId.from_chembl("chembl25")] == "aspirin"


class TestAssayId:
    """Tests for AssayId Value Object."""

    def test_valid_assay_id(self) -> None:
        """Test creation with valid assay ID."""
        aid = AssayId("CHEMBL1217643")
        assert aid.value == "CHEMBL1217643"
        assert aid.numeric_id == 1217643

    def test_normalizes_case(self) -> None:
        """Test case normalization to uppercase."""
        aid = AssayId("chembl829394")
        assert aid.value == "CHEMBL829394"

    def test_strips_whitespace(self) -> None:
        """Test whitespace stripping."""
        aid = AssayId("  CHEMBL100  ")
        assert aid.value == "CHEMBL100"

    def test_removes_leading_zeros(self) -> None:
        """Test leading zeros are normalized."""
        aid = AssayId("CHEMBL0025")
        assert aid.value == "CHEMBL25"

    def test_as_chembl_id_property(self) -> None:
        """Test as_chembl_id property."""
        aid = AssayId("CHEMBL100")
        chembl = aid.as_chembl_id
        assert isinstance(chembl, ChemblId)
        assert chembl.value == "CHEMBL100"

    def test_from_string_valid(self) -> None:
        """Test from_string with valid string."""
        aid = AssayId.from_string("CHEMBL100")
        assert aid is not None
        assert aid.value == "CHEMBL100"

    def test_from_string_none(self) -> None:
        """Test from_string with None returns None."""
        assert AssayId.from_string(None) is None

    def test_from_string_empty(self) -> None:
        """Test from_string with empty string returns None."""
        assert AssayId.from_string("") is None
        assert AssayId.from_string("   ") is None

    def test_invalid_format_raises(self) -> None:
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ChEMBL ID"):
            AssayId("INVALID")

    def test_empty_raises(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            AssayId("")

    def test_zero_id_raises(self) -> None:
        """Test zero numeric ID raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            AssayId("CHEMBL0")

    def test_immutability(self) -> None:
        """Test AssayId is immutable."""
        aid = AssayId("CHEMBL100")
        with pytest.raises(AttributeError, match="immutable"):
            aid._value = "CHEMBL200"  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        """Test equality is based on value."""
        aid1 = AssayId("CHEMBL100")
        aid2 = AssayId("chembl100")
        assert aid1 == aid2
        assert aid1 is not aid2

    def test_hash_consistency(self) -> None:
        """Test hash is consistent with equality."""
        aid1 = AssayId("CHEMBL100")
        aid2 = AssayId("chembl100")
        assert hash(aid1) == hash(aid2)

    def test_repr(self) -> None:
        """Test string representation."""
        aid = AssayId("CHEMBL100")
        assert repr(aid) == "AssayId('CHEMBL100')"

    def test_str(self) -> None:
        """Test string conversion."""
        aid = AssayId("CHEMBL100")
        assert str(aid) == "CHEMBL100"

    def test_can_be_used_in_set(self) -> None:
        """Test AssayId can be used in set."""
        ids = {AssayId("CHEMBL100"), AssayId("CHEMBL100"), AssayId("CHEMBL200")}
        assert len(ids) == 2

    def test_inequality_with_different_ids(self) -> None:
        """Test inequality for different IDs."""
        aid1 = AssayId("CHEMBL100")
        aid2 = AssayId("CHEMBL200")
        assert aid1 != aid2

    def test_inequality_with_different_types(self) -> None:
        """Test inequality with different types."""
        aid = AssayId("CHEMBL100")
        assert aid != "CHEMBL100"
        assert aid != 100
