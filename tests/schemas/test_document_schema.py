"""
Tests for the DocumentSchema (Pydantic V2).
"""
import pytest
from pydantic import ValidationError

from bioetl.domain.schemas.chembl.document import DocumentSchema


@pytest.fixture
def valid_document_data():
    """Return a valid document dictionary."""
    return {
        "abstract": "This is an abstract.",
        "authors": "Doe J, Smith A",
        "doc_type": "PUBLICATION",
        "document_chembl_id": "CHEMBL999",
        "doi": "10.1021/jm00000",
        "doi_chembl": None,
        "first_page": "100",
        "issue": "2",
        "journal": "J Med Chem",
        "journal_full_title": "Journal of Medicinal Chemistry",
        "last_page": "110",
        "patent_id": None,
        "pubmed_id": "12345678",
        "src_id": 1,
        "title": "New Inhibitors",
        "volume": "50",
        "year": 2021,
        "chembl_release_id": 33,
        "hash_row": "f" * 64,
    }


def test_document_schema_valid(valid_document_data):
    """Test that valid data passes validation."""
    doc = DocumentSchema(**valid_document_data)
    assert doc.doc_type == "PUBLICATION"
    assert doc.year == 2021


def test_document_schema_invalid_doc_type(valid_document_data):
    """Test that invalid doc_type fails validation."""
    data = valid_document_data.copy()
    data["doc_type"] = "INVALID_TYPE"
    
    with pytest.raises(ValidationError) as exc:
        DocumentSchema(**data)
    assert "Input should be 'PUBLICATION', 'DATASET', 'PATENT' or 'OTHER'" in str(exc.value)


def test_document_schema_missing_required(valid_document_data):
    """Test that missing title fails validation."""
    data = valid_document_data.copy()
    del data["title"]
    
    with pytest.raises(ValidationError) as exc:
        DocumentSchema(**data)
    assert "Field required" in str(exc.value)


def test_document_schema_bad_hash(valid_document_data):
    """Test that invalid hash_row fails validation."""
    data = valid_document_data.copy()
    data["hash_row"] = "short_hash"
    
    with pytest.raises(ValidationError) as exc:
        DocumentSchema(**data)
    assert "String should match pattern" in str(exc.value)

