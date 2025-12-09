"""Infrastructure implementation of the normalization service."""

from typing import Any, Callable, cast

import pandas as pd

from bioetl.domain.transform.contracts import (
    NormalizationConfigProviderProtocol,
    NormalizationServiceABC,
)
from bioetl.infrastructure.transform.impl import normalize
from bioetl.infrastructure.transform.impl.base_normalizer import (
    BaseNormalizationServiceImpl,
)
from bioetl.infrastructure.transform.impl.serializer import serialize_list


class NormalizationServiceImpl(NormalizationServiceABC, BaseNormalizationServiceImpl):
    """
    Сервис нормализации данных.
    Выполняет:
    - Сериализацию вложенных структур (list/dict -> str)
    - Нормализацию скалярных типов (float->round, str->trim/lower/upper)
    """

    def __init__(self, config: NormalizationConfigProviderProtocol):
        BaseNormalizationServiceImpl.__init__(self, config, empty_value=pd.NA)

    def apply_normalize_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Проходит по полям конфигурации и применяет нормализацию."""
        for field_cfg in self._iter_fields():
            name = field_cfg["name"]
            dtype = field_cfg.get("data_type")

            if name not in df.columns:
                continue

            mode = self._resolve_mode(name)
            custom_normalizer = normalize.get_normalizer(name)

            if custom_normalizer:
                base_normalizer: Callable[[Any], Any] = custom_normalizer
            else:

                def _default_normalizer(val: Any, m=mode) -> Any:
                    return normalize.normalize_scalar(val, mode=m)

                base_normalizer = _default_normalizer

            def _apply_value(
                val: Any,
                norm=base_normalizer,
                field_name=name,
                data_type=dtype,
            ) -> Any:
                try:
                    return self._normalize_value(
                        val,
                        data_type,
                        norm,
                        field_name,
                        allow_container_normalizer=True,
                        serialize_with_value_normalizer=False,
                    )
                except ValueError as exc:
                    raise ValueError(
                        f"Ошибка нормализации поля '{field_name}': {exc}"
                    ) from exc

            df[name] = df[name].apply(_apply_value)

            if dtype in ("array", "object"):
                df[name] = df[name].astype("string").replace({pd.NA: None})

        return self.ensure_numeric_columns(df)

    def apply_normalize(self, raw: pd.Series | dict[str, Any]) -> dict[str, Any]:
        """Normalize a raw record into a dict using configured field rules."""
        normalized: dict[str, Any] = {}

        for field_cfg in self._iter_fields():
            name = field_cfg.get("name")
            if not isinstance(name, str) or name not in raw:
                continue

            dtype = field_cfg.get("data_type")
            mode = self._resolve_mode(name)
            custom_normalizer = normalize.get_normalizer(name)

            if custom_normalizer:
                base_normalizer = custom_normalizer
            else:

                def _default_normalizer(val: Any, m: str = mode) -> Any:
                    return normalize.normalize_scalar(val, mode=m)

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

        return normalized

    def apply_normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize configured columns in the provided dataframe."""
        normalized_df = df.copy()

        for field_cfg in self._iter_fields():
            name = field_cfg.get("name")
            if not name or name not in normalized_df.columns:
                continue

            normalized_df[name] = self.apply_normalize_series(
                normalized_df[name], cast(dict[str, Any], field_cfg)
            )

        return self.ensure_numeric_columns(normalized_df)

    def apply_normalize_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize a batch dataframe and coerce numeric columns."""
        normalized = self.apply_normalize_dataframe(df)
        return self.ensure_numeric_columns(normalized)

    def apply_normalize_series(
        self, series: pd.Series, field_cfg: dict[str, Any]
    ) -> pd.Series:
        """Normalize a single series according to field configuration."""
        name = cast(str, field_cfg.get("name"))
        dtype = field_cfg.get("data_type")
        mode = self._resolve_mode(name)
        custom_normalizer = normalize.get_normalizer(name)

        if custom_normalizer:
            base_normalizer = custom_normalizer
        else:

            def _default_normalizer(val: Any, m: str = mode) -> Any:
                return normalize.normalize_scalar(val, mode=m)

            base_normalizer = _default_normalizer

        def _normalize_value_from_series(val: Any) -> Any:
            if (
                custom_normalizer
                and dtype == "array"
                and isinstance(val, (list, tuple))
            ):
                normalized_value = custom_normalizer(val)
                if normalized_value is None or not normalized_value:
                    return pd.NA
                return serialize_list(normalized_value, value_normalizer=None)
            return self._normalize_value(
                val,
                dtype,
                base_normalizer,
                name,
                allow_container_normalizer=True,
            )

        return cast(pd.Series, series.apply(_normalize_value_from_series))


__all__ = ["NormalizationServiceImpl"]
