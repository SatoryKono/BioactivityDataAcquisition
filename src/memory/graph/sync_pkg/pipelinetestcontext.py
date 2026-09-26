"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from dataclasses import dataclass

from memory.graph.sync_pkg._core_models import NodeKey

__all__ = [
    "PipelineTestContext",
]


@dataclass(frozen=True)
class PipelineTestContext:
    relation_type: str
    ownership: dict[object, object]
    provider_regression_suites: object
    include_provider_regression_suites: bool
    entity_pipeline_index: dict[tuple[str, str], NodeKey]
    provider_pipeline_index: dict[str, list[NodeKey]]
