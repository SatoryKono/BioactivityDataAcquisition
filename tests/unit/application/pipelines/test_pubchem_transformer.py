"""Unit tests for PubChem Compound transformer."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.transformations import safe_float
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
class TestPubChemCompoundTransformer:
    """Tests for PubChemCompoundTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create PubChemCompoundTransformer instance."""
        return PubChemCompoundTransformer(provider="pubchem")

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid compound record with all fields."""
        record = {
            "cid": 2244,
            "molecular_formula": "C9H8O4",
            "molecular_weight": "180.16",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "isomeric_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
            "inchikey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            "iupac_name": "2-acetoxybenzoic acid",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cid"] == "2244"
        assert result["molecular_formula"] == "C9H8O4"
        assert result["canonical_smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"
        assert result["inchikey"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
        assert "entity_id" in result
        assert "content_hash" in result
        # Lineage fields should be present
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_ingestion_ts" in result

    @pytest.mark.asyncio
    async def test_transform_missing_cid(self, transformer, mock_context):
        """Test transformation returns None when cid is missing."""
        record = {
            "molecular_formula": "C9H8O4",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_missing_structural_identifiers(
        self, transformer, mock_context
    ):
        """Test transformation returns None when no structural identifiers present.

        Compound entity invariant requires at least one of:
        canonical_smiles, isomeric_smiles, or inchi.
        """
        record = {
            "cid": 12345,
            "molecular_formula": "C10H12O2",
            "iupac_name": "Some compound",
            # Missing: canonical_smiles, isomeric_smiles, inchi
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_with_only_canonical_smiles(
        self, transformer, mock_context
    ):
        """Test transformation succeeds with only canonical_smiles."""
        record = {
            "cid": 12345,
            "canonical_smiles": "CCO",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cid"] == "12345"
        assert result["canonical_smiles"] == "CCO"

    @pytest.mark.asyncio
    async def test_transform_with_only_isomeric_smiles(self, transformer, mock_context):
        """Test transformation succeeds with only isomeric_smiles."""
        record = {
            "cid": 12345,
            "isomeric_smiles": "C[C@H](O)CC",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cid"] == "12345"
        assert result["isomeric_smiles"] == "C[C@H](O)CC"

    @pytest.mark.asyncio
    async def test_transform_with_only_inchi(self, transformer, mock_context):
        """Test transformation succeeds with only inchi."""
        record = {
            "cid": 12345,
            "inchi": "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cid"] == "12345"
        assert result["inchi"] == "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"

    @pytest.mark.asyncio
    async def test_transform_with_minimal_valid_record(self, transformer, mock_context):
        """Test transformation with minimal valid record (cid + one structural ID)."""
        record = {
            "cid": 1,
            "canonical_smiles": "C",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cid"] == "1"
        assert result["canonical_smiles"] == "C"
        assert result.get("molecular_formula") is None
        assert result.get("molecular_weight") is None
        assert result.get("inchikey") is None

    @pytest.mark.asyncio
    async def test_transform_cid_converted_to_string(self, transformer, mock_context):
        """Test that numeric cid is converted to string."""
        record = {
            "cid": 99999999,
            "canonical_smiles": "C",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cid"] == "99999999"
        assert isinstance(result["cid"], str)

    @pytest.mark.asyncio
    async def test_transform_entity_id_format(self, transformer, mock_context):
        """Test that entity_id follows expected format."""
        record = {
            "cid": 2244,
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result
        # Entity ID should contain provider and cid
        assert "pubchem" in result["entity_id"]
        assert "2244" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_transform_content_hash_generated(self, transformer, mock_context):
        """Test that content_hash is generated and is consistent."""
        record = {
            "cid": 2244,
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
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
        transformer = PubChemCompoundTransformer(provider="custom_pubchem")
        record = {
            "cid": 123,
            "canonical_smiles": "C",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "custom_pubchem" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_transform_empty_cid_rejected(self, transformer, mock_context):
        """Test that empty string cid is rejected."""
        record = {
            "cid": "",
            "canonical_smiles": "C",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_lineage_fields_present(self, transformer, mock_context):
        """Test that lineage fields are properly added to the result."""
        record = {
            "cid": 2244,
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
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
    async def test_transform_molecular_weight_float_conversion(
        self, transformer, mock_context
    ):
        """Test that molecular_weight is converted from string to float."""
        record = {
            "cid": 2244,
            "molecular_formula": "C9H8O4",
            "molecular_weight": "180.156",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["molecular_weight"] == 180.156
        assert isinstance(result["molecular_weight"], float)

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_numeric_input(
        self, transformer, mock_context
    ):
        """Test that numeric molecular_weight is preserved as float."""
        record = {
            "cid": 2244,
            "molecular_weight": 180.156,
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["molecular_weight"] == 180.156
        assert isinstance(result["molecular_weight"], float)

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_none(self, transformer, mock_context):
        """Test that None molecular_weight is preserved as None."""
        record = {
            "cid": 2244,
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            # molecular_weight not provided
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("molecular_weight") is None

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_empty_string(
        self, transformer, mock_context
    ):
        """Test that empty string molecular_weight becomes None."""
        record = {
            "cid": 2244,
            "molecular_weight": "",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("molecular_weight") is None

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_invalid_string(
        self, transformer, mock_context
    ):
        """Test that invalid string molecular_weight becomes None."""
        record = {
            "cid": 2244,
            "molecular_weight": "invalid",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("molecular_weight") is None

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_negative(self, transformer, mock_context):
        """Test that negative molecular_weight becomes None."""
        record = {
            "cid": 2244,
            "molecular_weight": "-5.0",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("molecular_weight") is None

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_zero(self, transformer, mock_context):
        """Test that zero molecular_weight returns None (invalid: must be > 0)."""
        record = {
            "cid": 2244,
            "molecular_weight": "0",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Zero MW is invalid per validate_molecular_weight (range: 0 < mw < 100000)
        assert result["molecular_weight"] is None

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_precision(
        self, transformer, mock_context
    ):
        """Test that molecular_weight precision is preserved up to 10 decimal places."""
        record = {
            "cid": 2244,
            "molecular_weight": "1234.5678901234",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Should be rounded to 10 decimal places
        assert abs(result["molecular_weight"] - 1234.5678901234) < 1e-10


@pytest.mark.unit
class TestSafeFloatConversion:
    """Tests for safe_float conversion function."""

    @pytest.mark.parametrize(
        "input_mw,expected",
        [
            ("180.156", 180.156),
            ("0", 0.0),
            ("1234.5678901234", 1234.5678901234),
            ("", None),
            (None, None),
            ("invalid", None),
            ("-5.0", -5.0),  # safe_float converts, transformer filters negative
            (180.156, 180.156),
            (0, 0.0),
        ],
    )
    def test_molecular_weight_conversion(self, input_mw, expected):
        """Test safe_float conversion for molecular weight values."""
        result = safe_float(input_mw)
        if expected is None:
            assert result is None
        else:
            assert abs(result - expected) < 1e-10
