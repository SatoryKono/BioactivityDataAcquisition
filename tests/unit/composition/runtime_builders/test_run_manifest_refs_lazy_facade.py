"""Public run-manifest helpers retain their canonical static bindings."""

from __future__ import annotations
import pytest
from bioetl.composition.control_plane_paths import control_plane_root
from bioetl.composition.runtime_builders._run_manifest_planned_artifacts import (
    build_planned_artifacts,
)
from bioetl.composition.runtime_builders import run_manifest_support

pytestmark = pytest.mark.unit


def test_run_manifest_public_helpers_use_canonical_implementations() -> None:
    assert run_manifest_support.control_plane_root is control_plane_root
    assert run_manifest_support.build_planned_artifacts is build_planned_artifacts
