# pyright: reportArgumentType=false
# Entity fixture overrides use intentional wide test inputs (PD2-9).
"""Unit tests for low-coverage ChEMBL domain entities."""

from __future__ import annotations

from typing import Any, cast


import pytest

from bioetl.domain.entities.chembl_assay_parameters import AssayParameters
from bioetl.domain.entities.chembl_compound_record import CompoundRecord
from bioetl.domain.entities.chembl_subcellular_fraction import SubcellularFraction


# === Shared fixtures ===

BASE_KWARGS = cast(Any, {
    "entity_id": "chembl:test:123",
    "content_hash": "abc123hash",
    "run_id": "run-001",
    "run_type": "incremental",
    "ingestion_ts": "2024-01-01T00:00:00",
    "_index": 0,
})


# ============================================================================
# SubcellularFraction tests
# ============================================================================


@pytest.mark.unit
class TestSubcellularFraction:
    """Tests for SubcellularFraction entity."""

    def test_subcellular_fraction__creation_minimal__42f8e0de(self) -> None:
        """Test creating SubcellularFraction with required fields."""
        sf = SubcellularFraction(
            **BASE_KWARGS,
            subcellular_fraction="Microsomes",
        )
        assert sf.subcellular_fraction == "Microsomes"
        assert sf.assay_count is None
        assert sf.example_assay_id is None

    def test_subcellular_fraction__valid_creation_full__7f46aeb9(self) -> None:
        """Test creating SubcellularFraction with all fields."""
        sf = SubcellularFraction(
            **BASE_KWARGS,
            subcellular_fraction="Cytosol",
            assay_count=42,
            example_assay_id="CHEMBL12345",
        )
        assert sf.subcellular_fraction == "Cytosol"
        assert sf.assay_count == 42
        assert sf.example_assay_id == "CHEMBL12345"

    def test_empty_fraction_name_raises(self) -> None:
        """Test that empty subcellular_fraction raises ValueError."""
        with pytest.raises(ValueError, match="Subcellular fraction name is required"):
            SubcellularFraction(
                **BASE_KWARGS,
                subcellular_fraction="",
            )

    def test_whitespace_fraction_name_raises(self) -> None:
        """Test that whitespace-only subcellular_fraction raises ValueError."""
        with pytest.raises(ValueError, match="empty or whitespace"):
            SubcellularFraction(
                **BASE_KWARGS,
                subcellular_fraction="   ",
            )

    def test_negative_assay_count_raises(self) -> None:
        """Test that negative assay_count raises ValueError."""
        with pytest.raises(ValueError, match="assay_count must be non-negative"):
            SubcellularFraction(
                **BASE_KWARGS,
                subcellular_fraction="Microsomes",
                assay_count=-1,
            )

    def test_zero_assay_count_is_valid(self) -> None:
        """Test that zero assay_count is valid."""
        sf = SubcellularFraction(
            **BASE_KWARGS,
            subcellular_fraction="Microsomes",
            assay_count=0,
        )
        assert sf.assay_count == 0

    def test_subcellular_fraction__is_frozen__04248875(self) -> None:
        """Test SubcellularFraction is immutable."""
        sf = SubcellularFraction(
            **BASE_KWARGS,
            subcellular_fraction="Microsomes",
        )
        with pytest.raises((AttributeError, TypeError)):
            sf.subcellular_fraction = "Other"  # type: ignore[misc]

    @pytest.mark.parametrize(
        "name",
        [
            "Microsomes",
            "Cytosol",
            "Mitochondria",
            "Membrane",
            "Cell lysate",
            "S9 fraction",
        ],
    )
    def test_valid_fraction_names(self, name: str) -> None:
        """Test various valid fraction names."""
        sf = SubcellularFraction(**BASE_KWARGS, subcellular_fraction=name)
        assert sf.subcellular_fraction == name


# ============================================================================
# CompoundRecord tests
# ============================================================================


@pytest.mark.unit
class TestCompoundRecord:
    """Tests for CompoundRecord entity."""

    def test_compound_record__valid_creation__5f79004e(self) -> None:
        """Test creating a valid CompoundRecord."""
        cr = CompoundRecord(
            **BASE_KWARGS,
            record_id=12345,
            molecule_id="CHEMBL25",
            publication_id="CHEMBL1234567",
            src_id=1,
        )
        assert cr.record_id == 12345
        assert cr.molecule_id == "CHEMBL25"
        assert cr.publication_id == "CHEMBL1234567"
        assert cr.src_id == 1
        assert cr.compound_key is None
        assert cr.compound_name is None
        assert cr.src_compound_id is None

    def test_full_creation(self) -> None:
        """Test creating CompoundRecord with all fields."""
        cr = CompoundRecord(
            **BASE_KWARGS,
            record_id=12345,
            molecule_id="CHEMBL25",
            publication_id="CHEMBL1234567",
            compound_key="ASPIRIN",
            compound_name="Aspirin",
            src_id=1,
            src_compound_id="ASP-001",
        )
        assert cr.compound_key == "ASPIRIN"
        assert cr.compound_name == "Aspirin"
        assert cr.src_compound_id == "ASP-001"

    def test_zero_record_id_raises(self) -> None:
        """Test that record_id of 0 raises ValueError."""
        with pytest.raises(ValueError, match="record_id must be > 0"):
            CompoundRecord(
                **BASE_KWARGS,
                record_id=0,
                molecule_id="CHEMBL25",
                publication_id="CHEMBL1234567",
                src_id=1,
            )

    def test_negative_record_id_raises(self) -> None:
        """Test that negative record_id raises ValueError."""
        with pytest.raises(ValueError, match="record_id must be > 0"):
            CompoundRecord(
                **BASE_KWARGS,
                record_id=-1,
                molecule_id="CHEMBL25",
                publication_id="CHEMBL1234567",
                src_id=1,
            )

    def test_zero_src_id_raises(self) -> None:
        """Test that src_id of 0 raises ValueError."""
        with pytest.raises(ValueError, match="src_id must be > 0"):
            CompoundRecord(
                **BASE_KWARGS,
                record_id=1,
                molecule_id="CHEMBL25",
                publication_id="CHEMBL1234567",
                src_id=0,
            )

    def test_compound_record__molecule_id_raises__b8d33ee2(self) -> None:
        """Test that empty molecule_id raises ValueError."""
        with pytest.raises(ValueError, match="molecule_id is required"):
            CompoundRecord(
                **BASE_KWARGS,
                record_id=1,
                molecule_id="",
                publication_id="CHEMBL1234567",
                src_id=1,
            )

    def test_empty_publication_id_raises(self) -> None:
        """Test that empty publication_id raises ValueError."""
        with pytest.raises(ValueError, match="publication_id is required"):
            CompoundRecord(
                **BASE_KWARGS,
                record_id=1,
                molecule_id="CHEMBL25",
                publication_id="",
                src_id=1,
            )

    def test_compound_record__is_frozen__791c0888(self) -> None:
        """Test CompoundRecord is immutable."""
        cr = CompoundRecord(
            **BASE_KWARGS,
            record_id=1,
            molecule_id="CHEMBL25",
            publication_id="CHEMBL1234567",
            src_id=1,
        )
        with pytest.raises((AttributeError, TypeError)):
            cr.record_id = 999  # type: ignore[misc]


# ============================================================================
# AssayParameters tests
# ============================================================================


@pytest.mark.unit
class TestAssayParameters:
    """Tests for AssayParameters entity."""

    def test_assay_parameters__creation_minimal__ee6e2754(self) -> None:
        """Test creating AssayParameters with required fields only."""
        ap = AssayParameters(
            **BASE_KWARGS,
            assay_param_id=1,
            assay_id="CHEMBL12345",
        )
        assert ap.assay_param_id == 1
        assert ap.assay_id == "CHEMBL12345"
        assert ap.type is None
        assert ap.value is None
        assert ap.units is None

    def test_assay_parameters__valid_creation_full__e6ce72be(self) -> None:
        """Test creating AssayParameters with all fields."""
        ap = AssayParameters(
            **BASE_KWARGS,
            assay_param_id=42,
            assay_id="CHEMBL12345",
            type="CONC",
            relation="=",
            value=10.0,
            units="uM",
            text_value=None,
            comments="Test comment",
            standard_type="CONC",
            standard_relation="=",
            standard_value=10.0,
            standard_units="uM",
            standard_text_value=None,
        )
        assert ap.type == "CONC"
        assert ap.value == pytest.approx(10.0)
        assert ap.comments == "Test comment"

    def test_zero_assay_param_id_raises(self) -> None:
        """Test that assay_param_id of 0 raises ValueError."""
        with pytest.raises(ValueError, match="assay_param_id must be positive"):
            AssayParameters(
                **BASE_KWARGS,
                assay_param_id=0,
                assay_id="CHEMBL12345",
            )

    def test_negative_assay_param_id_raises(self) -> None:
        """Test that negative assay_param_id raises ValueError."""
        with pytest.raises(ValueError, match="assay_param_id must be positive"):
            AssayParameters(
                **BASE_KWARGS,
                assay_param_id=-5,
                assay_id="CHEMBL12345",
            )

    def test_invalid_assay_id_raises(self) -> None:
        """Test that assay_id not starting with CHEMBL raises ValueError."""
        with pytest.raises(ValueError, match="Invalid assay_id"):
            AssayParameters(
                **BASE_KWARGS,
                assay_param_id=1,
                assay_id="INVALID123",
            )

    def test_assay_parameters__assay_id_raises__e07e408a(self) -> None:
        """Test that empty assay_id raises ValueError."""
        with pytest.raises(ValueError, match="Invalid assay_id"):
            AssayParameters(
                **BASE_KWARGS,
                assay_param_id=1,
                assay_id="",
            )

    def test_assay_parameters__value_with_value__57ad974c(self) -> None:
        """Test has_numeric_value returns True when value is set."""
        ap = AssayParameters(
            **BASE_KWARGS,
            assay_param_id=1,
            assay_id="CHEMBL12345",
            value=10.0,
        )
        assert ap.has_numeric_value() is True

    def test_assay_parameters__with_standard_value__edc79494(self) -> None:
        """Test has_numeric_value returns True when standard_value is set."""
        ap = AssayParameters(
            **BASE_KWARGS,
            assay_param_id=1,
            assay_id="CHEMBL12345",
            standard_value=10.0,
        )
        assert ap.has_numeric_value() is True

    def test_has_numeric_value_when_none(self) -> None:
        """Test has_numeric_value returns False when both values are None."""
        ap = AssayParameters(
            **BASE_KWARGS,
            assay_param_id=1,
            assay_id="CHEMBL12345",
        )
        assert ap.has_numeric_value() is False

    def test_assay_parameters__text_value_with_text__e467b6cd(self) -> None:
        """Test has_text_value returns True when text_value is set."""
        ap = AssayParameters(
            **BASE_KWARGS,
            assay_param_id=1,
            assay_id="CHEMBL12345",
            text_value="Room temperature",
        )
        assert ap.has_text_value() is True

    def test_assay_parameters__with_standard_text__9c5a4b99(self) -> None:
        """Test has_text_value returns True when standard_text_value is set."""
        ap = AssayParameters(
            **BASE_KWARGS,
            assay_param_id=1,
            assay_id="CHEMBL12345",
            standard_text_value="RT",
        )
        assert ap.has_text_value() is True

    def test_has_text_value_when_none(self) -> None:
        """Test has_text_value returns False when both text values are None."""
        ap = AssayParameters(
            **BASE_KWARGS,
            assay_param_id=1,
            assay_id="CHEMBL12345",
        )
        assert ap.has_text_value() is False

    def test_assay_parameters__prefers_standard__fa027b51(self) -> None:
        """Test get_comparable_value prefers standard over raw values."""
        ap = AssayParameters(
            **BASE_KWARGS,
            assay_param_id=1,
            assay_id="CHEMBL12345",
            value=10.0,
            units="uM",
            standard_value=10000.0,
            standard_units="nM",
        )
        val, units = ap.get_comparable_value()
        assert val == pytest.approx(10000.0)
        assert units == "nM"

    def test_assay_parameters__falls_back_to_raw__bd0e18f4(self) -> None:
        """Test get_comparable_value falls back to raw when standard is None."""
        ap = AssayParameters(
            **BASE_KWARGS,
            assay_param_id=1,
            assay_id="CHEMBL12345",
            value=10.0,
            units="uM",
        )
        val, units = ap.get_comparable_value()
        assert val == pytest.approx(10.0)
        assert units == "uM"

    def test_get_comparable_value_both_none(self) -> None:
        """Test get_comparable_value returns (None, None) when nothing is set."""
        ap = AssayParameters(
            **BASE_KWARGS,
            assay_param_id=1,
            assay_id="CHEMBL12345",
        )
        val, units = ap.get_comparable_value()
        assert val is None
        assert units is None
