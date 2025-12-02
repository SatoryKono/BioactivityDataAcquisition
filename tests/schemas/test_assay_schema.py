"""
Tests for the AssaySchema (Pydantic V2).
"""
import pytest
from pydantic import ValidationError

from bioetl.domain.schemas.chembl.assay import AssaySchema


@pytest.fixture
def valid_assay_data():
    """Return a valid assay dictionary."""
    return {
        "assay_chembl_id": "CHEMBL121",
        "assay_category": "screening",
        "assay_cell_type": "HeLa",
        "assay_test_type": "in vitro",
        "assay_tissue": "Lung",
        "assay_type": "B",
        "assay_type_description": "Binding",
        "cell_chembl_id": "CHEMBL33",
        "confidence_score": 9,
        "description": "Binding assay",
        "document_chembl_id": "CHEMBL22",
        "target_chembl_id": "CHEMBL44",
        "tissue_chembl_id": "CHEMBL55",
        "variant_sequence": None,
        "hash_row": "d" * 64,
        "hash_business_key": "e" * 64,
    }


def test_assay_schema_valid(valid_assay_data):
    """Test that valid data passes validation."""
    assay = AssaySchema(**valid_assay_data)
    assert assay.assay_chembl_id == "CHEMBL121"


def test_assay_schema_invalid_type(valid_assay_data):
    """Test that invalid assay_type fails validation."""
    data = valid_assay_data.copy()
    data["assay_type"] = "INVALID"
    
    with pytest.raises(ValidationError) as exc:
        AssaySchema(**data)
    assert "Input should be 'B', 'F', 'A', 'T', 'P' or 'U'" in str(exc.value)


def test_assay_schema_invalid_confidence(valid_assay_data):
    """Test that invalid confidence_score fails validation."""
    data = valid_assay_data.copy()
    data["confidence_score"] = 10  # max 9
    
    with pytest.raises(ValidationError) as exc:
        AssaySchema(**data)
    assert "less than or equal to 9" in str(exc.value)


def test_assay_schema_invalid_chembl_id(valid_assay_data):
    """Test regex validation for ChEMBL IDs."""
    data = valid_assay_data.copy()
    data["target_chembl_id"] = "bad_id"
    
    with pytest.raises(ValidationError) as exc:
        AssaySchema(**data)
    assert "String should match pattern" in str(exc.value)

