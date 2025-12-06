"""Shared helpers for normalization services."""
from __future__ import annotations

from typing import Any, Callable, cast

import pandas as pd

from bioetl.domain.transform.contracts import NormalizationConfigProvider
from bioetl.domain.transform.impl.serializer import serialize_dict, serialize_list
from bioetl.domain.transform.normalizers import normalize_array, normalize_record


class BaseNormalizationService:
    """Provide reusable normalization helpers for services."""

    def __init__(self, config: NormalizationConfigProvider, empty_value: Any = None):
        self._config = config
        self._empty_value = empty_value

    def _resolve_mode(self, field_name: str) -> str:
        if field_name in self._config.normalization.case_sensitive_fields:
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
        if value is None:
            return self._empty_value

        if not isinstance(value, (list, tuple, dict)):
            try:
                if pd.isna(value):
                    return self._empty_value
            except ValueError:
                pass

        if dtype in ("array", "object"):
            if isinstance(value, (list, tuple, dict)) and allow_container_normalizer:
                handled, direct_result = self._apply_container_normalizer(
                    value,
                    normalizer,
                    field_name,
                    serialize_with_value_normalizer=serialize_with_value_normalizer,
                )
                if handled:
                    return direct_result

            if isinstance(value, (list, tuple)):
                return self._process_list(
                    value,
                    normalizer,
                    field_name,
                    serialize_with_value_normalizer=serialize_with_value_normalizer,
                )

            if isinstance(value, dict):
                return self._process_dict(value, normalizer, field_name)

            normalized = self._apply_normalizer(value, normalizer, field_name)
            if isinstance(normalized, (list, tuple, dict)):
                return self._serialize_container_result(
                    normalized,
                    normalizer,
                    serialize_with_value_normalizer=serialize_with_value_normalizer,
                )
            return normalized

        return self._apply_normalizer(value, normalizer, field_name)

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
            raise ValueError(
                f"Ошибка нормализации поля '{field_name}': {exc}"
            ) from exc

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
                value_normalizer=normalizer if serialize_with_value_normalizer else None,
            )

        if isinstance(result, dict):
            serialized_dict = serialize_dict(cast(dict[str, Any], result))
            return self._empty_value if serialized_dict is pd.NA else serialized_dict

        return str(result)

    def _normalize_container_item(self, item: Any, normalizer: Callable[[Any], Any]) -> Any:
        if isinstance(item, dict):
            normalized_dict = normalize_record(
                cast(dict[str, Any], item), value_normalizer=normalizer
            )
            return normalized_dict if normalized_dict is not None else {}
        return normalizer(item)

    def _is_id_field(self, field_name: str) -> bool:
        if field_name in self._config.normalization.id_fields:
            return True
        if field_name.endswith("_id") or field_name.endswith("_chembl_id"):
            return True
        if field_name.startswith("id_"):
            return True
        return False
