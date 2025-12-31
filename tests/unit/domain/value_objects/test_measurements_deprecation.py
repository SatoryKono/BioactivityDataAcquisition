"""Tests for measurements module deprecation warning.

The measurements module is deprecated and should emit a DeprecationWarning
when imported. This test ensures backward compatibility while maintaining
proper deprecation notices.
"""

from __future__ import annotations

import warnings

import pytest


@pytest.mark.unit
class TestMeasurementsDeprecation:
    """Test measurements module deprecation."""

    def test_import_emits_deprecation_warning(self) -> None:
        """Test that importing measurements module emits DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Force reimport by removing from cache if present
            import sys
            if "bioetl.domain.value_objects.measurements" in sys.modules:
                del sys.modules["bioetl.domain.value_objects.measurements"]

            # Import the deprecated module
            import bioetl.domain.value_objects.measurements  # noqa: F401

            # Check that a DeprecationWarning was issued
            deprecation_warnings = [
                warning for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) >= 1

            # Check the warning message
            msg = str(deprecation_warnings[0].message)
            assert "measurements" in msg.lower()
            assert "deprecated" in msg.lower()

    def test_reexports_activity_values(self) -> None:
        """Test that measurements re-exports symbols from activity_values."""
        import sys
        if "bioetl.domain.value_objects.measurements" in sys.modules:
            del sys.modules["bioetl.domain.value_objects.measurements"]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from bioetl.domain.value_objects import measurements

            # Verify all expected symbols are re-exported
            assert hasattr(measurements, "ActivityType")
            assert hasattr(measurements, "Concentration")
            assert hasattr(measurements, "ConcentrationUnit")
            assert hasattr(measurements, "PChemblValue")

            # Verify __all__ contains expected exports
            expected = {"ActivityType", "Concentration", "ConcentrationUnit", "PChemblValue"}
            assert set(measurements.__all__) == expected
