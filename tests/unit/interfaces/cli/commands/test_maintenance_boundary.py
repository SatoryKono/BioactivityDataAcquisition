"""Targeted tests for maintenance CLI module boundary behavior."""

from __future__ import annotations

import importlib

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
def test_cli_main_registers_maintenance_via_public_command_seam() -> None:
    """cli.main should resolve maintenance through the lazy public command spec."""
    cli_main = importlib.import_module("bioetl.interfaces.cli.main")

    module_name, attribute_name, _help_text = cli_main._LAZY_COMMAND_SPECS[
        "maintenance"
    ]

    assert module_name == "bioetl.interfaces.cli.commands.maintenance"
    assert attribute_name == "maintenance"
