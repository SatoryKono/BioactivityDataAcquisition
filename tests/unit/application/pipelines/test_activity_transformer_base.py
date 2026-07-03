"""Unit tests for ActivityTransformer.

Tests both the main transform method and ligand efficiency extraction.
"""

from __future__ import annotations

import pytest

from bioetl.application.core.dict_transformers import flatten_nested_dict
from bioetl.application.pipelines.chembl.activity_transformer import (
    _ACTION_TYPE_FIELDS,
    _LIGAND_EFFICIENCY_FIELDS,
    ActivityTransformer,
)
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies
from tests.unit.application.pipelines.activity_transformer_shared import (
    SharedActivityTransformerActionTypeExtractionTests,
    SharedActivityTransformerLigandExtractionTests,
    SharedActivityTransformerTransformTests,
)


@pytest.mark.unit
class TestActivityTransformerTransform(SharedActivityTransformerTransformTests):
    """Base transformer tests shared with chembl-specific suite."""

    @pytest.mark.asyncio
    async def test_transform_custom_provider(self, mock_context):
        """Test transformation with custom provider."""
        transformer = ActivityTransformer(
            provider="custom_provider",
            dependencies=build_test_transformer_dependencies(),
        )
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result


@pytest.mark.unit
class TestActivityTransformerLigandEfficiency(
    SharedActivityTransformerLigandExtractionTests
):
    """Tests for ligand efficiency extraction using flatten_nested_dict."""

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
class TestActivityTransformerActionType(
    SharedActivityTransformerActionTypeExtractionTests
):
    """Tests for action type extraction using flatten_nested_dict."""

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
