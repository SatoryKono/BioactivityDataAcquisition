"""ChEMBL-specific normalization service implementation.

DEPRECATED: Use DefaultNormalizationTransformerImpl with appropriate parameters instead.
This module is kept for backward compatibility and will be removed in a future version.
"""

from __future__ import annotations

from typing import Any
import warnings

from bioetl.domain.transform.contracts import (
    NormalizationConfigProviderProtocol,
)
from bioetl.infrastructure.transform.impl.default_normalization_transformer_impl import (  # noqa: E501
    DefaultNormalizationTransformerImpl,
)


class ChemblNormalizationService(DefaultNormalizationTransformerImpl):
    """Normalization service for ChEMBL records.

    DEPRECATED: Use DefaultNormalizationTransformerImpl directly.

    This class is preserved for backward compatibility. It configures
    DefaultNormalizationTransformerImpl with empty_value=None and
    serialize_array_in_series=False to match legacy ChEMBL behavior.
    """

    def __init__(self, config: NormalizationConfigProviderProtocol):
        warnings.warn(
            "ChemblNormalizationService is deprecated. "
            "Use DefaultNormalizationTransformerImpl(config, empty_value=None, "
            "serialize_array_in_series=False) instead. Will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            config,
            empty_value=None,
            support_base_model=True,
            serialize_array_in_series=False,
        )


# Deprecated aliases for backward compatibility
_DEPRECATED_ALIASES = {
    "ChemblNormalizationServiceImpl": "ChemblNormalizationService",
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


# Type alias for backward compatibility
NormalizedRecord = dict[str, Any]


__all__ = [
    "ChemblNormalizationService",
    "ChemblNormalizationServiceImpl",
    "NormalizedRecord",
]
