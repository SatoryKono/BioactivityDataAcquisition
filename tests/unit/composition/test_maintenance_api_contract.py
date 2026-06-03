"""Contract tests for composition maintenance_api."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition import maintenance_api

pytestmark = pytest.mark.unit


class TestMaintenanceApiExports:
    """Test public exports and lazy export behavior."""

    def test_maintenance_api_exports__all_declares_public_exports(self) -> None:
        """__all__ should declare all public exports."""
        expected_exports = [
            "archive_table",
            "cleanup_bronze",
            "get_bronze_cleanup_service",
            "get_contract_migration_service",
            "get_lifecycle_service",
            "get_vacuum_service",
            "preview_cleanup",
            "vacuum_table",
        ]

        assert maintenance_api.__all__ == expected_exports

    def test_maintenance_api_exports__public_exports_maps_to_modules(self) -> None:
        """_PUBLIC_EXPORTS should map exports to correct modules."""
        expected_mapping = {
            "archive_table": "bioetl.composition._resource_management",
            "cleanup_bronze": "bioetl.composition._services",
            "get_bronze_cleanup_service": "bioetl.composition._services",
            "get_contract_migration_service": "bioetl.composition._services",
            "get_lifecycle_service": "bioetl.composition._resource_management",
            "get_vacuum_service": "bioetl.composition._services",
            "preview_cleanup": "bioetl.composition._resource_management",
            "vacuum_table": "bioetl.composition._resource_management",
        }

        assert maintenance_api._PUBLIC_EXPORTS == expected_mapping


class TestModuleConstants:
    """Test module constant definitions."""

    def test_services_module_constant(self) -> None:
        """_SERVICES_MODULE should point to correct module."""
        assert maintenance_api._SERVICES_MODULE == "bioetl.composition._services"

    def test_maintenance_api_constants__resource_management_module_points_correctly(self) -> None:
        """_RESOURCE_MANAGEMENT_MODULE should point to correct module."""
        assert (
            maintenance_api._RESOURCE_MANAGEMENT_MODULE
            == "bioetl.composition._resource_management"
        )


class TestLazyExportBehavior:
    """Test lazy export installation and behavior."""

    def test_maintenance_api_lazy_exports__installed_on_module_load(self) -> None:
        """Lazy exports should be installed on module load."""
        # Check that lazy export attributes exist
        assert hasattr(maintenance_api, "archive_table")
        assert hasattr(maintenance_api, "cleanup_bronze")
        assert hasattr(maintenance_api, "get_bronze_cleanup_service")
        assert hasattr(maintenance_api, "get_contract_migration_service")
        assert hasattr(maintenance_api, "get_lifecycle_service")
        assert hasattr(maintenance_api, "get_vacuum_service")
        assert hasattr(maintenance_api, "preview_cleanup")
        assert hasattr(maintenance_api, "vacuum_table")


class TestTypeCheckingStubs:
    """Test TYPE_CHECKING type stubs."""

    def test_maintenance_api_type_checking__imports_reference_valid_modules(self) -> None:
        """TYPE_CHECKING imports should reference valid modules."""
        # Verify key modules are importable
        import bioetl.application.services.bronze_cleanup_service
        import bioetl.application.services.contract_migration_service
        import bioetl.application.services.medallion_lifecycle
        import bioetl.application.services.vacuum_service
        import bioetl.composition._pipeline_execution
        import bioetl.composition._resource_management

        # Verify modules are importable
        assert bioetl.application.services.bronze_cleanup_service is not None
        assert bioetl.application.services.contract_migration_service is not None
        assert bioetl.application.services.medallion_lifecycle is not None
        assert bioetl.application.services.vacuum_service is not None
        assert bioetl.composition._pipeline_execution is not None
        assert bioetl.composition._resource_management is not None