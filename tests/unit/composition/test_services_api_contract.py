"""Contract tests for composition services_api."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition import services_api

pytestmark = pytest.mark.unit


class TestServicesApiExports:
    """Test public exports and lazy export behavior."""

    def test_services_api_exports__all_declares_public_exports(self) -> None:
        """__all__ should declare all public exports."""
        expected_exports = [
            "cleanup_bronze",
            "get_adr_service",
            "get_audit_service",
            "get_bronze_cleanup_service",
            "get_checkpoint_service",
            "get_config_service",
            "get_contract_migration_service",
            "get_export_service",
            "get_forensic_run_diff_service",
            "get_health_server_dependencies",
            "get_health_service",
            "get_lineage_service",
            "get_lock_service",
            "get_metrics_service",
            "get_observability_workflow_service",
            "get_pipeline_runner_service",
            "get_quarantine_port",
            "get_quarantine_service",
            "get_run_manifest_service",
            "get_vacuum_service",
            "get_workflow_execution_service",
            "get_workflow_inspection_service",
            "get_workflow_runner_service",
            "load_workflow_config",
        ]

        assert services_api.__all__ == expected_exports

    def test_services_api_exports__public_exports_maps_to_modules(self) -> None:
        """_PUBLIC_EXPORTS should map exports to correct modules."""
        expected_mapping = {
            "cleanup_bronze": "bioetl.composition.maintenance_api",
            "get_adr_service": "bioetl.composition.control_plane_api",
            "get_audit_service": "bioetl.composition.observability_api",
            "get_bronze_cleanup_service": "bioetl.composition.maintenance_api",
            "get_checkpoint_service": "bioetl.composition.observability_api",
            "get_config_service": "bioetl.composition.control_plane_api",
            "get_contract_migration_service": "bioetl.composition.maintenance_api",
            "get_export_service": "bioetl.composition.control_plane_api",
            "get_forensic_run_diff_service": "bioetl.composition.control_plane_api",
            "get_health_server_dependencies": "bioetl.composition.health_api",
            "get_health_service": "bioetl.composition.health_api",
            "get_lineage_service": "bioetl.composition.control_plane_api",
            "get_lock_service": "bioetl.composition.control_plane_api",
            "get_metrics_service": "bioetl.composition.observability_api",
            "get_observability_workflow_service": "bioetl.composition.observability_api",
            "get_pipeline_runner_service": "bioetl.composition.execution_api",
            "get_quarantine_port": "bioetl.composition.health_api",
            "get_quarantine_service": "bioetl.composition.health_api",
            "get_run_manifest_service": "bioetl.composition.control_plane_api",
            "get_vacuum_service": "bioetl.composition.maintenance_api",
            "get_workflow_execution_service": "bioetl.composition.control_plane_api",
            "get_workflow_inspection_service": "bioetl.composition.control_plane_api",
            "get_workflow_runner_service": "bioetl.composition.control_plane_api",
            "load_workflow_config": "bioetl.composition.control_plane_api",
        }

        assert services_api._PUBLIC_EXPORTS == expected_mapping


class TestLazyExportBehavior:
    """Test lazy export installation and behavior."""

    def test_services_api_lazy_exports__installed_on_module_load(self) -> None:
        """Lazy exports should be installed on module load."""
        # Check that lazy export attributes exist
        assert hasattr(services_api, "cleanup_bronze")
        assert hasattr(services_api, "get_adr_service")
        assert hasattr(services_api, "get_audit_service")
        assert hasattr(services_api, "get_bronze_cleanup_service")
        assert hasattr(services_api, "get_checkpoint_service")
        assert hasattr(services_api, "get_config_service")
        assert hasattr(services_api, "get_contract_migration_service")
        assert hasattr(services_api, "get_export_service")
        assert hasattr(services_api, "get_forensic_run_diff_service")
        assert hasattr(services_api, "get_health_server_dependencies")
        assert hasattr(services_api, "get_health_service")
        assert hasattr(services_api, "get_lineage_service")
        assert hasattr(services_api, "get_lock_service")
        assert hasattr(services_api, "get_metrics_service")
        assert hasattr(services_api, "get_observability_workflow_service")
        assert hasattr(services_api, "get_pipeline_runner_service")
        assert hasattr(services_api, "get_quarantine_port")
        assert hasattr(services_api, "get_quarantine_service")
        assert hasattr(services_api, "get_run_manifest_service")
        assert hasattr(services_api, "get_vacuum_service")
        assert hasattr(services_api, "get_workflow_execution_service")
        assert hasattr(services_api, "get_workflow_inspection_service")
        assert hasattr(services_api, "get_workflow_runner_service")
        assert hasattr(services_api, "load_workflow_config")


class TestTypeCheckingStubs:
    """Test TYPE_CHECKING type stubs."""

    def test_services_api_type_checking__imports_reference_valid_modules(self) -> None:
        """TYPE_CHECKING imports should reference valid modules."""
        # Verify key facade modules are importable
        import bioetl.composition.health_api
        import bioetl.composition.registry_api
        import bioetl.domain.ports
        import bioetl.domain.workflow

        # Verify modules are importable
        assert bioetl.composition.health_api is not None
        assert bioetl.composition.registry_api is not None
        assert bioetl.domain.ports is not None
        assert bioetl.domain.workflow is not None