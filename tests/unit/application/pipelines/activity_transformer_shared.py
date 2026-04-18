"""Shared test fixtures and mixins for activity transformer unit suites."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.chembl.activity_transformer import (
    ActivityTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


@pytest.fixture
def transformer() -> ActivityTransformer:
    """Fixture for ActivityTransformer instance."""
    return ActivityTransformer(
        provider="chembl", dependencies=build_test_transformer_dependencies()
    )


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


class SharedActivityTransformerTransformTests:
    """Common transform-path assertions shared across activity transformer suites."""

    require_full_run_metadata = False

    def _assert_valid_record_metadata(
        self,
        result: dict[str, object],
        mock_context: PipelineContext,
    ) -> None:
        assert "_run_id" in result
        if self.require_full_run_metadata:
            assert result["_run_id"] == str(mock_context.run_id)
            assert result["_run_type"] == mock_context.run_type.value
            assert "_ingestion_ts" in result

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid activity record."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "target_id": "CHEMBL1862",
            "assay_id": "CHEMBL1234567",
            "standard_type": "IC50",
            "standard_value": 10.5,
            "standard_units": "nM",
            "pchembl_value": 8.0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["activity_id"] == "12345"
        assert result["molecule_id"] == "CHEMBL25"
        assert result["target_id"] == "CHEMBL1862"
        assert result["standard_type"] == "IC50"
        assert result["standard_value"] == pytest.approx(10.5)
        assert result["pchembl_value"] == pytest.approx(8.0)
        assert "entity_id" in result
        assert "content_hash" in result
        self._assert_valid_record_metadata(result, mock_context)

    @pytest.mark.asyncio
    async def test_transform_missing_activity_id(self, transformer, mock_context):
        """Test transformation returns None when activity_id is missing."""
        record = {
            "molecule_id": "CHEMBL25",
            "target_id": "CHEMBL1862",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_missing_molecule_id(self, transformer, mock_context):
        """Test transformation returns None when molecule_id is missing."""
        record = {
            "activity_id": 12345,
            "target_id": "CHEMBL1862",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_with_ligand_efficiency(self, transformer, mock_context):
        """Test transformation with ligand efficiency data."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "ligand_efficiency": {
                "bei": "14.06",
                "le": "0.26",
                "lle": "1.30",
                "sei": "5.56",
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["ligand_efficiency_bei"] == pytest.approx(14.06)
        assert result["ligand_efficiency_le"] == pytest.approx(0.26)
        assert result["ligand_efficiency_lle"] == pytest.approx(1.30)
        assert result["ligand_efficiency_sei"] == pytest.approx(5.56)

    @pytest.mark.asyncio
    async def test_transform_with_all_core_fields(self, transformer, mock_context):
        """Test transformation with all core activity fields."""
        record = {
            "activity_id": 99999,
            "molecule_id": "CHEMBL25",
            "target_id": "CHEMBL1862",
            "assay_id": "CHEMBL123",
            "publication_id": "CHEMBL456",
            "record_id": 100,
            "src_id": 1,
            "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
            "molecule_pref_name": "ASPIRIN",
            "parent_molecule_id": "CHEMBL25",
            "target_pref_name": "Cyclooxygenase-2",
            "target_organism": "Homo sapiens",
            "target_tax_id": 9606,
            "assay_type": "B",
            "assay_description": "Binding assay",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
        assert result["molecule_pref_name"] == "ASPIRIN"
        assert result["target_pref_name"] == "Cyclooxygenase-2"
        assert result["target_organism"] == "Homo sapiens"
        assert result["target_taxonomy_id"] == 9606
        assert result["assay_type"] == "B"

    @pytest.mark.asyncio
    async def test_transform_with_activity_values(self, transformer, mock_context):
        """Test transformation with raw and standardized activity values."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "type": "IC50",
            "value": 10.5,
            "units": "nM",
            "relation": "=",
            "upper_value": 20.0,
            "text_value": "Active",
            "standard_type": "IC50",
            "standard_value": 10.5,
            "standard_units": "nM",
            "standard_relation": "=",
            "standard_upper_value": 20.0,
            "standard_text_value": "Active",
            "standard_flag": 1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["type"] == "IC50"
        assert result["value"] == pytest.approx(10.5)
        assert result["standard_value"] == pytest.approx(10.5)
        assert result["standard_flag"] == 1

    @pytest.mark.asyncio
    async def test_transform_with_quality_annotations(self, transformer, mock_context):
        """Test transformation with data quality annotations."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "activity_comment": "Potent inhibitor",
            "data_validity_comment": "Valid",
            "data_validity_description": "Data passed validation",
            "potential_duplicate": 0,
            "manual_curation_flag": 1,
            "original_activity_id": 98765,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["activity_comment"] == "Potent inhibitor"
        assert result["data_validity_comment"] == "Valid"
        assert result["data_validity_description"] == "Data passed validation"
        assert result["potential_duplicate"] == 0
        assert result["manual_curation_flag"] == 1
        assert result["original_activity_id"] == 98765

    @pytest.mark.asyncio
    async def test_transform_with_curation_fields_null(self, transformer, mock_context):
        """Test transformation handles nullable curation fields."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["manual_curation_flag"] is None
        assert result["original_activity_id"] is None
        assert result["data_validity_description"] is None

    @pytest.mark.asyncio
    async def test_transform_with_curation_flag_zero(self, transformer, mock_context):
        """Test transformation with manual_curation_flag set to 0 (not curated)."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "manual_curation_flag": 0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["manual_curation_flag"] == 0

    @pytest.mark.asyncio
    async def test_transform_with_json_fields_single(self, transformer, mock_context):
        """Test transformation unwraps single-element activity_properties."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "activity_properties": [{"type": "Ki", "value": 5.0}],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("activity_properties") == '{"type":"Ki","value":5.0}'

    @pytest.mark.asyncio
    async def test_transform_with_json_fields_multiple(self, transformer, mock_context):
        """Test transformation keeps multi-element activity_properties as array."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "activity_properties": [{"type": "Ki"}, {"type": "IC50"}],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("activity_properties") == '[{"type":"Ki"},{"type":"IC50"}]'

    @pytest.mark.asyncio
    async def test_transform_with_empty_activity_properties(
        self, transformer, mock_context
    ):
        """Test transformation returns None for empty activity_properties."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "activity_properties": [],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("activity_properties") is None

    @pytest.mark.asyncio
    async def test_transform_with_action_type(self, transformer, mock_context):
        """Test transformation with action type data (flattened structure)."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "action_type": {
                "action_type": "INHIBITOR",
                "description": "Compound that inhibits target activity",
                "parent_type": "NEGATIVE MODULATOR",
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["action_type"] == "INHIBITOR"
        assert (
            result["action_type_description"]
            == "Compound that inhibits target activity"
        )
        assert result["action_type_parent_type"] == "NEGATIVE MODULATOR"

    @pytest.mark.asyncio
    async def test_transform_with_action_type_null(self, transformer, mock_context):
        """Test transformation with null action type."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "action_type": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["action_type"] is None
        assert result["action_type_description"] is None
        assert result["action_type_parent_type"] is None


class SharedActivityTransformerExtractionTests:
    """Common extraction-path assertions shared across activity transformer suites."""

    def test_extract_ligand_efficiency_valid_dict(self, transformer):
        """Test extraction with valid ligand efficiency dictionary."""
        le_data = {
            "bei": "14.06",
            "le": "0.26",
            "lle": "1.30",
            "sei": "5.56",
        }

        result = transformer._extract_ligand_efficiency(le_data)

        assert result["ligand_efficiency_bei"] == pytest.approx(14.06)
        assert result["ligand_efficiency_le"] == pytest.approx(0.26)
        assert result["ligand_efficiency_lle"] == pytest.approx(1.30)
        assert result["ligand_efficiency_sei"] == pytest.approx(5.56)

    def test_extract_ligand_efficiency_none(self, transformer):
        """Test extraction with None input."""
        result = transformer._extract_ligand_efficiency(None)

        assert result["ligand_efficiency_bei"] is None
        assert result["ligand_efficiency_le"] is None
        assert result["ligand_efficiency_lle"] is None
        assert result["ligand_efficiency_sei"] is None

    def test_extract_action_type_valid_dict(self, transformer):
        """Test extraction with valid action type dictionary."""
        action_data = {
            "action_type": "INHIBITOR",
            "description": "Compound that inhibits target activity",
            "parent_type": "NEGATIVE MODULATOR",
        }

        result = transformer._extract_action_type(action_data)

        assert result["action_type"] == "INHIBITOR"
        assert (
            result["action_type_description"]
            == "Compound that inhibits target activity"
        )
        assert result["action_type_parent_type"] == "NEGATIVE MODULATOR"

    def test_extract_action_type_none(self, transformer):
        """Test extraction with None input."""
        result = transformer._extract_action_type(None)

        assert result["action_type"] is None
        assert result["action_type_description"] is None
        assert result["action_type_parent_type"] is None
