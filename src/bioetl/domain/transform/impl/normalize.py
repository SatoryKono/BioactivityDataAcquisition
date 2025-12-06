"""
Normalization implementation for domain entities.
"""

from typing import Any, Callable, cast

import pandas as pd

from bioetl.domain.transform.contracts import (
    NormalizationConfigProvider,
    NormalizationServiceABC,
)
from bioetl.domain.transform.impl.base_normalizer import BaseNormalizationService
from bioetl.domain.transform.impl.serializer import (
    serialize_dict,
    serialize_list,
)
from bioetl.domain.transform.normalizers import (
    normalize_array,
    normalize_pcid,
    normalize_pmid,
    normalize_record,
    normalize_uniprot,
)
from bioetl.domain.transform.normalizers.registry import get_normalizer
from bioetl.domain.record_source import RawRecord

# Aliases for backward compatibility or convenience
normalize_pubmed_id = normalize_pmid
normalize_pubchem_cid = normalize_pcid
normalize_uniprot_id = normalize_uniprot


def normalize_scalar(value: Any, mode: str = "default") -> Any:
    """
    Нормализует скалярное значение.

    Modes:
    - "default": trim + lower (str), round 3 (float)
    - "id": trim + upper (str)
    - "sensitive": trim only (str)
    """
    if value is None:
        return None

    if isinstance(value, (list, tuple, dict)):
        if not value:
            return None
        raise ValueError(f"Expected scalar, got {type(value).__name__}")

    if _is_missing_value(value):
        return None

    if isinstance(value, float):
        return round(value, 3)

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        return _normalize_string_value(value, mode)

    return value


def _is_missing_value(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except ValueError:
        return False


def _normalize_string_value(value: str, mode: str) -> str | None:
    val = value.strip()
    if not val:
        return None
    if mode == "id":
        return val.upper()
    if mode == "sensitive":
        return val
    return val.lower()


class NormalizationServiceImpl(NormalizationServiceABC, BaseNormalizationService):
    """
    Сервис нормализации данных.
    Выполняет:
    - Сериализацию вложенных структур (list/dict -> str)
    - Нормализацию скалярных типов (float->round, str->trim/lower/upper)
    """

    def __init__(self, config: NormalizationConfigProvider):
        BaseNormalizationService.__init__(self, config, empty_value=pd.NA)

    def normalize(self, raw: RawRecord | pd.Series) -> dict[str, Any]:
        df = pd.DataFrame([raw])
        normalized = self.normalize_dataframe(df)
        return cast(dict[str, Any], normalized.iloc[0].to_dict())

    def normalize_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Проходит по полям конфигурации и применяет нормализацию.
        """
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

        return df

    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.normalize_fields(df)

    def normalize_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.normalize_dataframe(df)

    def normalize_series(
        self, series: pd.Series, field_cfg: dict[str, Any]
    ) -> pd.Series:
        name = cast(str, field_cfg.get("name"))
        dtype = field_cfg.get("data_type")
        mode = self._resolve_mode(name)
        custom_normalizer = get_normalizer(name)

        if custom_normalizer:
            base_normalizer = custom_normalizer
        else:

            def _default_normalizer(val: Any, m=mode) -> Any:
                return normalize_scalar(val, mode=m)

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

        return series.apply(_normalize_value_from_series)

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


# Backward compatibility alias
NormalizationService = NormalizationServiceImpl
