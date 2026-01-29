"""Composite pipeline domain models.

This package contains domain models for composite pipeline orchestration:
- CompositeConfig: Complete composite pipeline configuration
- EnricherConfig: Single enrichment pipeline configuration
- EnrichmentResult: Result of enrichment execution
- MergeStrategy: Strategy for merging enriched data
- ConflictResolution: Strategy for field conflict resolution
- LineageMetadata: Provenance tracking for merged records
- CompositePipelineState: FSM states for pipeline execution lifecycle

See ADR-026 for architectural decisions.
"""

from bioetl.domain.composite.config import (
    CompositeConfig,
    DependencyConfig,
    EnricherConfig,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.composite.field_groups import (
    FieldGroupDefinition,
    FieldGroupId,
    FieldGroupRegistry,
    FieldMapping,
    build_field_group_registry,
)
from bioetl.domain.composite.lineage import (
    EnrichmentStatusRecord,
    FieldSource,
    LineageMetadata,
)
from bioetl.domain.composite.result import (
    CompositeResult,
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)
from bioetl.domain.composite.state import (
    CompositePipelineState,
    TransitionRules,
    can_transition,
    get_transition_rules,
    validate_transition,
)
from bioetl.domain.composite.strategy import (
    ConflictResolution,
    FallbackStrategy,
    MergeStrategy,
)

__all__ = [
    "CompositeConfig",
    "CompositePipelineState",
    "CompositeResult",
    "ConflictResolution",
    "DependencyConfig",
    "DependencyResult",
    "DependencyStatus",
    "EnricherConfig",
    "EnrichmentResult",
    "EnrichmentStatus",
    "EnrichmentStatusRecord",
    "FallbackStrategy",
    "FieldGroupDefinition",
    "FieldGroupId",
    "FieldGroupRegistry",
    "FieldMapping",
    "FieldSource",
    "LineageMetadata",
    "MergeConfig",
    "MergeResult",
    "MergeStrategy",
    "SeedConfig",
    "SeedResult",
    "TransitionRules",
    "build_field_group_registry",
    "can_transition",
    "get_transition_rules",
    "validate_transition",
]
