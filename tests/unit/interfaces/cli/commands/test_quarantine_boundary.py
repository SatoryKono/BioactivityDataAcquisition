"""Targeted tests for quarantine CLI module boundary behavior."""

from __future__ import annotations

import importlib

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
def test_cli_main_registers_quarantine_via_public_command_seam() -> None:
    """cli.main should resolve quarantine through the lazy public command spec."""
    cli_main = importlib.import_module("bioetl.interfaces.cli.main")

    module_name, attribute_name, _help_text = cli_main._LAZY_COMMAND_SPECS[
        "quarantine"
    ]

    assert module_name == "bioetl.interfaces.cli.commands.quarantine"
    assert attribute_name == "quarantine"
