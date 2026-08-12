"""Canonical public entrypoint for composite configuration domain models.

The package root owns the eager domain export set. This narrower facade reuses
those bindings so both public seams expose identical class objects without a
second dependency on the split ``config_*`` implementation modules.
"""

from __future__ import annotations

from bioetl.domain.composite import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    ColumnGroupConfig,
    CompositeConfig,
    CompositeDQConfig,
    CrossValidationConfig,
    DataSchemaConfig,
    DependencyConfig,
    DQOverrideConfig,
    EnricherCardinality,
    EnricherConfig,
    EnricherFieldPairing,
    ExecutionConfig,
    LayerColumnConfig,
    LineageConfig,
    MergeConfig,
    SeedConfig,
)

from .config_composite_serialization import (
    composite_from_dict,
    composite_to_dict,
)
from .config_composite_validation import (
    validate_composite_config,
)
from .config_validators import (
    require_non_empty,
    validate_positive,
)

__all__ = [
    "AggregationConfig",
    "AggregationFieldSpec",
    "AggregationFunction",
    "ColumnGroupConfig",
    "CompositeConfig",
    "CompositeDQConfig",
    "CrossValidationConfig",
    "DQOverrideConfig",
    "DataSchemaConfig",
    "DependencyConfig",
    "EnricherCardinality",
    "EnricherConfig",
    "EnricherFieldPairing",
    "ExecutionConfig",
    "LayerColumnConfig",
    "LineageConfig",
    "MergeConfig",
    "SeedConfig",
    "composite_from_dict",
    "composite_to_dict",
    "require_non_empty",
    "validate_composite_config",
    "validate_positive",
]
