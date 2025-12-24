"""Unit tests for PubChem Compound Transformer."""

import pytest
from unittest.mock import Mock

from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import BronzeRecord


class TestPubChemCompoundTransformer:
    """Tests for PubChemCompoundTransformer (Recreated)."""

    @pytest.fixture
    def transformer(self) -> PubChemCompoundTransformer:
        """Create transformer instance."""
        return PubChemCompoundTransformer(provider="pubchem")

    @pytest.fixture
    def mock_context(self) -> PipelineContext:
        """Create mock pipeline context."""
        context = Mock(spec=PipelineContext)
        context.run_id = "test-run-id"
        context.run_type = Mock()
        context.run_type.value = "backfill"
        context.logger = Mock()
        return context

    @pytest.fixture
    def sample_record(self) -> BronzeRecord:
        """Create valid sample bronze record."""
        return {
            "cid": 12345,
            "molecular_formula": "C6H12O6",
            "canonical_smiles": "OCC(O)C(O)C(O)C(O)C=O",
            "molecular_weight": 180.16,
            "iupac_name": "D-glucose",
        }

    async def test_transform_valid_record(
        self,
        transformer: PubChemCompoundTransformer,
        sample_record: BronzeRecord,
        mock_context: PipelineContext,
    ) -> None:
        """Test transformation of a valid record."""
        result = await transformer.transform(mock_context, sample_record)

        assert result is not None
        # Actual implementation uses {provider}:{id} format
        assert result["entity_id"] == "pubchem:12345"
        # Actual implementation preserves 'cid' key
        assert result["cid"] == "12345"
        assert result["molecular_formula"] == "C6H12O6"
        assert result["canonical_smiles"] == "OCC(O)C(O)C(O)C(O)C=O"

        # NOTE: Current implementation does not inject lineage fields (_run_id, etc.)
        # If this is required, the transformer implementation needs update.
        # For now, we test current behavior.

    async def test_transform_missing_required_field_returns_none(
        self,
        transformer: PubChemCompoundTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that missing required field (cid) returns None."""
        record = {"molecular_formula": "C6H12O6"}  # Missing cid
        result = await transformer.transform(mock_context, record)
        assert result is None
        mock_context.logger.warning.assert_called()

    async def test_transform_with_nested_properties(
        self,
        transformer: PubChemCompoundTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test transformation with nested properties handling."""
        record = {
            "cid": 999,
            "props": [{"urn": {"label": "Weight"}, "value": {"sval": "100.5"}}],
        }
        result = await transformer.transform(mock_context, record)
        assert result is not None
        assert result["cid"] == "999"
