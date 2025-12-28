"""Unit tests for GtoPdb transformers."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.gtopdb.interaction_transformer import (
    GtopdbInteractionTransformer,
)
from bioetl.application.pipelines.gtopdb.ligand_transformer import (
    GtopdbLigandTransformer,
)
from bioetl.application.pipelines.gtopdb.target_transformer import (
    GtopdbTargetTransformer,
)
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
class TestGtopdbTargetTransformer:
    """Tests for GtopdbTargetTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create GtopdbTargetTransformer instance."""
        return GtopdbTargetTransformer(provider="gtopdb")

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid target record with all fields."""
        record = {
            "targetId": 1,
            "name": "5-HT1A receptor",
            "abbreviation": "5-HT1A",
            "systematicName": "5-hydroxytryptamine receptor 1A",
            "type": "gpcr",
            "familyId": 1,
            "familyName": "5-Hydroxytryptamine receptors",
            "familyIds": [1, 2],
            "species": "Human",
            "speciesId": 9606,
            "geneSymbol": "HTR1A",
            "geneId": 3350,
            "ensemblGeneId": "ENSG00000178394",
            "uniprotIds": ["P08908"],
            "hgncId": 5286,
            "hgncSymbol": "HTR1A",
            "hgncName": "5-hydroxytryptamine receptor 1A",
            "nomenclatureStatus": "approved",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["target_id"] == 1
        assert result["name"] == "5-HT1A receptor"
        assert result["abbreviation"] == "5-HT1A"
        assert result["target_type"] == "gpcr"
        assert result["species"] == "Human"
        assert result["gene_symbol"] == "HTR1A"
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_ingestion_ts" in result

    @pytest.mark.asyncio
    async def test_transform_missing_target_id(self, transformer, mock_context):
        """Test transformation returns None when targetId is missing."""
        record = {
            "name": "5-HT1A receptor",
            "species": "Human",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_minimal_valid_record(self, transformer, mock_context):
        """Test transformation with minimal valid record (only targetId)."""
        record = {
            "targetId": 123,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["target_id"] == 123
        assert result["name"] is None
        assert result["species"] is None

    @pytest.mark.asyncio
    async def test_transform_entity_id_format(self, transformer, mock_context):
        """Test that entity_id follows expected format."""
        record = {
            "targetId": 42,
            "name": "Test Target",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result
        assert "gtopdb" in result["entity_id"]
        assert "42" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_transform_content_hash_consistent(self, transformer, mock_context):
        """Test that content_hash is consistent for same record."""
        record = {
            "targetId": 1,
            "name": "Test Target",
            "species": "Human",
        }

        result1 = await transformer.transform(mock_context, record, index=0)
        result2 = await transformer.transform(mock_context, record, index=0)

        assert result1 is not None
        assert result2 is not None
        assert result1["content_hash"] == result2["content_hash"]

    @pytest.mark.asyncio
    async def test_transform_json_serialization(self, transformer, mock_context):
        """Test that list fields are serialized to JSON."""
        record = {
            "targetId": 1,
            "familyIds": [1, 2, 3],
            "uniprotIds": ["P08908", "Q12345"],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # JSON serialized lists
        assert result["family_ids"] is not None
        assert result["uniprot_ids"] is not None


@pytest.mark.unit
class TestGtopdbLigandTransformer:
    """Tests for GtopdbLigandTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create GtopdbLigandTransformer instance."""
        return GtopdbLigandTransformer(provider="gtopdb")

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid ligand record with all fields."""
        record = {
            "ligandId": 1,
            "name": "aspirin",
            "type": "Synthetic organic",
            "approved": True,
            "withdrawn": False,
            "labelled": False,
            "radioactive": False,
            "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12",
            "inchiKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            "iupacName": "2-acetoxybenzoic acid",
            "inn": "aspirin",
            "approvedSource": "FDA",
            "pubchemSid": 46507011,
            "pubchemCid": 2244,
            "chemblId": "CHEMBL25",
            "drugbankId": "DB00945",
            "casNumber": "50-78-2",
            "comments": "Aspirin is a widely used medication.",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["ligand_id"] == 1
        assert result["name"] == "aspirin"
        assert result["ligand_type"] == "Synthetic organic"
        assert result["approved"] is True
        assert result["smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"
        assert result["chembl_id"] == "CHEMBL25"
        assert "entity_id" in result
        assert "content_hash" in result

    @pytest.mark.asyncio
    async def test_transform_missing_ligand_id(self, transformer, mock_context):
        """Test transformation returns None when ligandId is missing."""
        record = {
            "name": "aspirin",
            "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_minimal_valid_record(self, transformer, mock_context):
        """Test transformation with minimal valid record (only ligandId)."""
        record = {
            "ligandId": 456,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["ligand_id"] == 456
        assert result["name"] is None
        assert result["smiles"] is None

    @pytest.mark.asyncio
    async def test_transform_boolean_fields(self, transformer, mock_context):
        """Test that boolean fields are properly converted."""
        record = {
            "ligandId": 1,
            "approved": "true",
            "withdrawn": "false",
            "labelled": True,
            "radioactive": 0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["approved"] is True
        assert result["withdrawn"] is False
        assert result["labelled"] is True
        assert result["radioactive"] is False

    @pytest.mark.asyncio
    async def test_transform_entity_id_format(self, transformer, mock_context):
        """Test that entity_id follows expected format."""
        record = {
            "ligandId": 999,
            "name": "Test Ligand",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result
        assert "gtopdb" in result["entity_id"]
        assert "999" in result["entity_id"]


@pytest.mark.unit
class TestGtopdbInteractionTransformer:
    """Tests for GtopdbInteractionTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create GtopdbInteractionTransformer instance."""
        return GtopdbInteractionTransformer(provider="gtopdb")

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid interaction record with all fields."""
        record = {
            "interactionId": 1,
            "targetId": 42,
            "ligandId": 101,
            "type": "Agonist",
            "action": "Activation",
            "actionComment": "Full agonist",
            "selectivity": "Selective",
            "affinityParameter": "pKi",
            "affinityValue": 8.5,
            "affinityLow": 8.0,
            "affinityHigh": 9.0,
            "affinityMedian": 8.5,
            "affinityUnits": "M",
            "affinityQualifier": "=",
            "species": "Human",
            "speciesId": 9606,
            "endogenous": False,
            "primaryTarget": True,
            "pubmedIds": [12345678, 87654321],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["interaction_id"] == 1
        assert result["target_id"] == 42
        assert result["ligand_id"] == 101
        assert result["interaction_type"] == "Agonist"
        assert result["action"] == "Activation"
        assert result["affinity_type"] == "pKi"
        assert result["affinity_value"] == 8.5
        assert result["species"] == "Human"
        assert "entity_id" in result
        assert "content_hash" in result

    @pytest.mark.asyncio
    async def test_transform_missing_interaction_id(self, transformer, mock_context):
        """Test transformation returns None when interactionId is missing."""
        record = {
            "targetId": 42,
            "ligandId": 101,
            "type": "Agonist",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_missing_target_id(self, transformer, mock_context):
        """Test transformation returns None when targetId is missing."""
        record = {
            "interactionId": 1,
            "ligandId": 101,
            "type": "Agonist",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_missing_ligand_id(self, transformer, mock_context):
        """Test transformation returns None when ligandId is missing."""
        record = {
            "interactionId": 1,
            "targetId": 42,
            "type": "Agonist",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_minimal_valid_record(self, transformer, mock_context):
        """Test transformation with minimal valid record."""
        record = {
            "interactionId": 1,
            "targetId": 42,
            "ligandId": 101,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["interaction_id"] == 1
        assert result["target_id"] == 42
        assert result["ligand_id"] == 101
        assert result["interaction_type"] is None
        assert result["affinity_value"] is None

    @pytest.mark.asyncio
    async def test_transform_float_fields(self, transformer, mock_context):
        """Test that float fields are properly converted."""
        record = {
            "interactionId": 1,
            "targetId": 42,
            "ligandId": 101,
            "affinityValue": "8.5",
            "affinityLow": 8,
            "affinityHigh": "9.0",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["affinity_value"] == 8.5
        assert result["affinity_low"] == 8.0
        assert result["affinity_high"] == 9.0

    @pytest.mark.asyncio
    async def test_transform_entity_id_format(self, transformer, mock_context):
        """Test that entity_id follows expected format."""
        record = {
            "interactionId": 777,
            "targetId": 42,
            "ligandId": 101,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result
        assert "gtopdb" in result["entity_id"]
        assert "777" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_transform_pubmed_ids_serialized(self, transformer, mock_context):
        """Test that pubmedIds list is serialized to JSON."""
        record = {
            "interactionId": 1,
            "targetId": 42,
            "ligandId": 101,
            "pubmedIds": [12345678, 87654321],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pubmed_ids"] is not None
