"""Domain ports (hexagonal architecture boundaries).

Type aliases are available from :mod:`bioetl.domain.types` module.
This module re-exports them for convenience but new code should import
directly from ``bioetl.domain.types``.
"""

import warnings

from bioetl.domain.ports.entity_models import EntityModelRegistryABC
from bioetl.domain.ports.extraction import (
    BatchAdapterABC,
    ExtractionServiceABC,
    RecordFetcherABC,
    VersionProviderABC,
    from_raw_records,
    to_raw_records,
)
from bioetl.domain.ports.filesystem import PathResolverABC
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
from bioetl.domain.data import RecordBatch
from bioetl.domain.types import ApiPayload

# =============================================================================
# Deprecated Type Aliases (backward compatibility re-exports)
# =============================================================================

_DEPRECATED_TYPE_ALIASES = {
    "RawRecord": "Mapping[str, Any]",  # Use Mapping[str, Any] directly
    "RawRecordDict": "Mapping[str, Any]",
    "RawRecordBatch": "RecordBatch",
    "RawRecordList": "RecordBatch",
    "RawPayload": "ApiPayload",
}


def __getattr__(name: str) -> type:
    """Emit deprecation warning for legacy type alias imports."""
    from typing import Any

    if name in _DEPRECATED_TYPE_ALIASES:
        new_name = _DEPRECATED_TYPE_ALIASES[name]
        warnings.warn(
            f"{name} is deprecated, use {new_name} instead. "
            "See migration guide in bioetl.domain.types module docstring.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Return appropriate fallback types
        if name in ("RawRecord", "RawRecordDict"):
            return dict[str, Any]
        elif name in ("RawRecordBatch", "RawRecordList"):
            from bioetl.domain.data import RecordBatch as _RecordBatch

            return _RecordBatch
        elif name == "RawPayload":
            return ApiPayload
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__: list[str] = [
    # Canonical type aliases
    "ApiPayload",  # from domain.types
    "RecordBatch",  # from domain.data
    # Deprecated type aliases (for backward compatibility via __getattr__)
    "RawRecord",  # deprecated, use Mapping[str, Any]
    "RawRecordBatch",
    "RawRecordDict",
    "RawRecordList",
    "RawPayload",
    # Entity model ports
    "EntityModelRegistryABC",
    # Extraction ports
    "BatchAdapterABC",
    "ExtractionServiceABC",
    "RecordFetcherABC",
    "VersionProviderABC",
    # Backward compatibility helpers
    "from_raw_records",
    "to_raw_records",
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
