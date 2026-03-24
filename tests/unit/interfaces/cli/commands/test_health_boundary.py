"""Targeted tests for health CLI module boundary behavior."""

from __future__ import annotations

import ast
from pathlib import Path
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
def test_get_health_service_delegates_to_services_api() -> None:
    """Health command module should lazily delegate service resolution."""
    import bioetl.interfaces.cli.commands.health as health_module

    service = MagicMock()

    with patch(
        "bioetl.composition.services_api.get_health_service",
        return_value=service,
    ) as mock_get_health_service:
        result = health_module.get_health_service()

    assert result is service
    mock_get_health_service.assert_called_once_with()


@pytest.mark.unit
def test_get_health_server_dependencies_delegates_to_services_api() -> None:
    """Health command module should lazily delegate dependency resolution."""
    import bioetl.interfaces.cli.commands.health as health_module

    dependencies = MagicMock()

    with patch(
        "bioetl.composition.services_api.get_health_server_dependencies",
        return_value=dependencies,
    ) as mock_get_health_server_dependencies:
        result = health_module.get_health_server_dependencies()

    assert result is dependencies
    mock_get_health_server_dependencies.assert_called_once_with()


@pytest.mark.unit
def test_cli_main_imports_health_via_public_command_seam() -> None:
    """cli.main should wire the public health seam, not the internal owner module."""
    path = Path("src/bioetl/interfaces/cli/main.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "bioetl.interfaces.cli.commands.health" in imported_modules
    assert (
        "bioetl.interfaces.cli.commands.domains.health.command" not in imported_modules
    )
