"""Behavioral coverage for runtime-builder lazy module exports (AUD-009)."""

from __future__ import annotations

import pytest

import bioetl.composition.runtime_builders._run_manifest_refs as refs
import bioetl.composition.runtime_builders.inputs_resolver as resolver
import bioetl.composition.runtime_builders.run_manifest_data_roots as data_roots


pytestmark = pytest.mark.unit


def test_run_manifest_refs_resolve_data_root_helpers() -> None:
    for name in (
        "DataRootMode",
        "is_explicit_data_root_configured",
        "resolve_data_root_mode",
    ):
        assert refs.__getattr__(name) is getattr(data_roots, name)


def test_run_manifest_refs_pass_through_module_globals() -> None:
    assert refs.__getattr__("control_plane_root") is refs.control_plane_root
    assert refs.__getattr__("build_planned_artifacts") is refs.build_planned_artifacts


def test_run_manifest_refs_unknown_name_raises() -> None:
    with pytest.raises(AttributeError, match="has no attribute"):
        refs.__getattr__("does_not_exist")


def test_inputs_resolver_compat_symbol_and_unknown() -> None:
    assert (
        resolver.__getattr__("ResolvedVacuumSettings")
        is resolver.ResolvedVacuumSettings
    )
    with pytest.raises(AttributeError, match="has no attribute"):
        resolver.__getattr__("does_not_exist")
