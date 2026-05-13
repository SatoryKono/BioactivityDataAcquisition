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

base_provider
    BaseClientConfig, BaseProviderConfig, RateLimitConfig
"""

from __future__ import annotations

from bioetl.domain.config._converters import (
    convert_write_mode,
    freeze_sequences,
    resolve_loading_strategy,
)
from bioetl.domain.config.base_provider import (
    BaseClientConfig,
    BaseProviderConfig,
    RateLimitConfig,
)
from bioetl.domain.config.dq import DQConfig, DQReportConfig, KeyNullabilityRule
from bioetl.domain.config.memory import MemoryConfig
from bioetl.domain.config.pipeline import (
    FieldCoercionPolicy,
    FieldPolicyConfig,
    PipelineConfig,
)
from bioetl.domain.config.runtime import RuntimeConfig, SilverFilterCompatibilityMode
from bioetl.domain.config.table import TableConfig
from bioetl.domain.config.validation import (
    DEFAULT_VALIDATION_CONFIG,
    ConditionalValidation,
    CrossFieldValidation,
    FieldValidation,
    ValidationConfig,
)

__all__ = [
    "DEFAULT_VALIDATION_CONFIG",
    "BaseClientConfig",
    "BaseProviderConfig",
    "ConditionalValidation",
    "CrossFieldValidation",
    "DQConfig",
    "DQReportConfig",
    "FieldCoercionPolicy",
    "FieldPolicyConfig",
    "FieldValidation",
    "KeyNullabilityRule",
    "MemoryConfig",
    "PipelineConfig",
    "RateLimitConfig",
    "RuntimeConfig",
    "SilverFilterCompatibilityMode",
    "TableConfig",
    "ValidationConfig",
    "convert_write_mode",
    "freeze_sequences",
    "resolve_loading_strategy",
]
