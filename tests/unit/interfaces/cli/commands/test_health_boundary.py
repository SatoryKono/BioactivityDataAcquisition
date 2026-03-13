"""Targeted tests for health CLI module boundary behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_get_health_service_delegates_to_composition_entrypoints() -> None:
    """Health command module should lazily delegate service resolution."""
    import bioetl.interfaces.cli.commands.health as health_module

    service = MagicMock()

    with patch(
        "bioetl.composition.entrypoints.get_health_service",
        return_value=service,
    ) as mock_get_health_service:
        result = health_module.get_health_service()

    assert result is service
    mock_get_health_service.assert_called_once_with()


@pytest.mark.unit
def test_get_health_server_dependencies_delegates_to_composition_entrypoints() -> None:
    """Health command module should lazily delegate dependency resolution."""
    import bioetl.interfaces.cli.commands.health as health_module

    dependencies = MagicMock()

    with patch(
        "bioetl.composition.entrypoints.get_health_server_dependencies",
        return_value=dependencies,
    ) as mock_get_health_server_dependencies:
        result = health_module.get_health_server_dependencies()

    assert result is dependencies
    mock_get_health_server_dependencies.assert_called_once_with()
