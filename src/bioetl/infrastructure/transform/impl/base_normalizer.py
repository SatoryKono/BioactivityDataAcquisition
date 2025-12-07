"""Shared helpers for normalization services."""

from __future__ import annotations

from typing import Any, Callable, cast

import pandas as pd
from pandas._typing import DtypeArg

from bioetl.domain.transform.contracts import (
    BaseNormalizationServiceABC,
    NormalizationConfigProviderProtocol,
)
from bioetl.domain.transform.normalizers import normalize_array, normalize_record
from bioetl.infrastructure.transform.impl.serializer import (
    serialize_dict,
    serialize_list,
)


class BaseNormalizationServiceImpl(BaseNormalizationServiceABC):
    """Provide reusable normalization helpers for normalization services."""

    _NUMERIC_DTYPES: dict[str, DtypeArg] = {
        "number": "Float64",
        "integer": "Int64",
    }

    def __init__(
        self, config: NormalizationConfigProviderProtocol, empty_value: Any = None
    ):
        self._config = config
        self._empty_value = empty_value

    def _iter_fields(self) -> list[dict[str, Any]]:
        """Return field configs from provider, supporting legacy shapes."""

        if hasattr(self._config, "get_fields"):
            return cast(list[dict[str, Any]], self._config.get_fields())
        if hasattr(self._config, "fields"):
            return list(cast(list[dict[str, Any]], self._config.fields))
        raise AttributeError("Normalization config must expose fields")

    def _get_normalization_config(self) -> Any:
        """Return normalization settings from provider or attribute."""

        if hasattr(self._config, "get_normalization"):
            return self._config.get_normalization()
        if hasattr(self._config, "normalization"):
            return self._config.normalization
        raise AttributeError("Normalization config must expose normalization")

    def ensure_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cast configured numeric columns to nullable pandas dtypes."""

        for field_cfg in self._iter_fields():
            name = field_cfg.get("name")
            dtype = field_cfg.get("data_type")

            if not isinstance(name, str) or not isinstance(dtype, str):
                continue

            target_dtype = self._NUMERIC_DTYPES.get(dtype)
            if target_dtype is None or name not in df.columns:
                continue

            coerced = pd.to_numeric(df[name], errors="coerce")
            df[name] = pd.Series(coerced, dtype=target_dtype)  # type: ignore[arg-type]

        return df

    def _resolve_mode(self, field_name: str) -> str:
        normalization_config = self._get_normalization_config()

        if field_name in normalization_config.case_sensitive_fields:
            return "sensitive"
        if self._is_id_field(field_name):
            return "id"
        return "default"

    def _normalize_value(
        self,
        value: Any,
        dtype: str | None,
        normalizer: Callable[[Any], Any],
        field_name: str,
        *,
        allow_container_normalizer: bool = False,
        serialize_with_value_normalizer: bool = True,
    ) -> Any:
        if self._is_empty_value(value):
            return self._empty_value
        return self._dispatch_normalization(
            value,
            dtype,
            normalizer,
            field_name,
            allow_container_normalizer=allow_container_normalizer,
            serialize_with_value_normalizer=serialize_with_value_normalizer,
        )

    @staticmethod
    def _is_container_dtype(dtype: str | None) -> bool:
        return dtype in ("array", "object")

    def _dispatch_normalization(
        self,
        value: Any,
        dtype: str | None,
        normalizer: Callable[[Any], Any],
        field_name: str,
        *,
        allow_container_normalizer: bool,
        serialize_with_value_normalizer: bool,
    ) -> Any:
        if self._is_container_dtype(dtype):
            return self._normalize_container_value(
                value,
                normalizer,
                field_name,
                dtype=dtype,
                allow_container_normalizer=allow_container_normalizer,
                serialize_with_value_normalizer=serialize_with_value_normalizer,
            )

        return self._normalize_scalar_value(value, normalizer, field_name)

    def _normalize_scalar_value(
        self, value: Any, normalizer: Callable[[Any], Any], field_name: str
    ) -> Any:
        return self._apply_normalizer(value, normalizer, field_name)

    def _normalize_container_value(
        self,
        value: Any,
        normalizer: Callable[[Any], Any],
        field_name: str,
        *,
        dtype: str | None,
        allow_container_normalizer: bool,
        serialize_with_value_normalizer: bool,
    ) -> Any:
        container_value = value
        if dtype == "array" and not isinstance(value, (list, tuple)):
            try:
                container_value = normalize_array(
                    value, item_normalizer=lambda item: item
                )
            except ValueError as exc:
                raise ValueError(
                    f"Ошибка нормализации списка в поле '{field_name}': {exc}"
                ) from exc
            if not container_value:
                return self._empty_value

        if isinstance(container_value, (list, tuple, dict)) and allow_container_normalizer:
            handled, direct_result = self._apply_container_normalizer(
                container_value,
                normalizer,
                field_name,
                serialize_with_value_normalizer=serialize_with_value_normalizer,
            )
            if handled:
                return direct_result

        if isinstance(container_value, (list, tuple)):
            return self._process_list(
                container_value,
                normalizer,
                field_name,
                serialize_with_value_normalizer=serialize_with_value_normalizer,
            )

        if isinstance(container_value, dict):
            return self._process_dict(container_value, normalizer, field_name)

        normalized = self._apply_normalizer(container_value, normalizer, field_name)
        if isinstance(normalized, (list, tuple, dict)):
            return self._serialize_container_result(
                normalized,
                normalizer,
                serialize_with_value_normalizer=serialize_with_value_normalizer,
            )
        return normalized

    def _is_empty_value(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, (list, tuple, dict)):
            return False
        try:
            return bool(pd.isna(value))
        except ValueError:
            return False

    def _process_list(
        self,
        value: Any,
        normalizer: Callable[[Any], Any],
        field_name: str,
        *,
        serialize_with_value_normalizer: bool = True,
    ) -> Any:
        try:
            normalized_list = normalize_array(
                value,
                item_normalizer=lambda item: self._normalize_container_item(
                    item, normalizer
                ),
            )
        except ValueError as exc:
            raise ValueError(
                f"Ошибка нормализации списка в поле '{field_name}': {exc}"
            ) from exc

        if not normalized_list:
            return self._empty_value

        return serialize_list(
            normalized_list,
            value_normalizer=normalizer if serialize_with_value_normalizer else None,
        )

    def _process_dict(
        self, value: Any, normalizer: Callable[[Any], Any], field_name: str
    ) -> Any:
        try:
            dict_value = cast(dict[str, Any], value)
            normalized_dict = normalize_record(dict_value, value_normalizer=normalizer)
        except ValueError as exc:
            raise ValueError(
                f"Ошибка нормализации записи в поле '{field_name}': {exc}"
            ) from exc

        if normalized_dict is None:
            return self._empty_value

        return serialize_dict(dict(normalized_dict))

    def _apply_normalizer(
        self, value: Any, normalizer: Callable[[Any], Any], field_name: str
    ) -> Any:
        try:
            return normalizer(value)
        except ValueError as exc:
            raise ValueError(f"Ошибка нормализации поля '{field_name}': {exc}") from exc

    def _apply_container_normalizer(
        self,
        value: Any,
        normalizer: Callable[[Any], Any],
        field_name: str,
        *,
        serialize_with_value_normalizer: bool = True,
    ) -> tuple[bool, Any]:
        try:
            result = normalizer(value)
        except (ValueError, TypeError):
            return False, None

        serialized = self._serialize_container_result(
            result,
            normalizer,
            serialize_with_value_normalizer=serialize_with_value_normalizer,
        )
        return True, serialized

    def _serialize_container_result(
        self,
        result: Any,
        normalizer: Callable[[Any], Any],
        *,
        serialize_with_value_normalizer: bool = True,
    ) -> Any:
        if result is None or result is pd.NA:
            return self._empty_value

        if isinstance(result, (list, tuple)):
            if not result:
                return self._empty_value
            return serialize_list(
                list(result),
                value_normalizer=(
                    normalizer if serialize_with_value_normalizer else None
                ),
            )

        if isinstance(result, dict):
            serialized_dict = serialize_dict(cast(dict[str, Any], result))
            return self._empty_value if serialized_dict is pd.NA else serialized_dict

        return str(result)

    def _normalize_container_item(
        self, item: Any, normalizer: Callable[[Any], Any]
    ) -> Any:
        if isinstance(item, dict):
            normalized_dict = normalize_record(
                cast(dict[str, Any], item), value_normalizer=normalizer
            )
            return normalized_dict if normalized_dict is not None else {}
        return normalizer(item)

    def _is_id_field(self, field_name: str) -> bool:
        normalization_config = self._get_normalization_config()
        if field_name in normalization_config.id_fields:
            return True
        if field_name.endswith("_id") or field_name.endswith("_chembl_id"):
            return True
        if field_name.startswith("id_"):
            return True
        return False


__all__ = ["BaseNormalizationServiceImpl"]
