"""Core domain types for BioETL.

This facade preserves ``from bioetl.domain.types import X`` imports without
forcing eager import of all type submodules during package initialization.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent as DomainEvent
    from bioetl.domain.types.contract_rollout import (
        ContractRolloutPolicy as ContractRolloutPolicy,
    )
    from bioetl.domain.types.contract_rollout import (
        VersionedContractTarget as VersionedContractTarget,
    )
    from bioetl.domain.types.debug_export import (
        DebugExportPack as DebugExportPack,
    )
    from bioetl.domain.types.debug_export import (
        DebugExportResult as DebugExportResult,
    )
    from bioetl.domain.types.enums import (
        CellularityType as CellularityType,
    )
    from bioetl.domain.types.enums import (
        CircuitBreakerState as CircuitBreakerState,
    )
    from bioetl.domain.types.enums import (
        DataClassification as DataClassification,
    )
    from bioetl.domain.types.enums import (
        DriftLevel as DriftLevel,
    )
    from bioetl.domain.types.enums import (
        ErrorType as ErrorType,
    )
    from bioetl.domain.types.enums import (
        ExecutionContext as ExecutionContext,
    )
    from bioetl.domain.types.enums import (
        HealthStatus as HealthStatus,
    )
    from bioetl.domain.types.enums import (
        PublicationType as PublicationType,
    )
    from bioetl.domain.types.enums import (
        QuarantineRecordStatus as QuarantineRecordStatus,
    )
    from bioetl.domain.types.enums import (
        RunType as RunType,
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
    from bioetl.domain.types.health import (
        ComponentHealthResult as ComponentHealthResult,
    )
    from bioetl.domain.types.health import (
        HealthReport as HealthReport,
    )
    from bioetl.domain.types.health import (
        PreflightReport as PreflightReport,
    )
    from bioetl.domain.types.health import (
        ValidationResult as ValidationResult,
    )
    from bioetl.domain.types.identifiers import (
        ArrowSchema as ArrowSchema,
    )
    from bioetl.domain.types.identifiers import (
        BatchID as BatchID,
    )
    from bioetl.domain.types.identifiers import (
        BronzeRecord as BronzeRecord,
    )
    from bioetl.domain.types.identifiers import (
        ContentHash as ContentHash,
    )
    from bioetl.domain.types.identifiers import (
        EntityID as EntityID,
    )
    from bioetl.domain.types.identifiers import (
        GoldRecord as GoldRecord,
    )
    from bioetl.domain.types.identifiers import (
        GoldSchemaType as GoldSchemaType,
    )
    from bioetl.domain.types.identifiers import (
        JsonDict as JsonDict,
    )
    from bioetl.domain.types.identifiers import (
        MetaDict as MetaDict,
    )
    from bioetl.domain.types.identifiers import (
        PrimaryId as PrimaryId,
    )
    from bioetl.domain.types.identifiers import (
        RunID as RunID,
    )
    from bioetl.domain.types.identifiers import (
        SilverRecord as SilverRecord,
    )
    from bioetl.domain.types_config_validation import (
        ConfigValidationError as ConfigValidationError,
    )

_EXPORT_GROUPS: dict[str, tuple[str, ...]] = {
    "bioetl.domain.aggregates.events": ("DomainEvent",),
    "bioetl.domain.types.contract_rollout": (
        "ContractRolloutPolicy",
        "VersionedContractTarget",
    ),
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

__all__ = [*_EXPORT_MODULES]


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
