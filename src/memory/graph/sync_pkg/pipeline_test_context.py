"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.pipeline_test_indexes import _pipeline_test_indexes
from memory.graph.sync_pkg.pipeline_test_ownership_path import (
    _pipeline_test_mapping_config,
)
from memory.graph.sync_pkg.pipeline_test_payload import _pipeline_test_payload
from memory.graph.sync_pkg.pipelinetestcontext import PipelineTestContext

__all__ = [
    "_pipeline_test_context",
]


def _pipeline_test_context(
    snapshot: GraphSnapshot,
    root: Path,
    tests_mapping: object,
) -> PipelineTestContext | None:
    relation_type, ownership_config, include_provider_regression_suites = (
        _pipeline_test_mapping_config(tests_mapping)
    )
    payload, ownership = _pipeline_test_payload(root, ownership_config)
    if payload is None or ownership is None:
        return None
    entity_pipeline_index, provider_pipeline_index = _pipeline_test_indexes(snapshot)
    return PipelineTestContext(
        relation_type=relation_type,
        ownership=ownership,
        provider_regression_suites=payload.get("provider_regression_suites"),
        include_provider_regression_suites=include_provider_regression_suites,
        entity_pipeline_index=entity_pipeline_index,
        provider_pipeline_index=provider_pipeline_index,
    )
