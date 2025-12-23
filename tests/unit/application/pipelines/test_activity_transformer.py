"""Unit tests for ActivityTransformer ligand efficiency extraction."""

import pytest

from bioetl.application.pipelines.chembl.activity_transformer import ActivityTransformer


@pytest.fixture
def transformer():
    """Fixture for ActivityTransformer instance."""
    return ActivityTransformer(provider="chembl")


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
