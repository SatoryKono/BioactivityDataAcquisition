from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from bioetl.composition import health_api


def test_get_health_server_dependencies_uses_direct_bootstrap() -> None:
    with patch("bioetl.composition.health_api.import_module") as mock_import_module:
        result = health_api.get_health_server_dependencies()

    assert result.metrics is None
    assert result.health_monitor is None
    mock_import_module.assert_not_called()


def test_get_quarantine_port_uses_direct_bootstrap() -> None:
    expected_port = MagicMock(name="QuarantinePort")
    settings = MagicMock()
    settings.quarantine_path = Path("/tmp/quarantine")

    with (
        patch(
            "bioetl.infrastructure.config.get_settings",
            return_value=settings,
        ) as mock_get_settings,
        patch(
            "bioetl.infrastructure.quarantine.unified.UnifiedQuarantineAdapter",
            return_value=expected_port,
        ) as mock_adapter_cls,
        patch("bioetl.composition.health_api.import_module") as mock_import_module,
    ):
        result = health_api.get_quarantine_port()

    assert result is expected_port
    mock_get_settings.assert_called_once_with()
    mock_adapter_cls.assert_called_once_with(base_path="/tmp/quarantine")
    mock_import_module.assert_not_called()


def test_get_quarantine_service_uses_direct_bootstrap() -> None:
    settings = MagicMock()
    settings.data_dir = Path("/tmp/data")
    expected_port = MagicMock(name="QuarantinePort")
    expected_manifest_service = MagicMock(name="RunManifestInspectionService")
    expected_service = MagicMock(name="QuarantineService")

    with (
        patch(
            "bioetl.infrastructure.config.get_settings",
            return_value=settings,
        ),
        patch(
            "bioetl.application.services.control_plane.run_manifest_inspection_service.RunManifestInspectionService",
            return_value=expected_manifest_service,
        ),
        patch(
            "bioetl.application.services.quarantine_service.QuarantineService",
            return_value=expected_service,
        ) as mock_service_cls,
        patch(
            "bioetl.composition.health_api.get_quarantine_port",
            return_value=expected_port,
        ),
        patch("bioetl.composition.health_api.import_module") as mock_import_module,
    ):
        result = health_api.get_quarantine_service()

    assert result is expected_service
    assert mock_service_cls.call_args.kwargs["quarantine_port"] is expected_port
    assert mock_service_cls.call_args.kwargs["run_manifest_service"] is (
        expected_manifest_service
    )
    mock_import_module.assert_not_called()
