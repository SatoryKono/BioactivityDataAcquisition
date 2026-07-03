"""Architecture guard for degraded runtime-anchor fingerprint API boundary."""

from __future__ import annotations

import pytest

import ast
from pathlib import Path

import bioetl.domain.normalization as normalization

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "bioetl"
LEGACY_HELPER_MODULE = ROOT / "src/bioetl/domain/normalization/legacy_fingerprints.py"


def test_legacy_degraded_runtime_anchor_module_has_been_removed() -> None:
    assert not LEGACY_HELPER_MODULE.exists()


def test_degraded_runtime_anchor_fingerprint_is_not_top_level_normalization_api() -> (
    None
):
    assert "compute_degraded_runtime_anchor_fingerprint" not in normalization.__all__
    assert not hasattr(normalization, "compute_degraded_runtime_anchor_fingerprint")


def test_strict_control_plane_paths_do_not_import_legacy_degraded_fingerprint() -> None:
    offenders: list[str] = []
    strict_roots = (
        SRC_ROOT / "application" / "services" / "control_plane",
        SRC_ROOT / "composition" / "runtime_builders",
    )
    for root in strict_roots:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if node.module not in {
                    "bioetl.domain.normalization",
                    "bioetl.domain.normalization.fingerprints",
                }:
                    continue
                imported_names = {alias.name for alias in node.names}
                if "compute_degraded_runtime_anchor_fingerprint" in imported_names:
                    offenders.append(path.relative_to(ROOT).as_posix())
    assert not offenders, (
        "Strict replay/control-plane paths must not import degraded runtime-anchor "
        f"fingerprints: {offenders}"
    )
