"""Domain ports (hexagonal architecture boundaries).

Type aliases are available from :mod:`bioetl.domain.types` module.
This module re-exports them for convenience but new code should import
directly from ``bioetl.domain.types``.
"""

from __future__ import annotations

from bioetl.domain.data import RecordBatch
from bioetl.domain.ports.entity_models import EntityModelRegistryABC
from bioetl.domain.ports.extraction import (
    BatchAdapterABC,
    ExtractionServiceABC,
    RecordFetcherABC,
    VersionProviderABC,
)
from bioetl.domain.ports.filesystem import PathResolverABC
from bioetl.domain.ports.filters import FilterEnricherABC
from bioetl.domain.ports.output import (
    ChecksumCalculatorPort,
    DataWriterPort,
    MetadataBuilderPort,
    MetadataWriterPort,
    QcArtifactWriterPort,
    QcReportGeneratorPort,
)
from bioetl.domain.ports.parsing import (
    PaginationInfo,
    ResponseParserPortABC,
)
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.types import ApiPayload

__all__: list[str] = [
    # Canonical type aliases
    "ApiPayload",  # from domain.types
    "RecordBatch",  # from domain.data
    # Entity model ports
    "EntityModelRegistryABC",
    # Filter ports
    "FilterEnricherABC",
    # Extraction ports
    "BatchAdapterABC",
    "ExtractionServiceABC",
    "RecordFetcherABC",
    "VersionProviderABC",
    # Filesystem ports
    "PathResolverABC",
    # Output ports
    "ChecksumCalculatorPort",
    "DataWriterPort",
    "MetadataBuilderPort",
    "MetadataWriterPort",
    "QcArtifactWriterPort",
    "QcReportGeneratorPort",
    # Parsing ports
    "PaginationInfo",
    "ResponseParserPortABC",
    # Schema ports
    "SchemaContractProviderABC",
]
