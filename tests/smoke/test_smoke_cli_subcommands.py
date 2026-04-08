"""Smoke tests for CLI subcommand availability.

Validates that each registered Click subcommand responds to ``--help``
without raising, catching broken imports in command modules.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli.main import cli

_SUBCOMMANDS = [
    "run",
    "run-manifest",
    "run-all",
    "run-composite",
    "health",
    "config",
    "export",
    "checkpoint",
    "debug",
    "lock",
    "maintenance",
    "quarantine",
    "adr",
]


@pytest.mark.smoke
class TestCLISubcommandHealth:
    """Each registered CLI subcommand must load and respond to --help."""

    @pytest.mark.parametrize("subcommand", _SUBCOMMANDS)
    def test_subcommand_help(self, subcommand: str) -> None:
        """Invoke --help for each subcommand and assert exit_code == 0."""
        runner = CliRunner()
        result = runner.invoke(cli, [subcommand, "--help"])
        assert result.exit_code == 0, f"{subcommand} --help failed: {result.output}"
