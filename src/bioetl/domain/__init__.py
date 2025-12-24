"""Domain layer: entities, value objects, ports, and context objects.

This module provides a clean public API for the domain layer, exposing:
- Ports (Protocol interfaces for dependency injection)
- Entities (Rich domain objects with invariants)
- Types (Value objects, enums, type aliases)
- Exceptions (Domain-specific error hierarchy)
- Context (Pipeline execution context)
- Filters (Gold layer and input filtering configuration)
- Error classification (Pure domain logic for error categorization)
"""

# Ports (Protocol interfaces)
# Context objects
from bioetl.domain.context import (
    PipelineContext,
    PipelineRunContext,
)

# Entities (Domain objects)
from bioetl.domain.entities import (
    Activity,
    Assay,
    BaseEntity,
    Compound,
    Document,
    Molecule,
    Protein,
    Publication,
    Target,
    TargetComponent,
)

# Error classifier
from bioetl.domain.error_classifier import ErrorClassifier

# Exceptions
from bioetl.domain.exceptions import (
    ApiError,
    BioETLError,
    BucketNotFoundError,
    CheckpointConflictError,
    ChemblApiError,
    CircuitBreakerOpenError,
    CriticalError,
    DataQualityError,
    InvalidDataFormatError,
    LockAcquisitionError,
    LockLostError,
    MergeConflictError,
    MissingRequiredFieldError,
    RateLimitError,
    RecoverableError,
    RetryExhaustedError,
    SchemaViolationError,
    StorageError,
    TableNotFoundError,
    UploadError,
)

# Filter configuration
from bioetl.domain.filter_config import (
    FilterLoadResult,
    GoldColumnFilter,
    GoldFilterConfig,
    GoldListContainsFilter,
    GoldListLengthFilter,
    GoldRangeFilter,
    InputFilterConfig,
)
from bioetl.domain.ports import (
    CheckpointPort,
    DataSourcePort,
    GoldValidatorPort,
    InputFilterPort,
    LockPort,
    LoggerPort,
    MetricsPort,
    QuarantinePort,
    StoragePort,
    TracingPort,
)

# Types
from bioetl.domain.types import (
    BatchID,
    CircuitBreakerState,
    ContentHash,
    DataClassification,
    DQStatus,
    DriftLevel,
    EntityID,
    ErrorType,
    HealthStatus,
    RunID,
    RunType,
)

__all__ = [
    # Entities
    "Activity",
    # Exceptions - Base
    "ApiError",
    "Assay",
    "BaseEntity",
    # Types
    "BatchID",
    "BioETLError",
    # Exceptions - Critical
    "BucketNotFoundError",
    "CheckpointConflictError",
    # Ports
    "CheckpointPort",
    # Exceptions - Recoverable
    "ChemblApiError",
    "CircuitBreakerOpenError",
    "CircuitBreakerState",
    "Compound",
    "ContentHash",
    "CriticalError",
    "DQStatus",
    "DataClassification",
    "DataQualityError",
    "DataSourcePort",
    "Document",
    "DriftLevel",
    "EntityID",
    # Error classifier
    "ErrorClassifier",
    "ErrorType",
    # Filters
    "FilterLoadResult",
    "GoldColumnFilter",
    "GoldFilterConfig",
    "GoldListContainsFilter",
    "GoldListLengthFilter",
    "GoldRangeFilter",
    "GoldValidatorPort",
    "HealthStatus",
    "InputFilterConfig",
    "InputFilterPort",
    # Exceptions - Data Quality
    "InvalidDataFormatError",
    "LockAcquisitionError",
    "LockLostError",
    "LockPort",
    "LoggerPort",
    "MergeConflictError",
    "MetricsPort",
    "MissingRequiredFieldError",
    "Molecule",
    # Context
    "PipelineContext",
    "PipelineRunContext",
    "Protein",
    "Publication",
    "QuarantinePort",
    "RateLimitError",
    "RecoverableError",
    "RetryExhaustedError",
    "RunID",
    "RunType",
    "SchemaViolationError",
    "StorageError",
    "StoragePort",
    "TableNotFoundError",
    "Target",
    "TargetComponent",
    "TracingPort",
    "UploadError",
]
