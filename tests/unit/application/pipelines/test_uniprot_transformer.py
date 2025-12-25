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

        result = await transformer.transform(mock_context, record)

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

        result = await transformer.transform(mock_context, record)

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

        result = await transformer.transform(mock_context, record)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_missing_protein_name(self, transformer, mock_context):
        """Test transformation returns None when protein name path is missing."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "proteinDescription": {},  # No recommendedName
        }

        result = await transformer.transform(mock_context, record)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_with_minimal_valid_record(
        self, transformer, mock_context
    ):
        """Test transformation with minimal valid record (required fields only)."""
        record = {
            "primaryAccession": "Q99999",
            "uniProtkbId": "MIN_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Minimal Protein"}}
            },
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert result["accession"] == "Q99999"
        assert result["entry_name"] == "MIN_HUMAN"
        assert result["protein_name"] == "Minimal Protein"
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

        result = await transformer.transform(mock_context, record)

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

        result = await transformer.transform(mock_context, record)

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

        result = await transformer.transform(mock_context, record)

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

        result = await transformer.transform(mock_context, record)

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

        result1 = await transformer.transform(mock_context, record)
        result2 = await transformer.transform(mock_context, record)

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

        result = await transformer.transform(mock_context, record)

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

        result = await transformer.transform(mock_context, record)

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

        result = await transformer.transform(mock_context, record)

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

        result = await transformer.transform(mock_context, record)

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

        result = await transformer.transform(mock_context, record)

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
                "recommendedName": {
                    "fullName": {"value": "Deeply Nested Protein Name"}
                }
            },
        }

        result = await transformer.transform(mock_context, record)

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

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert result["organism_id"] == 10090
