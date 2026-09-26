"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Callable

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.link_pipeline_test_paths import _link_pipeline_test_paths

__all__ = [
    "_link_pipeline_test_targets",
]


def _link_pipeline_test_targets(
    link_test_target: Callable[[NodeKey, str, str], None],
    targets: tuple[tuple[NodeKey, tuple[str, ...]], ...],
    *,
    provenance: str,
) -> None:
    for pipeline_key, test_paths in targets:
        _link_pipeline_test_paths(
            link_test_target,
            pipeline_key,
            test_paths,
            provenance=provenance,
        )
