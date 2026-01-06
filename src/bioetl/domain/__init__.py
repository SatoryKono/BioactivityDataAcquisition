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

# Base configuration classes (consolidated DTOs per RULES.md §12.1.6)
from bioetl.domain.configs import (
    BaseClientConfig,
    BaseProviderConfig,
    RateLimitConfig,
)

# Context objects
from bioetl.domain.context import (
    PipelineContext,
    PipelineRunContext,
)

# Entities (Domain objects)
from bioetl.domain.entities import (  # DTO Records (Pydantic); Domain Entities (dataclass)
    ActivityRecord,
    ArticleRecord,
    Assay,
    AssayParameters,
    AssayRecord,
    BaseEntity,
    Bioactivity,
    BioactivityState,
    CellLine,
    CellLineRecord,
    Compound,
    CompoundRecord,
    Document,
    DocumentRecord,
    DocumentSimilarity,
    DocumentTerm,
    DocumentTermRecord,
    Molecule,
    MoleculeRecord,
    Protein,
    ProteinClassification,
    PubChemCompoundRecord,
    Publication,
    PublicationEntity,
    PublicationRecord,
    SemanticScholarPublicationEntity,
    Target,
    TargetComponent,
    TargetComponentRecord,
    TargetRecord,
)

# Error classifier
from bioetl.domain.error_classifier import ErrorClassifier

# Events
from bioetl.domain.events import PipelineEvent

# Exceptions
from bioetl.domain.exceptions import (
    ApiError,
    AuthFailureError,
    BioETLError,
    BronzeValidationError,
    BucketNotFoundError,
    CheckpointConflictError,
    CircuitBreakerOpenError,
    CriticalError,
    DataQualityError,
    DataQualityThresholdError,
    DataValidationError,
    DeltaOptimizeError,
    DeltaSchemaValidationError,
    DeltaTransactionError,
    DeltaWriteConflictError,
    ExternalServiceError,
    InfrastructureError,
    InvalidDataFormatError,
    InvalidStateError,
    LockAcquisitionError,
    LockLostError,
    MergeConflictError,
    MissingRequiredFieldError,
    NetworkError,
    PolicyViolationError,
    RateLimitError,
    RateLimitExceededError,
    RecoverableError,
    RetryExhaustedError,
    SchemaEvolutionError,
    SchemaViolationError,
    ServiceAuthenticationError,
    ServiceUnavailableError,
    StorageError,
    StorageQuotaExceededError,
    TableNotFoundError,
    TimeoutError,
    UploadError,
)

# Filter configuration
from bioetl.domain.filtering import (
    FilterLoadResult,
    GoldColumnFilter,
    GoldFilterConfig,
    GoldListContainsFilter,
    GoldListLengthFilter,
    GoldRangeFilter,
    InputFilterConfig,
)

# Locking (value objects for lock context)
from bioetl.domain.locking import LockContext, LockNotHeldError

# Medallion policies
from bioetl.domain.medallion import ClearPolicy, MedallionPolicy

# Pure domain normalization (REFACTOR-004)
from bioetl.domain.normalization import (
    extract_first_item,
    extract_first_string,
    format_date_parts,
    normalize_doi,
    normalize_string,
    normalize_to_string,
    parse_date_field,
    parse_page_range,
    strip_html_tags,
)

# Ports
from bioetl.domain.ports import (
    ActivityAggregatorPort,
    AuditEntry,
    AuditLayer,
    AuditOperation,
    AuditPort,
    CheckpointPort,
    CircuitBreakerPort,
    DataSourcePort,
    DQMonitorPort,
    FilterableDataSourcePort,
    GoldValidatorPort,
    HealthCheckPort,
    HealthCheckResult,
    HealthMonitorPort,
    HealthStatusLiteral,
    IDMappingPort,
    InputFilterPort,
    JsonEncoderPort,
    LockPort,
    LoggerPort,
    MemoryMonitorPort,
    MemoryStats,
    MetricsExtractorPort,
    MetricsPort,
    NoOpAudit,
    NoOpMemoryMonitor,
    NoOpMetrics,
    NoOpPiiHasher,
    NoOpTracing,
    NormalizationServicePort,
    OutlierFilterPort,
    PiiHasherPort,
    QuarantinePort,
    RateLimiterPort,
    RunnablePort,
    RunnerFactoryPort,
    ShutdownPort,
    SilverValidatorPort,
    StoragePort,
    TracingPort,
    UnitConverterPort,
    ValueValidatorPort,
)

# Resilience (domain value objects)
from bioetl.domain.resilience import CircuitBreakerConfig, RetryConfig, RetryPolicy

# Domain services
from bioetl.domain.services import IdentityService

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
    ConfigValidationError,
    ContentHash,
    DataClassification,
    DriftLevel,
    EntityID,
    ErrorType,
    HealthReport,
    HealthStatus,
    QuarantineRecordStatus,
    RunID,
    RunType,
    SilverRecord,
    ValidationResult,
)

# Pure domain validation (REFACTOR-004)
from bioetl.domain.validation import (
    validate_doi,
    validate_non_empty_string,
    validate_non_negative,
    validate_positive_int,
    validate_smiles,
    validate_year_range,
)

# Value Objects
from bioetl.domain.value_objects import (
    DOI,
    ActivityType,
    ChemblId,
    Concentration,
    ConcentrationUnit,
    DQEvaluationStatus,
    PChemblValue,
    PubChemCid,
    PubMedId,
    UniProtId,
    ValueObject,
)

__all__ = [
    # Configuration
    "DQConfig",
    "PipelineConfig",
    "RuntimeConfig",
    "TableConfig",
    # Base configuration classes (consolidated DTOs)
    "BaseClientConfig",
    "BaseProviderConfig",
    "RateLimitConfig",
    # Context
    "PipelineContext",
    "PipelineRunContext",
    # Entity DTOs (Pydantic Records)
    "ActivityRecord",
    "ArticleRecord",
    "AssayRecord",
    "CellLineRecord",
    "DocumentRecord",
    "DocumentTermRecord",
    "MoleculeRecord",
    "PubChemCompoundRecord",
    "PublicationRecord",
    "TargetComponentRecord",
    "TargetRecord",
    # Domain Entities (dataclass)
    "Assay",
    "AssayParameters",
    "BaseEntity",
    "Bioactivity",
    "BioactivityState",
    "CellLine",
    "Compound",
    "CompoundRecord",
    "Document",
    "DocumentSimilarity",
    "DocumentTerm",
    "Molecule",
    "Protein",
    "ProteinClassification",
    "Publication",
    "PublicationEntity",
    "SemanticScholarPublicationEntity",
    "Target",
    "TargetComponent",
    # Error classifier
    "ErrorClassifier",
    # Events
    "PipelineEvent",
    # Exceptions - Base
    "ApiError",
    "AuthFailureError",
    "BioETLError",
    "BronzeValidationError",
    "CriticalError",
    "DataQualityError",
    "RecoverableError",
    # Exceptions - External Service (abstract, for application layer)
    "ExternalServiceError",
    "ServiceUnavailableError",
    "RateLimitExceededError",
    "ServiceAuthenticationError",
    "DataValidationError",
    # Exceptions - Critical
    "BucketNotFoundError",
    "CheckpointConflictError",
    "DeltaSchemaValidationError",
    "DeltaTransactionError",
    "InfrastructureError",
    "InvalidStateError",
    "LockAcquisitionError",
    "LockLostError",
    "MergeConflictError",
    "PolicyViolationError",
    "StorageQuotaExceededError",
    # Exceptions - Recoverable
    "CircuitBreakerOpenError",
    "DeltaOptimizeError",
    "DeltaWriteConflictError",
    "NetworkError",
    "RateLimitError",
    "RetryExhaustedError",
    "SchemaEvolutionError",
    "StorageError",
    "TableNotFoundError",
    "TimeoutError",
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
    # Locking
    "LockContext",
    "LockNotHeldError",
    # Medallion policies
    "ClearPolicy",
    "MedallionPolicy",
    # Ports
    "ActivityAggregatorPort",
    "AuditEntry",
    "AuditLayer",
    "AuditOperation",
    "AuditPort",
    "CheckpointPort",
    "CircuitBreakerPort",
    "DataSourcePort",
    "DQMonitorPort",
    "FilterableDataSourcePort",
    "GoldValidatorPort",
    "HealthCheckPort",
    "HealthCheckResult",
    "HealthMonitorPort",
    "HealthStatusLiteral",
    "IDMappingPort",
    "InputFilterPort",
    "JsonEncoderPort",
    "LockPort",
    "LoggerPort",
    "MemoryMonitorPort",
    "MemoryStats",
    "MetricsExtractorPort",
    "MetricsPort",
    "NoOpAudit",
    "NoOpMemoryMonitor",
    "NoOpMetrics",
    "NoOpPiiHasher",
    "NoOpTracing",
    "NormalizationServicePort",
    "OutlierFilterPort",
    "PiiHasherPort",
    "QuarantinePort",
    "RateLimiterPort",
    "RunnablePort",
    "RunnerFactoryPort",
    "ShutdownPort",
    "SilverValidatorPort",
    "StoragePort",
    "TracingPort",
    "UnitConverterPort",
    "ValueValidatorPort",
    # Resilience
    "CircuitBreakerConfig",
    "RetryConfig",
    "RetryPolicy",
    # Services
    "IdentityService",
    # Normalization (pure functions, REFACTOR-004)
    "extract_first_item",
    "extract_first_string",
    "format_date_parts",
    "normalize_doi",
    "normalize_string",
    "normalize_to_string",
    "parse_date_field",
    "parse_page_range",
    "strip_html_tags",
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
    # Validation (pure functions, REFACTOR-004)
    "validate_doi",
    "validate_non_empty_string",
    "validate_non_negative",
    "validate_positive_int",
    "validate_smiles",
    "validate_year_range",
    # Types
    "ArrowSchema",
    "BatchID",
    "BronzeRecord",
    "CircuitBreakerState",
    "ComponentHealthResult",
    "ConfigValidationError",
    "ContentHash",
    "DataClassification",
    "DriftLevel",
    "EntityID",
    "ErrorType",
    "HealthReport",
    "HealthStatus",
    "QuarantineRecordStatus",
    "RunID",
    "RunType",
    "SilverRecord",
    "ValidationResult",
    # Value Objects
    "ActivityType",
    "ChemblId",
    "Concentration",
    "ConcentrationUnit",
    "DOI",
    "DQEvaluationStatus",
    "PChemblValue",
    "PubChemCid",
    "PubMedId",
    "UniProtId",
    "ValueObject",
]
