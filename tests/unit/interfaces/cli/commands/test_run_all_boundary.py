"""Targeted tests for run-all CLI module boundary behavior."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_run_all_module_reexports_canonical_run_all_command() -> None:
    """Top-level run_all module should expose the canonical domain command surface."""
    import bioetl.interfaces.cli.commands.run_all as run_all_module
    from bioetl.interfaces.cli.commands.domains.run_all import (
        command as canonical_command,
    )

    assert run_all_module.run_all is canonical_command.run_all
    assert (
        run_all_module.get_pipeline_runner_service
        is canonical_command.get_pipeline_runner_service
    )


@pytest.mark.unit
def test_get_pipeline_runner_service_delegates_to_services_api() -> None:
    """Run-all module should lazily delegate service resolution."""
    import bioetl.interfaces.cli.commands.run_all as run_all_module

    service = MagicMock()
    registry = MagicMock()

    with patch(
        "bioetl.composition.services_api.get_pipeline_runner_service",
        return_value=service,
    ) as mock_get_pipeline_runner_service:
        result = run_all_module.get_pipeline_runner_service(registry=registry)

    assert result is service
    mock_get_pipeline_runner_service.assert_called_once_with(registry=registry)


@pytest.mark.unit
def test_cli_main_imports_run_all_via_public_command_seam() -> None:
    """cli.main should wire the public run_all seam, not the internal owner module."""
    path = Path("src/bioetl/interfaces/cli/main.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "bioetl.interfaces.cli.commands.run_all" in imported_modules
    assert (
        "bioetl.interfaces.cli.commands.domains.run_all.command" not in imported_modules
    )
