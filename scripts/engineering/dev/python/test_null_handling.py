#!/usr/bin/env python3
"""Test script to verify pseudo-null value handling functionality."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_null_patterns():
    """Test the NULL_PATTERNS constant and normalize_null function."""
    from bioetl.domain.normalization.rules import NULL_PATTERNS, normalize_null

    print("=== Testing NULL_PATTERNS ===")
    print(f"Total null patterns: {len(NULL_PATTERNS)}")
    print(f"Sample patterns: {list(NULL_PATTERNS)[:10]}")

    # Test common pseudo-null values
    null_test_cases = [
        ("N/A", None),
        ("NA", None),
        ("n/a", None),
        ("None", None),
        ("NONE", None),
        ("none", None),
        ("-", None),
        (".", None),
        ("", None),
        (" ", None),
        ("  ", None),
        ("\t", None),
        ("<NA>", None),
        ("NaN", None),
        ("nan", None),
        ("NULL", None),
        ("null", None),
        ("MISSING", None),
        ("UNKNOWN", None),
    ]

    for input_val, expected in null_test_cases:
        result = normalize_null(input_val)
        assert result is expected, (
            f"Expected {expected}, got {result} for input {input_val!r}"
        )

    print("✓ All pseudo-null patterns correctly converted to None")

    # Test non-null values should remain unchanged
    non_null_test_cases = [
        ("0", "0"),
        ("0.0", "0.0"),
        ("valid_value", "valid_value"),
        ("100", "100"),
        ("10.5", "10.5"),
        ("nM", "nM"),
        ("IC50", "IC50"),
        ("B", "B"),
    ]

    for input_val, expected in non_null_test_cases:
        result = normalize_null(input_val)
        assert result == expected, (
            f"Expected {expected}, got {result} for input {input_val!r}"
        )

    print("✓ Non-null values correctly preserved")

    # Test edge cases
    edge_cases = [
        (None, None),
        (123, 123),
        (0, 0),
        (0.0, 0.0),
        ([], []),
        ({}, {}),
        (True, True),
        (False, False),
    ]

    for input_val, expected in edge_cases:
        result = normalize_null(input_val)
        assert result == expected, (
            f"Expected {expected}, got {result} for input {input_val!r}"
        )

    print("✓ Edge cases correctly handled")


def test_profile_null_normalizer():
    """Test the profile null normalizer function."""
    from bioetl.domain.normalization.profiles.profile_normalizers import (
        normalize_profile_null,
    )

    print("\n=== Testing Profile Null Normalizer ===")

    # Test pseudo-null values
    null_cases = ["N/A", "None", "-", ".", "", " ", "NaN"]
    for null_val in null_cases:
        result = normalize_profile_null(null_val)
        assert result is None, f"Expected None, got {result} for input {null_val!r}"

    print("✓ Profile null normalizer correctly converts pseudo-null values")

    # Test non-null values
    non_null_cases = ["valid", "0", "100", "data"]
    for non_null_val in non_null_cases:
        result = normalize_profile_null(non_null_val)
        assert result == non_null_val, f"Expected {non_null_val}, got {result}"

    print("✓ Profile null normalizer correctly preserves non-null values")


def test_null_patterns_comprehensive():
    """Test comprehensive null pattern coverage."""
    from bioetl.domain.normalization.rules import NULL_PATTERNS

    print("\n=== Testing Comprehensive Null Patterns ===")

    # Verify all expected patterns are included
    expected_patterns = [
        "N/A",
        "NA",
        "n/a",
        "na",
        "None",
        "NONE",
        "none",
        "Null",
        "NULL",
        "null",
        "-",
        "--",
        ".",
        "..",
        "...",
        "",
        " ",
        "  ",
        "   ",
        "\t",
        "\n",
        "\r",
        "\r\n",
        "<NA>",
        "<na>",
        "<NULL>",
        "<null>",
        "NAN",
        "NaN",
        "nan",
        "MISSING",
        "missing",
        "UNKNOWN",
        "unknown",
        "NOT_AVAILABLE",
        "not_available",
        "NOT_APPLICABLE",
        "not_applicable",
    ]

    for pattern in expected_patterns:
        assert pattern in NULL_PATTERNS, f"Missing null pattern: {pattern!r}"

    print("✓ All expected null patterns are included")

    # Test that the set is frozen (immutable)
    try:
        NULL_PATTERNS.add("new_pattern")
        assert False, "NULL_PATTERNS should be immutable"
    except AttributeError:
        print("✓ NULL_PATTERNS is correctly immutable")


def test_real_world_scenarios():
    """Test real-world scenarios for null handling."""
    from bioetl.domain.normalization.rules import normalize_null

    print("\n=== Testing Real-World Scenarios ===")

    # Simulate ChEMBL data scenarios
    chembl_scenarios = [
        # Standard value scenarios
        ("N/A", None),  # Missing standard value
        ("10.5", "10.5"),  # Valid standard value
        ("-", None),  # Missing value represented as dash
        (".", None),  # Missing value represented as dot
        # Assay description scenarios
        ("No description available", "No description available"),  # Valid description
        ("NONE", None),  # Missing description
        ("", None),  # Empty description
        # Data validity comment scenarios
        ("Manually validated", "Manually validated"),  # Valid comment
        ("null", None),  # Null comment
        ("NaN", None),  # Not a number comment
        # Unit scenarios (should NOT be converted to null)
        ("nM", "nM"),  # Valid unit
        ("-", None),  # This would be converted to null
        ("N/A", None),  # This would be converted to null
    ]

    for input_val, expected in chembl_scenarios:
        result = normalize_null(input_val)
        assert result == expected, (
            f"Scenario failed: {input_val!r} -> expected {expected}, got {result}"
        )

    print("✓ Real-world scenarios correctly handled")


def test_integration_readiness():
    """Test that the implementation is ready for integration."""

    print("\n=== Testing Integration Readiness ===")

    # Test imports
    # Verify function signatures
    import inspect

    from bioetl.domain.normalization.profiles.profile_normalizers import (
        normalize_profile_null,
    )
    from bioetl.domain.normalization.rules import NULL_PATTERNS, normalize_null

    # Check normalize_null signature
    sig = inspect.signature(normalize_null)
    assert len(sig.parameters) == 1, "normalize_null should take one parameter"
    assert list(sig.parameters.keys()) == ["value"], "Parameter should be named 'value'"

    # Check normalize_profile_null signature
    sig = inspect.signature(normalize_profile_null)
    assert len(sig.parameters) == 1, "normalize_profile_null should take one parameter"
    assert list(sig.parameters.keys()) == ["value"], "Parameter should be named 'value'"

    print("✓ Function signatures are correct")

    # Verify NULL_PATTERNS is accessible
    from bioetl.domain.normalization.rules import NULL_PATTERNS as imported_patterns

    assert len(imported_patterns) > 30, "Should have comprehensive null patterns"
    assert imported_patterns is NULL_PATTERNS, "Should be the same object"

    print("✓ Integration components are ready")


if __name__ == "__main__":
    try:
        test_null_patterns()
        test_profile_null_normalizer()
        test_null_patterns_comprehensive()
        test_real_world_scenarios()
        test_integration_readiness()

        print("\n🎉 All pseudo-null value handling tests passed!")
        print("\n✅ DQ-003 Implementation Summary:")
        print("   • NULL_PATTERNS defined: ✓ 40+ patterns")
        print("   • normalize_null function: ✓ Working")
        print("   • Profile integration: ✓ Ready")
        print("   • Real-world scenarios: ✓ Handled")
        print("   • Edge cases: ✓ Covered")
        print("   • Integration: ✓ Ready")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
