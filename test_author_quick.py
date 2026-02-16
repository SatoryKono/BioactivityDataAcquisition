#!/usr/bin/env python
"""Quick test for author normalization changes."""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bioetl.domain.services.author_normalization_service import AuthorNormalizationService

def test_basic():
    """Test basic functionality."""
    service = AuthorNormalizationService()

    # Test 1: List of strings
    print("Test 1: List of strings")
    result = service.normalize_author_list(["John Doe", "Jane Smith"])
    parsed = json.loads(result)
    assert parsed == ["John Doe", "Jane Smith"], f"Expected ['John Doe', 'Jane Smith'], got {parsed}"
    print("✓ PASSED")

    # Test 2: Semicolon delimited
    print("\nTest 2: Semicolon delimited")
    result = service.normalize_author_list("John Doe; Jane Smith")
    parsed = json.loads(result)
    assert parsed == ["John Doe", "Jane Smith"], f"Expected ['John Doe', 'Jane Smith'], got {parsed}"
    print("✓ PASSED")

    # Test 3: Dict with name key
    print("\nTest 3: Dict with name key")
    result = service.normalize_author_list([{"name": "John Doe"}, {"name": "Jane Smith"}])
    parsed = json.loads(result)
    assert parsed == ["John Doe", "Jane Smith"], f"Expected ['John Doe', 'Jane Smith'], got {parsed}"
    print("✓ PASSED")

    # Test 4: Empty inputs
    print("\nTest 4: Empty inputs")
    assert service.normalize_author_list(None) is None
    assert service.normalize_author_list([]) is None
    assert service.normalize_author_list("") is None
    print("✓ PASSED")

    # Test 5: Whitespace normalization
    print("\nTest 5: Whitespace normalization")
    result = service.normalize_author_list(["  John Doe  ", "Jane Smith"])
    parsed = json.loads(result)
    assert parsed == ["John Doe", "Jane Smith"], f"Expected ['John Doe', 'Jane Smith'], got {parsed}"
    print("✓ PASSED")

    print("\n" + "="*50)
    print("ALL TESTS PASSED ✓")
    print("="*50)

if __name__ == "__main__":
    try:
        test_basic()
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
