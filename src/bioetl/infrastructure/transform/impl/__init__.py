"""Concrete transform implementations."""

import warnings

from bioetl.infrastructure.transform.impl.chembl_normalization_service_impl import (
    ChemblNormalizationService,
)
from bioetl.infrastructure.transform.impl.default_normalization_transformer_impl import (  # noqa: E501
    NormalizationServiceImpl,
    NormalizationServiceImpl as DefaultNormalizationTransformerImpl,
)
from bioetl.infrastructure.transform.impl.hash_service import Blake2bHashService
from bioetl.infrastructure.transform.impl.hasher import HasherImpl
from bioetl.infrastructure.transform.impl.index_generator import (
    SequentialIndexGenerator,
)
from bioetl.infrastructure.transform.impl.timestamp_provider import (
    DeterministicTimestampProvider,
)

# Deprecated aliases for backward compatibility
_DEPRECATED_ALIASES = {
    "ChemblNormalizationServiceImpl": "ChemblNormalizationService",
    "DefaultNormalizationTransformerImpl": "NormalizationServiceImpl",
}


def __getattr__(name: str):
    if name in _DEPRECATED_ALIASES:
        warnings.warn(
            f"{name} is deprecated, use {_DEPRECATED_ALIASES[name]} instead. "
            "Will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[_DEPRECATED_ALIASES[name]]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "HasherImpl",
    "Blake2bHashService",
    "DeterministicTimestampProvider",
    "SequentialIndexGenerator",
    "NormalizationServiceImpl",
    "DefaultNormalizationTransformerImpl",  # Deprecated alias
    "ChemblNormalizationService",
    "ChemblNormalizationServiceImpl",  # Deprecated alias
]
