"""Tests for ChemBL assay enum field normalization."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.profiles.chembl_assay import CHEMBL_ASSAY_PROFILE
from bioetl.domain.schemas.constants import (
    ASSAY_TYPES,
    ASSAY_TEST_TYPES,
    ASSAY_CATEGORIES,
    RELATIONSHIP_TYPES,
)


class TestChemblAssayEnumFields:
    """Test enum field normalization in ChemBL assay profile."""

    def test_enum_fields_configured(self) -> None:
        """Test that enum fields are properly configured."""
        # Check that the profile has the expected enum fields
        enum_fields = [
            "assay_type",
            "assay_test_type",
            "assay_category",
            "relationship_type",
        ]

        for field_name in enum_fields:
            assert field_name in CHEMBL_ASSAY_PROFILE.field_rules, (
                f"{field_name} not found in field rules"
            )

            rule = CHEMBL_ASSAY_PROFILE.field_rules[field_name]
            assert "enum" in rule.notes.lower() or "normalize" in rule.notes.lower(), (
                f"{field_name} should have enum normalization"
            )

    def test_assay_type_enum_normalization(self) -> None:
        """Test assay_type enum normalization."""
        rule = CHEMBL_ASSAY_PROFILE.field_rules["assay_type"]

        # Test valid values
        for valid_value in ["B", "F", "A", "T", "P", "U"]:
            result = rule.normalizer(valid_value)
            assert result == valid_value.upper(), (
                f"Expected {valid_value.upper()}, got {result}"
            )

        # Test invalid value (should be preserved by special rules)
        result = rule.normalizer("X")
        assert result == "X", "Invalid value should be preserved by special rules"

    def test_relationship_type_enum_normalization(self) -> None:
        """Test relationship_type enum normalization."""
        rule = CHEMBL_ASSAY_PROFILE.field_rules["relationship_type"]

        # Test valid values
        for valid_value in ["D", "H", "M", "N", "S", "U"]:
            result = rule.normalizer(valid_value)
            assert result == valid_value.upper(), (
                f"Expected {valid_value.upper()}, got {result}"
            )

    def test_assay_test_type_preservation(self) -> None:
        """Test that assay_test_type preserves original case."""
        rule = CHEMBL_ASSAY_PROFILE.field_rules["assay_test_type"]

        # Test case preservation
        test_cases = [
            ("In vivo", "In vivo"),
            ("in vitro", "in vitro"),
            ("Ex vivo", "Ex vivo"),
        ]

        for input_val, expected in test_cases:
            result = rule.normalizer(input_val)
            assert result == expected, f"Expected {expected}, got {result}"

    def test_enum_constants_available(self) -> None:
        """Test that enum constants are available and correct."""
        # Test ASSAY_TYPES
        assert "B" in ASSAY_TYPES
        assert "F" in ASSAY_TYPES
        assert len(ASSAY_TYPES) == 6

        # Test RELATIONSHIP_TYPES
        assert "D" in RELATIONSHIP_TYPES
        assert "H" in RELATIONSHIP_TYPES
        assert len(RELATIONSHIP_TYPES) == 6

        # Test ASSAY_TEST_TYPES
        assert "In vivo" in ASSAY_TEST_TYPES
        assert "In vitro" in ASSAY_TEST_TYPES
        assert len(ASSAY_TEST_TYPES) == 3

    def test_profile_integration(self) -> None:
        """Test that the profile integrates enum normalization correctly."""
        # The profile should have both enum_fields and special_rules working together
        field_rules = CHEMBL_ASSAY_PROFILE.field_rules

        # Check that enum fields have appropriate rules
        enum_fields = [
            "assay_type",
            "assay_test_type",
            "assay_category",
            "relationship_type",
        ]

        for field_name in enum_fields:
            rule = field_rules[field_name]
            # Should have a normalizer function
            assert callable(rule.normalizer), (
                f"{field_name} should have a callable normalizer"
            )
            # Should have appropriate notes
            assert "normalize" in rule.notes.lower(), (
                f"{field_name} should have normalization notes"
            )


class TestEnumValidation:
    """Test enum validation functions."""

    def test_enum_validation_function(self) -> None:
        """Test the normalize_profile_enum function."""
        from bioetl.domain.normalization.profiles.profile_normalizers import (
            normalize_profile_enum,
        )

        allowed_values = frozenset(["B", "F", "A"])

        # Valid values should be returned as-is
        assert normalize_profile_enum("B", allowed_values=allowed_values) == "B"
        assert normalize_profile_enum("F", allowed_values=allowed_values) == "F"

        # Invalid values should return None
        assert normalize_profile_enum("X", allowed_values=allowed_values) is None
        assert normalize_profile_enum("invalid", allowed_values=allowed_values) is None

        # None should return None
        assert normalize_profile_enum(None, allowed_values=allowed_values) is None

        # Non-string should return None (function only handles strings)
        assert normalize_profile_enum(123, allowed_values=allowed_values) is None


class TestAssayOntologyNormalization:
    """Test ontology ID normalization in assay profile."""

    def test_bao_format_ontology_normalization(self) -> None:
        """Test BAO format ontology ID normalization."""
        rule = CHEMBL_ASSAY_PROFILE.field_rules["bao_format"]

        # Test colon format to underscore format conversion
        assert rule.normalizer("BAO:0000190") == "BAO_0000190"
        assert rule.normalizer("bao:0000190") == "BAO_0000190"

        # Test underscore format preservation
        assert rule.normalizer("BAO_0000190") == "BAO_0000190"

        # Test case normalization
        assert rule.normalizer("BAO:0000190") == "BAO_0000190"
        assert rule.normalizer("bao:0000190") == "BAO_0000190"

        # Test None handling
        assert rule.normalizer(None) is None

        # Test empty string handling
        assert rule.normalizer("") == ""

        # Test unknown format preservation
        assert rule.normalizer("unknown_format") == "unknown_format"
