"""Targeted tests for run CLI module boundary behavior."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


@pytest.mark.unit
def test_run_module_reexports_canonical_run_command_symbols() -> None:
    """Top-level run module should expose the canonical domain command surface."""
    import bioetl.interfaces.cli.commands.run as run_module
    from bioetl.interfaces.cli.commands.domains.run import command as canonical_command

    assert run_module.run is canonical_command.run
    assert run_module.execute_run is canonical_command.execute_run
    assert (
        run_module.get_cli_run_orchestration_service
        is canonical_command.get_cli_run_orchestration_service
    )


@pytest.mark.unit
def test_cli_main_imports_run_via_public_command_seam() -> None:
    """cli.main should wire the public run seam, not the internal owner module."""
    path = Path("src/bioetl/interfaces/cli/main.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "bioetl.interfaces.cli.commands.run" in imported_modules
    assert "bioetl.interfaces.cli.commands.domains.run.command" not in imported_modules
