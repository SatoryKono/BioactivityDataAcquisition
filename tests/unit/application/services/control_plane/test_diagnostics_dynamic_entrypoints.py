"""Prove classified zero-import modules remain reachable (#8711 / TD-I1-003)."""

from __future__ import annotations

from importlib import import_module
from unittest.mock import patch

from tests.unit.application.services.run_manifest_test_support import make_run_manifest

ZERO_IMPORT_MODULES = (
    "bioetl.application.services.control_plane.manifest.diagnostics.base",
    "bioetl.application.services.control_plane.manifest.diagnostics.finalization",
    "bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_support",
    "bioetl.interfaces.cli.commands.maintenance",
    "bioetl.domain.ports.stage_accounting",
)

DIAGNOSTICS_LEAVES = (
    "bioetl.application.services.control_plane.manifest.diagnostics.base",
    "bioetl.application.services.control_plane.manifest.diagnostics.finalization",
    "bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_support",
)


def test_classified_zero_import_modules_import() -> None:
    """All five classified zero-import modules load and expose a public surface."""
    for name in ZERO_IMPORT_MODULES:
        mod = import_module(name)
        assert mod is not None
        assert mod.__name__ == name
        public = [attr for attr in dir(mod) if not attr.startswith("_")]
        assert public, f"{name} has no public attributes"


def test_diagnostics_package_summary_entrypoint_uses_dynamic_leaves() -> None:
    """Entrypoint must importlib-load the three diagnostics leaves."""
    pkg = import_module(
        "bioetl.application.services.control_plane.manifest.diagnostics"
    )
    loaded: list[str] = []
    real_import = import_module

    def _tracking_import(name: str, package: str | None = None):
        loaded.append(name)
        return real_import(name, package) if package else real_import(name)

    with patch.object(pkg, "import_module", side_effect=_tracking_import):
        summary = pkg.build_diagnostics_summary(make_run_manifest(), ())

    assert isinstance(summary, dict)
    assert summary
    for leaf in DIAGNOSTICS_LEAVES:
        assert leaf in loaded, f"entrypoint did not importlib-load {leaf}"


def test_diagnostics_dynamic_leaves_match_package_wiring() -> None:
    """Leaf modules remain importable owner surfaces used by the package."""
    for name in DIAGNOSTICS_LEAVES:
        mod = import_module(name)
        assert any(
            callable(getattr(mod, attr, None))
            for attr in dir(mod)
            if not attr.startswith("__")
        )
