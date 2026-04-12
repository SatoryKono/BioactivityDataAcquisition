"""Targeted tests for diagnostics CLI module boundary behavior."""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_diagnostics_module_reexports_canonical_command_symbols() -> None:
    """Top-level diagnostics module should expose the canonical command surface."""
    import bioetl.interfaces.cli.commands.diagnostics as diagnostics_module
    from bioetl.interfaces.cli.commands.domains.diagnostics import (
        command as canonical_command,
    )

    assert diagnostics_module.diagnostics is canonical_command.diagnostics
    assert (
        diagnostics_module.get_observability_diagnostics_bundle
        is canonical_command.get_observability_diagnostics_bundle
    )
    assert (
        diagnostics_module.get_quarantine_manager
        is canonical_command.get_quarantine_manager
    )


@pytest.mark.unit
def test_get_observability_diagnostics_bundle_delegates_to_interfaces_api() -> None:
    """Diagnostics command module should lazily delegate bundle resolution."""
    import bioetl.interfaces.cli.commands.diagnostics as diagnostics_module

    bundle = MagicMock()

    with patch(
        "bioetl.interfaces.observability.get_observability_diagnostics_bundle",
        return_value=bundle,
    ) as mock_get_bundle:
        result = diagnostics_module.get_observability_diagnostics_bundle()

    assert result is bundle
    mock_get_bundle.assert_called_once_with()


@pytest.mark.unit
def test_cli_main_registers_diagnostics_via_public_command_seam() -> None:
    """cli.main should resolve diagnostics through the lazy public command spec."""
    cli_main = importlib.import_module("bioetl.interfaces.cli.main")

    module_name, attribute_name, _help_text = cli_main._LAZY_COMMAND_SPECS[
        "diagnostics"
    ]

    assert module_name == "bioetl.interfaces.cli.commands.diagnostics"
    assert attribute_name == "diagnostics"
