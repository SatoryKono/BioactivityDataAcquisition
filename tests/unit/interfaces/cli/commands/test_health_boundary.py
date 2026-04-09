"""Targeted tests for health CLI module boundary behavior."""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_health_module_reexports_canonical_health_command_symbols() -> None:
    """Top-level health module should expose the canonical domain command surface."""
    import bioetl.interfaces.cli.commands.health as health_module
    from bioetl.interfaces.cli.commands.domains.health import (
        command as canonical_command,
    )

    assert health_module.health is canonical_command.health
    assert health_module.get_health_service is canonical_command.get_health_service
    assert (
        health_module.get_health_server_dependencies
        is canonical_command.get_health_server_dependencies
    )


@pytest.mark.unit
def test_get_health_service_delegates_to_health_api() -> None:
    """Health command module should lazily delegate service resolution."""
    import bioetl.interfaces.cli.commands.health as health_module

    service = MagicMock()

    with patch(
        "bioetl.composition.health_api.get_health_service",
        return_value=service,
    ) as mock_get_health_service:
        result = health_module.get_health_service()

    assert result is service
    mock_get_health_service.assert_called_once_with()


@pytest.mark.unit
def test_get_health_server_dependencies_delegates_to_health_api() -> None:
    """Health command module should lazily delegate dependency resolution."""
    import bioetl.interfaces.cli.commands.health as health_module

    dependencies = MagicMock()

    with patch(
        "bioetl.composition.health_api.get_health_server_dependencies",
        return_value=dependencies,
    ) as mock_get_health_server_dependencies:
        result = health_module.get_health_server_dependencies()

    assert result is dependencies
    mock_get_health_server_dependencies.assert_called_once_with()


@pytest.mark.unit
def test_cli_main_registers_health_via_public_command_seam() -> None:
    """cli.main should resolve health through the lazy public command spec."""
    cli_main = importlib.import_module("bioetl.interfaces.cli.main")

    module_name, attribute_name, _help_text = cli_main._LAZY_COMMAND_SPECS["health"]

    assert module_name == "bioetl.interfaces.cli.commands.health"
    assert attribute_name == "health"
