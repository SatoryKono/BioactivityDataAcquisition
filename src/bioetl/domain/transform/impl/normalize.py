"""
Normalization implementation for domain entities.
"""
from typing import Any, Callable, cast

import pandas as pd

from bioetl.domain.transform.contracts import (
    NormalizationConfigProvider,
    NormalizationServiceABC,
)
from bioetl.domain.transform.normalizers import (
    normalize_array,
    normalize_pcid,
    normalize_pmid,
    normalize_record,
    normalize_uniprot,
)
from bioetl.domain.transform.normalizers.registry import get_normalizer
from bioetl.domain.transform.impl.serializer import (
    serialize_dict,
    serialize_list,
)


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

    # Safety check for lists/arrays to avoid "truth value ... ambiguous"
    if isinstance(value, (list, tuple, dict)):
        # Scalar normalizer should not receive collections.
        if not value:
            return None
        raise ValueError(f"Expected scalar, got {type(value).__name__}")

    try:
        if pd.isna(value):
            return None
    except ValueError:
        pass

    if isinstance(value, float):
        # User requested: "double (3 знака после запятой)"
        return round(value, 3)

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        val = value.strip()
        if not val:
            return None

        if mode == "id":
            return val.upper()
        if mode == "sensitive":
            return val
        return val.lower()  # default

    return value


class NormalizationService(NormalizationServiceABC):
    """
    Сервис нормализации данных.
    Выполняет:
    - Сериализацию вложенных структур (list/dict -> str)
    - Нормализацию скалярных типов (float->round, str->trim/lower/upper)
    """

    def __init__(self, config: NormalizationConfigProvider):
        self._config = config

    def is_case_sensitive(self, field_name: str) -> bool:
        return field_name in self._config.normalization.case_sensitive_fields

    def is_id_field(self, field_name: str) -> bool:
        if field_name in self._config.normalization.id_fields:
            return True
        if field_name.endswith("_id") or field_name.endswith("_chembl_id"):
            return True
        if field_name.startswith("id_"):
            return True
        return False

    def normalize_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Проходит по полям конфигурации и применяет нормализацию.
        """
        for field_cfg in self._config.fields:
            name = field_cfg["name"]
            dtype = field_cfg.get("data_type")

            if name not in df.columns:
                continue

            # Determine normalization mode
            mode = "default"
            if self.is_case_sensitive(name):
                mode = "sensitive"
            elif self.is_id_field(name):
                mode = "id"

            # Resolve normalizer
            custom_normalizer = get_normalizer(name)

            if custom_normalizer:
                base_normalizer: Callable[[Any], Any] = custom_normalizer
            else:
                # Create default scalar normalizer
                def _default_normalizer(val: Any, m=mode) -> Any:
                    return normalize_scalar(val, mode=m)

                base_normalizer = _default_normalizer

            # Define wrapper to capture base_normalizer
            def _apply_value(
                val: Any,
                norm=base_normalizer,
                field_name=name
            ) -> Any:
                try:
                    return norm(val)
                except ValueError as exc:
                    raise ValueError(
                        f"Ошибка нормализации поля '{field_name}': {exc}"
                    ) from exc

            if dtype in ("array", "object"):
                self._normalize_nested(df, name, base_normalizer)
            elif dtype in ("string", "integer", "number", "float", "boolean"):
                # For scalars, apply directly
                df[name] = df[name].apply(_apply_value)

        return df

    def _normalize_nested(
        self,
        df: pd.DataFrame,
        name: str,
        base_normalizer: Callable[[Any], Any]
    ) -> None:
        """Helper to handle nested field normalization."""
        def _serialize_wrapper(
            val: Any,
            norm=base_normalizer,
            field_name=name
        ) -> Any:
            try:
                if val is None:
                    return pd.NA
                if not isinstance(val, (list, dict, tuple)) and pd.isna(val):
                    return pd.NA
            except ValueError:
                pass

            # Try applying normalizer to the container first.
            if isinstance(val, (list, dict, tuple)):
                try:
                    res = norm(val)
                    # Normalizer worked, use result.
                    if res is not None and res is not pd.NA:
                        if isinstance(res, (list, tuple)):
                            return serialize_list(list(res))
                        if isinstance(res, dict):
                            return serialize_dict(res)
                        return str(res)
                except (ValueError, TypeError):
                    # Proceed to element-wise processing.
                    pass

            if isinstance(val, (list, tuple)):
                return self._process_list(val, norm, field_name)

            if isinstance(val, dict):
                return self._process_dict(val, norm, field_name)

            # Fallback for unexpected scalar in nested field
            try:
                res = norm(val)
            except ValueError as exc:
                raise ValueError(
                    f"Ошибка нормализации поля '{field_name}': {exc}"
                ) from exc
            return str(res) if res is not pd.NA and res is not None else pd.NA

        df[name] = df[name].apply(_serialize_wrapper)
        df[name] = df[name].astype("string").replace({pd.NA: None})

    def _process_list(self, val: Any, norm: Callable, field_name: str) -> Any:
        """Process list values."""
        try:
            def _smart_normalizer(item: Any) -> Any:
                if isinstance(item, dict):
                    return normalize_record(item, value_normalizer=norm)
                return norm(item)

            normalized_list = normalize_array(
                list(val), item_normalizer=_smart_normalizer
            )
        except ValueError as exc:
            raise ValueError(
                f"Ошибка нормализации списка в поле '{field_name}': {exc}"
            ) from exc
        if normalized_list is None:
            return pd.NA
        return serialize_list(normalized_list)

    def _process_dict(self, val: Any, norm: Callable, field_name: str) -> Any:
        """Process dict values."""
        try:
            dict_val = cast(dict[str, Any], val)
            normalized_dict = normalize_record(dict_val, value_normalizer=norm)
        except ValueError as exc:
            raise ValueError(
                f"Ошибка нормализации записи в поле '{field_name}': {exc}"
            ) from exc
        if normalized_dict is None:
            return pd.NA
        return serialize_dict(dict(normalized_dict))
