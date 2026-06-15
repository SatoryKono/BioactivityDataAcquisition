"""Core domain types for BioETL.

This facade preserves ``from bioetl.domain.types import X`` imports without
forcing eager import of all type submodules during package initialization.
"""

from __future__ import annotations

from importlib import import_module

from bioetl.domain.types.debug_export import (
    DebugExportPack as DebugExportPack,
)
from bioetl.domain.types.debug_export import (
    DebugExportResult as DebugExportResult,
)
from bioetl.domain.types.gold_contracts import (
    GOLD_CONTRACT_VERSION_UNKNOWN as GOLD_CONTRACT_VERSION_UNKNOWN,
)
from bioetl.domain.types.gold_contracts import (
    GoldBusinessRuleSpec as GoldBusinessRuleSpec,
)
from bioetl.domain.types.gold_contracts import (
    GoldContractValidationError as GoldContractValidationError,
)
from bioetl.domain.types.gold_contracts import (
    GoldRejectReason as GoldRejectReason,
)
from bioetl.domain.types.gold_contracts import (
    GoldRejectReasonCode as GoldRejectReasonCode,
)
from bioetl.domain.types.gold_contracts import (
    ScdConfig as ScdConfig,
)
from bioetl.domain.types.gold_contracts import (
    build_gold_contract_reject_reason as build_gold_contract_reject_reason,
)
from bioetl.domain.types.gold_contracts import (
    build_gold_semantic_reject_reason as build_gold_semantic_reject_reason,
)
from bioetl.domain.types.gold_contracts import (
    classify_gold_schema_error_reason as classify_gold_schema_error_reason,
)
from bioetl.domain.types.gold_contracts import (
    resolve_gold_contract_version as resolve_gold_contract_version,
)
from bioetl.domain.types.gold_schema_policy import (
    GoldSchemaPolicyByVersion as GoldSchemaPolicyByVersion,
)
from bioetl.domain.types.gold_schema_policy import (
    GoldSchemaVersionPolicy as GoldSchemaVersionPolicy,
)

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
        "GOLD_CONTRACT_VERSION_UNKNOWN",
        "GoldContractValidationError",
        "GoldRejectReason",
        "GoldRejectReasonCode",
        "GoldBusinessRuleSpec",
        "ScdConfig",
        "build_gold_contract_reject_reason",
        "build_gold_semantic_reject_reason",
        "classify_gold_schema_error_reason",
        "resolve_gold_contract_version",
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
    "bioetl.domain.types.debug_export": (
        "DebugExportPack",
        "DebugExportResult",
    ),
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
