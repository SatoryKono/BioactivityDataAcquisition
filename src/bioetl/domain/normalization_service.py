"""Domain-level normalization service interfaces."""

from __future__ import annotations

from typing import Any, Protocol, TypedDict, cast

import pandas as pd

from bioetl.domain.record_source import RawRecord
from bioetl.domain.transform.contracts import (
    NormalizationConfigProvider,
    NormalizationServiceABC,
)
from bioetl.domain.transform.impl import normalize as normalize_impl
from bioetl.domain.transform.impl.base_normalizer import BaseNormalizationService
from bioetl.domain.transform.impl.serializer import serialize_dict, serialize_list
from bioetl.domain.transform.normalizers import (
    normalize_array,
    normalize_record,
)


class NormalizedRecord(TypedDict, total=False):
    """Normalized record ready for downstream processing."""

    ...


class NormalizationService(Protocol):
    """Protocol for record normalization."""

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        """Normalize a single raw record."""

    def normalize_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize an entire DataFrame chunk."""

    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize a DataFrame with ChEMBL field rules."""

    def normalize_series(
        self, series: pd.Series, field_cfg: dict[str, Any]
    ) -> pd.Series:
        """Normalize a Series using field configuration."""


class ChemblNormalizationService(
    BaseNormalizationService, NormalizationServiceABC, NormalizationService
):
    """Normalization service for ChEMBL records."""

    def __init__(self, config: NormalizationConfigProvider):
        super().__init__(config)

    def normalize(self, raw: RawRecord | pd.Series) -> NormalizedRecord:
        normalized: dict[str, Any] = {}

        for field_cfg in self._config.fields:
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

    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        normalized_df = df.copy()

        for field_cfg in self._config.fields:
            name = field_cfg.get("name")
            if not name or name not in normalized_df.columns:
                continue

            normalized_df[name] = self.normalize_series(normalized_df[name], field_cfg)

        return self.coerce_numeric_columns(normalized_df)

    def normalize_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        normalized = self.normalize_dataframe(df)
        return self.coerce_numeric_columns(normalized)

    def normalize_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        normalized = self.normalize_dataframe(df)
        return self.coerce_numeric_columns(normalized)

    def normalize_series(
        self, series: pd.Series, field_cfg: dict[str, Any]
    ) -> pd.Series:
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
            if (
                custom_normalizer
                and dtype == "array"
                and isinstance(val, (list, tuple))
            ):
                normalized = custom_normalizer(val)
                if normalized is None or not normalized:
                    return None
                return serialize_list(normalized, value_normalizer=None)
            return self._normalize_value(
                val,
                dtype,
                base_normalizer,
                name,
                allow_container_normalizer=True,
            )

        return cast(pd.Series, series.apply(_normalize_value_from_series))

    def _process_list(
        self,
        value: Any,
        normalizer: Any,
        field_name: str,
        *,
        serialize_with_value_normalizer: bool = True,
    ) -> Any:
        try:
            normalized_list = normalize_array(
                list(value),
                item_normalizer=lambda item: self._normalize_container_item(
                    item, normalizer
                ),
            )
        except ValueError as exc:
            raise ValueError(
                f"Ошибка нормализации списка в поле '{field_name}': {exc}"
            ) from exc

        if not normalized_list:
            return None
        return serialize_list(
            normalized_list,
            value_normalizer=normalizer if serialize_with_value_normalizer else None,
        )

    def _process_dict(self, value: Any, normalizer: Any, field_name: str) -> Any:
        try:
            dict_value = cast(dict[str, Any], value)
            normalized_dict = normalize_record(dict_value, value_normalizer=normalizer)
        except ValueError as exc:
            raise ValueError(
                f"Ошибка нормализации записи в поле '{field_name}': {exc}"
            ) from exc

        if normalized_dict is None:
            return None
        return serialize_dict(dict(normalized_dict))

    def _normalize_container_item(self, item: Any, normalizer: Any) -> Any:
        if isinstance(item, dict):
            normalized_dict = normalize_record(
                cast(dict[str, Any], item), value_normalizer=normalizer
            )
            return normalized_dict if normalized_dict is not None else {}
        return normalizer(item)
