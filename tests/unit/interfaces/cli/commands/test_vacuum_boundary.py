"""Targeted tests for vacuum CLI module boundary behavior."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_vacuum_module_reexports_canonical_vacuum_command_symbols() -> None:
    """Top-level vacuum module should expose the canonical maintenance command surface."""
    import bioetl.interfaces.cli.commands.vacuum as vacuum_module
    from bioetl.interfaces.cli.commands.domains.maintenance import (
        vacuum as canonical_command,
    )

    assert vacuum_module.vacuum_command is canonical_command.vacuum_command
    assert vacuum_module.vacuum_all_command is canonical_command.vacuum_all_command
    assert (
        vacuum_module.get_lifecycle_service is canonical_command.get_lifecycle_service
    )
    assert vacuum_module.get_vacuum_service is canonical_command.get_vacuum_service


@pytest.mark.unit
def test_get_lifecycle_service_delegates_to_resources_api() -> None:
    """Vacuum command module should lazily delegate lifecycle resolution."""
    import bioetl.interfaces.cli.commands.vacuum as vacuum_module

    service = MagicMock()

    with patch(
        "bioetl.composition.resources_api.get_lifecycle_service",
        return_value=service,
    ) as mock_get_lifecycle_service:
        result = vacuum_module.get_lifecycle_service()

    assert result is service
    mock_get_lifecycle_service.assert_called_once_with()


@pytest.mark.unit
def test_get_vacuum_service_delegates_to_services_api() -> None:
    """Vacuum command module should lazily delegate vacuum service resolution."""
    import bioetl.interfaces.cli.commands.vacuum as vacuum_module

    service = MagicMock()

    with patch(
        "bioetl.composition.services_api.get_vacuum_service",
        return_value=service,
    ) as mock_get_vacuum_service:
        result = vacuum_module.get_vacuum_service()

    assert result is service
    mock_get_vacuum_service.assert_called_once_with()


@pytest.mark.unit
def test_vacuum_module_aliases_expected_canonical_module() -> None:
    """Vacuum seam should alias the canonical maintenance vacuum module."""
    path = Path("src/bioetl/interfaces/cli/commands/vacuum.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))

    targets = {
        node.args[1].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "alias_module"
        and len(node.args) == 2
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "__name__"
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    }

    assert targets == {"bioetl.interfaces.cli.commands.domains.maintenance.vacuum"}
