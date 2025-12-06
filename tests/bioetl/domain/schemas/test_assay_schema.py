"""
Tests for the AssaySchema (Pandera).
"""
import pytest
# pylint: disable=redefined-outer-name
import pandas as pd
import pandera as pa
from bioetl.domain.schemas.chembl.assay import AssaySchema


@pytest.fixture
def valid_assay_data():
    """Return a valid assay dictionary."""
    df = pd.DataFrame(
        {
            "assay_chembl_id": ["CHEMBL121"],
            "assay_category": ["screening"],
            "assay_cell_type": ["HeLa"],
            "assay_test_type": ["in vitro"],
            "assay_tissue": ["Lung"],
            "assay_type": ["B"],
            "assay_type_description": ["Binding"],
            "cell_chembl_id": ["CHEMBL33"],
            "confidence_score": [9],
            "description": ["Binding assay"],
            "document_chembl_id": ["CHEMBL22"],
            "target_chembl_id": ["CHEMBL44"],
            "tissue_chembl_id": ["CHEMBL55"],
            "variant_sequence": [None],
            "hash_row": ["d" * 64],
            "hash_business_key": ["e" * 64],
            "index": [0],
            "database_version": ["chembl_34"],
            "extracted_at": ["2023-10-26T12:00:00+00:00"],
            # Missing columns required by schema
            "aidx": [None],
            "assay_classifications": [None],
            "assay_group": [None],
            "assay_organism": [None],
            "assay_parameters": [None],
            "assay_strain": [None],
            "assay_subcellular_fraction": [None],
            "assay_tax_id": [None],
            "bao_format": [None],
            "bao_label": [None],
            "confidence_description": [None],
            "relationship_description": [None],
            "relationship_type": [None],
            "score": [None],
            "src_assay_id": [None],
            "src_id": [None],
        }
    )
    schema_columns = list(AssaySchema.to_schema().columns.keys())
    return df.reindex(columns=schema_columns)


def test_assay_schema_valid(valid_assay_data):
    """Test that valid data passes validation."""
    df = valid_assay_data.copy()
    validated_df = AssaySchema.validate(df)
    assert validated_df.iloc[0]["assay_chembl_id"] == "CHEMBL121"


def test_assay_schema_invalid_type(valid_assay_data):
    """Test that invalid assay_type fails validation."""
    df = valid_assay_data.copy()
    df["assay_type"] = ["INVALID"]

    with pytest.raises(pa.errors.SchemaError) as exc:
        AssaySchema.validate(df)
    assert "isin" in str(exc.value)


def test_assay_schema_invalid_confidence(valid_assay_data):
    """Test that invalid confidence_score fails validation."""
    df = valid_assay_data.copy()
    df["confidence_score"] = [10]  # max 9

    with pytest.raises(pa.errors.SchemaError) as exc:
        AssaySchema.validate(df)
    assert "less_than_or_equal_to" in str(exc.value)


def test_assay_schema_invalid_chembl_id(valid_assay_data):
    """Test regex validation for ChEMBL IDs."""
    df = valid_assay_data.copy()
    df["target_chembl_id"] = ["bad_id"]

    with pytest.raises(pa.errors.SchemaError) as exc:
        AssaySchema.validate(df)
    assert "str_matches" in str(exc.value)
