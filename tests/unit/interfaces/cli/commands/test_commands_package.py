"""Unit tests for the public CLI commands package surface."""

from __future__ import annotations

import pytest

import bioetl.interfaces.cli.commands as commands_package


def test_commands_package_exports_reviewed_public_command_whitelist() -> None:
    """Helper modules must not silently re-enter the package-root command map."""
    assert commands_package.__all__ == [
        "adr",
        "archive",
        "checkpoint",
        "cleanup",
        "config",
        "config_dq",
        "debug",
        "diagnostics",
        "export",
        "health",
        "lineage",
        "lock",
        "maintenance",
        "plan",
        "quarantine",
        "run",
        "run_all",
        "run_composite",
        "run_manifest",
        "vacuum",
        "workflow",
    ]


@pytest.mark.parametrize("module_name", ["export_support", "inspection_output"])
def test_commands_package_rejects_helper_only_modules_at_package_root(
    module_name: str,
) -> None:
    """Direct helper modules stay importable as submodules, not package-root seams."""
    with pytest.raises(AttributeError, match=module_name):
        getattr(commands_package, module_name)
