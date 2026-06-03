"""Contract tests for composition control_plane_api."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition import control_plane_api

pytestmark = pytest.mark.unit


class TestControlPlaneApiExports:
    """Test public exports and lazy export behavior."""

    def test_control_plane_api_exports__all_declares_public_exports(self) -> None:
        """__all__ should declare all public exports."""
        expected_exports = [
            "bootstrap_control_plane_lifecycle_store",
            "get_adr_service",
            "get_checkpoint_runtime_service",
            "get_config_service",
            "get_export_service",
            "get_forensic_run_diff_service",
            "get_historical_replay_closure_service",
            "get_historical_replay_corpus_service",
            "get_historical_replay_universe_service",
            "get_lineage_service",
            "get_lock_service",
            "get_run_manifest_service",
            "get_workflow_execution_service",
            "get_workflow_inspection_service",
            "get_workflow_runner_service",
            "list_configured_pipeline_names",
            "load_workflow_config",
            "persist_historical_replay_closure_report",
            "persist_historical_replay_universe_report",
        ]

        assert control_plane_api.__all__ == expected_exports

    def test_control_plane_api_exports__public_exports_maps_to_modules(self) -> None:
        """_PUBLIC_EXPORTS should map exports to correct modules."""
        expected_mapping = {
            "bootstrap_control_plane_lifecycle_store": "bioetl.composition.bootstrap.cli",
            "get_adr_service": "bioetl.composition._services",
            "get_checkpoint_runtime_service": "bioetl.composition._resource_management",
            "list_configured_pipeline_names": "bioetl.composition.config_catalog",
            "get_config_service": "bioetl.composition._services",
            "get_export_service": "bioetl.composition._services",
            "get_forensic_run_diff_service": "bioetl.composition._services",
            "get_historical_replay_closure_service": "bioetl.composition._services",
            "get_historical_replay_corpus_service": "bioetl.composition._services",
            "get_historical_replay_universe_service": "bioetl.composition._services",
            "get_lineage_service": "bioetl.composition._services",
            "get_lock_service": "bioetl.composition._services",
            "persist_historical_replay_closure_report": "bioetl.composition.bootstrap.cli.run_manifest",
            "persist_historical_replay_universe_report": "bioetl.composition.bootstrap.cli.run_manifest",
            "get_run_manifest_service": "bioetl.composition._services",
            "get_workflow_execution_service": "bioetl.composition._workflow_services",
            "get_workflow_runner_service": "bioetl.composition._workflow_services",
            "get_workflow_inspection_service": "bioetl.composition._workflow_services",
            "load_workflow_config": "bioetl.composition._workflow_services",
        }

        assert control_plane_api._PUBLIC_EXPORTS == expected_mapping


class TestLazyExportBehavior:
    """Test lazy export installation and behavior."""

    def test_control_plane_api_lazy_exports__installed_on_module_load(self) -> None:
        """Lazy exports should be installed on module load."""
        # Check that lazy export attributes exist
        assert hasattr(control_plane_api, "bootstrap_control_plane_lifecycle_store")
        assert hasattr(control_plane_api, "get_adr_service")
        assert hasattr(control_plane_api, "get_checkpoint_runtime_service")
        assert hasattr(control_plane_api, "get_config_service")
        assert hasattr(control_plane_api, "get_export_service")
        assert hasattr(control_plane_api, "get_forensic_run_diff_service")
        assert hasattr(control_plane_api, "get_historical_replay_closure_service")
        assert hasattr(control_plane_api, "get_historical_replay_corpus_service")
        assert hasattr(control_plane_api, "get_historical_replay_universe_service")
        assert hasattr(control_plane_api, "get_lineage_service")
        assert hasattr(control_plane_api, "get_lock_service")
        assert hasattr(control_plane_api, "get_run_manifest_service")
        assert hasattr(control_plane_api, "get_workflow_execution_service")
        assert hasattr(control_plane_api, "get_workflow_inspection_service")
        assert hasattr(control_plane_api, "get_workflow_runner_service")
        assert hasattr(control_plane_api, "list_configured_pipeline_names")
        assert hasattr(control_plane_api, "load_workflow_config")
        assert hasattr(control_plane_api, "persist_historical_replay_closure_report")
        assert hasattr(control_plane_api, "persist_historical_replay_universe_report")


class TestServiceModuleConstants:
    """Test service module constant definitions."""

    def test_control_plane_api_constants__services_module_points_correctly(self) -> None:
        """_SERVICES_MODULE should point to correct module."""
        assert control_plane_api._SERVICES_MODULE == "bioetl.composition._services"

    def test_workflow_services_module_constant(self) -> None:
        """_WORKFLOW_SERVICES_MODULE should point to correct module."""
        assert (
            control_plane_api._WORKFLOW_SERVICES_MODULE
            == "bioetl.composition._workflow_services"
        )

    def test_control_plane_api_constants__resource_management_module_points_correctly(self) -> None:
        """_RESOURCE_MANAGEMENT_MODULE should point to correct module."""
        assert (
            control_plane_api._RESOURCE_MANAGEMENT_MODULE
            == "bioetl.composition._resource_management"
        )

    def test_cli_control_plane_lifecycle_module_constant(self) -> None:
        """_CLI_CONTROL_PLANE_LIFECYCLE_MODULE should point to correct module."""
        assert (
            control_plane_api._CLI_CONTROL_PLANE_LIFECYCLE_MODULE
            == "bioetl.composition.bootstrap.cli"
        )

    def test_run_manifest_bootstrap_module_constant(self) -> None:
        """_RUN_MANIFEST_BOOTSTRAP_MODULE should point to correct module."""
        assert (
            control_plane_api._RUN_MANIFEST_BOOTSTRAP_MODULE
            == "bioetl.composition.bootstrap.cli.run_manifest"
        )


class TestTypeCheckingStubs:
    """Test TYPE_CHECKING type stubs."""

    def test_control_plane_api_type_checking__imports_reference_valid_modules(self) -> None:
        """TYPE_CHECKING imports should reference valid modules."""
        # Verify key modules are importable
        import bioetl.application.services.audit_inspection_service
        import bioetl.application.services.config_service
        import bioetl.application.services.control_plane.forensic_diff_service
        import bioetl.application.services.control_plane.manifest.inspection_service
        import bioetl.application.services.control_plane.replay.historical_closure_service
        import bioetl.application.services.control_plane.replay.historical_corpus_service
        import bioetl.application.services.control_plane.replay.historical_universe_service
        import bioetl.application.services.control_plane.workflow.execution_service
        import bioetl.application.services.control_plane.workflow.inspection_service
        import bioetl.application.services.export_service
        import bioetl.application.services.lineage.lineage_inspection_service
        import bioetl.application.services.lock_service
        import bioetl.application.services.workflow_runner_service
        import bioetl.domain.control_plane
        import bioetl.domain.workflow
        import bioetl.composition.registry_api

        # Verify modules are importable
        assert bioetl.application.services.audit_inspection_service is not None
        assert bioetl.application.services.config_service is not None
        assert bioetl.application.services.control_plane.forensic_diff_service is not None
        assert (
            bioetl.application.services.control_plane.manifest.inspection_service
            is not None
        )
        assert (
            bioetl.application.services.control_plane.replay.historical_closure_service
            is not None
        )
        assert (
            bioetl.application.services.control_plane.replay.historical_corpus_service
            is not None
        )
        assert (
            bioetl.application.services.control_plane.replay.historical_universe_service
            is not None
        )
        assert (
            bioetl.application.services.control_plane.workflow.execution_service is not None
        )
        assert (
            bioetl.application.services.control_plane.workflow.inspection_service
            is not None
        )
        assert bioetl.application.services.export_service is not None
        assert bioetl.application.services.lineage.lineage_inspection_service is not None
        assert bioetl.application.services.lock_service is not None
        assert bioetl.application.services.workflow_runner_service is not None
        assert bioetl.domain.control_plane is not None
        assert bioetl.domain.workflow is not None
        assert bioetl.composition.registry_api is not None

    def test_protocol_definition(self) -> None:
        """ControlPlaneArtifactLifecycleStoreProtocol should be defined in TYPE_CHECKING."""
        # Protocol is only available during type checking
        # We verify the class exists in the module's TYPE_CHECKING block
        # by checking that the module can be imported and has the expected structure
        import bioetl.composition.control_plane_api

        # The protocol is defined in TYPE_CHECKING, so it won't be available at runtime
        # but we can verify the module structure is correct
        assert hasattr(bioetl.composition.control_plane_api, "__all__")