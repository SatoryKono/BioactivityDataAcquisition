import hashlib
import json
import unicodedata
from decimal import Decimal
from typing import Any, Iterable

import pandas as pd

from bioetl.domain.transform.contracts import HasherABC


def normalize_unicode(text: str) -> str:
    """
    Нормализует строку в форму NFC.
    """
    return unicodedata.normalize("NFC", text)


def format_float(value: float | Decimal) -> str:
    """
    Форматирует число с плавающей точкой по спецификации: %.15g.
    """
    # Decimal is treated as float for canonicalization purposes per spec
    # to avoid discrepancies between float and Decimal types in source
    val = float(value)

    if val == float("inf") or val == float("-inf") or val != val:  # NaN
        raise ValueError(f"Invalid float value for hashing: {value}")

    # %.15g formatting
    return "%.15g" % val


def _serialize_canonical(obj: Any) -> str:
    """
    Рекурсивная функция сериализации в строку.
    """
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


def _serialize_number(value: int | float | Decimal) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return format_float(value)


def _serialize_string(text: str) -> str:
    norm_str = normalize_unicode(text)
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
        key_str = json.dumps(normalize_unicode(key), ensure_ascii=False)
        val_str = _serialize_canonical(obj[key])
        items.append(f"{key_str}:{val_str}")
    return "{" + ",".join(items) + "}"


def blake2b_hash_hex(data_bytes: bytes, digest_size: int = 32) -> str:
    """
    Вычисляет BLAKE2b хеш.
    """
    return hashlib.blake2b(data_bytes, digest_size=digest_size).hexdigest()


class HasherImpl(HasherABC):
    """
    Реализация хеширования (BLAKE2b-256) с канонической JSON сериализацией.
    """

    @property
    def algorithm(self) -> str:
        return "blake2b_256"

    def hash_row(self, row: pd.Series) -> str:
        """
        Хеширует строку Series как полный объект (hash_row).
        """
        # Convert to dict
        record = row.to_dict()
        # Serialize canonical
        serialized = _serialize_canonical(record)
        # Hash
        return blake2b_hash_hex(serialized.encode("utf-8"))

    def hash_columns(self, df: pd.DataFrame, columns: list[str]) -> pd.Series:
        """
        Хеширует выбранные колонки DataFrame (как список значений в заданном порядке).
        Используется для hash_business_key.
        Если columns пуст -> возвращает None (в Series).
        """
        if not columns:
            # Return series of None
            return pd.Series([None] * len(df), index=df.index, dtype=object)

        def _hash_vals(row: pd.Series) -> str | None:
            values = []
            for col in columns:
                val = row.get(col)
                # Columns exist in DF; None/NaN handled by serializer.
                values.append(val)

            serialized = _serialize_canonical(values)
            return blake2b_hash_hex(serialized.encode("utf-8"))

        return df.apply(_hash_vals, axis=1)
