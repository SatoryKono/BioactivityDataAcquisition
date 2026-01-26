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
    common_config.py: Backward compatibility re-exports (deprecated).

Schema Hierarchy:
    base_schemas.py (base classes)
    ├── pipeline_config.py (extends base classes)
    ├── source_config.py (extends base classes)
    ├── filter_config.py (extends base classes)
    └── common_config.py (re-exports for backward compatibility)

Usage:
    # Preferred: Import from specific modules
    >>> from bioetl.infrastructure.schemas.base_schemas import BaseDQConfig
    >>> from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

    # For backward compatibility only
    >>> from bioetl.infrastructure.schemas.common_config import DQConfig

These schemas ensure type safety and validation when loading
YAML configuration files from configs/pipelines/.
"""

from bioetl.infrastructure.schemas.base_schemas import (
    BaseApiConfig,
    BaseCircuitBreakerConfig,
    BaseClientConfig,
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

__all__ = [
    # Base schemas (preferred for new code)
    "BaseApiConfig",
    "BaseCircuitBreakerConfig",
    "BaseClientConfig",
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
    # Composite config
    "CompositeConfigFileSchema",
    "CompositeConfigSchema",
    "CompositeDQSchema",
    "DQConfigFile",
    "DQOverrideSchema",
    "EnricherSchema",
    "ExecutionSchema",
    "FilterConfigFile",
    "GoldFiltersFileConfig",
    "InputFilterFileConfig",
    "LineageSchema",
    "MergeOutputSchema",
    "MergeSchema",
    "RetrySchema",
    "SeedSchema",
    "ThresholdsConfig",
]
