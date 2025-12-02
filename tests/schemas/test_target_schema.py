"""
Tests for the TargetSchema (Pydantic V2).
"""
import pytest
from pydantic import ValidationError

from bioetl.domain.schemas.chembl.target import TargetSchema


@pytest.fixture
def valid_target_data():
    """Return a valid target dictionary."""
    return {
        "target_chembl_id": "CHEMBL202",
        "pref_name": "Serotonin receptor",
        "organism": "Homo sapiens",
        "target_type": "SINGLE PROTEIN",
        "tax_id": 9606,
        "species_group_flag": False,
        "target_components": [{"accession": "P12345"}],
        "cross_references": [{"xref_src": "Uniprot", "xref_id": "P12345"}],
        "hash_row": "0" * 64,
    }


def test_target_schema_valid(valid_target_data):
    """Test that valid data passes validation."""
    target = TargetSchema(**valid_target_data)
    assert target.target_chembl_id == "CHEMBL202"
    assert len(target.target_components) == 1


def test_target_schema_invalid_chembl_id(valid_target_data):
    """Test invalid target_chembl_id format."""
    data = valid_target_data.copy()
    data["target_chembl_id"] = "INVALID"
    
    with pytest.raises(ValidationError) as exc:
        TargetSchema(**data)
    assert "String should match pattern" in str(exc.value)


def test_target_schema_missing_type(valid_target_data):
    """Test missing target_type."""
    data = valid_target_data.copy()
    del data["target_type"]
    
    with pytest.raises(ValidationError) as exc:
        TargetSchema(**data)
    assert "Field required" in str(exc.value)

