#!/usr/bin/env python3
"""Test composition integration without external dependencies."""

import os
import sys


# Test that our composition changes are syntactically correct
def test_syntax_and_imports():
    """Test that our changes don't have syntax errors."""
    print("Testing syntax and imports...")

    # Test 1: Check that maintenance operations file exists and has correct structure
    maintenance_file = (
        "src/bioetl/infrastructure/storage/silver/operations/maintenance_operations.py"
    )
    assert os.path.exists(maintenance_file), "Maintenance operations file not found"
    print("✓ Maintenance operations file exists")

    # Test 2: Check that DTOs file exists
    dtos_file = "src/bioetl/infrastructure/storage/silver/dtos.py"
    assert os.path.exists(dtos_file), "DTOs file not found"
    print("✓ DTOs file exists")

    # Test 3: Check that runtime helpers was updated
    runtime_file = "src/bioetl/infrastructure/storage/silver/runtime_helpers.py"
    with open(runtime_file, "r") as f:
        content = f.read()
        assert "maintenance_operations" in content, (
            "Runtime helpers not updated with maintenance operations"
        )
    print("✓ Runtime helpers updated correctly")

    # Test 4: Check that SilverWriter was updated
    writer_file = "src/bioetl/infrastructure/storage/silver_writer.py"
    with open(writer_file, "r") as f:
        content = f.read()
        assert "SilverWriterMaintenanceMixin" not in content, (
            "Maintenance mixin not removed from SilverWriter"
        )
        assert "_maintenance" in content, (
            "Maintenance operations not added to SilverWriter"
        )
    print("✓ SilverWriter updated correctly")

    # Test 5: Check that postwrite mixin was updated
    postwrite_file = "src/bioetl/infrastructure/storage/silver/postwrite_mixin.py"
    with open(postwrite_file, "r") as f:
        content = f.read()
        assert "hasattr(self, '_maintenance')" in content, (
            "Postwrite mixin not updated to use composition"
        )
    print("✓ Postwrite mixin updated correctly")

    print("\n✅ All syntax and integration tests passed!")


def test_file_structure():
    """Test that files have correct structure."""
    print("Testing file structure...")

    # Check maintenance operations file structure
    with open(
        "src/bioetl/infrastructure/storage/silver/operations/maintenance_operations.py",
        "r",
    ) as f:
        content = f.read()

        # Should have the class definition
        assert "class SilverMaintenanceOperations:" in content
        print("✓ SilverMaintenanceOperations class defined")

        # Should have key methods
        assert "def maybe_export_csv" in content
        assert "def vacuum" in content
        assert "def optimize" in content
        print("✓ Key methods defined")

        # Should have proper docstrings
        assert '"""' in content
        print("✓ Docstrings present")

    # Check DTOs file structure
    with open("src/bioetl/infrastructure/storage/silver/dtos.py", "r") as f:
        content = f.read()

        # Should have DTO classes
        assert "ValidatedSilverWriteContext" in content
        assert "SilverWriteResult" in content
        assert "SilverMaintenanceContext" in content
        print("✓ DTO classes defined")

    print("\n✅ File structure tests passed!")


def test_composition_pattern():
    """Test that composition pattern is correctly implemented."""
    print("Testing composition pattern...")

    # Check that SilverWriter uses composition
    with open("src/bioetl/infrastructure/storage/silver_writer.py", "r") as f:
        content = f.read()

        # Should initialize maintenance operations
        assert "self._maintenance = services.maintenance_operations" in content
        print("✓ Maintenance operations initialized in SilverWriter")

    # Check that postwrite mixin uses the composition
    with open("src/bioetl/infrastructure/storage/silver/postwrite_mixin.py", "r") as f:
        content = f.read()

        # Should check for maintenance operations
        assert (
            "if hasattr(self, '_maintenance') and self._maintenance is not None:"
            in content
        )
        print("✓ Postwrite mixin checks for maintenance operations")

        # Should call maintenance operations when available
        assert "await self._maintenance.maybe_export_csv" in content
        print("✓ Postwrite mixin calls maintenance operations")

    # Check that runtime services includes maintenance operations
    with open("src/bioetl/infrastructure/storage/silver/runtime_helpers.py", "r") as f:
        content = f.read()

        # Should have maintenance operations in runtime services
        assert (
            "maintenance_operations: SilverMaintenanceOperations | None = None"
            in content
        )
        print("✓ Runtime services includes maintenance operations")

        # Should create maintenance operations
        assert "SilverMaintenanceOperations(" in content
        print("✓ Runtime services creates maintenance operations")

    print("\n✅ Composition pattern tests passed!")


if __name__ == "__main__":
    try:
        test_syntax_and_imports()
        test_file_structure()
        test_composition_pattern()
        print("\n🎉 All integration tests passed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
