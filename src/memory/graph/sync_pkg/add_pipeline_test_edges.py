"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.contract_ref_identity import (
    _link_provider_regression_suite_tests,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.pipeline_test_context import _pipeline_test_context
from memory.graph.sync_pkg.pipeline_test_suite_name import _link_entity_pipeline_tests
from memory.graph.sync_pkg.provider_pipeline_index_key import _pipeline_test_linker

__all__ = [
    "_add_pipeline_test_edges",
]


def _add_pipeline_test_edges(
    snapshot: GraphSnapshot,
    root: Path,
    _pipeline_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> None:
    test_context = _pipeline_test_context(
        snapshot, root, memory_mapping.get("pipeline_tests")
    )
    if test_context is None:
        return
    test_linker = _pipeline_test_linker(snapshot, test_context.relation_type)
    _link_entity_pipeline_tests(
        test_linker,
        test_context.entity_pipeline_index,
        test_context.ownership,
    )
    _link_provider_regression_suite_tests(
        test_linker,
        test_context.provider_pipeline_index,
        suites=test_context.provider_regression_suites,
        enabled=test_context.include_provider_regression_suites,
    )
