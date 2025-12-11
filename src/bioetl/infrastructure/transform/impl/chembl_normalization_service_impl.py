"""ChEMBL-specific normalization service implementation.

DEPRECATED: Use NormalizationServiceImpl with appropriate parameters instead.
This module is kept for backward compatibility and will be removed in a future version.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import warnings

import pandas as pd

from bioetl.domain.transform.contracts import (
    NormalizationConfigProviderProtocol,
    NormalizationServiceABC,
)

if TYPE_CHECKING:
    pass


class ChemblNormalizationService(NormalizationServiceABC):
    """ChEMBL-specific normalization delegating to base service.

    DEPRECATED: Use NormalizationServiceImpl directly with
    empty_value=None, serialize_array_in_series=False.

    This class uses composition to delegate normalization to the base service
    while allowing ChEMBL-specific preprocessing if needed.

    Args:
        config: Normalization configuration provider.
        base: Optional base normalization service. If None, creates
            NormalizationServiceImpl with ChEMBL-specific defaults.
    """

    def __init__(
        self,
        config: NormalizationConfigProviderProtocol,
        base: NormalizationServiceABC | None = None,
    ):
        warnings.warn(
            "ChemblNormalizationService is deprecated. "
            "Use NormalizationServiceImpl(config, empty_value=None, "
            "serialize_array_in_series=False) instead. Will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        if base is not None:
            self._base = base
        else:
            # Lazy import to avoid circular dependency
            from bioetl.infrastructure.transform.impl.default_normalization_transformer_impl import (
                NormalizationServiceImpl,
            )

            self._base = NormalizationServiceImpl(
                config,
                empty_value=None,
                support_base_model=True,
                serialize_array_in_series=False,
            )

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize dataframe according to configured fields."""
        return self._base.normalize(df)

    def normalize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize single record using configured field rules."""
        return self._base.normalize_record(record)

    def ensure_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Coerce numeric columns to appropriate types."""
        return self._base.ensure_numeric_columns(df)

    # Delegate additional methods for backward compatibility
    def apply_normalize(self, raw: pd.Series | dict[str, Any]) -> dict[str, Any]:
        """Normalize a raw record into a dict using configured field rules."""
        return self._base.apply_normalize(raw)

    def apply_normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize configured columns in the provided dataframe."""
        return self._base.apply_normalize_dataframe(df)

    def apply_normalize_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize a batch dataframe and coerce numeric columns."""
        return self._base.apply_normalize_batch(df)

    def apply_normalize_series(
        self, series: pd.Series, field_cfg: dict[str, Any]
    ) -> pd.Series:
        """Normalize a single series according to field configuration."""
        return self._base.apply_normalize_series(series, field_cfg)


# Type alias for backward compatibility
NormalizedRecord = dict[str, Any]


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


__all__ = [
    "ChemblNormalizationService",
    "ChemblNormalizationServiceImpl",  # noqa: F822
    "NormalizedRecord",
]
