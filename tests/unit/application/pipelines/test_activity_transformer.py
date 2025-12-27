"""Unit tests for ActivityTransformer.

Tests both the main transform method and ligand efficiency extraction.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.transform_utils import flatten_nested_dict
from bioetl.application.pipelines.chembl.activity_transformer import (
    ActivityTransformer,
    _ACTION_TYPE_FIELDS,
    _LIGAND_EFFICIENCY_FIELDS,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


@pytest.fixture
def transformer():
    """Fixture for ActivityTransformer instance."""
    return ActivityTransformer(provider="chembl")


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
class TestActivityTransformerTransform:
    """Tests for ActivityTransformer transform method."""

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid activity record."""
        record = {
            "activity_id": 12345,
            "molecule_chembl_id": "CHEMBL25",
            "target_chembl_id": "CHEMBL1862",
            "assay_chembl_id": "CHEMBL1234567",
            "standard_type": "IC50",
            "standard_value": 10.5,
            "standard_units": "nM",
            "pchembl_value": 8.0,
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert result["activity_id"] == "12345"
        assert result["molecule_chembl_id"] == "CHEMBL25"
        assert result["target_chembl_id"] == "CHEMBL1862"
        assert result["standard_type"] == "IC50"
        assert result["standard_value"] == pytest.approx(10.5)
        assert result["pchembl_value"] == pytest.approx(8.0)
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_activity_id(self, transformer, mock_context):
        """Test transformation returns None when activity_id is missing."""
        record = {
            "molecule_chembl_id": "CHEMBL25",
            "target_chembl_id": "CHEMBL1862",
        }

        result = await transformer.transform(mock_context, record)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_missing_molecule_id(self, transformer, mock_context):
        """Test transformation returns None when molecule_chembl_id is missing."""
        record = {
            "activity_id": 12345,
            "target_chembl_id": "CHEMBL1862",
        }

        result = await transformer.transform(mock_context, record)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_with_ligand_efficiency(self, transformer, mock_context):
        """Test transformation with ligand efficiency data."""
        record = {
            "activity_id": 12345,
            "molecule_chembl_id": "CHEMBL25",
            "ligand_efficiency": {
                "bei": "14.06",
                "le": "0.26",
                "lle": "1.30",
                "sei": "5.56",
            },
        }

        result = await transformer.transform(mock_context, record)

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
            "molecule_chembl_id": "CHEMBL25",
            "target_chembl_id": "CHEMBL1862",
            "assay_chembl_id": "CHEMBL123",
            "document_chembl_id": "CHEMBL456",
            "record_id": 100,
            "src_id": 1,
            "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
            "molecule_pref_name": "ASPIRIN",
            "parent_molecule_chembl_id": "CHEMBL25",
            "target_pref_name": "Cyclooxygenase-2",
            "target_organism": "Homo sapiens",
            "target_tax_id": 9606,
            "assay_type": "B",
            "assay_description": "Binding assay",
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert result["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
        assert result["molecule_pref_name"] == "ASPIRIN"
        assert result["target_pref_name"] == "Cyclooxygenase-2"
        assert result["target_organism"] == "Homo sapiens"
        assert result["assay_type"] == "B"

    @pytest.mark.asyncio
    async def test_transform_with_activity_values(self, transformer, mock_context):
        """Test transformation with raw and standardized activity values."""
        record = {
            "activity_id": 12345,
            "molecule_chembl_id": "CHEMBL25",
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

        result = await transformer.transform(mock_context, record)

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
            "molecule_chembl_id": "CHEMBL25",
            "activity_comment": "Potent inhibitor",
            "data_validity_comment": "Valid",
            "data_validity_description": "Data passed validation",
            "potential_duplicate": 0,
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert result["activity_comment"] == "Potent inhibitor"
        assert result["data_validity_comment"] == "Valid"
        assert result["potential_duplicate"] == 0

    @pytest.mark.asyncio
    async def test_transform_with_json_fields_single(self, transformer, mock_context):
        """Test transformation unwraps single-element activity_properties."""
        record = {
            "activity_id": 12345,
            "molecule_chembl_id": "CHEMBL25",
            "activity_properties": [{"type": "Ki", "value": 5.0}],
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        # Single-element list is unwrapped to just the dict
        assert result.get("activity_properties") == '{"type": "Ki", "value": 5.0}'

    @pytest.mark.asyncio
    async def test_transform_with_json_fields_multiple(self, transformer, mock_context):
        """Test transformation keeps multi-element activity_properties as array."""
        record = {
            "activity_id": 12345,
            "molecule_chembl_id": "CHEMBL25",
            "activity_properties": [{"type": "Ki"}, {"type": "IC50"}],
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        # Multi-element list stays as array
        assert result.get("activity_properties") == '[{"type": "Ki"}, {"type": "IC50"}]'

    @pytest.mark.asyncio
    async def test_transform_with_empty_activity_properties(
        self, transformer, mock_context
    ):
        """Test transformation returns None for empty activity_properties."""
        record = {
            "activity_id": 12345,
            "molecule_chembl_id": "CHEMBL25",
            "activity_properties": [],  # Empty array from ChEMBL API
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        # Empty collections are treated as None for semantic consistency
        assert result.get("activity_properties") is None

    @pytest.mark.asyncio
    async def test_transform_with_action_type(self, transformer, mock_context):
        """Test transformation with action type data (flattened structure)."""
        record = {
            "activity_id": 12345,
            "molecule_chembl_id": "CHEMBL25",
            "action_type": {
                "action_type": "INHIBITOR",
                "description": "Compound that inhibits target activity",
                "parent_type": "NEGATIVE MODULATOR",
            },
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert result["action_type_action_type"] == "INHIBITOR"
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
            "molecule_chembl_id": "CHEMBL25",
            "action_type": None,
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert result["action_type_action_type"] is None
        assert result["action_type_description"] is None
        assert result["action_type_parent_type"] is None

    @pytest.mark.asyncio
    async def test_transform_custom_provider(self, mock_context):
        """Test transformation with custom provider."""
        transformer = ActivityTransformer(provider="custom_provider")
        record = {
            "activity_id": 12345,
            "molecule_chembl_id": "CHEMBL25",
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert "entity_id" in result


@pytest.mark.unit
class TestActivityTransformerLigandEfficiency:
    """Tests for ligand efficiency extraction using flatten_nested_dict."""

    def test_extract_ligand_efficiency_valid_dict(self):
        """Test extraction with valid ligand efficiency dictionary."""
        le_data = {
            "bei": "14.06",
            "le": "0.26",
            "lle": "1.30",
            "sei": "5.56",
        }

        result = flatten_nested_dict(
            le_data, "ligand_efficiency_", _LIGAND_EFFICIENCY_FIELDS
        )

        assert result["ligand_efficiency_bei"] == pytest.approx(14.06)
        assert result["ligand_efficiency_le"] == pytest.approx(0.26)
        assert result["ligand_efficiency_lle"] == pytest.approx(1.30)
        assert result["ligand_efficiency_sei"] == pytest.approx(5.56)

    def test_extract_ligand_efficiency_none(self):
        """Test extraction with None input."""
        result = flatten_nested_dict(
            None, "ligand_efficiency_", _LIGAND_EFFICIENCY_FIELDS
        )

        assert result["ligand_efficiency_bei"] is None
        assert result["ligand_efficiency_le"] is None
        assert result["ligand_efficiency_lle"] is None
        assert result["ligand_efficiency_sei"] is None

    def test_extract_ligand_efficiency_empty_dict(self):
        """Test extraction with empty dictionary."""
        result = flatten_nested_dict(
            {}, "ligand_efficiency_", _LIGAND_EFFICIENCY_FIELDS
        )

        assert result["ligand_efficiency_bei"] is None
        assert result["ligand_efficiency_le"] is None
        assert result["ligand_efficiency_lle"] is None
        assert result["ligand_efficiency_sei"] is None

    def test_extract_ligand_efficiency_partial_dict(self):
        """Test extraction with partially filled dictionary."""
        le_data = {
            "bei": "10.5",
            "le": "0.2",
            # lle and sei missing
        }

        result = flatten_nested_dict(
            le_data, "ligand_efficiency_", _LIGAND_EFFICIENCY_FIELDS
        )

        assert result["ligand_efficiency_bei"] == pytest.approx(10.5)
        assert result["ligand_efficiency_le"] == pytest.approx(0.2)
        assert result["ligand_efficiency_lle"] is None
        assert result["ligand_efficiency_sei"] is None

    def test_extract_ligand_efficiency_invalid_values(self):
        """Test extraction with invalid numeric values."""
        le_data = {
            "bei": "invalid",
            "le": "not_a_number",
            "lle": None,
            "sei": "",
        }

        result = flatten_nested_dict(
            le_data, "ligand_efficiency_", _LIGAND_EFFICIENCY_FIELDS
        )

        # safe_float should return None for invalid values
        assert result["ligand_efficiency_bei"] is None
        assert result["ligand_efficiency_le"] is None
        assert result["ligand_efficiency_lle"] is None
        assert result["ligand_efficiency_sei"] is None

    def test_extract_ligand_efficiency_non_dict_input(self):
        """Test extraction with non-dictionary input."""
        # String input - flatten_nested_dict handles gracefully
        result1 = flatten_nested_dict(
            "not a dict", "ligand_efficiency_", _LIGAND_EFFICIENCY_FIELDS
        )
        assert all(v is None for v in result1.values())

        # List input
        result2 = flatten_nested_dict(
            [1, 2, 3], "ligand_efficiency_", _LIGAND_EFFICIENCY_FIELDS
        )
        assert all(v is None for v in result2.values())

        # Integer input
        result3 = flatten_nested_dict(
            123, "ligand_efficiency_", _LIGAND_EFFICIENCY_FIELDS
        )
        assert all(v is None for v in result3.values())

    def test_extract_ligand_efficiency_negative_values(self):
        """Test extraction with negative values (valid edge case)."""
        le_data = {
            "bei": "-5.0",
            "le": "-0.1",
            "lle": "-2.5",
            "sei": "0.0",
        }

        result = flatten_nested_dict(
            le_data, "ligand_efficiency_", _LIGAND_EFFICIENCY_FIELDS
        )

        # Negative values are technically valid floats
        assert result["ligand_efficiency_bei"] == pytest.approx(-5.0)
        assert result["ligand_efficiency_le"] == pytest.approx(-0.1)
        assert result["ligand_efficiency_lle"] == pytest.approx(-2.5)
        assert result["ligand_efficiency_sei"] == pytest.approx(0.0)

    def test_extract_ligand_efficiency_float_precision(self):
        """Test extraction preserves float precision."""
        le_data = {
            "bei": "14.123456789",
            "le": "0.987654321",
            "lle": "1.111111111",
            "sei": "5.999999999",
        }

        result = flatten_nested_dict(
            le_data, "ligand_efficiency_", _LIGAND_EFFICIENCY_FIELDS
        )

        # Check that precision is preserved within float64 limits
        assert result["ligand_efficiency_bei"] == pytest.approx(14.123456789, rel=1e-9)
        assert result["ligand_efficiency_le"] == pytest.approx(0.987654321, rel=1e-9)
        assert result["ligand_efficiency_lle"] == pytest.approx(1.111111111, rel=1e-9)
        assert result["ligand_efficiency_sei"] == pytest.approx(5.999999999, rel=1e-9)


@pytest.mark.unit
class TestActivityTransformerActionType:
    """Tests for action type extraction using flatten_nested_dict."""

    def test_extract_action_type_valid_dict(self):
        """Test extraction with valid action type dictionary."""
        action_data = {
            "action_type": "INHIBITOR",
            "description": "Compound that inhibits target activity",
            "parent_type": "NEGATIVE MODULATOR",
        }

        result = flatten_nested_dict(action_data, "action_type_", _ACTION_TYPE_FIELDS)

        assert result["action_type_action_type"] == "INHIBITOR"
        assert (
            result["action_type_description"]
            == "Compound that inhibits target activity"
        )
        assert result["action_type_parent_type"] == "NEGATIVE MODULATOR"

    def test_extract_action_type_none(self):
        """Test extraction with None input."""
        result = flatten_nested_dict(None, "action_type_", _ACTION_TYPE_FIELDS)

        assert result["action_type_action_type"] is None
        assert result["action_type_description"] is None
        assert result["action_type_parent_type"] is None

    def test_extract_action_type_empty_dict(self):
        """Test extraction with empty dictionary."""
        result = flatten_nested_dict({}, "action_type_", _ACTION_TYPE_FIELDS)

        assert result["action_type_action_type"] is None
        assert result["action_type_description"] is None
        assert result["action_type_parent_type"] is None

    def test_extract_action_type_partial_dict(self):
        """Test extraction with partial data (parent_type nullable)."""
        action_data = {
            "action_type": "AGONIST",
            "description": "Activates receptor",
            # parent_type missing
        }

        result = flatten_nested_dict(action_data, "action_type_", _ACTION_TYPE_FIELDS)

        assert result["action_type_action_type"] == "AGONIST"
        assert result["action_type_description"] == "Activates receptor"
        assert result["action_type_parent_type"] is None

    def test_extract_action_type_only_type(self):
        """Test extraction with only action_type field."""
        action_data = {
            "action_type": "ANTAGONIST",
        }

        result = flatten_nested_dict(action_data, "action_type_", _ACTION_TYPE_FIELDS)

        assert result["action_type_action_type"] == "ANTAGONIST"
        assert result["action_type_description"] is None
        assert result["action_type_parent_type"] is None

    def test_extract_action_type_non_dict_input(self):
        """Test extraction with non-dictionary input."""
        # String input
        result1 = flatten_nested_dict("INHIBITOR", "action_type_", _ACTION_TYPE_FIELDS)
        assert all(v is None for v in result1.values())

        # List input (old format like ["INHIBITOR"])
        result2 = flatten_nested_dict(
            ["INHIBITOR"], "action_type_", _ACTION_TYPE_FIELDS
        )
        assert all(v is None for v in result2.values())

        # Integer input
        result3 = flatten_nested_dict(123, "action_type_", _ACTION_TYPE_FIELDS)
        assert all(v is None for v in result3.values())

    def test_extract_action_type_all_parent_types(self):
        """Test extraction with different parent_type values."""
        # POSITIVE MODULATOR parent type
        action_data_positive = {
            "action_type": "AGONIST",
            "description": "Activates receptor",
            "parent_type": "POSITIVE MODULATOR",
        }
        result = flatten_nested_dict(
            action_data_positive, "action_type_", _ACTION_TYPE_FIELDS
        )
        assert result["action_type_parent_type"] == "POSITIVE MODULATOR"

        # NEGATIVE MODULATOR parent type
        action_data_negative = {
            "action_type": "INHIBITOR",
            "description": "Inhibits activity",
            "parent_type": "NEGATIVE MODULATOR",
        }
        result = flatten_nested_dict(
            action_data_negative, "action_type_", _ACTION_TYPE_FIELDS
        )
        assert result["action_type_parent_type"] == "NEGATIVE MODULATOR"

    def test_extract_action_type_preserves_whitespace(self):
        """Test extraction preserves whitespace in strings."""
        action_data = {
            "action_type": "PARTIAL AGONIST",
            "description": "Compound with partial agonist activity",
            "parent_type": "POSITIVE MODULATOR",
        }

        result = flatten_nested_dict(action_data, "action_type_", _ACTION_TYPE_FIELDS)

        assert result["action_type_action_type"] == "PARTIAL AGONIST"
        assert (
            result["action_type_description"]
            == "Compound with partial agonist activity"
        )
