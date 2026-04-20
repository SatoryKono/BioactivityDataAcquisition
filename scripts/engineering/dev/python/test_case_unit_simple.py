#!/usr/bin/env python3
"""Simple test script to verify case normalization and unit canonicalization without full dependencies."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_normalization_rules():
    """Test the normalization rules functionality."""
    from bioetl.domain.normalization.rules import (
        UNIT_MAPPING,
        normalize_case,
        normalize_unit,
    )

    print("=== Testing Case Normalization ===")

    # Test case normalization with allowed values
    assay_types = frozenset(["B", "F", "A", "T", "P", "U"])
    # Use actual activity types from ChEMBL
    activity_types = frozenset(["IC50", "EC50", "Ki", "Kd", "AC50", "GI50", "Potency"])

    # Valid assay type cases
    assert normalize_case("b", assay_types) == "B"
    assert normalize_case("B", assay_types) == "B"
    assert normalize_case("  f  ", assay_types) == "F"
    assert normalize_case("a", assay_types) == "A"
    assert normalize_case("t", assay_types) == "T"
    assert normalize_case("p", assay_types) == "P"
    assert normalize_case("u", assay_types) == "U"

    # Valid activity type cases (case-insensitive matching, preserves enum case)
    assert normalize_case("ic50", activity_types) == "IC50"
    assert normalize_case("IC50", activity_types) == "IC50"
    assert normalize_case("  ec50  ", activity_types) == "EC50"
    assert normalize_case("ki", activity_types) == "Ki"  # Returns enum's original case
    assert normalize_case("Ki", activity_types) == "Ki"  # Exact match
    assert normalize_case("KI", activity_types) == "Ki"  # Case-insensitive, returns enum case
    assert normalize_case("kd", activity_types) == "Kd"  # Returns enum's original case
    assert normalize_case("Kd", activity_types) == "Kd"  # Exact match
    assert normalize_case("KD", activity_types) == "Kd"  # Case-insensitive, returns enum case

    # Invalid cases
    assert normalize_case("X", assay_types) is None
    assert normalize_case("invalid", assay_types) is None
    assert normalize_case(None, assay_types) is None
    assert normalize_case(123, assay_types) is None

    print("✓ Case normalization tests passed!")

    print("\n=== Testing Unit Canonicalization ===")

    # Test unit canonicalization - common bioactivity units
    assert normalize_unit("nM") == "nM"
    assert normalize_unit("NM") == "nM"
    assert normalize_unit("nm") == "nM"
    assert normalize_unit("uM") == "µM"
    assert normalize_unit("UM") == "µM"
    assert normalize_unit("µM") == "µM"
    assert normalize_unit("μM") == "µM"
    assert normalize_unit("mM") == "mM"
    assert normalize_unit("MM") == "mM"
    assert normalize_unit("mm") == "mM"
    assert normalize_unit("M") == "M"
    assert normalize_unit("m") == "M"

    # Percentage and other units
    assert normalize_unit("percent") == "%"
    assert normalize_unit("PERCENT") == "%"
    assert normalize_unit("%") == "%"

    # Volume units
    assert normalize_unit("uL") == "µL"
    assert normalize_unit("UL") == "µL"
    assert normalize_unit("µL") == "µL"
    assert normalize_unit("mL") == "mL"
    assert normalize_unit("ML") == "mL"

    # Unknown units should pass through
    assert normalize_unit("unknown_unit") == "unknown_unit"
    assert normalize_unit("custom_metric") == "custom_metric"

    # Invalid inputs
    assert normalize_unit(None) is None
    assert normalize_unit(123) is None
    assert normalize_unit("") is None
    assert normalize_unit("  ") is None

    print("✓ Unit canonicalization tests passed!")

    print("\n=== Unit Mapping Info ===")
    print("Total unit mappings:", len(UNIT_MAPPING))

    # Show bioactivity-relevant units
    bioactivity_units = {k: v for k, v in UNIT_MAPPING.items() if v in ['nM', 'µM', 'mM', 'M', '%']}
    print("Bioactivity units:", len(bioactivity_units), "mappings")
    for k, v in list(bioactivity_units.items())[:10]:
        print(f"  {k} → {v}")

def test_profile_normalizers():
    """Test the profile normalizer functions."""
    from bioetl.domain.normalization.profiles.profile_normalizers import (
        normalize_profile_case,
        normalize_profile_unit,
    )

    print("\n=== Testing Profile Normalizer Functions ===")

    # Test case normalizer with assay types
    assay_types = frozenset(["B", "F", "A", "T", "P", "U"])

    # Test all assay type variations
    test_cases = [
        ("b", "B"),
        ("B", "B"),
        ("  f  ", "F"),
        ("F", "F"),
        ("a", "A"),
        ("A", "A"),
        ("t", "T"),
        ("T", "T"),
        ("p", "P"),
        ("P", "P"),
        ("u", "U"),
        ("U", "U"),
    ]

    for input_val, expected in test_cases:
        result = normalize_profile_case(input_val, allowed_values=assay_types)
        assert result == expected, f"Expected {expected}, got {result} for input {input_val}"

    # Test invalid cases
    assert normalize_profile_case("X", allowed_values=assay_types) is None
    assert normalize_profile_case("invalid", allowed_values=assay_types) is None
    assert normalize_profile_case(None, allowed_values=assay_types) is None

    print("✓ Case normalizer tests passed!")

    # Test unit normalizer with common bioactivity units
    unit_test_cases = [
        ("nM", "nM"),
        ("NM", "nM"),
        ("nm", "nM"),
        ("uM", "µM"),
        ("UM", "µM"),
        ("µM", "µM"),
        ("mM", "mM"),
        ("MM", "mM"),
        ("percent", "%"),
        ("PERCENT", "%"),
        ("unknown_unit", "unknown_unit"),
    ]

    for input_val, expected in unit_test_cases:
        result = normalize_profile_unit(input_val)
        assert result == expected, f"Expected {expected}, got {result} for input {input_val}"

    # Test invalid unit inputs
    assert normalize_profile_unit(None) is None
    assert normalize_profile_unit(123) is None
    assert normalize_profile_unit("") is None

    print("✓ Unit normalizer tests passed!")

def test_edge_cases():
    """Test edge cases and error handling."""
    from bioetl.domain.normalization.rules import normalize_case, normalize_unit

    print("\n=== Testing Edge Cases ===")

    # Test case normalization edge cases
    assay_types = frozenset(["B", "F", "A", "T", "P", "U"])

    # Whitespace handling
    assert normalize_case("  b  ", assay_types) == "B"
    assert normalize_case("\tb\t", assay_types) == "B"
    assert normalize_case("\n f \n", assay_types) == "F"

    # Mixed case
    assert normalize_case("bF", assay_types) is None  # Not a valid assay type
    assert normalize_case("BF", assay_types) is None  # Not a valid assay type

    # Empty and None
    assert normalize_case("", assay_types) is None
    assert normalize_case(None, assay_types) is None
    assert normalize_case("   ", assay_types) is None

    # Non-string types
    assert normalize_case(123, assay_types) is None
    assert normalize_case([], assay_types) is None
    assert normalize_case({}, assay_types) is None

    print("✓ Edge case tests passed!")

if __name__ == "__main__":
    try:
        test_normalization_rules()
        test_profile_normalizers()
        test_edge_cases()
        print("\n🎉 All case normalization and unit canonicalization tests passed!")
        print("\n✅ DQ-002 Implementation Summary:")
        print("   • Case normalization: ✓ Working")
        print("   • Unit canonicalization: ✓ Working")
        print("   • Profile integration: ✓ Ready")
        print("   • Edge cases: ✓ Handled")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
