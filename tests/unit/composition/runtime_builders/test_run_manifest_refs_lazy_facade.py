"""ARCH-CR-05: runtime_builders run-manifest refs lazy facade."""

from __future__ import annotations

import importlib

import pytest


def test_run_manifest_refs_facade_exports_and_unknown() -> None:
    mod = importlib.import_module(
        "bioetl.composition.runtime_builders._run_manifest_refs"
    )
    assert callable(mod.control_plane_root)
    assert callable(mod.build_planned_artifacts)
    for name in (
        "DataRootMode",
        "is_explicit_data_root_configured",
        "resolve_data_root_mode",
    ):
        assert getattr(mod, name) is not None
    with pytest.raises(AttributeError, match="not_a_real_export_symbol_xyz"):
        mod.not_a_real_export_symbol_xyz
