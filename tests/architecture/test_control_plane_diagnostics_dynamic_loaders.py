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
"""Owner-test anchors for control-plane diagnostics dynamic loaders and CLI seams."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

DIAGNOSTICS_MODULES = (
    "bioetl.application.services.control_plane.manifest.diagnostics.base",
    "bioetl.application.services.control_plane.manifest.diagnostics.finalization",
    "bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_support",
)


@pytest.mark.architecture
@pytest.mark.parametrize("module_name", DIAGNOSTICS_MODULES)
def test_diagnostics_dynamic_loader_modules_import(module_name: str) -> None:
    """Dynamic diagnostics modules remain importable owner surfaces."""
    module = importlib.import_module(module_name)
    assert module is not None
    assert module.__name__ == module_name


@pytest.mark.architecture
def test_maintenance_public_reexport_matches_domain_owner() -> None:
    """Top-level maintenance.py re-exports the domain command group only."""
    public = importlib.import_module("bioetl.interfaces.cli.commands.maintenance")
    owner = importlib.import_module(
        "bioetl.interfaces.cli.commands.domains.maintenance.command_group"
    )
    assert public.maintenance is owner.maintenance


@pytest.mark.architecture
def test_diagnostics_package_lazy_loads_split_modules() -> None:
    """Package root continues to resolve diagnostics helpers via importlib."""
    package = importlib.import_module(
        "bioetl.application.services.control_plane.manifest.diagnostics"
    )
    # Importable package with documented split modules on disk.
    package_dir = (
        ROOT / "src/bioetl/application/services/control_plane/manifest/diagnostics"
    )
    for stem in ("base", "finalization", "replay_refresh_support"):
        assert (package_dir / f"{stem}.py").is_file()
    assert package is not None
