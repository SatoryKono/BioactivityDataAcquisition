#!/usr/bin/env python3
"""Test script to verify case normalization and unit canonicalization functionality."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_normalization_rules():
    """Test the normalization rules functionality."""
    from bioetl.domain.normalization.rules import normalize_case, normalize_unit, UNIT_MAPPING
    
    print("=== Testing Case Normalization ===")
    
    # Test case normalization with allowed values
    assay_types = frozenset(["B", "F", "A", "T", "P", "U"])
    
    # Valid cases
    assert normalize_case("b", assay_types) == "B"
    assert normalize_case("B", assay_types) == "B"
    assert normalize_case("  f  ", assay_types) == "F"
    assert normalize_case("a", assay_types) == "A"
    
    # Invalid cases
    assert normalize_case("X", assay_types) is None
    assert normalize_case("invalid", assay_types) is None
    assert normalize_case(None, assay_types) is None
    assert normalize_case(123, assay_types) is None
    
    print("✓ Case normalization tests passed!")
    
    print("\n=== Testing Unit Canonicalization ===")
    
    # Test unit canonicalization
    assert normalize_unit("nM") == "nM"
    assert normalize_unit("NM") == "nM"
    assert normalize_unit("nm") == "nM"
    assert normalize_unit("uM") == "µM"
    assert normalize_unit("UM") == "µM"
    assert normalize_unit("µM") == "µM"
    assert normalize_unit("mM") == "mM"
    assert normalize_unit("MM") == "mM"
    assert normalize_unit("percent") == "%"
    assert normalize_unit("PERCENT") == "%"
    
    # Unknown units should pass through
    assert normalize_unit("unknown_unit") == "unknown_unit"
    
    # Invalid inputs
    assert normalize_unit(None) is None
    assert normalize_unit(123) is None
    assert normalize_unit("") is None
    assert normalize_unit("  ") is None
    
    print("✓ Unit canonicalization tests passed!")
    
    print(f"\n=== Unit Mapping Info ===")
    print(f"Total unit mappings: {len(UNIT_MAPPING)}")
    print(f"Sample mappings: {list(UNIT_MAPPING.items())[:5]}")

def test_profile_integration():
    """Test that the profile integration works correctly."""
    # Test imports work
    from bioetl.domain.normalization.profiles.chembl_activity import (
        ASSAY_TYPES,
        ACTIVITY_STANDARD_TYPES,
        CHEMBL_ACTIVITY_PROFILE,
    )
    
    print("\n=== Testing Profile Integration ===")
    
    # Verify constants
    assert "B" in ASSAY_TYPES
    assert "F" in ASSAY_TYPES
    assert "IC50" in ACTIVITY_STANDARD_TYPES
    assert "EC50" in ACTIVITY_STANDARD_TYPES
    
    # Verify profile was created
    assert CHEMBL_ACTIVITY_PROFILE is not None
    assert CHEMBL_ACTIVITY_PROFILE.profile_name == "chembl.activity"
    
    print("✓ Profile integration tests passed!")

def test_normalize_functions():
    """Test the profile normalizer functions."""
    from bioetl.domain.normalization.profiles.profile_normalizers import (
        normalize_profile_case,
        normalize_profile_unit,
    )
    
    print("\n=== Testing Profile Normalizer Functions ===")
    
    # Test case normalizer
    assay_types = frozenset(["B", "F", "A", "T", "P", "U"])
    assert normalize_profile_case("b", allowed_values=assay_types) == "B"
    assert normalize_profile_case("F", allowed_values=assay_types) == "F"
    assert normalize_profile_case("invalid", allowed_values=assay_types) is None
    
    # Test unit normalizer
    assert normalize_profile_unit("nM") == "nM"
    assert normalize_profile_unit("NM") == "nM"
    assert normalize_profile_unit("unknown") == "unknown"
    assert normalize_profile_unit(None) is None
    
    print("✓ Profile normalizer function tests passed!")

if __name__ == "__main__":
    try:
        test_normalization_rules()
        test_profile_integration()
        test_normalize_functions()
        print("\n🎉 All case normalization and unit canonicalization tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)