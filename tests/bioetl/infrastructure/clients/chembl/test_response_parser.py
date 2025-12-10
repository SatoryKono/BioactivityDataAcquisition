from pydantic import ValidationError
import pytest

from bioetl.domain.schemas.chembl.raw_models import (
    ActivityRawModel,
    AssayRawModel,
    DocumentRawModel,
    MoleculeRawModel,
    TargetRawModel,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblActivityResponseParser,
    ChemblResponseParserImpl,
    create_activity_parser,
)


class TestActivityParser:
    """Tests for activity parsing."""

    def test_parse_activities(self):
        parser = ChemblResponseParserImpl(ActivityRawModel)
        response = {
            "activities": [
                {"activity_id": "1", "standard_flag": True},
                {"activity_id": "2", "standard_flag": False},
            ],
            "page_meta": {"limit": 20},
        }
        records = parser.parse(response)
        assert len(records) == 2
        assert isinstance(records[0], ActivityRawModel)
        assert records[0].activity_id == "1"

    def test_parse_empty(self):
        parser = ChemblResponseParserImpl(ActivityRawModel)
        response = {"page_meta": {}}
        records = parser.parse(response)
        assert records == []

    def test_parse_invalid_payload(self):
        parser = ChemblResponseParserImpl(ActivityRawModel)
        response = {"activities": [{"activity_id": 1}]}

        with pytest.raises(ValidationError):
            parser.parse(response)

    def test_extract_metadata(self):
        parser = ChemblResponseParserImpl(ActivityRawModel)
        response = {"page_meta": {"offset": 10}}
        meta = parser.extract_metadata(response)
        assert meta["offset"] == 10


class TestMoleculeParser:
    """Tests for molecule parsing."""

    def test_parse_molecules(self):
        parser = ChemblResponseParserImpl(MoleculeRawModel)
        response = {
            "molecules": [
                {"molecule_chembl_id": "CHEMBL1", "pref_name": "Aspirin"},
                {"molecule_chembl_id": "CHEMBL2", "molecule_type": "Small molecule"},
            ],
            "page_meta": {"limit": 20},
        }
        records = parser.parse(response)
        assert len(records) == 2
        assert isinstance(records[0], MoleculeRawModel)
        assert records[0].molecule_chembl_id == "CHEMBL1"
        assert records[0].pref_name == "Aspirin"

    def test_parse_molecule_with_extra_fields(self):
        """Test that extra fields are allowed."""
        parser = ChemblResponseParserImpl(MoleculeRawModel)
        response = {
            "molecules": [
                {
                    "molecule_chembl_id": "CHEMBL1",
                    "unknown_field": "value",
                    "another_field": 123,
                },
            ],
        }
        records = parser.parse(response)
        assert len(records) == 1
        assert records[0].molecule_chembl_id == "CHEMBL1"

    def test_stringify_molecule_id(self):
        """Test that molecule_chembl_id is stringified."""
        parser = ChemblResponseParserImpl(MoleculeRawModel)
        response = {
            "molecules": [{"molecule_chembl_id": 12345}],
        }
        records = parser.parse(response)
        assert records[0].molecule_chembl_id == "12345"


class TestTargetParser:
    """Tests for target parsing."""

    def test_parse_targets(self):
        parser = ChemblResponseParserImpl(TargetRawModel)
        response = {
            "targets": [
                {
                    "target_chembl_id": "CHEMBL1234",
                    "pref_name": "Cyclooxygenase-2",
                    "organism": "Homo sapiens",
                },
            ],
            "page_meta": {"limit": 20},
        }
        records = parser.parse(response)
        assert len(records) == 1
        assert isinstance(records[0], TargetRawModel)
        assert records[0].target_chembl_id == "CHEMBL1234"
        assert records[0].organism == "Homo sapiens"


class TestAssayParser:
    """Tests for assay parsing."""

    def test_parse_assays(self):
        parser = ChemblResponseParserImpl(AssayRawModel)
        response = {
            "assays": [
                {
                    "assay_chembl_id": "CHEMBL1000",
                    "assay_type": "B",
                    "description": "Binding assay",
                },
            ],
            "page_meta": {"limit": 20},
        }
        records = parser.parse(response)
        assert len(records) == 1
        assert isinstance(records[0], AssayRawModel)
        assert records[0].assay_chembl_id == "CHEMBL1000"
        assert records[0].assay_type == "B"


class TestDocumentParser:
    """Tests for document parsing."""

    def test_parse_documents(self):
        parser = ChemblResponseParserImpl(DocumentRawModel)
        response = {
            "documents": [
                {
                    "document_chembl_id": "CHEMBL_DOC_1",
                    "journal": "Nature",
                    "year": 2023,
                    "title": "Example paper",
                },
            ],
            "page_meta": {"limit": 20},
        }
        records = parser.parse(response)
        assert len(records) == 1
        assert isinstance(records[0], DocumentRawModel)
        assert records[0].document_chembl_id == "CHEMBL_DOC_1"
        assert records[0].journal == "Nature"
        assert records[0].year == 2023


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_create_activity_parser_factory(self):
        """Test factory function creates activity parser."""
        parser = create_activity_parser()
        response = {
            "activities": [
                {"activity_id": "1", "standard_flag": True},
            ],
        }
        records = parser.parse(response)
        assert len(records) == 1
        assert isinstance(records[0], ActivityRawModel)

    def test_chembl_activity_response_parser_alias(self):
        """Test type alias is available."""
        # This should not raise - type alias exists
        assert ChemblActivityResponseParser is not None
