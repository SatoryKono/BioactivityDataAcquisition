"""Targeted tests for cleanup CLI module boundary behavior."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


@pytest.mark.unit
def test_cleanup_module_reexports_canonical_cleanup_command_symbols() -> None:
    """Top-level cleanup module should expose the canonical maintenance command surface."""
    import bioetl.interfaces.cli.commands.cleanup as cleanup_module
    from bioetl.interfaces.cli.commands.domains.maintenance import (
        cleanup as canonical_command,
    )

    assert (
        cleanup_module.bronze_cleanup_command
        is canonical_command.bronze_cleanup_command
    )
    assert (
        cleanup_module.cleanup_preview_command
        is canonical_command.cleanup_preview_command
    )
    assert (
        cleanup_module.get_bronze_cleanup_service
        is canonical_command.get_bronze_cleanup_service
    )
    assert (
        cleanup_module.preview_pipeline_cleanup
        is canonical_command.preview_pipeline_cleanup
    )


@pytest.mark.unit
def test_cleanup_module_aliases_expected_canonical_module() -> None:
    """Cleanup seam should alias the canonical maintenance cleanup module."""
    path = Path("src/bioetl/interfaces/cli/commands/cleanup.py")
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

    assert targets == {"bioetl.interfaces.cli.commands.domains.maintenance.cleanup"}
