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
- Composite (Composite pipeline domain models, ADR-026)
"""

from __future__ import annotations

# Composite pipeline subpackage (ADR-026)
from bioetl.domain import composite

# Data contracts (Gold layer validation schemas)
from bioetl.domain import contracts

# Domain constants module
from bioetl.domain import constants

# Configuration objects
from bioetl.domain.config import (
    DEFAULT_VALIDATION_CONFIG,
    DQConfig,
    PipelineConfig,
    RuntimeConfig,
    TableConfig,
    ValidationConfig,
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
    ChemblPublication,
    ChemblPublicationRecord,
    ChemblPublicationTermRecord,
    CompoundRecord,
    # CrossRef
    CrossRefPublicationEntity,
    DocumentSimilarity,
    DocumentTerm,
    Molecule,
    MoleculeRecord,
    # OpenAlex
    OpenAlexPublicationEntity,
    ProteinClassification,
    PubchemMolecule,
    PubchemMoleculeRecord,
    # PubMed
    PubMedPublicationEntity,
    # Publication Base (for composite pipelines, ADR-024)
    PublicationEntityBase,
    PublicationRecord,
    # SemanticScholar
    SemanticScholarPublicationEntity,
    Target,
    TargetComponent,
    TargetComponentRecord,
    TargetRecord,
    UniprotTarget,
    # Deprecated aliases (ADR-024, glossary v2.0)
    Compound,
    Document,
    Protein,
    PubChemCompoundRecord,
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
    MetricsServerError,
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
    normalize_pmc_id,
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
    BronzeDQAnalyzerPort,
    BronzeDQConfigPort,
    BronzeMetadataInput,
    CheckpointPort,
    CircuitBreakerPort,
    DQMonitorPort,
    DQReportWriterPort,
    DataNormalizationPort,
    DataSourcePort,
    DeltaReaderPort,
    FilterableDataSourcePort,
    GoldDQAnalyzerPort,
    GoldDQConfigPort,
    GoldMetadataInput,
    GoldValidatorPort,
    HealthCheckPort,
    HealthCheckResult,
    HealthMonitorPort,
    HealthStatePort,
    HealthStatusLiteral,
    IDMappingPort,
    InputFilterPort,
    JsonEncoderPort,
    LockPort,
    LoggerPort,
    MemoryMonitorPort,
    MemoryStats,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsExtractorPort,
    MetricsPort,
    NoOpAudit,
    NoOpMemoryMonitor,
    NoOpMetadataWriter,
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
    SilverDQAnalyzerPort,
    SilverDQConfigPort,
    SilverMetadataInput,
    SilverRef,
    SilverValidatorPort,
    StoragePort,
    TracingPort,
    UnitConverterPort,
    ValueValidatorPort,
)

# Resilience (domain value objects)
from bioetl.domain.resilience import CircuitBreakerConfig, RetryConfig

# Serialization (centralized JSON per RULES.md §2.8.1)
from bioetl.domain.serialization import (
    deserialize_from_json,
    flatten_arrow_table_for_export,
    is_orjson_available,
    serialize_to_json,
    serialize_to_json_canonical,
)

# Domain services
from bioetl.domain.services import IdentityService

# Domain constants
from bioetl.domain.constants import META_FIELDS

# Pure domain transformations
from bioetl.domain.transformations import (
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
    MolecularWeight,
    PChemblValue,
    PubChemCid,
    PubMedId,
    PublicationYear,
    UniProtId,
    ValueObject,
)

__all__ = [
    # Composite pipeline (subpackage)
    "composite",
    # Data contracts (subpackage)
    "contracts",
    # Constants
    "constants",
    # Configuration
    "DEFAULT_VALIDATION_CONFIG",
    "DQConfig",
    "PipelineConfig",
    "RuntimeConfig",
    "TableConfig",
    "ValidationConfig",
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
    "ChemblPublicationRecord",
    "ChemblPublicationTermRecord",
    "MoleculeRecord",
    "PubchemMoleculeRecord",
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
    "ChemblPublication",
    "CompoundRecord",
    # CrossRef
    "CrossRefPublicationEntity",
    "DocumentSimilarity",
    "DocumentTerm",
    "Molecule",
    # OpenAlex
    "OpenAlexPublicationEntity",
    "ProteinClassification",
    "PubchemMolecule",
    # PubMed
    "PubMedPublicationEntity",
    # Publication Base (for composite pipelines, ADR-024)
    "PublicationEntityBase",
    # SemanticScholar
    "SemanticScholarPublicationEntity",
    "Target",
    "TargetComponent",
    "UniprotTarget",
    # Deprecated entity aliases (ADR-024, glossary v2.0)
    "Compound",  # → PubchemMolecule
    "Document",  # → ChemblPublication
    "Protein",  # → UniprotTarget
    "PubChemCompoundRecord",  # → PubchemMoleculeRecord
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
    "MetricsServerError",
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
    "BronzeDQAnalyzerPort",
    "BronzeDQConfigPort",
    "BronzeMetadataInput",
    "CheckpointPort",
    "CircuitBreakerPort",
    "DQMonitorPort",
    "DQReportWriterPort",
    "DataNormalizationPort",
    "DataSourcePort",
    "DeltaReaderPort",
    "FilterableDataSourcePort",
    "GoldDQAnalyzerPort",
    "GoldDQConfigPort",
    "GoldMetadataInput",
    "GoldValidatorPort",
    "HealthCheckPort",
    "HealthCheckResult",
    "HealthMonitorPort",
    "HealthStatePort",
    "HealthStatusLiteral",
    "IDMappingPort",
    "InputFilterPort",
    "JsonEncoderPort",
    "LockPort",
    "LoggerPort",
    "MemoryMonitorPort",
    "MemoryStats",
    "MetadataCoordinatorPort",
    "MetadataWriterPort",
    "MetricsExtractorPort",
    "MetricsPort",
    "NoOpAudit",
    "NoOpMemoryMonitor",
    "NoOpMetadataWriter",
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
    "SilverDQAnalyzerPort",
    "SilverDQConfigPort",
    "SilverMetadataInput",
    "SilverRef",
    "SilverValidatorPort",
    "StoragePort",
    "TracingPort",
    "UnitConverterPort",
    "ValueValidatorPort",
    # Resilience
    "CircuitBreakerConfig",
    "RetryConfig",
    # Services
    "IdentityService",
    # Serialization (centralized JSON)
    "deserialize_from_json",
    "flatten_arrow_table_for_export",
    "is_orjson_available",
    "serialize_to_json",
    "serialize_to_json_canonical",
    # Normalization (pure functions, REFACTOR-004)
    "extract_first_item",
    "extract_first_string",
    "format_date_parts",
    "normalize_doi",
    "normalize_pmc_id",
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
    "MolecularWeight",
    "PChemblValue",
    "PubChemCid",
    "PubMedId",
    "PublicationYear",
    "UniProtId",
    "ValueObject",
]
