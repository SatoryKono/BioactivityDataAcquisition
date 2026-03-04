"""Domain configuration objects.

This package defines configuration value objects used within the Domain and
Application layers.  These are distinct from Infrastructure configuration
schemas (Pydantic) to maintain strict layer separation.

All public symbols are re-exported here so that existing imports of the form
``from bioetl.domain.config import X`` continue to work without changes.

Modules
-------
validation
    ValidationConfig, FieldValidation, CrossFieldValidation, ConditionalValidation
dq
    DQConfig, DQReportConfig
table
    TableConfig
pipeline
    PipelineConfig
runtime
    RuntimeConfig
memory
    MemoryConfig
_converters
    Internal helpers: convert_write_mode, resolve_loading_strategy, freeze_sequences

Re-exported from ``domain.configs``:
    BaseClientConfig, BaseProviderConfig, RateLimitConfig
"""

from bioetl.domain.config._converters import (
    convert_write_mode,
    freeze_sequences,
    resolve_loading_strategy,
)
from bioetl.domain.config.dq import DQConfig, DQReportConfig, KeyNullabilityRule
from bioetl.domain.config.memory import MemoryConfig
from bioetl.domain.config.pipeline import PipelineConfig
from bioetl.domain.config.runtime import RuntimeConfig
from bioetl.domain.config.table import TableConfig
from bioetl.domain.config.validation import (
    DEFAULT_VALIDATION_CONFIG,
    ConditionalValidation,
    CrossFieldValidation,
    FieldValidation,
    ValidationConfig,
)

# Re-export base provider/client configs from domain.configs for unified access.
from bioetl.domain.configs.base import (
    BaseClientConfig,
    BaseProviderConfig,
    RateLimitConfig,
)

__all__ = [
    "BaseClientConfig",
    "BaseProviderConfig",
    "DEFAULT_VALIDATION_CONFIG",
    "ConditionalValidation",
    "CrossFieldValidation",
    "DQConfig",
    "DQReportConfig",
    "FieldValidation",
    "KeyNullabilityRule",
    "MemoryConfig",
    "PipelineConfig",
    "RateLimitConfig",
    "RuntimeConfig",
    "TableConfig",
    "ValidationConfig",
    "convert_write_mode",
    "freeze_sequences",
    "resolve_loading_strategy",
]
