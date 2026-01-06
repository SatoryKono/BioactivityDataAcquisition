"""Unit tests for UniProt Protein transformer."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


@pytest.fixture
def mock_context():
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestUniProtProteinTransformer:
    """Tests for UniProtProteinTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create UniProtProteinTransformer instance."""
        return UniProtProteinTransformer(provider="uniprot")

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid protein record with all fields."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "COX2_HUMAN",
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "Prostaglandin G/H synthase 2"}
                }
            },
            "genes": [{"geneName": {"value": "PTGS2"}}],
            "organism": {"taxonId": 9606},
            "sequence": {"length": 604},
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["accession"] == "P12345"
        assert result["entry_name"] == "COX2_HUMAN"
        assert result["protein_name"] == "Prostaglandin G/H synthase 2"
        assert result["gene_names"] == ["PTGS2"]
        assert result["organism_id"] == 9606
        assert result["sequence_length"] == 604
        assert "entity_id" in result
        assert "content_hash" in result
        # Lineage fields should be present
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_ingestion_ts" in result

    @pytest.mark.asyncio
    async def test_transform_missing_accession(self, transformer, mock_context):
        """Test transformation returns None when primaryAccession is missing."""
        record = {
            "uniProtkbId": "TEST_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Test Protein"}}
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_missing_entry_name(self, transformer, mock_context):
        """Test transformation returns None when uniProtkbId is missing."""
        record = {
            "primaryAccession": "P12345",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Test Protein"}}
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_missing_protein_name_accepted(
        self, transformer, mock_context
    ):
        """Test transformation succeeds when protein name is missing.

        protein_name is optional - records without it should still be processed.
        """
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "proteinDescription": {},  # No recommendedName
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["accession"] == "P12345"
        assert result["entry_name"] == "TEST_HUMAN"
        assert result["protein_name"] is None

    @pytest.mark.asyncio
    async def test_transform_with_minimal_valid_record(self, transformer, mock_context):
        """Test transformation with minimal valid record (required fields only).

        Only accession and entry_name are required. protein_name is optional.
        """
        record = {
            "primaryAccession": "Q99999",
            "uniProtkbId": "MIN_HUMAN",
            # No proteinDescription - protein_name will be None
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["accession"] == "Q99999"
        assert result["entry_name"] == "MIN_HUMAN"
        assert result["protein_name"] is None
        assert result["gene_names"] == []
        assert result.get("organism_id") is None
        assert result.get("sequence_length") is None

    @pytest.mark.asyncio
    async def test_transform_with_multiple_genes(self, transformer, mock_context):
        """Test transformation extracts multiple gene names."""
        record = {
            "primaryAccession": "P00001",
            "uniProtkbId": "MULTI_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Multi-gene Protein"}}
            },
            "genes": [
                {"geneName": {"value": "GENE1"}},
                {"geneName": {"value": "GENE2"}},
                {"geneName": {"value": "GENE3"}},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["gene_names"] == ["GENE1", "GENE2", "GENE3"]

    @pytest.mark.asyncio
    async def test_transform_with_empty_genes(self, transformer, mock_context):
        """Test transformation handles empty genes list."""
        record = {
            "primaryAccession": "P00002",
            "uniProtkbId": "EMPTY_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Empty Genes Protein"}}
            },
            "genes": [],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["gene_names"] == []

    @pytest.mark.asyncio
    async def test_transform_with_malformed_genes(self, transformer, mock_context):
        """Test transformation handles malformed genes structure gracefully."""
        record = {
            "primaryAccession": "P00003",
            "uniProtkbId": "MAL_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Malformed Protein"}}
            },
            "genes": [
                {"geneName": {"value": "VALID"}},
                {"wrongKey": "invalid"},  # Missing geneName
                "not a dict",  # Not a dict
                {"geneName": "not a dict"},  # geneName not a dict
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["gene_names"] == ["VALID"]

    @pytest.mark.asyncio
    async def test_transform_entity_id_format(self, transformer, mock_context):
        """Test that entity_id follows expected format."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Test Protein"}}
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result
        # Entity ID should contain provider and accession
        assert "uniprot" in result["entity_id"]
        assert "P12345" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_transform_content_hash_consistent(self, transformer, mock_context):
        """Test that content_hash is generated and is consistent."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Test Protein"}}
            },
        }

        result1 = await transformer.transform(mock_context, record, index=0)
        result2 = await transformer.transform(mock_context, record, index=0)

        assert result1 is not None
        assert result2 is not None
        assert "content_hash" in result1
        assert "content_hash" in result2
        assert result1["content_hash"] == result2["content_hash"]

    @pytest.mark.asyncio
    async def test_transform_custom_provider(self, mock_context):
        """Test transformation with custom provider."""
        transformer = UniProtProteinTransformer(provider="custom_uniprot")
        record = {
            "primaryAccession": "Q11111",
            "uniProtkbId": "CUST_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Custom Protein"}}
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "custom_uniprot" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_transform_empty_accession_rejected(self, transformer, mock_context):
        """Test that empty string accession is rejected."""
        record = {
            "primaryAccession": "",
            "uniProtkbId": "EMPTY_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Empty Protein"}}
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_lineage_fields_present(self, transformer, mock_context):
        """Test that lineage fields are properly added to the result."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Test Protein"}}
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Lineage fields should be present with underscore prefix
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_source_batch_id" in result
        assert "_ingestion_ts" in result
        # Verify types
        assert isinstance(result["_run_id"], str)
        assert isinstance(result["_run_type"], str)
        assert isinstance(result["_ingestion_ts"], str)

    @pytest.mark.asyncio
    async def test_transform_sequence_length_validation(
        self, transformer, mock_context
    ):
        """Test that negative sequence_length causes validation error."""
        record = {
            "primaryAccession": "P99999",
            "uniProtkbId": "NEG_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Negative Seq Protein"}}
            },
            "sequence": {"length": -100},  # Invalid: negative
        }

        result = await transformer.transform(mock_context, record, index=0)

        # Entity validation should fail due to invariant
        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_zero_sequence_length(self, transformer, mock_context):
        """Test that zero sequence_length causes validation error."""
        record = {
            "primaryAccession": "P88888",
            "uniProtkbId": "ZERO_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Zero Seq Protein"}}
            },
            "sequence": {"length": 0},  # Invalid: zero
        }

        result = await transformer.transform(mock_context, record, index=0)

        # Entity validation should fail due to invariant
        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_deeply_nested_protein_name(
        self, transformer, mock_context
    ):
        """Test extraction of deeply nested protein name."""
        record = {
            "primaryAccession": "P77777",
            "uniProtkbId": "DEEP_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Deeply Nested Protein Name"}}
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_name"] == "Deeply Nested Protein Name"

    @pytest.mark.asyncio
    async def test_transform_with_organism_taxon(self, transformer, mock_context):
        """Test extraction of organism taxon ID from nested structure."""
        record = {
            "primaryAccession": "P66666",
            "uniProtkbId": "ORG_MOUSE",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Mouse Protein"}}
            },
            "organism": {"taxonId": 10090},  # Mus musculus
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["organism_id"] == 10090

    def test_transformer_accepts_entity_type(self):
        """Transformer MUST accept entity_type parameter."""
        transformer = UniProtProteinTransformer(entity_type="protein")
        assert transformer.entity_type == "protein"

    def test_transformer_default_entity_type(self):
        """Transformer SHOULD default entity_type to 'protein'."""
        transformer = UniProtProteinTransformer()
        assert transformer.entity_type == "protein"

    def test_transformer_custom_entity_type(self):
        """Transformer MUST accept custom entity_type."""
        transformer = UniProtProteinTransformer(entity_type="custom_entity")
        assert transformer.entity_type == "custom_entity"

    def test_transformer_accepts_pii_hasher(self):
        """Transformer MUST accept pii_hasher parameter."""
        from bioetl.domain.ports import NoOpPiiHasher

        hasher = NoOpPiiHasher()
        transformer = UniProtProteinTransformer(pii_hasher=hasher)
        assert transformer._pii_hasher is hasher

    def test_transformer_default_pii_hasher(self):
        """Transformer SHOULD default pii_hasher to NoOpPiiHasher."""
        from bioetl.domain.ports import NoOpPiiHasher

        transformer = UniProtProteinTransformer()
        assert isinstance(transformer._pii_hasher, NoOpPiiHasher)


@pytest.mark.unit
class TestUniProtProteinTransformerExtendedFields:
    """Tests for extended UniProt fields extraction."""

    @pytest.fixture
    def transformer(self):
        """Create UniProtProteinTransformer instance."""
        return UniProtProteinTransformer(provider="uniprot")

    @pytest.mark.asyncio
    async def test_extract_entry_type_reviewed(self, transformer, mock_context):
        """Test extraction of entry type for Swiss-Prot entry."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "entryType": "UniProtKB reviewed (Swiss-Prot)",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["entry_type"] == "UniProtKB reviewed (Swiss-Prot)"
        assert result["reviewed"] is True

    @pytest.mark.asyncio
    async def test_extract_entry_type_unreviewed(self, transformer, mock_context):
        """Test extraction of entry type for TrEMBL entry."""
        record = {
            "primaryAccession": "A0A000",
            "uniProtkbId": "TEST_HUMAN",
            "entryType": "UniProtKB unreviewed (TrEMBL)",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["entry_type"] == "UniProtKB unreviewed (TrEMBL)"
        assert result["reviewed"] is False

    @pytest.mark.asyncio
    async def test_extract_secondary_accessions(self, transformer, mock_context):
        """Test extraction of secondary accessions."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "secondaryAccessions": ["Q5TEV0", "Q96QA2"],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["secondary_accessions"] == '["Q5TEV0", "Q96QA2"]'

    @pytest.mark.asyncio
    async def test_extract_annotation_score(self, transformer, mock_context):
        """Test extraction of annotation score."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "annotationScore": 5,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["annotation_score"] == 5

    @pytest.mark.asyncio
    async def test_annotation_score_validation(self, transformer, mock_context):
        """Test that invalid annotation score causes validation error."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "annotationScore": 10,  # Invalid: > 5
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_extract_protein_existence(self, transformer, mock_context):
        """Test extraction of protein existence level."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "proteinExistence": "1: Evidence at protein level",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_existence"] == "Evidence at protein level"

    @pytest.mark.asyncio
    async def test_extract_short_names(self, transformer, mock_context):
        """Test extraction of short protein names."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "RAC-alpha serine/threonine-protein kinase"},
                    "shortNames": [{"value": "AKT1"}, {"value": "PKB alpha"}],
                }
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_short_names"] == '["AKT1", "PKB alpha"]'

    @pytest.mark.asyncio
    async def test_extract_alternative_names(self, transformer, mock_context):
        """Test extraction of alternative protein names."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "proteinDescription": {
                "alternativeNames": [
                    {"fullName": {"value": "Protein kinase B alpha"}},
                    {"fullName": {"value": "Proto-oncogene c-Akt"}},
                ]
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert (
            result["protein_alternative_names"]
            == '["Protein kinase B alpha", "Proto-oncogene c-Akt"]'
        )

    @pytest.mark.asyncio
    async def test_extract_ec_numbers(self, transformer, mock_context):
        """Test extraction of EC numbers."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "Test Kinase"},
                    "ecNumbers": [{"value": "2.7.11.1"}],
                }
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_ec_numbers"] == '["2.7.11.1"]'

    @pytest.mark.asyncio
    async def test_extract_flag(self, transformer, mock_context):
        """Test extraction of protein flag."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "proteinDescription": {"flag": "Precursor"},
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["flag"] == "Precursor"

    @pytest.mark.asyncio
    async def test_extract_organism_info(self, transformer, mock_context):
        """Test extraction of organism information."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "organism": {
                "scientificName": "Homo sapiens",
                "commonName": "Human",
                "taxonId": 9606,
                "lineage": ["Eukaryota", "Metazoa", "Chordata"],
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["organism_scientific"] == "Homo sapiens"
        assert result["organism_common"] == "Human"
        assert result["taxonomy_id"] == 9606
        assert result["lineage"] == '["Eukaryota", "Metazoa", "Chordata"]'

    @pytest.mark.asyncio
    async def test_extract_gene_synonyms(self, transformer, mock_context):
        """Test extraction of gene synonyms."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "genes": [
                {
                    "geneName": {"value": "AKT1"},
                    "synonyms": [{"value": "PKB"}, {"value": "RAC"}],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["gene_primary"] == "AKT1"
        assert result["gene_synonyms"] == '["PKB", "RAC"]'

    @pytest.mark.asyncio
    async def test_extract_function_comment(self, transformer, mock_context):
        """Test extraction of function comment."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "comments": [
                {
                    "commentType": "FUNCTION",
                    "texts": [
                        {"value": "Serine/threonine kinase involved in cell survival."}
                    ],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert (
            result["function_comment"]
            == '["Serine/threonine kinase involved in cell survival."]'
        )

    @pytest.mark.asyncio
    async def test_extract_catalytic_activity(self, transformer, mock_context):
        """Test extraction of catalytic activity."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "comments": [
                {
                    "commentType": "CATALYTIC ACTIVITY",
                    "reaction": {
                        "name": "ATP + protein = ADP + phosphoprotein",
                        "ecNumber": "2.7.11.1",
                    },
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert (
            '"reaction": "ATP + protein = ADP + phosphoprotein"'
            in result["catalytic_activity"]
        )
        assert '"ec_number": "2.7.11.1"' in result["catalytic_activity"]

    @pytest.mark.asyncio
    async def test_extract_subcellular_location(self, transformer, mock_context):
        """Test extraction of subcellular location."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "comments": [
                {
                    "commentType": "SUBCELLULAR LOCATION",
                    "subcellularLocations": [
                        {"location": {"value": "Cytoplasm"}},
                        {"location": {"value": "Nucleus"}},
                    ],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["subcellular_location"] == '["Cytoplasm", "Nucleus"]'

    @pytest.mark.asyncio
    async def test_extract_alternative_products(self, transformer, mock_context):
        """Test extraction of alternative products (isoforms)."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "comments": [
                {
                    "commentType": "ALTERNATIVE PRODUCTS",
                    "isoforms": [
                        {"isoformIds": ["P31749-1"], "name": {"value": "1"}},
                        {"isoformIds": ["P31749-2"], "name": {"value": "2"}},
                    ],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["isoform_count"] == 2
        assert '"ids": ["P31749-1"]' in result["alternative_products"]

    @pytest.mark.asyncio
    async def test_extract_go_terms(self, transformer, mock_context):
        """Test extraction of GO terms."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "uniProtKBCrossReferences": [
                {
                    "database": "GO",
                    "id": "GO:0005524",
                    "properties": [
                        {"key": "GoTerm", "value": "F:ATP binding"},
                        {"key": "GoEvidenceType", "value": "IEA"},
                    ],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert '"id": "GO:0005524"' in result["go_terms"]
        assert '"term": "ATP binding"' in result["go_terms"]
        assert '"aspect": "F"' in result["go_terms"]
        assert '"evidence": "IEA"' in result["go_terms"]

    @pytest.mark.asyncio
    async def test_extract_drugbank_ids(self, transformer, mock_context):
        """Test extraction of DrugBank IDs."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "uniProtKBCrossReferences": [
                {"database": "DrugBank", "id": "DB00171"},
                {"database": "DrugBank", "id": "DB00734"},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["drugbank_ids"] == '["DB00171", "DB00734"]'

    @pytest.mark.asyncio
    async def test_extract_chembl_ids(self, transformer, mock_context):
        """Test extraction of ChEMBL IDs."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "uniProtKBCrossReferences": [
                {"database": "ChEMBL", "id": "CHEMBL4282"},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["chembl_ids"] == '["CHEMBL4282"]'

    @pytest.mark.asyncio
    async def test_extract_guidetopharmacology_ids(self, transformer, mock_context):
        """Test extraction of Guide to Pharmacology IDs."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "uniProtKBCrossReferences": [
                {"database": "GuidetoPHARMACOLOGY", "id": "1479"},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["guidetopharmacology_ids"] == '["1479"]'

    @pytest.mark.asyncio
    async def test_extract_features(self, transformer, mock_context):
        """Test extraction of sequence features."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "features": [
                {
                    "type": "Chain",
                    "description": "RAC-alpha serine/threonine-protein kinase",
                    "location": {
                        "start": {"value": 1},
                        "end": {"value": 480},
                    },
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["feature_count"] == 1
        assert '"type": "Chain"' in result["features"]
        assert '"start": 1' in result["features"]
        assert '"end": 480' in result["features"]

    @pytest.mark.asyncio
    async def test_extract_keywords(self, transformer, mock_context):
        """Test extraction of UniProt keywords."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "keywords": [
                {
                    "id": "KW-0067",
                    "category": "Molecular function",
                    "name": "ATP-binding",
                },
                {"id": "KW-0418", "category": "Biological process", "name": "Kinase"},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["keyword_count"] == 2
        assert '"id": "KW-0067"' in result["keywords"]
        assert '"name": "ATP-binding"' in result["keywords"]
        assert '"category": "Molecular function"' in result["keywords"]

    @pytest.mark.asyncio
    async def test_extract_sequence_info(self, transformer, mock_context):
        """Test extraction of sequence information."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "sequence": {
                "value": "MSDV" * 120,  # 480 amino acids
                "length": 480,
                "molWeight": 55686,
                "crc64": "C7E35E7E9B7C6B5A",
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["sequence_length"] == 480
        assert result["sequence_mass"] == 55686
        assert result["sequence_checksum"] == "C7E35E7E9B7C6B5A"
        assert result["sequence"] == "MSDV" * 120

    @pytest.mark.asyncio
    async def test_extract_counts(self, transformer, mock_context):
        """Test extraction of various counts."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "uniProtKBCrossReferences": [
                {"database": "GO", "id": "GO:0001"},
                {"database": "DrugBank", "id": "DB001"},
            ],
            "features": [{"type": "Chain"}, {"type": "Domain"}],
            "keywords": [{"id": "KW-0067"}],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cross_reference_count"] == 2
        assert result["feature_count"] == 2
        assert result["keyword_count"] == 1

    @pytest.mark.asyncio
    async def test_full_record_transformation(self, transformer, mock_context):
        """Test transformation of a comprehensive UniProt record."""
        record = {
            "entryType": "UniProtKB reviewed (Swiss-Prot)",
            "primaryAccession": "P31749",
            "secondaryAccessions": ["Q5TEV0"],
            "uniProtkbId": "AKT1_HUMAN",
            "annotationScore": 5,
            "proteinExistence": "1: Evidence at protein level",
            "organism": {
                "scientificName": "Homo sapiens",
                "commonName": "Human",
                "taxonId": 9606,
                "lineage": ["Eukaryota", "Metazoa"],
            },
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "RAC-alpha serine/threonine-protein kinase"},
                    "shortNames": [{"value": "AKT1"}],
                    "ecNumbers": [{"value": "2.7.11.1"}],
                },
                "alternativeNames": [{"fullName": {"value": "PKB alpha"}}],
                "flag": "Precursor",
            },
            "genes": [{"geneName": {"value": "AKT1"}, "synonyms": [{"value": "PKB"}]}],
            "comments": [
                {
                    "commentType": "FUNCTION",
                    "texts": [{"value": "Serine/threonine kinase."}],
                },
                {
                    "commentType": "SUBCELLULAR LOCATION",
                    "subcellularLocations": [{"location": {"value": "Cytoplasm"}}],
                },
            ],
            "uniProtKBCrossReferences": [
                {
                    "database": "GO",
                    "id": "GO:0005524",
                    "properties": [{"key": "GoTerm", "value": "F:ATP binding"}],
                },
                {"database": "ChEMBL", "id": "CHEMBL4282"},
            ],
            "features": [
                {
                    "type": "Chain",
                    "location": {"start": {"value": 1}, "end": {"value": 480}},
                }
            ],
            "keywords": [{"id": "KW-0067", "name": "ATP-binding"}],
            "sequence": {"value": "MSDV", "length": 480, "molWeight": 55686},
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Core identifiers
        assert result["accession"] == "P31749"
        assert result["entry_name"] == "AKT1_HUMAN"
        assert result["entry_type"] == "UniProtKB reviewed (Swiss-Prot)"
        assert result["reviewed"] is True
        assert result["annotation_score"] == 5
        # Organism
        assert result["organism_scientific"] == "Homo sapiens"
        assert result["taxonomy_id"] == 9606
        # Protein names
        assert result["protein_name"] == "RAC-alpha serine/threonine-protein kinase"
        assert result["protein_short_names"] == '["AKT1"]'
        assert result["flag"] == "Precursor"
        # Functional annotations
        assert result["function_comment"] == '["Serine/threonine kinase."]'
        assert result["subcellular_location"] == '["Cytoplasm"]'
        # Cross-references
        assert '"GO:0005524"' in result["go_terms"]
        assert result["chembl_ids"] == '["CHEMBL4282"]'
        # Counts
        assert result["cross_reference_count"] == 2
        assert result["feature_count"] == 1
        assert result["keyword_count"] == 1
