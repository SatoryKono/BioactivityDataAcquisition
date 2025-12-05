"""
Tests for the TestitemSchema using pandera DataFrameModel.
"""
import pandas as pd
import pytest
from pandera.errors import SchemaError

from bioetl.domain.schemas.chembl.testitem import TestitemSchema as SchemaTestitem


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
        "molecule_synonyms": [],
        "cross_references": [{"xref_src": "PubChem", "xref_id": "3672"}],
        "pubchem_cid": 3672,
        "helm_notation": None,
        "hash_row": "9" * 64,
        "hash_business_key": None,
        "index": 0,
        "database_version": "chembl_34",
        "extracted_at": "2023-10-26T12:00:00+00:00",
    }


def test_testitem_schema_valid(valid_testitem_data):
    """Test that valid data passes validation."""
    df = pd.DataFrame([valid_testitem_data])
    item = SchemaTestitem.validate(df)
    assert item.loc[0, "molecule_chembl_id"] == "CHEMBL500"
    assert item.loc[0, "max_phase"] == 4


def test_testitem_schema_invalid_chembl_id(valid_testitem_data):
    """Test invalid molecule_chembl_id format."""
    data = valid_testitem_data.copy()
    data["molecule_chembl_id"] = "bad_id"

    with pytest.raises(SchemaError):
        SchemaTestitem.validate(pd.DataFrame([data]))


def test_testitem_schema_extra_field(valid_testitem_data):
    """Test extra fields forbidden."""
    data = valid_testitem_data.copy()
    data["unknown_prop"] = 123

    with pytest.raises(SchemaError):
        SchemaTestitem.validate(pd.DataFrame([data]))

