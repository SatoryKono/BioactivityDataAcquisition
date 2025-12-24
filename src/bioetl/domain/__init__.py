"""Domain layer: entities, value objects, ports, and context objects.

This module provides a clean public API for the domain layer, exposing:
- Ports (Protocol interfaces for dependency injection)
- Entities (Rich domain objects with invariants)
- Types (Value objects, enums, type aliases)
- Exceptions (Domain-specific error hierarchy)
- Context (Pipeline execution context)
- Filters (Gold layer and input filtering configuration)
- Configuration (Domain config objects)
- Transformations (Pure functions for hashing, schema drift, DQ)
- Error classification (Pure domain logic for error categorization)
"""

from __future__ import annotations

# Configuration objects
from bioetl.domain.config import (
    DQConfig,
    PipelineConfig,
    RuntimeConfig,
    TableConfig,
)

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
    AuthFailureError,
    BioETLError,
    BucketNotFoundError,
    CheckpointConflictError,
    ChemblApiError,
    CircuitBreakerOpenError,
    CriticalError,
    DataQualityError,
    DataQualityThresholdError,
    InfrastructureError,
    InvalidDataFormatError,
    LockAcquisitionError,
    LockLostError,
    MergeConflictError,
    MissingRequiredFieldError,
    NetworkError,
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

# Medallion policies
from bioetl.domain.medallion import ClearPolicy, MedallionPolicy

# Ports
from bioetl.domain.ports import (
    CheckpointPort,
    DataSourcePort,
    FilterableDataSourcePort,
    GoldValidatorPort,
    InputFilterPort,
    LockPort,
    LoggerPort,
    MetricsPort,
    QuarantinePort,
    StoragePort,
    TracingPort,
)

# Pure domain transformations
from bioetl.domain.transformations import (
    META_FIELDS,
    calculate_dq_score,
    canonical_json_dumps,
    detect_hash_collision,
    detect_schema_drift,
    exceeds_threshold,
    generate_content_hash,
    generate_entity_id,
    normalize_for_hash,
    safe_float,
    safe_int,
    safe_str,
)

# Types
from bioetl.domain.types import (
    ArrowSchema,
    BatchID,
    BronzeRecord,
    CircuitBreakerState,
    ComponentHealthResult,
    ContentHash,
    DataClassification,
    DQStatus,
    DriftLevel,
    EntityID,
    ErrorType,
    HealthReport,
    HealthStatus,
    RunID,
    RunType,
    SilverRecord,
    ValidationResult,
)

__all__ = [
    # Configuration
    "DQConfig",
    "PipelineConfig",
    "RuntimeConfig",
    "TableConfig",
    # Context
    "PipelineContext",
    "PipelineRunContext",
    # Entities
    "Activity",
    "Assay",
    "BaseEntity",
    "Compound",
    "Document",
    "Molecule",
    "Protein",
    "Publication",
    "Target",
    "TargetComponent",
    # Error classifier
    "ErrorClassifier",
    # Exceptions - Base
    "ApiError",
    "AuthFailureError",
    "BioETLError",
    "CriticalError",
    "DataQualityError",
    "RecoverableError",
    # Exceptions - Critical
    "BucketNotFoundError",
    "CheckpointConflictError",
    "InfrastructureError",
    "LockAcquisitionError",
    "LockLostError",
    "MergeConflictError",
    # Exceptions - Recoverable
    "ChemblApiError",
    "CircuitBreakerOpenError",
    "NetworkError",
    "RateLimitError",
    "RetryExhaustedError",
    "StorageError",
    "TableNotFoundError",
    "UploadError",
    # Exceptions - Data Quality
    "DataQualityThresholdError",
    "InvalidDataFormatError",
    "MissingRequiredFieldError",
    "SchemaViolationError",
    # Filters
    "FilterLoadResult",
    "GoldColumnFilter",
    "GoldFilterConfig",
    "GoldListContainsFilter",
    "GoldListLengthFilter",
    "GoldRangeFilter",
    "InputFilterConfig",
    # Medallion policies
    "ClearPolicy",
    "MedallionPolicy",
    # Ports
    "CheckpointPort",
    "DataSourcePort",
    "FilterableDataSourcePort",
    "GoldValidatorPort",
    "InputFilterPort",
    "LockPort",
    "LoggerPort",
    "MetricsPort",
    "QuarantinePort",
    "StoragePort",
    "TracingPort",
    # Transformations (pure functions)
    "META_FIELDS",
    "calculate_dq_score",
    "canonical_json_dumps",
    "detect_hash_collision",
    "detect_schema_drift",
    "exceeds_threshold",
    "generate_content_hash",
    "generate_entity_id",
    "normalize_for_hash",
    "safe_float",
    "safe_int",
    "safe_str",
    # Types
    "ArrowSchema",
    "BatchID",
    "BronzeRecord",
    "CircuitBreakerState",
    "ComponentHealthResult",
    "ContentHash",
    "DataClassification",
    "DQStatus",
    "DriftLevel",
    "EntityID",
    "ErrorType",
    "HealthReport",
    "HealthStatus",
    "RunID",
    "RunType",
    "SilverRecord",
    "ValidationResult",
]
