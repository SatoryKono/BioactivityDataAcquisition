"""ChEMBL-specific normalization service implementation."""

from __future__ import annotations

from typing import Any, TypedDict, cast

import pandas as pd

from bioetl.domain.record_source import RawRecord
from bioetl.domain.transform.contracts import (
    NormalizationConfigProviderProtocol,
    NormalizationServiceABC,
)
from bioetl.infrastructure.transform.impl import normalize as normalize_impl
from bioetl.infrastructure.transform.impl.base_normalizer import (
    BaseNormalizationServiceImpl,
)


class NormalizedRecord(TypedDict, total=False):
    """Normalized record ready for downstream processing."""

    ...


class ChemblNormalizationServiceImpl(
    BaseNormalizationServiceImpl, NormalizationServiceABC
):
    """Normalization service for ChEMBL records."""

    def __init__(self, config: NormalizationConfigProviderProtocol):
        super().__init__(config)

    def apply_normalize(self, raw: RawRecord | pd.Series) -> NormalizedRecord:
        """Normalize single raw ChEMBL record into flat dict."""
        normalized: dict[str, Any] = {}

        for field_cfg in self._iter_fields():
            name = field_cfg.get("name")
            if not isinstance(name, str) or name not in raw:
                continue

            dtype = field_cfg.get("data_type")
            mode = self._resolve_mode(name)
            custom_normalizer = normalize_impl.get_normalizer(name)

            if custom_normalizer:
                base_normalizer = custom_normalizer
            else:

                def _default_normalizer(val: Any, m: str = mode) -> Any:
                    return normalize_impl.normalize_scalar(val, mode=m)

                base_normalizer = _default_normalizer

            value = raw.get(name)
            normalized[name] = self._normalize_value(
                value,
                dtype,
                base_normalizer,
                name,
                allow_container_normalizer=True,
            )

        for key, value in raw.items():
            key_str = cast(str, key)
            if key_str not in normalized:
                normalized[key_str] = value

        return cast(NormalizedRecord, normalized)

    def apply_normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize configured fields across dataframe columns."""
        normalized_df = df.copy()

        for field_cfg in self._iter_fields():
            name = field_cfg.get("name")
            if not name or name not in normalized_df.columns:
                continue

            normalized_df[name] = self.apply_normalize_series(
                normalized_df[name], field_cfg
            )

        return self.ensure_numeric_columns(normalized_df)

    def apply_normalize_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize an entire batch DataFrame."""
        normalized = self.apply_normalize_dataframe(df)
        return self.ensure_numeric_columns(normalized)

    def apply_normalize_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Alias for apply_normalize_dataframe retained for compatibility."""
        normalized = self.apply_normalize_dataframe(df)
        return self.ensure_numeric_columns(normalized)

    def apply_normalize_series(
        self, series: pd.Series, field_cfg: dict[str, Any]
    ) -> pd.Series:
        """Normalize a single column according to field configuration."""
        name = cast(str, field_cfg.get("name"))
        dtype = field_cfg.get("data_type")
        mode = self._resolve_mode(name)
        custom_normalizer = normalize_impl.get_normalizer(name)

        if custom_normalizer:
            base_normalizer = custom_normalizer
        else:

            def _default_normalizer(val: Any, m: str = mode) -> Any:
                return normalize_impl.normalize_scalar(val, mode=m)

            base_normalizer = _default_normalizer

        def _normalize_value_from_series(val: Any) -> Any:
            return self._normalize_value(
                val,
                dtype,
                base_normalizer,
                name,
                allow_container_normalizer=True,
            )

        return cast(pd.Series, series.apply(_normalize_value_from_series))
