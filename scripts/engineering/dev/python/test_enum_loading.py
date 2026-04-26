#!/usr/bin/env python3
"""Test script to verify enum loading functionality."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_enum_loader():
    """Test the enum loader functionality."""
    from bioetl.domain.config.enum_loader import get_enum_config, load_chembl_enums

    # Test loading the full config
    enums = load_chembl_enums()
    print(f"Loaded {len(enums)} enum sections")
    print(f"Sections: {list(enums.keys())}")

    # Test getting specific enum configs
    standard_relations = get_enum_config("activity", "standard_relations")
    print(f"Standard relations: {standard_relations}")

    standard_types = get_enum_config("activity", "standard_types")
    print(f"Standard types: {standard_types}")

    data_validity_comments = get_enum_config("activity", "data_validity_comments")
    print(f"Data validity comments: {data_validity_comments}")

    print("✓ Enum loader tests passed!")


def test_normalize_enum():
    """Test the enum normalization function."""
    from bioetl.domain.normalization.profiles.profile_normalizers import (
        normalize_profile_enum,
    )

    # Test allowed values
    allowed_values = frozenset(["IC50", "EC50", "Ki"])

    # Test valid values
    assert normalize_profile_enum("IC50", allowed_values=allowed_values) == "IC50"
    assert (
        normalize_profile_enum("ic50", allowed_values=allowed_values) == "ic50"
    )  # Should be normalized by string normalization
    assert normalize_profile_enum("  IC50  ", allowed_values=allowed_values) == "IC50"

    # Test invalid values
    assert normalize_profile_enum("InvalidType", allowed_values=allowed_values) is None
    assert normalize_profile_enum("", allowed_values=allowed_values) is None
    assert normalize_profile_enum(None, allowed_values=allowed_values) is None

    print("✓ Enum normalization tests passed!")


def test_field_loading():
    """Test that fields can be loaded from the updated module."""
    from bioetl.domain.normalization.profiles._chembl_activity_fields import (
        ACTIVITY_STANDARD_TYPES,
        DATA_VALIDITY_COMMENTS,
        STANDARD_RELATIONS,
    )

    print(f"STANDARD_RELATIONS: {STANDARD_RELATIONS}")
    print(f"ACTIVITY_STANDARD_TYPES: {ACTIVITY_STANDARD_TYPES}")
    print(f"DATA_VALIDITY_COMMENTS: {DATA_VALIDITY_COMMENTS}")

    # Verify they are frozensets
    assert isinstance(STANDARD_RELATIONS, frozenset)
    assert isinstance(ACTIVITY_STANDARD_TYPES, frozenset)
    assert isinstance(DATA_VALIDITY_COMMENTS, frozenset)

    print("✓ Field loading tests passed!")


if __name__ == "__main__":
    try:
        test_enum_loader()
        test_normalize_enum()
        test_field_loading()
        print("\n🎉 All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
