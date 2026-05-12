from __future__ import annotations

from unittest.mock import MagicMock, patch

from bioetl.composition import health_api


def test_get_health_server_dependencies_delegates_to_services_seam() -> None:
    expected_dependencies = MagicMock(name="HealthServerDependencies")
    with (
        patch(
            "bioetl.composition.health_api.get_health_server_dependencies",
            return_value=expected_dependencies,
        ) as mock_impl,
        patch("bioetl.composition.health_api.import_module") as mock_import_module,
    ):
        result = health_api.get_health_server_dependencies()

    assert result is expected_dependencies
    mock_impl.assert_called_once_with()
    mock_import_module.assert_not_called()


def test_get_quarantine_port_delegates_to_services_seam() -> None:
    expected_port = MagicMock(name="QuarantinePort")

    with (
        patch(
            "bioetl.composition.health_api.get_quarantine_port",
            return_value=expected_port,
        ) as mock_impl,
        patch("bioetl.composition.health_api.import_module") as mock_import_module,
    ):
        result = health_api.get_quarantine_port()

    assert result is expected_port
    mock_impl.assert_called_once_with()
    mock_import_module.assert_not_called()


def test_get_quarantine_service_delegates_to_services_seam() -> None:
    expected_service = MagicMock(name="QuarantineService")

    with (
        patch(
            "bioetl.composition.health_api.get_quarantine_service",
            return_value=expected_service,
        ) as mock_impl,
        patch("bioetl.composition.health_api.import_module") as mock_import_module,
    ):
        result = health_api.get_quarantine_service()

    assert result is expected_service
    mock_impl.assert_called_once_with()
    mock_import_module.assert_not_called()
