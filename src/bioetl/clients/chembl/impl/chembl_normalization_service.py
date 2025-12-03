"""Record-level normalization for ChEMBL payloads."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Callable

import pandas as pd

from bioetl.clients.records.contracts import RecordNormalizationServiceABC
from bioetl.domain.records import NormalizedRecord, RawRecord
from bioetl.domain.transform.impl.serializer import serialize_dict, serialize_list
from bioetl.domain.transform.normalizers.registry import get_normalizer


def _normalize_scalar(value: Any, mode: str = "default") -> Any:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except ValueError:
        pass

    if isinstance(value, float):
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
        return val.lower()
    return value


class ChemblNormalizationServiceImpl(RecordNormalizationServiceABC):
    """Normalize raw ChEMBL records to canonical shape."""

    def __init__(
        self,
        *,
        fields: list[dict[str, Any]],
        case_sensitive_fields: list[str],
        id_fields: list[str],
    ) -> None:
        self._fields = fields
        self._case_sensitive_fields = set(case_sensitive_fields)
        self._id_fields = set(id_fields)

    def normalize(self, record: RawRecord) -> NormalizedRecord:
        normalized: NormalizedRecord = dict(record)

        for field_cfg in self._fields:
            name = field_cfg["name"]
            dtype = field_cfg.get("data_type")
            mode = self._resolve_mode(name)

            custom_normalizer = get_normalizer(name)
            base_normalizer: Callable[[Any], Any] = (
                custom_normalizer if custom_normalizer else lambda val: _normalize_scalar(val, mode)
            )

            value = record.get(name)
            normalized[name] = self._normalize_value(
                value=value, dtype=dtype, normalizer=base_normalizer, field_name=name
            )

        return normalized

    def normalize_many(self, records: Iterable[RawRecord]) -> Iterable[NormalizedRecord]:
        for record in records:
            yield self.normalize(record)

    def _normalize_value(
        self,
        *,
        value: Any,
        dtype: str | None,
        normalizer: Callable[[Any], Any],
        field_name: str,
    ) -> Any:
        if dtype in ("array", "object"):
            if isinstance(value, dict):
                return serialize_dict(value, value_normalizer=normalizer)
            if isinstance(value, (list, tuple)):
                return serialize_list(list(value), value_normalizer=normalizer)
            return None

        if dtype in ("string", "integer", "number", "float", "boolean"):
            try:
                return normalizer(value)
            except ValueError as exc:  # pragma: no cover - defensive
                raise ValueError(
                    f"Normalization error for field '{field_name}': {exc}"
                ) from exc

        return value

    def _resolve_mode(self, field_name: str) -> str:
        if field_name in self._case_sensitive_fields:
            return "sensitive"
        if field_name in self._id_fields or field_name.endswith("_id"):
            return "id"
        if field_name.endswith("_chembl_id") or field_name.startswith("id_"):
            return "id"
        return "default"


__all__ = ["ChemblNormalizationServiceImpl"]
