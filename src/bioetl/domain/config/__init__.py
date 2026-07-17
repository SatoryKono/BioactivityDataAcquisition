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

_EXPORT_MODULES = {
    "APPEND_SAFE_IDEMPOTENCY_CONTRACTS": "bioetl.domain.config.table",
    "DEFAULT_VALIDATION_CONFIG": "bioetl.domain.config.validation",
    "IDEMPOTENCY_CONTRACT_VALUES": "bioetl.domain.config.table",
    "BaseClientConfig": "bioetl.domain.config.base_provider",
    "BaseProviderConfig": "bioetl.domain.config.base_provider",
    "ConditionalValidation": "bioetl.domain.config.validation",
    "CrossFieldValidation": "bioetl.domain.config.validation",
    "DQConfig": "bioetl.domain.config.dq",
    "DQReportConfig": "bioetl.domain.config.dq",
    "FieldCoercionPolicy": "bioetl.domain.config.pipeline",
    "FieldPolicyConfig": "bioetl.domain.config.pipeline",
    "FieldValidation": "bioetl.domain.config.validation",
    "IdempotencyContract": "bioetl.domain.config.table",
    "KeyNullabilityRule": "bioetl.domain.config.dq",
    "MemoryConfig": "bioetl.domain.config.memory",
    "PipelineConfig": "bioetl.domain.config.pipeline",
    "RateLimitConfig": "bioetl.domain.config.base_provider",
    "RuntimeConfig": "bioetl.domain.config.runtime",
    "SilverFilterCompatibilityMode": "bioetl.domain.config.runtime",
    "TableConfig": "bioetl.domain.config.table",
    "ValidationConfig": "bioetl.domain.config.validation",
    "convert_write_mode": "bioetl.domain.config._converters",
    "freeze_sequences": "bioetl.domain.config._converters",
    "resolve_loading_strategy": "bioetl.domain.config._converters",
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
