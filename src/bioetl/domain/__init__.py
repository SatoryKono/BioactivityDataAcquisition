"""
Domain layer package.

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

Migration Notes (v3.0)
----------------------
- ``RawRecord`` is deprecated. Use ``Mapping[str, Any]`` or ``Record`` protocol.
- ``RecordBatch`` moved from ``domain.types`` to ``domain.data``.
  The canonical definition is now ``Sequence[Mapping[str, Any]]``.
"""

from bioetl.domain.aggregates import PipelineIdentity
from bioetl.domain.data import (
    MutableTabularData,
    Record,
    RecordBatch,
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
)
from bioetl.domain.value_objects import ChemblId, EntityName, HashDigest, PipelineId, RunId

__all__ = [
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
