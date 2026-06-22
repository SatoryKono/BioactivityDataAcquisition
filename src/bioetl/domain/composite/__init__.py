"""Composite pipeline domain models.

This package contains domain models for composite pipeline orchestration:
- CompositeConfig: Complete composite pipeline configuration
- EnricherConfig: Single enrichment pipeline configuration
- EnrichmentResult: Result of enrichment execution
- MergeStrategy: Strategy for merging enriched data
- ConflictResolution: Strategy for field conflict resolution
- CompositeLineageMetadata: Provenance tracking for merged records
- CompositePipelineState: FSM states for pipeline execution lifecycle

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from bioetl.domain.composite.config import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    ColumnGroupConfig,
    CompositeConfig,
    CompositeDQConfig,
    CrossValidationConfig,
    DQOverrideConfig,
    DataSchemaConfig,
    DependencyConfig,
    EnricherCardinality,
    EnricherConfig,
    ExecutionConfig,
    LayerColumnConfig,
    LineageConfig,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.composite.cross_validation import (
    ComparisonMethod,
    CrossValidationStats,
    CrossValidationVerdict,
    EnricherCVStats,
    EnricherFieldPairing,
    FieldComparisonSpec,
    FieldMismatch,
    RecordCrossValidationResult,
)
from bioetl.domain.composite.field_groups import (
    FieldGroupDefinition,
    FieldGroupId,
    FieldGroupRegistry,
    FieldMapping,
    build_field_group_registry,
)
from bioetl.domain.composite.lineage import (
    CompositeLineageMetadata,
    EnrichmentStatusRecord,
    FieldSource,
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
    "AggregationConfig",
    "AggregationFieldSpec",
    "AggregationFunction",
    "ColumnGroupConfig",
    "ComparisonMethod",
    "CompositeConfig",
    "CompositeDQConfig",
    "CompositeLineageMetadata",
    "CompositePipelineState",
    "CompositeResult",
    "ConflictResolution",
    "CrossValidationConfig",
    "CrossValidationStats",
    "CrossValidationVerdict",
    "DQOverrideConfig",
    "DataSchemaConfig",
    "DependencyConfig",
    "DependencyResult",
    "DependencyStatus",
    "EnricherCardinality",
    "EnricherCVStats",
    "EnricherConfig",
    "EnricherFieldPairing",
    "EnrichmentResult",
    "EnrichmentStatus",
    "EnrichmentStatusRecord",
    "ExecutionConfig",
    "FallbackStrategy",
    "FieldComparisonSpec",
    "FieldGroupDefinition",
    "FieldGroupId",
    "FieldGroupRegistry",
    "FieldMapping",
    "FieldMismatch",
    "FieldSource",
    "LayerColumnConfig",
    "LineageConfig",
    "MergeConfig",
    "MergeResult",
    "MergeStrategy",
    "RecordCrossValidationResult",
    "SeedConfig",
    "SeedResult",
    "TransitionRules",
    "build_field_group_registry",
    "can_transition",
    "get_transition_rules",
    "validate_transition",
]
