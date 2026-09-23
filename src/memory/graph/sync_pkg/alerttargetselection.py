"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from dataclasses import dataclass

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_contexts import (
    SurfaceAnchorSets,
    SurfaceComplexityMetrics,
)

__all__ = [
    "AlertTargetSelection",
    "ComplexityCandidateContext",
]


@dataclass(frozen=True)
class AlertTargetSelection:
    selected_pipelines: tuple[NodeKey, ...]
    selected_providers: tuple[NodeKey, ...]
    selected_contracts: tuple[NodeKey, ...]


@dataclass(frozen=True)
class ComplexityCandidateContext:
    anchors: SurfaceAnchorSets
    metrics: SurfaceComplexityMetrics
    runtime_anchors: tuple[NodeKey, ...]
    config_anchors: tuple[NodeKey, ...]
    doc_anchors: tuple[NodeKey, ...]
    test_anchors: tuple[NodeKey, ...]
    blocked_by_current_cycle: bool
    simplification_score: float
    classification: str
