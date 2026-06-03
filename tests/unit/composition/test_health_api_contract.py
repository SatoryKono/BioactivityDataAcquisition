"""Contract tests for composition health_api."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition import health_api

pytestmark = pytest.mark.unit


class TestHealthApiExports:
    """Test public exports and lazy export behavior."""

    def test_health_api_exports__all_declares_public_exports(self) -> None:
        """__all__ should declare all public exports."""
        expected_exports = [
            "HealthServerDependencies",
            "HealthServerDependenciesProtocol",
            "get_health_server_dependencies",
            "get_health_service",
            "get_quarantine_port",
            "get_quarantine_runtime_service",
            "get_quarantine_service",
            "get_runtime_settings",
        ]

        assert health_api.__all__ == expected_exports

    def test_health_api_exports__public_exports_maps_to_modules(self) -> None:
        """_PUBLIC_EXPORTS should map exports to correct modules."""
        expected_mapping = {
            "HealthServerDependencies": "bioetl.composition.bootstrap.cli.health",
            "get_health_service": "bioetl.composition._services",
            "get_quarantine_runtime_service": "bioetl.composition._resource_management",
        }

        assert health_api._PUBLIC_EXPORTS == expected_mapping


class TestModuleConstants:
    """Test module constant definitions."""

    def test_health_api_constants__services_module_points_correctly(self) -> None:
        """_SERVICES_MODULE should point to correct module."""
        assert health_api._SERVICES_MODULE == "bioetl.composition._services"

    def test_bootstrap_health_module_constant(self) -> None:
        """_BOOTSTRAP_HEALTH_MODULE should point to correct module."""
        assert (
            health_api._BOOTSTRAP_HEALTH_MODULE == "bioetl.composition.bootstrap.cli.health"
        )

    def test_health_api_constants__resource_management_module_points_correctly(self) -> None:
        """_RESOURCE_MANAGEMENT_MODULE should point to correct module."""
        assert (
            health_api._RESOURCE_MANAGEMENT_MODULE == "bioetl.composition._resource_management"
        )


class TestGetRuntimeSettings:
    """Test get_runtime_settings function."""

    @patch("bioetl.composition.runtime_builders.config_access.get_settings")
    def test_get_runtime_settings_calls_impl(self, mock_get_settings: MagicMock) -> None:
        """Should call get_settings from runtime_builders."""
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        result = health_api.get_runtime_settings()

        mock_get_settings.assert_called_once()
        assert result == mock_settings


class TestGetHealthServerDependencies:
    """Test get_health_server_dependencies function."""

    @patch("bioetl.composition._services.get_health_server_dependencies")
    def test_get_health_server_dependencies_calls_impl(self, mock_impl: MagicMock) -> None:
        """Should call implementation from _services module."""
        mock_deps = MagicMock()
        mock_impl.return_value = mock_deps

        result = health_api.get_health_server_dependencies()

        mock_impl.assert_called_once()
        assert result == mock_deps


class TestGetQuarantinePort:
    """Test get_quarantine_port function."""

    @patch("bioetl.composition._services.get_quarantine_port")
    def test_get_quarantine_port_calls_impl(self, mock_impl: MagicMock) -> None:
        """Should call implementation from _services module."""
        mock_port = MagicMock()
        mock_impl.return_value = mock_port

        result = health_api.get_quarantine_port()

        mock_impl.assert_called_once()
        assert result == mock_port


class TestGetQuarantineService:
    """Test get_quarantine_service function."""

    @patch("bioetl.composition._services.get_quarantine_service")
    def test_get_quarantine_service_calls_impl(self, mock_impl: MagicMock) -> None:
        """Should call implementation from _services module."""
        mock_service = MagicMock()
        mock_impl.return_value = mock_service

        result = health_api.get_quarantine_service()

        mock_impl.assert_called_once()
        assert result == mock_service


class TestLazyExportBehavior:
    """Test lazy export installation and behavior."""

    def test_health_api_lazy_exports__installed_on_module_load(self) -> None:
        """Lazy exports should be installed on module load."""
        # Check that lazy export attributes exist
        assert hasattr(health_api, "HealthServerDependencies")
        assert hasattr(health_api, "get_health_service")
        assert hasattr(health_api, "get_quarantine_runtime_service")


class TestProtocolDefinitions:
    """Test Protocol definitions."""

    def test_health_server_dependencies_protocol_defined(self) -> None:
        """HealthServerDependenciesProtocol should be defined."""
        assert hasattr(health_api, "HealthServerDependenciesProtocol")


class TestTypeCheckingStubs:
    """Test TYPE_CHECKING type stubs."""

    def test_health_api_type_checking__imports_reference_valid_modules(self) -> None:
        """TYPE_CHECKING imports should reference valid modules."""
        # Verify key modules are importable
        import bioetl.application.services.health_service
        import bioetl.application.services.quarantine_service
        import bioetl.composition._resource_management
        import bioetl.composition.bootstrap.cli.health
        import bioetl.domain.ports

        # Verify modules are importable
        assert bioetl.application.services.health_service is not None
        assert bioetl.application.services.quarantine_service is not None
        assert bioetl.composition._resource_management is not None
        assert bioetl.composition.bootstrap.cli.health is not None
        assert bioetl.domain.ports is not None