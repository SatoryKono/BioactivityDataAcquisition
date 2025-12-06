"""Infrastructure implementation of the normalization service."""

from typing import Any, Callable

import pandas as pd

from bioetl.domain.transform.contracts import (
    NormalizationConfigProvider,
    NormalizationServiceABC,
)
from bioetl.domain.transform.impl.base_normalizer import BaseNormalizationService
from bioetl.domain.transform.impl.normalize import normalize_scalar
from bioetl.domain.transform.impl.serializer import serialize_dict, serialize_list
from bioetl.domain.transform.normalizers import normalize_array, normalize_record
from bioetl.domain.transform.normalizers.registry import get_normalizer

_NUMERIC_DTYPES: dict[str, str] = {
    "number": "Float64",
    "integer": "Int64",
}


def _coerce_numeric_columns(
    df: pd.DataFrame,
    fields_cfg: list[dict[str, Any]],
) -> pd.DataFrame:
    for field_cfg in fields_cfg:
        name = field_cfg.get("name")
        dtype = field_cfg.get("data_type")
        target_dtype = _NUMERIC_DTYPES.get(dtype)
        if not name or target_dtype is None or name not in df.columns:
            continue
        df[name] = pd.to_numeric(df[name], errors="coerce").astype(target_dtype)
    return df


class NormalizationServiceImpl(NormalizationServiceABC, BaseNormalizationService):
    """
    Сервис нормализации данных.
    Выполняет:
    - Сериализацию вложенных структур (list/dict -> str)
    - Нормализацию скалярных типов (float->round, str->trim/lower/upper)
    """

    def __init__(self, config: NormalizationConfigProvider):
        BaseNormalizationService.__init__(self, config, empty_value=pd.NA)

    def normalize_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Проходит по полям конфигурации и применяет нормализацию."""
        for field_cfg in self._config.fields:
            name = field_cfg["name"]
            dtype = field_cfg.get("data_type")

            if name not in df.columns:
                continue

            mode = self._resolve_mode(name)
            custom_normalizer = get_normalizer(name)

            if custom_normalizer:
                base_normalizer: Callable[[Any], Any] = custom_normalizer
            else:

                def _default_normalizer(val: Any, m=mode) -> Any:
                    return normalize_scalar(val, mode=m)

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

        return _coerce_numeric_columns(df, self._config.fields)

    def _normalize_container_item(
        self, item: Any, normalizer: Callable[[Any], Any]
    ) -> Any:
        if isinstance(item, dict):
            normalized_dict = normalize_record(item, value_normalizer=normalizer)
            return normalized_dict if normalized_dict is not None else {}
        return normalizer(item)

    def _process_list(
        self,
        val: Any,
        norm: Callable[[Any], Any],
        field_name: str,
        *,
        serialize_with_value_normalizer: bool = False,
    ) -> Any:
        try:

            def _smart_normalizer(item: Any) -> Any:
                return self._normalize_container_item(item, norm)

            normalized_list = normalize_array(
                list(val), item_normalizer=_smart_normalizer
            )
        except ValueError as exc:
            raise ValueError(
                f"Ошибка нормализации списка в поле '{field_name}': {exc}"
            ) from exc
        if not normalized_list:
            return pd.NA
        return serialize_list(
            normalized_list,
            value_normalizer=norm if serialize_with_value_normalizer else None,
        )

    def _process_dict(
        self, val: Any, norm: Callable[[Any], Any], field_name: str
    ) -> Any:
        try:
            normalized_dict = normalize_record(val, value_normalizer=norm)
        except ValueError as exc:
            raise ValueError(
                f"Ошибка нормализации записи в поле '{field_name}': {exc}"
            ) from exc
        if normalized_dict is None:
            return pd.NA
        return serialize_dict(normalized_dict)


__all__ = ["NormalizationServiceImpl"]
