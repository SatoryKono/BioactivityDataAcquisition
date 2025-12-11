"""Domain ports (hexagonal architecture boundaries).

Type aliases are available from :mod:`bioetl.domain.types` module.
This module re-exports them for convenience but new code should import
directly from ``bioetl.domain.types``.
"""

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
from bioetl.domain._deprecations import (
    emit_deprecation_warning,
    resolve_deprecated_type,
    get_deprecated_names_for_module,
)

# =============================================================================
# Deprecated Type Aliases (backward compatibility re-exports)
# =============================================================================
# Deprecated names are now managed centrally in bioetl.domain._deprecations.

_DEPRECATED_TYPE_ALIASES = get_deprecated_names_for_module(__name__)


def __getattr__(name: str) -> type:
    """Emit deprecation warning for legacy type alias imports.

    Uses centralized deprecation registry from bioetl.domain._deprecations.
    """
    if name in _DEPRECATED_TYPE_ALIASES:
        emit_deprecation_warning(name, stacklevel=2)
        return resolve_deprecated_type(name)
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
