"""Targeted tests for run CLI module boundary behavior."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

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
def test_get_pipeline_runner_service_delegates_to_services_api() -> None:
    """Run command module should lazily delegate service resolution."""
    import bioetl.interfaces.cli.commands.run as run_module

    service = MagicMock()
    registry = MagicMock()

    with patch(
        "bioetl.composition.services_api.get_pipeline_runner_service",
        return_value=service,
    ) as mock_get_pipeline_runner_service:
        result = run_module.get_pipeline_runner_service(registry=registry)

    assert result is service
    mock_get_pipeline_runner_service.assert_called_once_with(registry=registry)


@pytest.mark.unit
def test_cli_main_imports_run_via_public_command_seam() -> None:
    """cli.main should reference the public run seam, not the internal owner module."""
    path = Path("src/bioetl/interfaces/cli/main.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    if "bioetl.interfaces.cli.commands.run" in imported_modules:
        assert "bioetl.interfaces.cli.commands.domains.run.command" not in imported_modules
        return

    lazy_specs = next(
        (
            node
            for node in tree.body
            if (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name)
                    and target.id == "_LAZY_COMMAND_SPECS"
                    for target in node.targets
                )
            )
            or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "_LAZY_COMMAND_SPECS"
            )
        ),
        None,
    )
    assert lazy_specs is not None, "main.py must define _LAZY_COMMAND_SPECS"

    lazy_mapping = ast.literal_eval(lazy_specs.value)
    run_spec = lazy_mapping["run"]
    assert run_spec[0] == "bioetl.interfaces.cli.commands.run"
    assert "bioetl.interfaces.cli.commands.domains.run.command" not in str(run_spec)
