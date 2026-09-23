"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Callable

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.provider_suite_provenance import _provider_suite_provenance

__all__ = [
    "_link_provider_suite_targets",
]


def _link_provider_suite_targets(
    link_test_target: Callable[[NodeKey, str, str], None],
    provider_pipeline_index: dict[str, list[NodeKey]],
    *,
    suite_name: str,
    provider_targets: tuple[tuple[str, str], ...],
) -> None:
    provenance = _provider_suite_provenance(suite_name)
    for provider_name, raw_test_path in provider_targets:
        for pipeline_key in provider_pipeline_index.get(provider_name, []):
            link_test_target(pipeline_key, raw_test_path, provenance)
