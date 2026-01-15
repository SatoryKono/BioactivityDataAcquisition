"""Composite pipeline domain models.

This package contains domain models for composite pipeline orchestration:
- CompositeConfig: Complete composite pipeline configuration
- EnricherConfig: Single enrichment pipeline configuration
- EnrichmentResult: Result of enrichment execution
- MergeStrategy: Strategy for merging enriched data
- ConflictResolution: Strategy for field conflict resolution
- LineageMetadata: Provenance tracking for merged records

See ADR-026 for architectural decisions.
"""

from bioetl.domain.composite.config import (
    CompositeConfig,
    EnricherConfig,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.composite.lineage import (
    EnrichmentStatusRecord,
    FieldSource,
    LineageMetadata,
)
from bioetl.domain.composite.result import (
    CompositeResult,
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)
from bioetl.domain.composite.strategy import (
    ConflictResolution,
    FallbackStrategy,
    MergeStrategy,
)

__all__ = [
    "CompositeConfig",
    "CompositeResult",
    "ConflictResolution",
    "EnricherConfig",
    "EnrichmentResult",
    "EnrichmentStatus",
    "EnrichmentStatusRecord",
    "FallbackStrategy",
    "FieldSource",
    "LineageMetadata",
    "MergeConfig",
    "MergeResult",
    "MergeStrategy",
    "SeedConfig",
    "SeedResult",
]
