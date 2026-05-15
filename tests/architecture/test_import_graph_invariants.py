"""Canonical graph-proof architecture invariant over the import map."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa.generate_architecture_dependency_map import (
    collect_dependency_snapshot,
)


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.architecture
def test_import_graph_respects_layer_matrix() -> None:
    """The aggregated import graph must not contain layer-boundary violations."""
    snapshot = collect_dependency_snapshot(ROOT / "src" / "bioetl")
    assert snapshot.violations == [], (
        "Import graph contains forbidden layer edges:\n"
        + "\n".join(
            f"  - {edge.source} -> {edge.target} ({edge.imports} imports)"
            for edge in snapshot.violations
        )
    )
