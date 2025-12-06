"""
Tests for the ActivitySchema (Pandera).
"""
import pandas as pd
import pytest
from pandera.errors import SchemaError

from bioetl.domain.schemas.chembl.activity import ActivitySchema


@pytest.fixture
def valid_activity_df():
    """Return a valid activity DataFrame with all required columns."""
    df = pd.DataFrame({
        "activity_id": [100],
        "action_type": ["agonist"],
        "assay_chembl_id": ["CHEMBL1"],
        "molecule_chembl_id": ["CHEMBL10"],
        "document_chembl_id": ["CHEMBL20"],
        "canonical_smiles": ["CCO"],
        "assay_type": ["B"],
        "standard_flag": [True],
        "hash_row": ["a" * 64],
        "hash_business_key": ["c" * 64],
        # Optional fields
        "assay_variant_accession": [None],
        "assay_variant_mutation": [None],
        "pchembl_value": [7.5],
        "standard_value": [10.5],
        "standard_units": ["nM"],
        "standard_type": ["IC50"],
        "relation": ["="],
        "standard_relation": ["="],
        "activity_comment": ["Test comment"],
        "assay_description": ["Test assay"],
        "bao_endpoint": ["BAO_0000190"],
        "bao_format": ["BAO_0000218"],
        "bao_label": ["IC50"],
        "data_validity_comment": [None],
        "data_validity_description": [None],
        "document_journal": ["J. Med. Chem."],
        "document_year": [2020.0],
        "ligand_efficiency": [{"bei": 12.3}],
        "molecule_pref_name": ["Aspirin"],
        "parent_molecule_chembl_id": ["CHEMBL10"],
        "potential_duplicate": [False],
        "qudt_units": ["http://qudt.org/vocab/unit/NanoMOL-PER-L"],
        "record_id": [12345.0],
        "src_id": [1.0],
        "standard_text_value": [None],
        "standard_upper_value": [None],
        "target_chembl_id": ["CHEMBL30"],
        "target_organism": ["Homo sapiens"],
        "target_pref_name": ["Target 1"],
        "target_tax_id": [9606.0],
        "text_value": [None],
        "toid": [None],
        "type": ["IC50"],
        "units": ["nM"],
        "uo_units": ["UO_0000065"],
        "upper_value": [None],
        "value": [10.5],
        "activity_properties": [None],
        # Generated columns
        "index": [0],
        "database_version": ["chembl_34"],
        "extracted_at": ["2023-10-26T12:00:00+00:00"]
    })
    schema_columns = list(ActivitySchema.to_schema().columns.keys())
    return df.reindex(columns=schema_columns)


def test_activity_schema_valid(valid_activity_df):
    """Test that valid data passes validation."""
    validated_df = ActivitySchema.validate(valid_activity_df)
    assert isinstance(validated_df, pd.DataFrame)
    assert len(validated_df) == 1


def test_activity_schema_invalid_id(valid_activity_df):
    """Test that invalid activity_id fails validation."""
    df = valid_activity_df.copy()
    df["activity_id"] = [-1]

    with pytest.raises(SchemaError) as exc:
        ActivitySchema.validate(df)
    assert ("greater_than_or_equal_to" in str(exc.value) or
            "ge" in str(exc.value))


def test_activity_schema_invalid_chembl_id_format(
    valid_activity_df
):
    """Test that invalid ChEMBL ID format fails validation."""
    df = valid_activity_df.copy()
    df["assay_chembl_id"] = ["INVALID_ID"]

    with pytest.raises(SchemaError) as exc:
        ActivitySchema.validate(df)
    assert "str_matches" in str(exc.value)


def test_activity_schema_invalid_assay_type(valid_activity_df):
    """Test that invalid assay_type fails validation."""
    df = valid_activity_df.copy()
    df["assay_type"] = ["X"]  # Invalid enum

    with pytest.raises(SchemaError) as exc:
        ActivitySchema.validate(df)
    assert "isin" in str(exc.value)


def test_activity_schema_invalid_pchembl_range(valid_activity_df):
    """Test that invalid pchembl_value range fails validation."""
    df = valid_activity_df.copy()
    df["pchembl_value"] = [16.0]

    with pytest.raises(SchemaError) as exc:
        ActivitySchema.validate(df)
    assert "less_than_or_equal_to" in str(exc.value) or "le" in str(exc.value)


def test_activity_schema_extra_column(valid_activity_df):
    """Test that extra columns are not allowed (strict)."""
    df = valid_activity_df.copy()
    df["extra_column"] = ["unexpected"]

    with pytest.raises(SchemaError) as exc:
        ActivitySchema.validate(df)
    assert "column 'extra_column' not in DataFrameSchema" in str(exc.value)
