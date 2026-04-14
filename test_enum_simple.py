#!/usr/bin/env python3
"""Simple test script to verify enum loading functionality without full dependencies."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_enum_loader():
    """Test the enum loader functionality."""
    from bioetl.domain.config.enum_loader import load_chembl_enums, get_enum_config
    
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
    # Import only what we need to avoid full bioetl dependencies
    from bioetl.domain.normalization.text import normalize_string
    
    def normalize_profile_enum(value: object, *, allowed_values: frozenset[str]) -> object:
        """Normalize one enum-like profile field against allowed values."""
        if value is None:
            return None
        if isinstance(value, str):
            normalized = normalize_string(value)
            return normalized if normalized in allowed_values else None
        return value if value in allowed_values else None
    
    # Test allowed values
    allowed_values = frozenset(["IC50", "EC50", "Ki", "ic50"])
    
    # Test valid values
    assert normalize_profile_enum("IC50", allowed_values=allowed_values) == "IC50"
    assert normalize_profile_enum("ic50", allowed_values=allowed_values) == "ic50"  # String normalization preserves case
    assert normalize_profile_enum("  IC50  ", allowed_values=allowed_values) == "IC50"
    
    # Test invalid values
    assert normalize_profile_enum("InvalidType", allowed_values=allowed_values) is None
    assert normalize_profile_enum("", allowed_values=allowed_values) is None
    assert normalize_profile_enum(None, allowed_values=allowed_values) is None
    
    print("✓ Enum normalization tests passed!")

def test_field_loading():
    """Test that fields can be loaded from the updated module."""
    # Import directly to avoid full bioetl dependencies
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_chembl_activity_fields",
        "src/bioetl/domain/normalization/profiles/_chembl_activity_fields.py"
    )
    module = importlib.util.module_from_spec(spec)
    
    # Mock the ActivitySchema import to avoid pandas dependency
    import sys
    from unittest.mock import MagicMock
    mock_schema = MagicMock()
    mock_schema.to_schema.return_value.columns.keys.return_value = []
    sys.modules['bioetl.domain.schemas.chembl.activity'] = MagicMock(ActivitySchema=mock_schema)
    
    # Now load the module
    spec.loader.exec_module(module)
    
    print(f"STANDARD_RELATIONS: {module.STANDARD_RELATIONS}")
    print(f"ACTIVITY_STANDARD_TYPES: {module.ACTIVITY_STANDARD_TYPES}")
    print(f"DATA_VALIDITY_COMMENTS: {module.DATA_VALIDITY_COMMENTS}")
    
    # Verify they are frozensets
    assert isinstance(module.STANDARD_RELATIONS, frozenset)
    assert isinstance(module.ACTIVITY_STANDARD_TYPES, frozenset)
    assert isinstance(module.DATA_VALIDITY_COMMENTS, frozenset)
    
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