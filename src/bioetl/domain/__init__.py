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

Pydantic Models (from ``bioetl.domain.record_source``):
    - SourceRecordModel: Pydantic model for API boundary parsing
    - SourceRecord: Deprecated alias for SourceRecordModel

Migration Notes (v3.0)
----------------------
- ``RawRecord`` has been removed. Use ``Mapping[str, Any]`` or ``Record`` protocol.
- ``SourceRecord`` renamed to ``SourceRecordModel``. Old name available as alias.
- ``RecordBatch`` moved from ``domain.types`` to ``domain.data``.
  The canonical definition is now ``Sequence[Mapping[str, Any]]``.
- ``RecordSourceABC.iter_records()`` now returns ``Iterable[Sequence[Mapping[str, Any]]]``
  instead of ``Iterable[list[SourceRecord]]``.
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
    SourceRecord,  # Deprecated alias for SourceRecordModel
    SourceRecordModel,
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
    "SourceRecordModel",
    "SourceRecord",  # Deprecated alias for SourceRecordModel
]
