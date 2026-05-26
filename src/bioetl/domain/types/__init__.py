"""Core domain types for BioETL.

This facade preserves ``from bioetl.domain.types import X`` imports without
forcing eager import of all type submodules during package initialization.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_GROUPS: dict[str, tuple[str, ...]] = {
    "bioetl.domain.types.enums": (
        "CellularityType",
        "CircuitBreakerState",
        "DataClassification",
        "DriftLevel",
        "ErrorType",
        "ExecutionContext",
        "HealthStatus",
        "PublicationType",
        "QuarantineRecordStatus",
        "RunType",
    ),
    "bioetl.domain.types.gold_contracts": (
        "GoldBusinessRuleSpec",
        "ScdConfig",
    ),
    "bioetl.domain.types.gold_schema_policy": (
        "GoldSchemaPolicyByVersion",
        "GoldSchemaVersionPolicy",
    ),
    "bioetl.domain.types.health": (
        "ComponentHealthResult",
        "HealthReport",
        "PreflightReport",
        "ValidationResult",
    ),
    "bioetl.domain.types.identifiers": (
        "ArrowSchema",
        "BatchID",
        "BronzeRecord",
        "ContentHash",
        "EntityID",
        "GoldRecord",
        "GoldSchemaType",
        "JsonDict",
        "MetaDict",
        "PrimaryId",
        "RunID",
        "SilverRecord",
    ),
    "bioetl.domain.types_config_validation": ("ConfigValidationError",),
}

_EXPORT_MODULES = {
    export_name: module_name
    for module_name, export_names in _EXPORT_GROUPS.items()
    for export_name in export_names
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str) -> object:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
