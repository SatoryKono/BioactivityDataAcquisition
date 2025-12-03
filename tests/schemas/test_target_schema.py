"""
Tests for the TargetSchema using pandera DataFrameModel.
"""
import pandas as pd
import pytest
from pandera.errors import SchemaError

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
        "uniprot_id": "P12345",
        "hash_row": "0" * 64,
        "hash_business_key": None,
        "index": 0,
        "database_version": "chembl_34",
        "extracted_at": "2023-10-26T12:00:00+00:00",
        "score": None,
    }


def test_target_schema_valid(valid_target_data):
    """Test that valid data passes validation."""
    df = pd.DataFrame([valid_target_data])
    target = TargetSchema.validate(df)
    assert target.loc[0, "target_chembl_id"] == "CHEMBL202"
    assert "P12345" in str(target.loc[0, "target_components"])


def test_target_schema_invalid_chembl_id(valid_target_data):
    """Test invalid target_chembl_id format."""
    data = valid_target_data.copy()
    data["target_chembl_id"] = "INVALID"

    with pytest.raises(SchemaError):
        TargetSchema.validate(pd.DataFrame([data]))


def test_target_schema_missing_type(valid_target_data):
    """Test missing target_type."""
    data = valid_target_data.copy()
    del data["target_type"]

    with pytest.raises(SchemaError):
        TargetSchema.validate(pd.DataFrame([data]))

