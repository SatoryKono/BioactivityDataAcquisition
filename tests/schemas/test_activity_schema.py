"""
Tests for the ActivitySchema.
"""
import pandas as pd
import pytest
from pandera.errors import SchemaError

from bioetl.schemas.chembl.activity import ActivitySchema


def test_activity_schema_valid():
    """Test that valid data passes validation."""
    df = pd.DataFrame({
        "activity_id": [100, 101],
        "assay_chembl_id": ["CHEMBL1", "CHEMBL2"],
        "molecule_chembl_id": ["CHEMBL10", "CHEMBL11"],
        "standard_type": ["IC50", "Ki"],
        "standard_value": [10.5, 5.0],
        "standard_units": ["nM", "nM"],
        "pchembl_value": [7.5, 8.0],
        "hash_row": ["a" * 64, "b" * 64],
        "hash_business_key": ["c" * 64, None]
    })

    validated_df = ActivitySchema.validate(df)
    assert isinstance(validated_df, pd.DataFrame)
    assert len(validated_df) == 2


def test_activity_schema_invalid_id():
    """Test that invalid activity_id fails validation."""
    df = pd.DataFrame({
        "activity_id": [-1],  # Invalid
        "assay_chembl_id": ["CHEMBL1"],
        "molecule_chembl_id": ["CHEMBL10"],
        "hash_row": ["a" * 64]
    })

    with pytest.raises(SchemaError):
        ActivitySchema.validate(df)


def test_activity_schema_invalid_chembl_id_format():
    """Test that invalid ChEMBL ID format fails validation."""
    df = pd.DataFrame({
        "activity_id": [1],
        "assay_chembl_id": ["INVALID_ID"],  # Invalid format
        "molecule_chembl_id": ["CHEMBL10"],
        "hash_row": ["a" * 64]
    })

    with pytest.raises(SchemaError):
        ActivitySchema.validate(df)
