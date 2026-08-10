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

from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    EnricherCardinality,
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

from .config_composite_serialization import composite_from_dict, composite_to_dict
from .config_composite_validation import validate_composite_config
from .config_merge import ColumnGroupConfig
from .config_models import (
    CompositeConfig,
    CompositeDQConfig,
    CrossValidationConfig,
    DataSchemaConfig,
    DependencyConfig,
    DQOverrideConfig,
    EnricherConfig,
    ExecutionConfig,
    LayerColumnConfig,
    LineageConfig,
    MergeConfig,
    SeedConfig,
)
from .config_validators import require_non_empty, validate_positive

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
    "EnricherCVStats",
    "EnricherCardinality",
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
    "composite_from_dict",
    "composite_to_dict",
    "get_transition_rules",
    "require_non_empty",
    "validate_composite_config",
    "validate_positive",
    "validate_transition",
]
