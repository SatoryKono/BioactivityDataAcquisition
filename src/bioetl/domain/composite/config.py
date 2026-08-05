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
]
