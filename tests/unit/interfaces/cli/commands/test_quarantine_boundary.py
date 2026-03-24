"""Targeted tests for quarantine CLI module boundary behavior."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


@pytest.mark.unit
def test_quarantine_module_reexports_canonical_quarantine_command_symbols() -> None:
    """Top-level quarantine module should expose the canonical domain command surface."""
    import bioetl.interfaces.cli.commands.quarantine as quarantine_module
    from bioetl.interfaces.cli.commands.domains.quarantine import (
        command as canonical_command,
    )

    assert quarantine_module.quarantine is canonical_command.quarantine
    assert (
        quarantine_module.get_quarantine_manager
        is canonical_command.get_quarantine_manager
    )
    assert (
        quarantine_module.get_quarantine_service
        is canonical_command.get_quarantine_service
    )


@pytest.mark.unit
def test_cli_main_imports_quarantine_via_public_command_seam() -> None:
    """cli.main should wire the public quarantine seam, not the internal owner module."""
    path = Path("src/bioetl/interfaces/cli/main.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "bioetl.interfaces.cli.commands.quarantine" in imported_modules
    assert (
        "bioetl.interfaces.cli.commands.domains.quarantine.command"
        not in imported_modules
    )
