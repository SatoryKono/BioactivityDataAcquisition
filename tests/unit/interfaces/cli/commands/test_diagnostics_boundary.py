"""Boundary ownership tests for the diagnostics command surface."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.diagnostics.command import (
    COMMANDS,
    diagnostics,
)


def test_diagnostics_group_exposes_expected_commands() -> None:
    """The diagnostics Click group should keep its canonical subcommand registry."""
    assert diagnostics.name == "diagnostics"
    assert tuple(COMMANDS) == (
        "guide",
        "metrics",
        "health",
        "run",
        "dossier",
        "contract-checks",
        "checkpoint",
        "manifest",
        "forensic-diff",
        "quarantine",
    )
