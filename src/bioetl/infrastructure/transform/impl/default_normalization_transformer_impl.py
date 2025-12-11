"""Infrastructure implementation of the normalization service."""

from typing import Any, Callable, cast

import pandas as pd
from pydantic import BaseModel

from bioetl.domain.transform.contracts import (
    NormalizationConfigProviderProtocol,
    NormalizationServiceABC,
)
from bioetl.domain.transform.serializers import serialize_nested
from bioetl.infrastructure.transform.impl import normalize
from bioetl.infrastructure.transform.impl.base_normalizer import (
    BaseNormalizationService,
)


class NormalizationServiceImpl(BaseNormalizationService, NormalizationServiceABC):
    """
    Unified normalization service for all data sources.

    Performs:
    - Serialization of nested structures (list/dict -> str)
    - Scalar type normalization (float->round, str->trim/lower/upper)

    Args:
        config: Normalization configuration provider.
        empty_value: Value for empty/missing data (default: pd.NA).
        support_base_model: Accept pydantic BaseModel in apply_normalize.
        serialize_array_in_series: Serialize arrays in apply_normalize_series.
    """

    def __init__(
        self,
        config: NormalizationConfigProviderProtocol,
        empty_value: Any = pd.NA,
        *,
        support_base_model: bool = True,
        serialize_array_in_series: bool = True,
    ):
        super().__init__(
            config,
            empty_value=empty_value,
            support_base_model=support_base_model,
            serialize_array_in_series=serialize_array_in_series,
        )

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize dataframe according to configured fields."""
        return self.apply_normalize_dataframe(df)

    def normalize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize single record using configured field rules."""
        return self.apply_normalize(record)

    def _get_normalizer_for_field(self, name: str) -> Callable[[Any], Any]:
        """Get the appropriate normalizer function for a field.

        Args:
            name: Field name.

        Returns:
            Normalizer function (custom or default).
        """
        mode = self._resolve_mode(name)
        custom_normalizer = normalize.get_normalizer(name)

        if custom_normalizer:
            return custom_normalizer

        def _default_normalizer(val: Any, m: str = mode) -> Any:
            return normalize.normalize_scalar(val, mode=m)

        return _default_normalizer

    def apply_normalize_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Iterate through configuration fields and apply normalization."""
        for field_cfg in self._iter_fields():
            name = field_cfg["name"]
            dtype = field_cfg.get("data_type")

            if name not in df.columns:
                continue

            base_normalizer = self._get_normalizer_for_field(name)

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
                        f"Error normalizing field '{field_name}': {exc}"
                    ) from exc

            df[name] = df[name].apply(_apply_value)

            if dtype in ("array", "object"):
                df[name] = df[name].astype("string").replace({pd.NA: None})

        return self.ensure_numeric_columns(df)

    def apply_normalize(
        self, raw: pd.Series | dict[str, Any] | BaseModel
    ) -> dict[str, Any]:
        """Normalize a raw record into a dict using configured field rules.

        Args:
            raw: Input data as Series, dict, or pydantic BaseModel.

        Returns:
            Normalized dictionary with all fields processed.
        """
        raw_data: dict[str, Any]
        if self._support_base_model and isinstance(raw, BaseModel):
            raw_data = raw.model_dump()
        elif isinstance(raw, pd.Series):
            raw_data = raw.to_dict()
        elif isinstance(raw, dict):
            raw_data = raw
        else:
            raw_data = cast(dict[str, Any], raw.model_dump())

        normalized: dict[str, Any] = {}

        for field_cfg in self._iter_fields():
            name = field_cfg.get("name")
            if not isinstance(name, str) or name not in raw_data:
                continue

            dtype = field_cfg.get("data_type")
            base_normalizer = self._get_normalizer_for_field(name)

            value = raw_data.get(name)
            normalized[name] = self._normalize_value(
                value,
                dtype,
                base_normalizer,
                name,
                allow_container_normalizer=True,
            )

        for key, value in raw_data.items():
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
        base_normalizer = self._get_normalizer_for_field(name)
        # Get custom normalizer for special array handling
        custom_normalizer = normalize.get_normalizer(name)

        def _normalize_value_from_series(val: Any) -> Any:
            if (
                self._serialize_array_in_series
                and custom_normalizer
                and dtype == "array"
                and isinstance(val, (list, tuple))
            ):
                normalized_value = custom_normalizer(val)
                if normalized_value is None or not normalized_value:
                    return self._empty_value
                serialized = serialize_nested(
                    normalized_value, mode=self._serialization_mode
                )
                return self._empty_value if serialized == "" else serialized
            return self._normalize_value(
                val,
                dtype,
                base_normalizer,
                name,
                allow_container_normalizer=True,
            )

        return cast(pd.Series, series.apply(_normalize_value_from_series))


__all__ = ["NormalizationServiceImpl"]
