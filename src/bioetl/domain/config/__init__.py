"""Domain configuration objects.

This package preserves ``from bioetl.domain.config import X`` imports without
forcing eager import of every configuration submodule during bootstrap.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
    from bioetl.domain.config.runtime import (
        RuntimeConfig,
        SilverFilterCompatibilityMode,
    )
    from bioetl.domain.config.table import (
        APPEND_SAFE_IDEMPOTENCY_CONTRACTS,
        IDEMPOTENCY_CONTRACT_VALUES,
        IdempotencyContract,
        TableConfig,
    )
    from bioetl.domain.config.validation import (
        DEFAULT_VALIDATION_CONFIG,
        ConditionalValidation,
        CrossFieldValidation,
        FieldValidation,
        ValidationConfig,
    )

__all__ = [
    "APPEND_SAFE_IDEMPOTENCY_CONTRACTS",
    "DEFAULT_VALIDATION_CONFIG",
    "IDEMPOTENCY_CONTRACT_VALUES",
    "BaseClientConfig",
    "BaseProviderConfig",
    "ConditionalValidation",
    "CrossFieldValidation",
    "DQConfig",
    "DQReportConfig",
    "FieldCoercionPolicy",
    "FieldPolicyConfig",
    "FieldValidation",
    "IdempotencyContract",
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

_BASE_PROVIDER_MODULE = "bioetl.domain.config.base_provider"
_CONVERTERS_MODULE = "bioetl.domain.config._converters"
_DQ_MODULE = "bioetl.domain.config.dq"
_MEMORY_MODULE = "bioetl.domain.config.memory"
_PIPELINE_MODULE = "bioetl.domain.config.pipeline"
_RUNTIME_MODULE = "bioetl.domain.config.runtime"
_TABLE_MODULE = "bioetl.domain.config.table"
_VALIDATION_MODULE = "bioetl.domain.config.validation"

_EXPORT_MODULES = {
    "APPEND_SAFE_IDEMPOTENCY_CONTRACTS": _TABLE_MODULE,
    "DEFAULT_VALIDATION_CONFIG": _VALIDATION_MODULE,
    "IDEMPOTENCY_CONTRACT_VALUES": _TABLE_MODULE,
    "BaseClientConfig": _BASE_PROVIDER_MODULE,
    "BaseProviderConfig": _BASE_PROVIDER_MODULE,
    "ConditionalValidation": _VALIDATION_MODULE,
    "CrossFieldValidation": _VALIDATION_MODULE,
    "DQConfig": _DQ_MODULE,
    "DQReportConfig": _DQ_MODULE,
    "FieldCoercionPolicy": _PIPELINE_MODULE,
    "FieldPolicyConfig": _PIPELINE_MODULE,
    "FieldValidation": _VALIDATION_MODULE,
    "IdempotencyContract": _TABLE_MODULE,
    "KeyNullabilityRule": _DQ_MODULE,
    "MemoryConfig": _MEMORY_MODULE,
    "PipelineConfig": _PIPELINE_MODULE,
    "RateLimitConfig": _BASE_PROVIDER_MODULE,
    "RuntimeConfig": _RUNTIME_MODULE,
    "SilverFilterCompatibilityMode": _RUNTIME_MODULE,
    "TableConfig": _TABLE_MODULE,
    "ValidationConfig": _VALIDATION_MODULE,
    "convert_write_mode": _CONVERTERS_MODULE,
    "freeze_sequences": _CONVERTERS_MODULE,
    "resolve_loading_strategy": _CONVERTERS_MODULE,
}


def __getattr__(name: str) -> object:  # pragma: no cover
    if TYPE_CHECKING:
        raise AttributeError
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
