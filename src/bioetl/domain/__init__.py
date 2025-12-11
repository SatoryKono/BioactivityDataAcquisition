"""
Domain layer package.

This is the core domain layer following Hexagonal Architecture (Ports & Adapters)
and Domain-Driven Design (DDD) principles.

Domain Entities (from ``bioetl.domain.entities``):
    - Activity: Bioactivity measurement
    - Assay: Biological assay
    - Target: Biological target
    - Molecule: Chemical compound
    - Cell: Cell line
    - Publication: Scientific publication
    - Tissue: Biological tissue

Domain Services (from ``bioetl.domain.services``):
    - BusinessKeyService: Compute business keys for deduplication
    - EntityFactory: Create entities from raw records

Type Aliases
------------
API-specific types (from ``bioetl.domain.types``):
    - ApiPayload: Raw API response as dict[str, Any]
    - FieldConfig: Field configuration as dict[str, Any]

Tabular Data Abstractions (from ``bioetl.domain.data``):
    - Record: Single data record (dict-like interface)
    - RecordBatch: Batch of records as Sequence[Mapping[str, Any]]
    - RecordSet: Collection of records with schema
    - TabularData: Full tabular data abstraction (replaces pd.DataFrame)
    - MutableTabularData: TabularData with mutation capabilities

Pydantic Models (from ``bioetl.domain.record_source``):
    - SourceRecordModel: Pydantic model for API boundary parsing
"""

from bioetl.domain.aggregates import PipelineIdentity
from bioetl.domain.data import (
    MutableTabularData,
    Record,
    RecordBatch,
    RecordSet,
    TabularData,
)
from bioetl.domain.entities import (
    Activity,
    Assay,
    Cell,
    EntityBase,
    Molecule,
    Publication,
    Target,
    Tissue,
)
from bioetl.domain.errors import (
    BioetlError,
    ClientError,
    ClientNetworkError,
    ClientRateLimitError,
    ClientResponseError,
    ConfigError,
    ConfigValidationError,
    PipelineStageError,
    ProviderError,
)
from bioetl.domain.record_source import (
    InMemoryRecordSource,
    RecordSourceABC,
    SourceRecordModel,
)
from bioetl.domain.services import (
    BusinessKeyService,
    EntityFactory,
    get_business_key_service,
    get_entity_factory,
)
from bioetl.domain.types import (
    ApiPayload,
    FieldConfig,
)
from bioetl.domain.value_objects import (
    ActivityId,
    AssayId,
    CellId,
    ChemblId,
    DocumentId,
    EntityName,
    HashDigest,
    MoleculeId,
    PipelineId,
    RunId,
    StageName,
    TargetId,
    TissueId,
)

__all__ = [
    # Domain Entities
    "Activity",
    "Assay",
    "Cell",
    "EntityBase",
    "Molecule",
    "Publication",
    "Target",
    "Tissue",
    # Domain Services
    "BusinessKeyService",
    "EntityFactory",
    "get_business_key_service",
    "get_entity_factory",
    # Tabular data abstractions (from domain.data)
    "MutableTabularData",
    "Record",
    "RecordBatch",
    "RecordSet",
    "TabularData",
    # API-specific type aliases (from domain.types)
    "ApiPayload",
    "FieldConfig",
    # Errors
    "BioetlError",
    "ClientError",
    "ClientNetworkError",
    "ClientRateLimitError",
    "ClientResponseError",
    "ConfigError",
    "ConfigValidationError",
    "PipelineStageError",
    "ProviderError",
    # Value objects - generic
    "EntityName",
    "HashDigest",
    "PipelineId",
    "RunId",
    "StageName",
    # Value objects - ChEMBL identifiers
    "ActivityId",
    "AssayId",
    "CellId",
    "ChemblId",
    "DocumentId",
    "MoleculeId",
    "TargetId",
    "TissueId",
    # Aggregates
    "PipelineIdentity",
    # Record source
    "InMemoryRecordSource",
    "RecordSourceABC",
    "SourceRecordModel",
]
