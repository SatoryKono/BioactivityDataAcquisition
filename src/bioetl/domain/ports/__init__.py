"""Domain ports (hexagonal architecture boundaries).

Type aliases are available from :mod:`bioetl.domain.types` module.
This module re-exports them for convenience but new code should import
directly from ``bioetl.domain.types``.
"""

from __future__ import annotations

from typing import cast

from bioetl.domain._deprecations import (
    emit_deprecation_warning,
    get_deprecated_names_for_module,
    resolve_deprecated_type,
)
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
from bioetl.domain.ports.config_loader_port import (
    ConfigLoaderPortABC,
    ConfigPathResolverPortABC,
)
from bioetl.domain.ports.infrastructure_factory_port import (
    ABCRegistryResolverPortABC,
    InfrastructureFactoryPortABC,
)
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.types import ApiPayload

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
        return cast(type, resolve_deprecated_type(name))
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
    # Configuration ports
    "ConfigLoaderPortABC",
    "ConfigPathResolverPortABC",
    # Infrastructure factory ports
    "ABCRegistryResolverPortABC",
    "InfrastructureFactoryPortABC",
]
