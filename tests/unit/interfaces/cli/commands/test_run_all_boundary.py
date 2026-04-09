"""Targeted tests for run-all CLI module boundary behavior."""

from __future__ import annotations

import importlib
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
def test_get_pipeline_runner_service_delegates_to_execution_api() -> None:
    """Run-all module should lazily delegate service resolution."""
    import bioetl.interfaces.cli.commands.run_all as run_all_module

    service = MagicMock()
    registry = MagicMock()

    with patch(
        "bioetl.composition.execution_api.get_pipeline_runner_service",
        return_value=service,
    ) as mock_get_pipeline_runner_service:
        result = run_all_module.get_pipeline_runner_service(registry=registry)

    assert result is service
    mock_get_pipeline_runner_service.assert_called_once_with(registry=registry)


@pytest.mark.unit
def test_cli_main_registers_run_all_via_public_command_seam() -> None:
    """cli.main should resolve run-all through the lazy public command spec."""
    cli_main = importlib.import_module("bioetl.interfaces.cli.main")

    module_name, attribute_name, _help_text = cli_main._LAZY_COMMAND_SPECS["run-all"]

    assert module_name == "bioetl.interfaces.cli.commands.run_all"
    assert attribute_name == "run_all"
