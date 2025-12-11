"""
Value Objects для ключевых идентификаторов.

Обеспечивают type safety и валидацию на уровне типов.

Этот пакет содержит:
- identifiers: ActivityId, RunId, PipelineId, EntityName, ChemblId, StageName
- crypto: HashDigest
- network: HttpUrl
- temporal: Timestamp
"""

from bioetl.domain.value_objects.crypto import HashDigest
from bioetl.domain.value_objects.identifiers import (
    ActivityId,
    ChemblId,
    EntityName,
    PipelineId,
    RunId,
    StageName,
)
from bioetl.domain.value_objects.network import HttpUrl
from bioetl.domain.value_objects.temporal import Timestamp

__all__ = [
    # Identifiers
    "ActivityId",
    "RunId",
    "StageName",
    "EntityName",
    "PipelineId",
    "ChemblId",
    # Crypto
    "HashDigest",
    # Network
    "HttpUrl",
    # Temporal
    "Timestamp",
]
