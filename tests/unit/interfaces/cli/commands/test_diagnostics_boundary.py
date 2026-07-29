# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Boundary ownership tests for the diagnostics command surface."""

from __future__ import annotations

import pytest

from bioetl.interfaces.cli.commands.domains.diagnostics.command import (
    COMMANDS,
    diagnostics,
)


pytestmark = pytest.mark.unit


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
