"""Targeted tests for run-composite CLI module boundary behavior."""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_run_composite_module_reexports_canonical_command_surface() -> None:
    """Top-level run_composite module should expose the canonical domain command."""
    import bioetl.interfaces.cli.commands.run_composite as run_composite_module
    from bioetl.interfaces.cli.commands.domains.composite import (
        command as canonical_command,
    )

    assert run_composite_module.run_composite is canonical_command.run_composite
    assert (
        run_composite_module.load_composite_config
        is canonical_command.load_composite_config
    )
    assert (
        run_composite_module.bootstrap_composite_runner
        is canonical_command.bootstrap_composite_runner
    )


@pytest.mark.unit
def test_load_composite_config_delegates_to_composite_api() -> None:
    """Run-composite module should lazily delegate config loading."""
    import bioetl.interfaces.cli.commands.run_composite as run_composite_module

    config = MagicMock()

    with patch(
        "bioetl.composition.composite_api.load_composite_config",
        return_value=config,
    ) as mock_load_composite_config:
        result = run_composite_module.load_composite_config("publication")

    assert result is config
    mock_load_composite_config.assert_called_once_with("publication")


@pytest.mark.unit
def test_bootstrap_composite_runner_delegates_to_composite_api() -> None:
    """Run-composite module should lazily delegate runner bootstrap."""
    import bioetl.interfaces.cli.commands.run_composite as run_composite_module

    config = MagicMock()
    runtime = run_composite_module.CompositeRuntimeConfig()
    runner = MagicMock()

    with patch(
        "bioetl.composition.composite_api.bootstrap_composite_runner",
        return_value=runner,
    ) as mock_bootstrap_composite_runner:
        result = run_composite_module.bootstrap_composite_runner(config, runtime)

    assert result is runner
    mock_bootstrap_composite_runner.assert_called_once_with(config, runtime)


@pytest.mark.unit
def test_cli_main_registers_run_composite_via_public_command_seam() -> None:
    """cli.main should resolve run-composite through the lazy public command spec."""
    cli_main = importlib.import_module("bioetl.interfaces.cli.main")

    module_name, attribute_name, _help_text = cli_main._LAZY_COMMAND_SPECS[
        "run-composite"
    ]

    assert module_name == "bioetl.interfaces.cli.commands.run_composite"
    assert attribute_name == "run_composite"
