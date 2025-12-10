"""ChEMBL-specific normalization service implementation.

DEPRECATED: Use DefaultNormalizationTransformerImpl with appropriate parameters instead.
This module is kept for backward compatibility and will be removed in a future version.
"""

from __future__ import annotations

import warnings
from typing import Any

from bioetl.domain.transform.contracts import (
    NormalizationConfigProviderProtocol,
)
from bioetl.infrastructure.transform.impl.default_normalization_transformer_impl import (
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
            "serialize_array_in_series=False) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            config,
            empty_value=None,
            support_base_model=True,
            serialize_array_in_series=False,
        )


# Deprecated alias for backward compatibility (will be removed in next major version)
ChemblNormalizationServiceImpl = ChemblNormalizationService

# Type alias for backward compatibility
NormalizedRecord = dict[str, Any]


__all__ = [
    "ChemblNormalizationService",
    "ChemblNormalizationServiceImpl",
    "NormalizedRecord",
]
