"""Targeted tests for run-composite CLI module boundary behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


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
