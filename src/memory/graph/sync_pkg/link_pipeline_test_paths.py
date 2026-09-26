"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Callable

from memory.graph.sync_pkg._core_models import NodeKey

__all__ = [
    "_link_pipeline_test_paths",
]


def _link_pipeline_test_paths(
    link_test_target: Callable[[NodeKey, str, str], None],
    pipeline_key: NodeKey,
    test_paths: tuple[str, ...],
    *,
    provenance: str,
) -> None:
    for test_path in test_paths:
        link_test_target(pipeline_key, test_path, provenance)
