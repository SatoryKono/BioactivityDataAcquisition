"""Targeted tests for run CLI module boundary behavior."""

from __future__ import annotations

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
