"""Canonical public entrypoint for composite configuration domain models."""

from __future__ import annotations

from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    EnricherCardinality,
)
from bioetl.domain.composite.config_merge import ColumnGroupConfig
from bioetl.domain.composite.config_models import (
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
from bioetl.domain.composite.cross_validation import EnricherFieldPairing

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
