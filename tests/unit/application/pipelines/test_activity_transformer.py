"""Unit tests for ActivityTransformer.

Tests both the main transform method and ligand efficiency extraction.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.chembl.activity_transformer import ActivityTransformer
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
    async def test_transform_with_json_fields(self, transformer, mock_context):
        """Test transformation serializes complex fields as JSON."""
        record = {
            "activity_id": 12345,
            "molecule_chembl_id": "CHEMBL25",
            "action_type": ["INHIBITOR"],
            "activity_properties": [{"type": "Ki", "value": 5.0}],
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        # JSON fields should be serialized as strings
        assert isinstance(result.get("action_type"), str)
        assert isinstance(result.get("activity_properties"), str)

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
    """Tests for ActivityTransformer ligand efficiency extraction."""


def test_extract_ligand_efficiency_valid_dict(transformer):
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


def test_extract_ligand_efficiency_none(transformer):
    """Test extraction with None input."""
    result = transformer._extract_ligand_efficiency(None)

    assert result["ligand_efficiency_bei"] is None
    assert result["ligand_efficiency_le"] is None
    assert result["ligand_efficiency_lle"] is None
    assert result["ligand_efficiency_sei"] is None


def test_extract_ligand_efficiency_empty_dict(transformer):
    """Test extraction with empty dictionary."""
    result = transformer._extract_ligand_efficiency({})

    assert result["ligand_efficiency_bei"] is None
    assert result["ligand_efficiency_le"] is None
    assert result["ligand_efficiency_lle"] is None
    assert result["ligand_efficiency_sei"] is None


def test_extract_ligand_efficiency_partial_dict(transformer):
    """Test extraction with partially filled dictionary."""
    le_data = {
        "bei": "10.5",
        "le": "0.2",
        # lle and sei missing
    }

    result = transformer._extract_ligand_efficiency(le_data)

    assert result["ligand_efficiency_bei"] == pytest.approx(10.5)
    assert result["ligand_efficiency_le"] == pytest.approx(0.2)
    assert result["ligand_efficiency_lle"] is None
    assert result["ligand_efficiency_sei"] is None


def test_extract_ligand_efficiency_invalid_values(transformer):
    """Test extraction with invalid numeric values."""
    le_data = {
        "bei": "invalid",
        "le": "not_a_number",
        "lle": None,
        "sei": "",
    }

    result = transformer._extract_ligand_efficiency(le_data)

    # safe_float should return None for invalid values
    assert result["ligand_efficiency_bei"] is None
    assert result["ligand_efficiency_le"] is None
    assert result["ligand_efficiency_lle"] is None
    assert result["ligand_efficiency_sei"] is None


def test_extract_ligand_efficiency_non_dict_input(transformer):
    """Test extraction with non-dictionary input."""
    # String input
    result1 = transformer._extract_ligand_efficiency("not a dict")
    assert all(v is None for v in result1.values())

    # List input
    result2 = transformer._extract_ligand_efficiency([1, 2, 3])
    assert all(v is None for v in result2.values())

    # Integer input
    result3 = transformer._extract_ligand_efficiency(123)
    assert all(v is None for v in result3.values())


def test_extract_ligand_efficiency_negative_values(transformer):
    """Test extraction with negative values (valid edge case)."""
    le_data = {
        "bei": "-5.0",
        "le": "-0.1",
        "lle": "-2.5",
        "sei": "0.0",
    }

    result = transformer._extract_ligand_efficiency(le_data)

    # Negative values are technically valid floats
    assert result["ligand_efficiency_bei"] == pytest.approx(-5.0)
    assert result["ligand_efficiency_le"] == pytest.approx(-0.1)
    assert result["ligand_efficiency_lle"] == pytest.approx(-2.5)
    assert result["ligand_efficiency_sei"] == pytest.approx(0.0)


def test_extract_ligand_efficiency_float_precision(transformer):
    """Test extraction preserves float precision."""
    le_data = {
        "bei": "14.123456789",
        "le": "0.987654321",
        "lle": "1.111111111",
        "sei": "5.999999999",
    }

    result = transformer._extract_ligand_efficiency(le_data)

    # Check that precision is preserved within float64 limits
    assert result["ligand_efficiency_bei"] == pytest.approx(14.123456789, rel=1e-9)
    assert result["ligand_efficiency_le"] == pytest.approx(0.987654321, rel=1e-9)
    assert result["ligand_efficiency_lle"] == pytest.approx(1.111111111, rel=1e-9)
    assert result["ligand_efficiency_sei"] == pytest.approx(5.999999999, rel=1e-9)
