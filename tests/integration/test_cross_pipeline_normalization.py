"""Integration tests for cross-pipeline normalization consistency."""

from __future__ import annotations

from typing import Any, cast


from bioetl.domain.normalization.profiles.chembl_activity import CHEMBL_ACTIVITY_PROFILE
from bioetl.domain.normalization.profiles.chembl_assay import CHEMBL_ASSAY_PROFILE
from bioetl.domain.normalization.profiles.chembl_cell_line import (
    CHEMBL_CELL_LINE_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_target import CHEMBL_TARGET_PROFILE
from bioetl.domain.normalization.profiles.chembl_target_component import (
    CHEMBL_TARGET_COMPONENT_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_tissue import CHEMBL_TISSUE_PROFILE
from bioetl.domain.normalization.rules import normalize_cross_pipeline_case
from bioetl.domain.normalization.identifiers import normalize_ontology_id


class TestCrossPipelineCaseNormalization:
    """Test case normalization consistency across pipelines."""

    def test_case_normalization_uppercase_consistency(self) -> None:
        """Test that uppercase strategy is consistent across profiles."""
        # Test the core function
        assert normalize_cross_pipeline_case("test", "uppercase") == "TEST"
        assert normalize_cross_pipeline_case("Test", "uppercase") == "TEST"

        # Test that assay profile uses uppercase for appropriate fields
        assay_type_rule = CHEMBL_ASSAY_PROFILE.field_rules["assay_type"]
        assert "uppercase" in assay_type_rule.notes.lower()

        relationship_type_rule = CHEMBL_ASSAY_PROFILE.field_rules["relationship_type"]
        assert "uppercase" in relationship_type_rule.notes.lower()

    def test_case_normalization_preserve_consistency(self) -> None:
        """Test that preserve strategy is consistent across profiles."""
        # Test the core function
        assert normalize_cross_pipeline_case("In vivo", "preserve") == "In vivo"
        assert normalize_cross_pipeline_case("  In vivo  ", "preserve") == "In vivo"

        # Test that assay profile uses preserve for appropriate fields
        assay_test_type_rule = CHEMBL_ASSAY_PROFILE.field_rules["assay_test_type"]
        assert "preserving" in assay_test_type_rule.notes.lower()

        assay_category_rule = CHEMBL_ASSAY_PROFILE.field_rules["assay_category"]
        assert "preserving" in assay_category_rule.notes.lower()

    def test_case_normalization_edge_cases(self) -> None:
        """Test edge cases for case normalization."""
        # None handling
        assert normalize_cross_pipeline_case(cast(Any, None), "uppercase") is None
        assert normalize_cross_pipeline_case(cast(Any, None), "preserve") is None

        # Empty string handling
        assert normalize_cross_pipeline_case("", "uppercase") is None
        assert normalize_cross_pipeline_case("   ", "uppercase") is None

        # Non-string handling
        assert normalize_cross_pipeline_case(cast(Any, 123), "uppercase") is None
        assert normalize_cross_pipeline_case(cast(Any, []), "preserve") is None


class TestCrossPipelineOntologyNormalization:
    """Test ontology ID normalization consistency across pipelines."""

    def test_ontology_id_normalization_consistency(self) -> None:
        """Test that ontology ID normalization is consistent."""
        # Test core function with various formats
        assert normalize_ontology_id("GO:0008150") == "GO_0008150"
        assert normalize_ontology_id("go:0008150") == "GO_0008150"
        assert normalize_ontology_id("CLO:0000045") == "CLO_0000045"
        assert normalize_ontology_id("EFO:0000319") == "EFO_0000319"
        assert normalize_ontology_id("UBERON:0002107") == "UBERON_0002107"

    def test_cell_line_ontology_fields(self) -> None:
        """Test that cell line profile has ontology ID normalization."""
        # Check that CLO and EFO fields have ontology normalization rules
        clo_rule = CHEMBL_CELL_LINE_PROFILE.field_rules["clo_id"]
        assert "ontology" in clo_rule.notes.lower()

        efo_rule = CHEMBL_CELL_LINE_PROFILE.field_rules["efo_id"]
        assert "ontology" in efo_rule.notes.lower()

    def test_tissue_ontology_fields(self) -> None:
        """Test that tissue profile has ontology ID normalization."""
        # Check that ontology fields have appropriate normalization rules
        bto_rule = CHEMBL_TISSUE_PROFILE.field_rules["bto_id"]
        assert "ontology" in bto_rule.notes.lower()

        efo_rule = CHEMBL_TISSUE_PROFILE.field_rules["efo_id"]
        assert "ontology" in efo_rule.notes.lower()

        uberon_rule = CHEMBL_TISSUE_PROFILE.field_rules["uberon_id"]
        assert "ontology" in uberon_rule.notes.lower()

    def test_ontology_id_edge_cases(self) -> None:
        """Test edge cases for ontology ID normalization."""
        # None handling
        assert normalize_ontology_id(cast(Any, None)) is None

        # Empty string handling
        assert normalize_ontology_id("") == ""
        assert normalize_ontology_id("   ") is None

        # Unknown formats preserved
        assert normalize_ontology_id("unknown") == "unknown"
        assert normalize_ontology_id("ABC123") == "ABC123"


class TestProfileSpecialRulesCoverage:
    """Test that all profiles have appropriate special rules."""

    def test_assay_profile_special_rules(self) -> None:
        """Test that assay profile has expected special rules."""
        special_rules = {
            field_name: rule
            for field_name, rule in CHEMBL_ASSAY_PROFILE.field_rules.items()
            if any(keyword in rule.notes for keyword in ["Normalize", "normalize"])
        }

        # Should have rules for enum fields
        expected_fields = {
            "assay_type",
            "assay_test_type",
            "assay_category",
            "relationship_type",
        }
        actual_fields = set(special_rules.keys())

        assert expected_fields.issubset(actual_fields), (
            f"Missing special rules for: {expected_fields - actual_fields}"
        )

    def test_cell_line_profile_special_rules(self) -> None:
        """Test that cell line profile has expected special rules."""
        special_rules = {
            field_name: rule
            for field_name, rule in CHEMBL_CELL_LINE_PROFILE.field_rules.items()
            if any(keyword in rule.notes for keyword in ["Normalize", "normalize"])
        }

        # Should have rules for ontology fields
        expected_fields = {"clo_id", "efo_id"}
        actual_fields = set(special_rules.keys())

        assert expected_fields.issubset(actual_fields), (
            f"Missing special rules for: {expected_fields - actual_fields}"
        )

    def test_tissue_profile_special_rules(self) -> None:
        """Test that tissue profile has expected special rules."""
        special_rules = {
            field_name: rule
            for field_name, rule in CHEMBL_TISSUE_PROFILE.field_rules.items()
            if any(keyword in rule.notes for keyword in ["Normalize", "normalize"])
        }

        # Should have rules for ontology fields
        expected_fields = {"bto_id", "efo_id", "uberon_id"}
        actual_fields = set(special_rules.keys())

        assert expected_fields.issubset(actual_fields), (
            f"Missing special rules for: {expected_fields - actual_fields}"
        )


class TestNormalizationFunctionIntegration:
    """Test integration between normalization functions and profiles."""

    def test_case_normalizer_integration(self) -> None:
        """Test that case normalizer function works with profile rules."""
        from bioetl.domain.normalization.profiles.chembl_assay import (
            create_case_normalizer,
        )

        # Test the helper function
        upper_normalizer = create_case_normalizer("uppercase")
        assert upper_normalizer("test") == "TEST"
        assert upper_normalizer("  test  ") == "TEST"

        preserve_normalizer = create_case_normalizer("preserve")
        assert preserve_normalizer("In vivo") == "In vivo"
        assert preserve_normalizer("  In vivo  ") == "In vivo"

    def test_ontology_normalizer_integration(self) -> None:
        """Test that ontology normalizer works correctly in profiles."""
        # Test various ontology formats that should be handled by profiles
        test_cases = [
            ("CLO:0000045", "CLO_0000045"),
            ("EFO:0000319", "EFO_0000319"),
            ("UBERON:0002107", "UBERON_0002107"),
            ("GO:0008150", "GO_0008150"),
        ]

        for input_id, expected in test_cases:
            assert normalize_ontology_id(input_id) == expected

    def test_chembl_organism_normalization_consistency_across_profiles(self) -> None:
        """Activity, target, and target-component should share one organism seam."""
        activity_rule = CHEMBL_ACTIVITY_PROFILE.field_rules["target_organism"]
        target_rule = CHEMBL_TARGET_PROFILE.field_rules["organism"]
        component_rule = CHEMBL_TARGET_COMPONENT_PROFILE.field_rules["organism"]

        dirty_inputs = ("  homo   sapiens  ", "e. coli")
        expected = ("Homo sapiens", "Escherichia coli")

        for raw_value, canonical in zip(dirty_inputs, expected, strict=True):
            assert activity_rule.apply(raw_value) == canonical
            assert target_rule.apply(raw_value) == canonical
            assert component_rule.apply(raw_value) == canonical
