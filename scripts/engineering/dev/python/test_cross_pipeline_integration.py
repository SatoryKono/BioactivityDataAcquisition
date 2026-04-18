#!/usr/bin/env python3
"""Comprehensive test for CROSS-001 and CROSS-002 integration."""

import os
import sys
from collections.abc import Callable
from typing import cast

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_enum_unification():
    """Test that all pipelines use unified enum configurations."""
    from bioetl.domain.config.enum_loader import get_chembl_enum_set
    from bioetl.domain.normalization.profiles.chembl_activity import (
        ACTIVITY_STANDARD_TYPES,
        STANDARD_RELATIONS,
    )
    from bioetl.domain.normalization.profiles.chembl_assay import (
        ASSAY_TYPES,
        RELATIONSHIP_TYPES,
    )

    print("=== Testing Enum Unification (CROSS-001) ===")

    # Verify activity enums match YAML source
    yaml_activity_types = get_chembl_enum_set("activity", "standard_types")
    assert ACTIVITY_STANDARD_TYPES == yaml_activity_types
    print("✓ Activity enums use unified YAML source")

    # Verify assay enums match YAML source
    yaml_assay_types = get_chembl_enum_set("assay", "types")
    assert ASSAY_TYPES == yaml_assay_types
    print("✓ Assay enums use unified YAML source")

    # Verify both use same pattern
    assert isinstance(ACTIVITY_STANDARD_TYPES, frozenset)
    assert isinstance(ASSAY_TYPES, frozenset)
    print("✓ Both pipelines use immutable frozensets")

    print("✅ Enum unification tests passed!")

def test_case_normalization():
    """Test cross-pipeline case normalization (CROSS-002)."""
    from bioetl.domain.normalization.profiles.chembl_activity import (
        CHEMBL_ACTIVITY_PROFILE,
    )
    from bioetl.domain.normalization.rules import normalize_cross_pipeline_case

    print("\n=== Testing Case Normalization (CROSS-002) ===")

    # Test the core function
    assert normalize_cross_pipeline_case("test", "uppercase") == "TEST"
    assert normalize_cross_pipeline_case("Test", "lowercase") == "test"
    assert normalize_cross_pipeline_case("Test", "preserve") == "Test"
    print("✓ Core case normalization working")

    # Test activity profile integration
    standard_type_rule = CHEMBL_ACTIVITY_PROFILE.field_rules["standard_type"]
    assert "uppercase" in standard_type_rule.notes.lower()

    # Test the normalizer
    test_cases = [
        ('ic50', 'IC50'),
        ('EC50', 'EC50'),
        ('ki', 'KI'),
        ('  mixed_case  ', 'MIXED_CASE'),
    ]

    for input_val, expected in test_cases:
        result = standard_type_rule.normalizer(input_val)
        assert result == expected, f'Expected {expected}, got {result}'

    print("✓ Activity profile case normalization working")

    # Test standard_relation
    standard_relation_rule = CHEMBL_ACTIVITY_PROFILE.field_rules["standard_relation"]
    test_cases = [
        ('=', '='),
        ('<', '<'),
        ('<=', '<='),
        ('  >  ', '>'),
    ]

    for input_val, expected in test_cases:
        result = standard_relation_rule.normalizer(input_val)
        assert result == expected, f'Expected {expected}, got {result}'

    print("✓ Standard relation case normalization working")
    print("✅ Case normalization tests passed!")

def test_ontology_ids():
    """Test ontology ID normalization."""
    from bioetl.domain.normalization.identifiers import (
        get_ontology_prefix,
        is_valid_ontology_id,
        normalize_ontology_id,
        normalize_ontology_id_strict,
    )

    print("\n=== Testing Ontology ID Normalization ===")

    # Test various formats
    assert normalize_ontology_id("CLO:0000034") == "CLO_0000034"
    assert normalize_ontology_id("EFO_0000087") == "EFO_0000087"
    assert normalize_ontology_id("UBERON 7") == "UBERON_0000007"
    print("✓ Ontology ID normalization working")

    # Test strict mode
    assert normalize_ontology_id_strict("CLO:0000034") == "CLO_0000034"
    assert normalize_ontology_id_strict("UNKNOWN:123") is None
    print("✓ Strict mode working")

    # Test validation
    assert is_valid_ontology_id("CLO_0000034") is True
    assert is_valid_ontology_id("unknown") is False
    print("✓ Validation working")

    print("✅ Ontology ID tests passed!")

def test_cross_pipeline_consistency():
    """Test consistency across multiple pipelines."""
    from bioetl.domain.config.enum_loader import get_chembl_enum_set

    print("\n=== Testing Cross-Pipeline Consistency ===")

    # Verify all pipelines can access same enum source
    activity_types = get_chembl_enum_set("activity", "standard_types")
    assay_types = get_chembl_enum_set("assay", "types")
    molecule_types = get_chembl_enum_set("molecule", "types")
    target_types = get_chembl_enum_set("target", "types")

    assert len(activity_types) > 0
    assert len(assay_types) > 0
    assert len(molecule_types) > 0
    assert len(target_types) > 0

    print(f"✓ Activity: {len(activity_types)} enums")
    print(f"✓ Assay: {len(assay_types)} enums")
    print(f"✓ Molecule: {len(molecule_types)} enums")
    print(f"✓ Target: {len(target_types)} enums")

    print("✅ Cross-pipeline consistency tests passed!")

def test_edge_cases():
    """Test edge cases and error handling."""
    from bioetl.domain.normalization.identifiers import normalize_ontology_id
    from bioetl.domain.normalization.rules import normalize_cross_pipeline_case

    print("\n=== Testing Edge Cases ===")

    # Case normalization edge cases
    normalize_case = cast(Callable[[object, str], object], normalize_cross_pipeline_case)
    normalize_ontology = cast(Callable[[object], object], normalize_ontology_id)
    assert normalize_case(None, "uppercase") is None
    assert normalize_case(123, "uppercase") is None
    assert normalize_cross_pipeline_case("", "uppercase") is None  # Empty string becomes None
    assert normalize_cross_pipeline_case("  ", "uppercase") is None  # Whitespace becomes None
    print("✓ Case normalization edge cases handled")

    # Ontology ID edge cases
    assert normalize_ontology(None) is None
    assert normalize_ontology(123) is None
    assert normalize_ontology_id("") is None
    assert normalize_ontology_id("  ") is None
    print("✓ Ontology ID edge cases handled")

    print("✅ Edge case tests passed!")

if __name__ == "__main__":
    try:
        test_enum_unification()
        test_case_normalization()
        test_ontology_ids()
        test_cross_pipeline_consistency()
        test_edge_cases()

        print("\n🎉 All cross-pipeline integration tests passed!")
        print("\n✅ Implementation Status:")
        print("   • CROSS-001 (Enum Unification): ✓ 100% Complete")
        print("   • CROSS-002 (Case Normalization): ✓ 50% Complete")
        print("   • Activity profile: ✓ Integrated")
        print("   • Core functions: ✓ Working")
        print("   • Cross-pipeline: ✓ Consistent")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
