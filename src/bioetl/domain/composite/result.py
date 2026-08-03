"""Composite pipeline result models facade."""

from __future__ import annotations

from bioetl.domain.composite.result_composite import CompositeResult
from bioetl.domain.composite.result_enrichment import EnrichmentResult, EnrichmentStatus
from bioetl.domain.composite.result_merge import MergeResult
from bioetl.domain.composite.result_seed_dependency import (
    DependencyResult,
    DependencyStatus,
    SeedResult,
)

__all__ = [
    "CompositeResult",
    "DependencyResult",
    "DependencyStatus",
    "EnrichmentResult",
    "EnrichmentStatus",
    "MergeResult",
    "SeedResult",
]
