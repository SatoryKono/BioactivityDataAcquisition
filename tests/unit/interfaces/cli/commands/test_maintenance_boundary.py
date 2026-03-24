"""Targeted tests for maintenance CLI module boundary behavior."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


@pytest.mark.unit
def test_maintenance_module_reexports_canonical_maintenance_command() -> None:
    """Top-level maintenance module should expose the canonical domain command."""
    import bioetl.interfaces.cli.commands.maintenance as maintenance_module
    from bioetl.interfaces.cli.commands.domains.maintenance import (
        command as canonical_command,
    )

    assert maintenance_module.maintenance is canonical_command.maintenance


@pytest.mark.unit
def test_cli_main_imports_maintenance_via_public_command_seam() -> None:
    """cli.main should wire the public maintenance seam, not the internal owner module."""
    path = Path("src/bioetl/interfaces/cli/main.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "bioetl.interfaces.cli.commands.maintenance" in imported_modules
    assert (
        "bioetl.interfaces.cli.commands.domains.maintenance.command"
        not in imported_modules
    )
