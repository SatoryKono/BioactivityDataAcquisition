"""Configuration schema definitions for BioETL infrastructure.

This package contains Pydantic/dataclass schemas for validating
and parsing configuration files for pipelines and data sources.

Architecture:
    base_schemas.py: Base classes for shared configuration components (DRY principle).
    pipeline_config.py: Pipeline-specific configuration schemas.
    source_config.py: Data source configuration schemas.
    filter_config.py: Standalone filter configuration file schemas.
    dq_config.py: Standalone DQ configuration file schemas.
    composite_config.py: Composite pipeline configuration schemas (ADR-026).

Schema Hierarchy:
    base_schemas.py (base classes)
    ├── pipeline_config.py (extends base classes)
    ├── source_config.py (extends base classes)
    └── filter_config.py (extends base classes)

Usage:
    >>> from bioetl.infrastructure.schemas.base_schemas import BaseDQConfig
    >>> from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

These schemas ensure type safety and validation when loading
YAML configuration files from configs/entities/.
"""

from __future__ import annotations

from bioetl.infrastructure.schemas.base_schemas import (
    BaseApiConfig,
    BaseCircuitBreakerConfig,
    BaseCsvExportConfig,
    BaseDQConfig,
    BaseDQThresholds,
    BaseFilterColumnSchema,
    BaseGoldColumnFilterConfig,
    BaseGoldFiltersConfig,
    BaseGoldListContainsFilterConfig,
    BaseGoldListLengthFilterConfig,
    BaseGoldRangeFilterConfig,
    BaseInputFilterConfig,
    BaseMaintenanceConfig,
    BaseRateLimitConfig,
    HttpClientConfig,
)
from bioetl.infrastructure.schemas.composite_config import (
    CompositeConfigFileSchema,
    CompositeConfigSchema,
    CompositeDQSchema,
    DQOverrideSchema,
    EnricherSchema,
    ExecutionSchema,
    LineageSchema,
    MergeOutputSchema,
    MergeSchema,
    RetrySchema,
    SeedSchema,
)
from bioetl.infrastructure.schemas.dq_config import DQConfigFile, ThresholdsConfig
from bioetl.infrastructure.schemas.filter_config import (
    FilterConfigFile,
    GoldFiltersFileConfig,
    InputFilterFileConfig,
)
from bioetl.infrastructure.schemas.source_profile_config import SourceProfileYamlConfig

__all__ = [
    "BaseApiConfig",
    "BaseCircuitBreakerConfig",
    "BaseCsvExportConfig",
    "BaseDQConfig",
    "BaseDQThresholds",
    "BaseFilterColumnSchema",
    "BaseGoldColumnFilterConfig",
    "BaseGoldFiltersConfig",
    "BaseGoldListContainsFilterConfig",
    "BaseGoldListLengthFilterConfig",
    "BaseGoldRangeFilterConfig",
    "BaseInputFilterConfig",
    "BaseMaintenanceConfig",
    "BaseRateLimitConfig",
    "CompositeConfigFileSchema",
    "CompositeConfigSchema",
    "CompositeDQSchema",
    "DQConfigFile",
    "DQOverrideSchema",
    "EnricherSchema",
    "ExecutionSchema",
    "FilterConfigFile",
    "GoldFiltersFileConfig",
    "HttpClientConfig",
    "InputFilterFileConfig",
    "LineageSchema",
    "MergeOutputSchema",
    "MergeSchema",
    "RetrySchema",
    "SeedSchema",
    "SourceProfileYamlConfig",
    "ThresholdsConfig",
]
