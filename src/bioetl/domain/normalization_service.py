"""Domain-level normalization service interfaces."""
from __future__ import annotations

from typing import Any, Protocol, TypedDict, cast

import pandas as pd

from bioetl.domain.record_source import RawRecord
from bioetl.domain.transform.contracts import NormalizationConfigProvider
from bioetl.domain.transform.impl import normalize as normalize_impl
from bioetl.domain.transform.normalizers import (
    normalize_array,
    normalize_record,
)
from bioetl.domain.transform.impl.serializer import serialize_dict, serialize_list


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


class ChemblNormalizationService(NormalizationService):
    """Normalization service for ChEMBL records."""

    def __init__(self, config: NormalizationConfigProvider):
        self._config = config

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        normalized: dict[str, Any] = {}

        for field_cfg in self._config.fields:
            name = field_cfg.get("name")
            if not name or name not in raw:
                continue

            dtype = field_cfg.get("data_type")
            mode = self._resolve_mode(name)
            custom_normalizer = normalize_impl.get_normalizer(name)

            if custom_normalizer:
                base_normalizer = custom_normalizer
            else:
                def _default_normalizer(val: Any, m=mode) -> Any:
                    return normalize_impl.normalize_scalar(val, mode=m)

                base_normalizer = _default_normalizer

            value = raw.get(name)
            normalized[name] = self._normalize_value(
                value, dtype, base_normalizer, name
            )

        for key, value in raw.items():
            if key not in normalized:
                normalized[key] = value

        return cast(NormalizedRecord, normalized)

    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        normalized_df = df.copy()

        for field_cfg in self._config.fields:
            name = field_cfg.get("name")
            if not name or name not in normalized_df.columns:
                continue

            normalized_df[name] = self.normalize_series(
                normalized_df[name], field_cfg
            )

        return normalized_df

    def normalize_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.normalize_dataframe(df)

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
            def _default_normalizer(val: Any, m=mode) -> Any:
                return normalize_impl.normalize_scalar(val, mode=m)

            base_normalizer = _default_normalizer

        def _normalize_value_from_series(val: Any) -> Any:
            # If custom normalizer exists and dtype is array, apply it to the whole list
            if custom_normalizer and dtype == "array" and isinstance(val, (list, tuple)):
                normalized = custom_normalizer(val)
                if normalized is None or not normalized:
                    return None
                # Don't re-normalize values inside dicts - they're already normalized
                # by the custom normalizer (e.g., normalize_target_components)
                # Serialize the normalized list without additional normalization
                return serialize_list(normalized, value_normalizer=None)
            return self._normalize_value(val, dtype, base_normalizer, name)

        return series.apply(_normalize_value_from_series)

    def _resolve_mode(self, field_name: str) -> str:
        if field_name in self._config.normalization.case_sensitive_fields:
            return "sensitive"
        if self._is_id_field(field_name):
            return "id"
        return "default"

    def _is_id_field(self, field_name: str) -> bool:
        if field_name in self._config.normalization.id_fields:
            return True
        if field_name.endswith("_id") or field_name.endswith("_chembl_id"):
            return True
        if field_name.startswith("id_"):
            return True
        return False

    def _normalize_value(
        self,
        value: Any,
        dtype: str | None,
        normalizer: Any,
        field_name: str,
    ) -> Any:
        if value is None:
            return None

        if isinstance(value, (list, tuple, dict)):
            pd_na = False
        else:
            try:
                pd_na = pd.isna(value)
            except ValueError:
                pd_na = False

        if pd_na:
            return None

        if dtype in ("array", "object"):
            if isinstance(value, (list, tuple)):
                return self._process_list(value, normalizer, field_name)
            if isinstance(value, dict):
                return self._process_dict(value, normalizer, field_name)

        if dtype in ("string", "integer", "number", "float", "boolean"):
            return self._apply_normalizer(value, normalizer, field_name)

        return self._apply_normalizer(value, normalizer, field_name)

    def _apply_normalizer(self, value: Any, normalizer: Any, field_name: str) -> Any:
        try:
            return normalizer(value)
        except ValueError as exc:
            raise ValueError(
                f"Ошибка нормализации поля '{field_name}': {exc}"
            ) from exc

    def _process_list(self, value: Any, normalizer: Any, field_name: str) -> Any:
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
        # normalized_list contains already normalized dicts/items
        # serialize_list will serialize them, and for dicts it will use value_normalizer
        # to normalize scalar values inside dicts
        return serialize_list(normalized_list, value_normalizer=normalizer)

    def _process_dict(self, value: Any, normalizer: Any, field_name: str) -> Any:
        try:
            dict_value = cast(dict[str, Any], value)
            normalized_dict = normalize_record(
                dict_value, value_normalizer=normalizer
            )
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
                cast(dict[str, Any], item),
                value_normalizer=normalizer,
            )
            # normalize_record returns None for empty dicts, but we need the dict for serialization
            # Return empty dict instead of None to preserve structure
            return normalized_dict if normalized_dict is not None else {}
        return normalizer(item)
