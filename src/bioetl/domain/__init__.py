"""
Domain layer package.

Terminology updates (v3.0 migration):
    - SourceRecord: Canonical name for records from data sources.
      Deprecated alias: RawRecord (will be removed in v3.0).

Type Aliases (unified in v3.0):
    - RawRecord: Single record as dict[str, Any]
    - RecordBatch: Batch of records as list[RawRecord]
    - ApiPayload: Raw API response as dict[str, Any]
    - FieldConfig: Field configuration as dict[str, Any]

    Import from ``bioetl.domain.types`` for type aliases.

Tabular Data Abstractions:
    - Record: Single data record (dict-like interface)
    - RecordSet: Collection of records with schema
    - TabularData: Full tabular data abstraction (replaces pd.DataFrame)
    - MutableTabularData: TabularData with mutation capabilities

    Import from ``bioetl.domain.data`` for tabular data protocols.
"""

from bioetl.domain.aggregates import PipelineIdentity
from bioetl.domain.data import (
    MutableTabularData,
    Record,
    RecordSet,
    TabularData,
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
    SourceRecord,
)
from bioetl.domain.types import (
    ApiPayload,
    FieldConfig,
    RawRecord,
    RecordBatch,
)
from bioetl.domain.value_objects import ChemblId, EntityName, HashDigest, PipelineId, RunId

__all__ = [
    # Tabular data abstractions
    "MutableTabularData",
    "Record",
    "RecordSet",
    "TabularData",
    # Type aliases
    "ApiPayload",
    "FieldConfig",
    "RawRecord",
    "RecordBatch",
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
    # Value objects
    "ChemblId",
    "EntityName",
    "HashDigest",
    "PipelineId",
    "RunId",
    # Aggregates
    "PipelineIdentity",
    # Record source
    "InMemoryRecordSource",
    "RecordSourceABC",
    "SourceRecord",
]
