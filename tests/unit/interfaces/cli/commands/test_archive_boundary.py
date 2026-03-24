"""Targeted tests for archive CLI module boundary behavior."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_archive_module_reexports_canonical_archive_command_symbols() -> None:
    """Top-level archive module should expose the canonical maintenance command surface."""
    import bioetl.interfaces.cli.commands.archive as archive_module
    from bioetl.interfaces.cli.commands.domains.maintenance import (
        archive as canonical_command,
    )

    assert archive_module.archive_command is canonical_command.archive_command
    assert (
        archive_module.get_lifecycle_service is canonical_command.get_lifecycle_service
    )


@pytest.mark.unit
def test_get_lifecycle_service_delegates_to_resources_api() -> None:
    """Archive command module should lazily delegate service resolution."""
    import bioetl.interfaces.cli.commands.archive as archive_module

    service = MagicMock()

    with patch(
        "bioetl.composition.resources_api.get_lifecycle_service",
        return_value=service,
    ) as mock_get_lifecycle_service:
        result = archive_module.get_lifecycle_service()

    assert result is service
    mock_get_lifecycle_service.assert_called_once_with()


@pytest.mark.unit
def test_archive_module_aliases_expected_canonical_module() -> None:
    """Archive seam should alias the canonical maintenance archive module."""
    path = Path("src/bioetl/interfaces/cli/commands/archive.py")
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

    assert targets == {"bioetl.interfaces.cli.commands.domains.maintenance.archive"}
