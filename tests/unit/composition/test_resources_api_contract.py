"""Contract tests for composition resources_api."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition import resources_api

pytestmark = pytest.mark.unit


class TestResourcesApiExports:
    """Test public exports and lazy export behavior."""

    def test_resources_api_exports__all_declares_public_exports(self) -> None:
        """__all__ should declare all public exports."""
        expected_exports = [
            "ArchiveOptions",
            "VacuumOptions",
            "archive_table",
            "get_checkpoint_runtime_service",
            "get_lifecycle_service",
            "get_quarantine_runtime_service",
            "inspect_quarantine",
            "list_checkpoints",
            "preview_cleanup",
            "vacuum_table",
        ]

        assert resources_api.__all__ == expected_exports

    def test_resources_api_exports__public_exports_maps_to_modules(self) -> None:
        """_PUBLIC_EXPORTS should map exports to correct modules."""
        expected_mapping = {
            "ArchiveOptions": "bioetl.composition._pipeline_execution",
            "VacuumOptions": "bioetl.composition._pipeline_execution",
            "archive_table": "bioetl.composition._resource_management",
            "get_checkpoint_runtime_service": "bioetl.composition._resource_management",
            "get_lifecycle_service": "bioetl.composition._resource_management",
            "get_quarantine_runtime_service": "bioetl.composition._resource_management",
            "inspect_quarantine": "bioetl.composition._resource_management",
            "list_checkpoints": "bioetl.composition._resource_management",
            "preview_cleanup": "bioetl.composition._resource_management",
            "vacuum_table": "bioetl.composition._resource_management",
        }

        assert resources_api._PUBLIC_EXPORTS == expected_mapping


class TestModuleConstants:
    """Test module constant definitions."""

    def test_resources_api_constants__resource_management_module_points_correctly(self) -> None:
        """_RESOURCE_MANAGEMENT_MODULE should point to correct module."""
        assert (
            resources_api._RESOURCE_MANAGEMENT_MODULE
            == "bioetl.composition._resource_management"
        )

    def test_pipeline_execution_module_constant(self) -> None:
        """_PIPELINE_EXECUTION_MODULE should point to correct module."""
        assert (
            resources_api._PIPELINE_EXECUTION_MODULE
            == "bioetl.composition._pipeline_execution"
        )


class TestLazyExportBehavior:
    """Test lazy export installation and behavior."""

    def test_resources_api_lazy_exports__installed_on_module_load(self) -> None:
        """Lazy exports should be installed on module load."""
        # Check that lazy export attributes exist
        assert hasattr(resources_api, "ArchiveOptions")
        assert hasattr(resources_api, "VacuumOptions")
        assert hasattr(resources_api, "archive_table")
        assert hasattr(resources_api, "get_checkpoint_runtime_service")
        assert hasattr(resources_api, "get_lifecycle_service")
        assert hasattr(resources_api, "get_quarantine_runtime_service")
        assert hasattr(resources_api, "inspect_quarantine")
        assert hasattr(resources_api, "list_checkpoints")
        assert hasattr(resources_api, "preview_cleanup")
        assert hasattr(resources_api, "vacuum_table")


class TestTypeCheckingStubs:
    """Test TYPE_CHECKING type stubs."""

    def test_resources_api_type_checking__imports_reference_valid_modules(self) -> None:
        """TYPE_CHECKING imports should reference valid modules."""
        # Verify key modules are importable
        import bioetl.composition._json_types
        import bioetl.composition._pipeline_execution
        import bioetl.composition._resource_management

        # Verify modules are importable
        assert bioetl.composition._json_types is not None
        assert bioetl.composition._pipeline_execution is not None
        assert bioetl.composition._resource_management is not None