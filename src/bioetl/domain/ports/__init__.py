"""Domain ports (hexagonal architecture boundaries).

Type aliases are available from :mod:`bioetl.domain.types` module.
This module re-exports them for convenience but new code should import
directly from ``bioetl.domain.types``.
"""

import warnings

from bioetl.domain.ports.extraction import (
    BatchAdapterABC,
    ExtractionServiceABC,
    RecordFetcherABC,
    VersionProviderABC,
    from_raw_records,
    to_raw_records,
)
from bioetl.domain.ports.parsing import (
    PaginationInfo,
    ResponseParserPortABC,
)
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.types import (
    ApiPayload,
    RawRecord,
    RecordBatch,
)

# =============================================================================
# Deprecated Type Aliases (backward compatibility re-exports)
# =============================================================================

_DEPRECATED_TYPE_ALIASES = {
    "RawRecordDict": "RawRecord",
    "RawRecordBatch": "RecordBatch",
    "RawRecordList": "RecordBatch",
    "RawPayload": "ApiPayload",
}


def __getattr__(name: str) -> type:
    """Emit deprecation warning for legacy type alias imports."""
    if name in _DEPRECATED_TYPE_ALIASES:
        new_name = _DEPRECATED_TYPE_ALIASES[name]
        warnings.warn(
            f"{name} is deprecated, use {new_name} from bioetl.domain.types instead. "
            "See migration guide in bioetl.domain.types module docstring.",
            DeprecationWarning,
            stacklevel=2,
        )
        from bioetl.domain import types

        return getattr(types, new_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__: list[str] = [
    # Canonical type aliases (from domain.types)
    "ApiPayload",
    "RawRecord",
    "RecordBatch",
    # Deprecated type aliases (for backward compatibility)
    "RawRecordBatch",
    "RawRecordDict",
    "RawRecordList",
    "RawPayload",
    # Extraction ports
    "BatchAdapterABC",
    "ExtractionServiceABC",
    "RecordFetcherABC",
    "VersionProviderABC",
    # Backward compatibility helpers
    "from_raw_records",
    "to_raw_records",
    # Parsing ports
    "PaginationInfo",
    "ResponseParserPortABC",
    # Schema ports
    "SchemaContractProviderABC",
]
