"""Smoke coverage for composition bootstrap runtime bundle dataclasses."""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "module_path",
    [
        "bioetl.composition.bootstrap.runtime.observability_bundle",
        "bioetl.composition.bootstrap.runtime.composite_control_plane_bundle",
        "bioetl.composition.bootstrap.runtime.composite_execution_support_bundle",
        "bioetl.composition.bootstrap.runtime.composite_merge_dependencies_bundle",
        "bioetl.composition.bootstrap.runtime.composite_runtime_management_bundle",
    ],
)
def test_runtime_bundle_modules_expose_public_dataclass(module_path: str) -> None:
    """Each runtime bundle module must import and expose a public bundle type."""
    module = importlib.import_module(module_path)
    exported = [name for name in dir(module) if name.endswith("Bundle")]
    assert exported, f"{module_path} must export a *Bundle type"
    bundle_cls = getattr(module, exported[0])
    assert hasattr(bundle_cls, "__annotations__")
