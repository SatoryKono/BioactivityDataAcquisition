"""Доменный фасад для хеширования и служебных колонок."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Iterable

import pandas as pd

from bioetl.domain.transform.contracts import HasherABC, HashServiceABC


def _normalize_unicode(text: str) -> str:
    """Нормализует строку в форму NFC."""

    return unicodedata.normalize("NFC", text)


def _format_float(value: float | Decimal) -> str:
    """Форматирует число с плавающей точкой по спецификации %.15g."""

    val = float(value)

    if val in (float("inf"), float("-inf")) or val != val:
        raise ValueError(f"Invalid float value for hashing: {value}")

    return "%.15g" % val


def _serialize_number(value: int | float | Decimal) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return _format_float(value)


def _serialize_string(text: str) -> str:
    norm_str = _normalize_unicode(text)
    return json.dumps(norm_str, ensure_ascii=False)


def _serialize_sequence(items: Iterable[Any]) -> str:
    serialized_items = [_serialize_canonical(item) for item in items]
    return "[" + ",".join(serialized_items) + "]"


def _serialize_mapping(obj: dict[str, Any]) -> str:
    sorted_keys = sorted(obj.keys())
    items = []
    for key in sorted_keys:
        if not isinstance(key, str):
            raise TypeError(f"Dict keys must be strings, got {type(key)}")
        key_str = json.dumps(_normalize_unicode(key), ensure_ascii=False)
        val_str = _serialize_canonical(obj[key])
        items.append(f"{key_str}:{val_str}")
    return "{" + ",".join(items) + "}"


def _serialize_canonical(obj: Any) -> str:
    """Рекурсивно сериализует объект в каноническую JSON-строку."""

    if obj is None:
        return "null"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if isinstance(obj, (int, float, Decimal)):
        return _serialize_number(obj)
    if isinstance(obj, str):
        return _serialize_string(obj)
    if isinstance(obj, (list, tuple)):
        return _serialize_sequence(obj)
    if isinstance(obj, dict):
        return _serialize_mapping(obj)

    raise TypeError(f"Type {type(obj)} not supported for canonical serialization")


def _blake2b_hash_hex(data_bytes: bytes, digest_size: int = 32) -> str:
    """Вычисляет BLAKE2b хеш в шестнадцатеричном представлении."""

    return hashlib.blake2b(data_bytes, digest_size=digest_size).hexdigest()


class _DefaultHasher(HasherABC):
    """Доменная реализация HasherABC с канонической сериализацией."""

    @property
    def algorithm(self) -> str:
        return "blake2b_256"

    def hash_row(self, row: pd.Series) -> str:
        record = row.to_dict()
        serialized = _serialize_canonical(record)
        return _blake2b_hash_hex(serialized.encode("utf-8"))

    def hash_columns(self, df: pd.DataFrame, columns: list[str]) -> pd.Series:
        if not columns:
            return pd.Series([None] * len(df), index=df.index, dtype=object)

        def _hash_vals(row: pd.Series) -> str | None:
            values = [row.get(col) for col in columns]
            serialized = _serialize_canonical(values)
            return _blake2b_hash_hex(serialized.encode("utf-8"))

        return df.apply(_hash_vals, axis=1)


class HashService(HashServiceABC):
    """Фасад для детерминированного хеширования и служебных колонок."""

    def __init__(
        self,
        *,
        hasher: HasherABC | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._hasher = hasher or _DefaultHasher()
        self._index_counter = 0
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self._extracted_at: str | None = None

    def add_hash_columns(
        self, df: pd.DataFrame, business_key_cols: list[str] | None = None
    ) -> pd.DataFrame:
        df = df.copy()

        if business_key_cols:
            cols_to_hash = [c for c in business_key_cols if c in df.columns]
            if cols_to_hash:
                df["hash_business_key"] = self._hasher.hash_columns(df, cols_to_hash)
            else:
                df["hash_business_key"] = None
        else:
            df["hash_business_key"] = None

        df["hash_row"] = df.apply(self._hasher.hash_row, axis=1)
        return df

    def add_index_column(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        start_index = self._index_counter
        end_index = start_index + len(df)
        df["index"] = list(range(start_index, end_index))
        self._index_counter = end_index
        return df

    def add_database_version_column(
        self, df: pd.DataFrame, database_version: str
    ) -> pd.DataFrame:
        df = df.copy()
        df["database_version"] = str(database_version)
        return df

    def add_fulldate_column(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if self._extracted_at is None:
            self._extracted_at = self._now_provider().isoformat()
        df["extracted_at"] = self._extracted_at
        return df

    def reset_state(self) -> None:
        self._index_counter = 0
        self._extracted_at = None


__all__ = ["HashService"]
