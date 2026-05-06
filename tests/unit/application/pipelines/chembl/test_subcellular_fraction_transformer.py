"""Unit tests for ChEMBL Subcellular Fraction transformer.

Tests for the derived entity transformer that extracts unique
subcellular fractions from Assay records.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.chembl.subcellular_fraction_transformer import (
    SubcellularFractionTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def transformer() -> SubcellularFractionTransformer:
    """Create transformer instance."""
    return SubcellularFractionTransformer(
        dependencies=build_test_transformer_dependencies()
    )


@pytest.mark.unit
class TestSubcellularFractionTransformer:
    """Tests for SubcellularFractionTransformer."""

    @pytest.mark.asyncio
    async def test_transform_valid_record(
        self,
        transformer: SubcellularFractionTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Transformer should recompute entity_id from canonical fraction semantics."""
        record = {
            "entity_id": "a1b2c3d4e5f67890",
            "subcellular_fraction": "Microsomes",
            "assay_count": 42,
            "example_assay_id": "CHEMBL123456",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["subcellular_fraction"] == "Microsomes"
        assert result["assay_count"] == 42
        assert result["example_assay_id"] == "CHEMBL123456"
        assert result["entity_id"] == transformer.compute_fraction_entity_id(
            "Microsomes"
        )
        assert "content_hash" in result
        assert result["_run_id"] == str(mock_context.run_id)
        assert result["_run_type"] == mock_context.run_type.value
        assert "_ingestion_ts" in result

    @pytest.mark.asyncio
    async def test_transform_record_without_entity_id(
        self,
        transformer: SubcellularFractionTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test transformation computes entity_id when not provided."""
        record = {
            "subcellular_fraction": "Cytosol",
            "assay_count": 10,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["subcellular_fraction"] == "Cytosol"
        # entity_id should be computed
        assert "entity_id" in result
        assert len(result["entity_id"]) == 16  # SHA256 prefix

    @pytest.mark.asyncio
    async def test_transform_missing_primary_key(
        self,
        transformer: SubcellularFractionTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test transformation returns None for missing primary key."""
        record: dict[str, str] = {}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_empty_fraction(
        self,
        transformer: SubcellularFractionTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test transformation returns None for empty fraction."""
        record = {
            "subcellular_fraction": "",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_whitespace_fraction(
        self,
        transformer: SubcellularFractionTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test transformation returns None for whitespace-only fraction."""
        record = {
            "subcellular_fraction": "   ",
        }

        result = await transformer.transform(mock_context, record, index=0)

        # After strip(), empty string should be rejected
        assert result is None

    @pytest.mark.asyncio
    async def test_content_hash_deterministic(
        self,
        transformer: SubcellularFractionTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test content_hash is deterministic for same input."""
        record = {
            "subcellular_fraction": "Mitochondria",
            "assay_count": 5,
        }

        result1 = await transformer.transform(mock_context, record, index=0)
        result2 = await transformer.transform(mock_context, record, index=0)

        assert result1 is not None
        assert result2 is not None
        assert result1["content_hash"] == result2["content_hash"]

    @pytest.mark.asyncio
    async def test_entity_id_deterministic(
        self,
        transformer: SubcellularFractionTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test entity_id is deterministic for same fraction name."""
        record1 = {"subcellular_fraction": "Membrane"}
        record2 = {"subcellular_fraction": "Membrane"}

        result1 = await transformer.transform(mock_context, record1, index=0)
        result2 = await transformer.transform(mock_context, record2, index=1)

        assert result1 is not None
        assert result2 is not None
        assert result1["entity_id"] == result2["entity_id"]

    @pytest.mark.asyncio
    async def test_entity_id_case_insensitive(
        self,
        transformer: SubcellularFractionTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test entity_id is case-insensitive (normalized to lowercase)."""
        record1 = {"subcellular_fraction": "Microsomes"}
        record2 = {"subcellular_fraction": "MICROSOMES"}
        record3 = {"subcellular_fraction": "microsomes"}

        result1 = await transformer.transform(mock_context, record1, index=0)
        result2 = await transformer.transform(mock_context, record2, index=1)
        result3 = await transformer.transform(mock_context, record3, index=2)

        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        # All should produce the same entity_id
        assert result1["entity_id"] == result2["entity_id"] == result3["entity_id"]

    @pytest.mark.asyncio
    async def test_fraction_trimmed(
        self,
        transformer: SubcellularFractionTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test whitespace is trimmed from fraction name."""
        record = {"subcellular_fraction": "  Cytosol  "}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["subcellular_fraction"] == "Cytosol"

    @pytest.mark.asyncio
    async def test_optional_fields_null(
        self,
        transformer: SubcellularFractionTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test transformation with optional fields as None."""
        record = {
            "subcellular_fraction": "S9 fraction",
            "assay_count": None,
            "example_assay_id": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["subcellular_fraction"] == "S9 fraction"
        assert result["assay_count"] is None
        assert result["example_assay_id"] is None

    @pytest.mark.asyncio
    async def test_transform_pre_silver_extracts_fraction_from_assay(
        self,
        transformer: SubcellularFractionTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Staged path should support assay-derived fraction payloads."""
        record = {
            "assay_id": "CHEMBL123456",
            "assay_subcellular_fraction": "  Microsomes  ",
        }

        result = await transformer.transform_pre_silver(mock_context, record, index=0)

        assert isinstance(result, PreSilverRecord)
        assert result.business_data["subcellular_fraction"] == "Microsomes"
        assert result.business_data["example_assay_id"] == "CHEMBL123456"
        assert result.business_data["assay_count"] == 1
        assert "content_hash" not in result.business_data

    @pytest.mark.asyncio
    async def test_transform_pre_silver_recomputes_entity_id_from_canonical_fraction(
        self,
        transformer: SubcellularFractionTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Staged identity should ignore stale upstream ids and use canonical fraction."""
        record = {
            "entity_id": "deadbeefdeadbeef",
            "subcellular_fraction": "  MICROSOMES  ",
        }

        result = await transformer.transform_pre_silver(mock_context, record, index=0)

        assert isinstance(result, PreSilverRecord)
        assert result.entity_id == transformer.compute_fraction_entity_id("Microsomes")

    @pytest.mark.asyncio
    async def test_transform_matches_staged_finalization_for_assay_input(
        self,
        transformer: SubcellularFractionTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Legacy subcellular-fraction transform should match staged finalization."""
        record = {
            "assay_id": "CHEMBL123456",
            "assay_subcellular_fraction": "  Microsomes  ",
        }

        pre_silver = await transformer.transform_pre_silver(
            mock_context, record, index=0
        )
        assert isinstance(pre_silver, PreSilverRecord)
        staged_result = RecordNormalizationProcessor(
            provider=transformer.provider,
        ).finalize_pre_silver(pre_silver, mock_context, 0)
        legacy_result = await transformer.transform(mock_context, record, index=0)

        assert staged_result is not None
        assert legacy_result is not None
        assert (
            legacy_result["subcellular_fraction"]
            == staged_result["subcellular_fraction"]
        )
        assert legacy_result["example_assay_id"] == staged_result["example_assay_id"]
        assert legacy_result["assay_count"] == staged_result["assay_count"]
        assert legacy_result["entity_id"] == staged_result["entity_id"]
        assert legacy_result["content_hash"] == staged_result["content_hash"]


@pytest.mark.unit
class TestComputeFractionEntityId:
    """Tests for the compute_fraction_entity_id method."""

    @pytest.fixture
    def transformer(self) -> SubcellularFractionTransformer:
        """Create transformer instance."""
        return SubcellularFractionTransformer(
            dependencies=build_test_transformer_dependencies()
        )

    def test_basic_computation(
        self,
        transformer: SubcellularFractionTransformer,
    ) -> None:
        """Test basic entity_id computation."""
        entity_id = transformer.compute_fraction_entity_id("Microsomes")

        assert entity_id is not None
        assert len(entity_id) == 16
        # Should be hex characters only
        assert all(c in "0123456789abcdef" for c in entity_id)

    def test_deterministic(
        self,
        transformer: SubcellularFractionTransformer,
    ) -> None:
        """Test entity_id computation is deterministic."""
        id1 = transformer.compute_fraction_entity_id("Cytosol")
        id2 = transformer.compute_fraction_entity_id("Cytosol")

        assert id1 == id2

    def test_case_insensitive(
        self,
        transformer: SubcellularFractionTransformer,
    ) -> None:
        """Canonical governed vocabulary should keep ids stable across case variants."""
        id1 = transformer.compute_fraction_entity_id("Membrane")
        id2 = transformer.compute_fraction_entity_id("MEMBRANE")
        id3 = transformer.compute_fraction_entity_id("membrane")

        assert id1 == id2 == id3

    def test_whitespace_normalized(
        self,
        transformer: SubcellularFractionTransformer,
    ) -> None:
        """Test whitespace is normalized."""
        id1 = transformer.compute_fraction_entity_id("Microsomes")
        id2 = transformer.compute_fraction_entity_id("  Microsomes  ")

        assert id1 == id2

    def test_different_fractions_different_ids(
        self,
        transformer: SubcellularFractionTransformer,
    ) -> None:
        """Test different fractions produce different entity_ids."""
        id1 = transformer.compute_fraction_entity_id("Microsomes")
        id2 = transformer.compute_fraction_entity_id("Cytosol")
        id3 = transformer.compute_fraction_entity_id("Mitochondria")

        assert id1 != id2
        assert id2 != id3
        assert id1 != id3


@pytest.mark.unit
class TestExtractFractionFromAssay:
    """Tests for the extract_fraction_from_assay method."""

    @pytest.fixture
    def transformer(self) -> SubcellularFractionTransformer:
        """Create transformer instance."""
        return SubcellularFractionTransformer(
            dependencies=build_test_transformer_dependencies()
        )

    def test_extract_valid_fraction(
        self,
        transformer: SubcellularFractionTransformer,
    ) -> None:
        """Test extraction from valid assay record."""
        assay = {
            "assay_id": "CHEMBL123456",
            "assay_subcellular_fraction": "Microsomes",
        }

        result = transformer.extract_fraction_from_assay(assay)

        assert result is not None
        assert result["subcellular_fraction"] == "Microsomes"
        assert result["example_assay_id"] == "CHEMBL123456"
        assert result["assay_count"] == 1

    def test_extract_missing_fraction(
        self,
        transformer: SubcellularFractionTransformer,
    ) -> None:
        """Test extraction returns None when fraction is missing."""
        assay = {
            "assay_id": "CHEMBL123456",
            # No assay_subcellular_fraction field
        }

        result = transformer.extract_fraction_from_assay(assay)

        assert result is None

    def test_extract_empty_fraction(
        self,
        transformer: SubcellularFractionTransformer,
    ) -> None:
        """Test extraction returns None when fraction is empty."""
        assay = {
            "assay_id": "CHEMBL123456",
            "assay_subcellular_fraction": "",
        }

        result = transformer.extract_fraction_from_assay(assay)

        assert result is None

    def test_extract_none_fraction(
        self,
        transformer: SubcellularFractionTransformer,
    ) -> None:
        """Test extraction returns None when fraction is None."""
        assay = {
            "assay_id": "CHEMBL123456",
            "assay_subcellular_fraction": None,
        }

        result = transformer.extract_fraction_from_assay(assay)

        assert result is None

    def test_extract_whitespace_fraction(
        self,
        transformer: SubcellularFractionTransformer,
    ) -> None:
        """Test extraction returns None for whitespace-only fraction."""
        assay = {
            "assay_id": "CHEMBL123456",
            "assay_subcellular_fraction": "   ",
        }

        result = transformer.extract_fraction_from_assay(assay)

        assert result is None

    def test_extract_missing_assay_id(
        self,
        transformer: SubcellularFractionTransformer,
    ) -> None:
        """Test extraction works without assay_id."""
        assay = {
            "assay_subcellular_fraction": "Cytosol",
        }

        result = transformer.extract_fraction_from_assay(assay)

        assert result is not None
        assert result["subcellular_fraction"] == "Cytosol"
        assert result["example_assay_id"] is None
