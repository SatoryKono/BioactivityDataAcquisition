"""
Tests for the TestitemSchema (Pydantic V2).
"""
import pytest
from pydantic import ValidationError

from bioetl.domain.schemas.chembl.testitem import TestitemSchema


@pytest.fixture
def valid_testitem_data():
    """Return a valid testitem dictionary."""
    return {
        "molecule_chembl_id": "CHEMBL500",
        "pref_name": "Ibuprofen",
        "molecule_type": "Small molecule",
        "max_phase": 4,
        "structure_type": "MOL",
        "molecule_properties": {"mw": 206.29},
        "molecule_structures": {"canonical_smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O"},
        "molecule_hierarchy": {"parent": "CHEMBL500"},
        "atc_classifications": ["M01AE01"],
        "helm_notation": None,
        "hash_row": "9" * 64,
    }


def test_testitem_schema_valid(valid_testitem_data):
    """Test that valid data passes validation."""
    item = TestitemSchema(**valid_testitem_data)
    assert item.molecule_chembl_id == "CHEMBL500"
    assert item.max_phase == 4


def test_testitem_schema_invalid_chembl_id(valid_testitem_data):
    """Test invalid molecule_chembl_id format."""
    data = valid_testitem_data.copy()
    data["molecule_chembl_id"] = "bad_id"
    
    with pytest.raises(ValidationError) as exc:
        TestitemSchema(**data)
    assert "String should match pattern" in str(exc.value)


def test_testitem_schema_extra_field(valid_testitem_data):
    """Test extra fields forbidden."""
    data = valid_testitem_data.copy()
    data["unknown_prop"] = 123
    
    with pytest.raises(ValidationError) as exc:
        TestitemSchema(**data)
    assert "Extra inputs are not permitted" in str(exc.value)

