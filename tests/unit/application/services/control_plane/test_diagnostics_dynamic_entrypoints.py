"""Prove classified zero-import modules remain reachable (#8711 / TD-I1-003)."""

from __future__ import annotations

import inspect
from importlib import import_module

# Repo-wide classified zero-import set (dead-code inventory / scorecard ceiling 5/5).
ZERO_IMPORT_MODULES = (
    "bioetl.application.services.control_plane.manifest.diagnostics.base",
    "bioetl.application.services.control_plane.manifest.diagnostics.finalization",
    "bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_support",
    "bioetl.interfaces.cli.commands.maintenance",
    "bioetl.domain.ports.stage_accounting",
)

DIAGNOSTICS_LEAVES = ZERO_IMPORT_MODULES[:3]


def test_classified_zero_import_modules_import() -> None:
    """All five classified zero-import modules load and expose a public surface."""
    for name in ZERO_IMPORT_MODULES:
        mod = import_module(name)
        assert mod is not None
        assert mod.__name__ == name
        public = [attr for attr in dir(mod) if not attr.startswith("_")]
        assert public, f"{name} has no public attributes"


def test_diagnostics_package_summary_entrypoint_uses_dynamic_leaves() -> None:
    """Package facade must keep importlib loading of diagnostics leaf modules."""
    pkg = import_module(
        "bioetl.application.services.control_plane.manifest.diagnostics"
    )
    source = inspect.getsource(pkg.build_diagnostics_summary)
    assert "import_module" in source
    for leaf in (
        "manifest.diagnostics.base",
        "manifest.diagnostics.finalization",
        "replay_refresh_support",
    ):
        assert leaf in source or leaf.rsplit(".", maxsplit=1)[-1] in source


def test_diagnostics_dynamic_leaves_match_package_wiring() -> None:
    """Leaf modules listed for dynamic load remain present on disk and importable."""
    for name in DIAGNOSTICS_LEAVES:
        mod = import_module(name)
        assert any(
            callable(getattr(mod, attr, None))
            for attr in dir(mod)
            if not attr.startswith("__")
        )
