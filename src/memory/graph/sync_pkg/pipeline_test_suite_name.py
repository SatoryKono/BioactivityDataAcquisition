"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Callable

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.default_batch_size import TEST_SURFACES
from memory.graph.sync_pkg.entity_pipeline_contract_tests import (
    _entity_pipeline_contract_tests,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_pipeline_test_targets import _link_pipeline_test_targets

__all__ = [
    "_link_entity_pipeline_tests",
    "_pipeline_test_suite_name",
]


def _pipeline_test_suite_name(
    snapshot: GraphSnapshot,
    artifact_key: NodeKey,
) -> str | None:
    return TEST_SURFACES.get(
        str(snapshot.nodes[artifact_key].properties.get("suite", ""))
    )


def _link_entity_pipeline_tests(
    link_test_target: Callable[[NodeKey, str, str], None],
    entity_pipeline_index: dict[tuple[str, str], NodeKey],
    ownership: dict[object, object],
) -> None:
    _link_pipeline_test_targets(
        link_test_target,
        _entity_pipeline_contract_tests(entity_pipeline_index, ownership),
        provenance="impact_pipeline_tests",
    )
