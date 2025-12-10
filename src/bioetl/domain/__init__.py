"""
Domain layer package.

Terminology updates (v3.0 migration):
    - SourceRecord: Canonical name for records from data sources.
      Deprecated alias: RawRecord (will be removed in v3.0).
"""

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
from bioetl.domain.value_objects import ChemblId, EntityName, RunId

__all__ = [
    "BioetlError",
    "ChemblId",
    "ClientError",
    "ClientNetworkError",
    "ClientRateLimitError",
    "ClientResponseError",
    "ConfigError",
    "ConfigValidationError",
    "EntityName",
    "InMemoryRecordSource",
    "PipelineStageError",
    "ProviderError",
    "RecordSourceABC",
    "RunId",
    "SourceRecord",
]
