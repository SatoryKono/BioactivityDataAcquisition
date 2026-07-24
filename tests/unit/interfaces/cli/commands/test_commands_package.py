"""Unit tests for the public CLI commands package surface."""

from __future__ import annotations

import pytest

import bioetl.interfaces.cli.commands as commands_package


pytestmark = pytest.mark.unit


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
        "quarantine",
        "report",
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


def test_commands_package_rejects_export_support_after_command_module_import() -> None:
    """Importing the public export command must not re-expose helper submodules."""
    import bioetl.interfaces.cli.commands.export  # noqa: F401

    missing_attribute = "export_support"
    with pytest.raises(AttributeError, match="export_support"):
        getattr(commands_package, missing_attribute)


def test_commands_package_rejects_inspection_output_after_command_module_import() -> (
    None
):
    """Importing public diagnostics commands must not re-expose helper submodules."""
    import bioetl.interfaces.cli.commands.diagnostics  # noqa: F401

    missing_attribute = "inspection_output"
    with pytest.raises(AttributeError, match="inspection_output"):
        getattr(commands_package, missing_attribute)
