"""Core domain types for BioETL.

Implements RULES.md §1 - Domain Layer with pure types and value objects.
No I/O operations are allowed (REQ-ARCH-003).

Type Safety: NewType for IDs, TypedDict for records, frozen dataclasses for VOs.
See RULES.md §1.3 for Any usage justification (external APIs, logging, protocols).

Sub-modules:
- identifiers: NewType IDs, type aliases, SilverRecord TypedDict
- enums: StrEnum classes with business logic methods
- health: Frozen dataclasses for health reports and preflight validation
"""

from bioetl.domain.types.enums import (
    CellularityType,
    CircuitBreakerState,
    DataClassification,
    DriftLevel,
    ErrorType,
    ExecutionContext,
    HealthStatus,
    PublicationType,
    QuarantineRecordStatus,
    RunType,
)
from bioetl.domain.types.health import (
    ComponentHealthResult,
    HealthReport,
    PreflightReport,
    ValidationResult,
)
from bioetl.domain.types.identifiers import (
    ArrowSchema,
    BatchID,
    BronzeRecord,
    ContentHash,
    EntityID,
    GoldRecord,
    GoldSchemaType,
    JsonDict,
    MetaDict,
    PrimaryId,
    RunID,
    ScdConfig,
    SilverRecord,
)
from bioetl.domain.types_config_validation import ConfigValidationError

__all__ = [
    "BatchID",
    "CellularityType",
    "CircuitBreakerState",
    "ComponentHealthResult",
    "ConfigValidationError",
    "ContentHash",
    "DataClassification",
    "DriftLevel",
    "EntityID",
    "ErrorType",
    "ExecutionContext",
    "HealthReport",
    "HealthStatus",
    "JsonDict",
    "PreflightReport",
    "PublicationType",
    "QuarantineRecordStatus",
    "RunID",
    "RunType",
    "SilverRecord",
    "ValidationResult",
]
