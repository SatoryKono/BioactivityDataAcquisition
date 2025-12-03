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
        if isinstance(obj, bool):  # Python bools are ints
            return "true" if obj else "false"
        if isinstance(obj, int) and not isinstance(obj, bool):
            return str(obj)
        # Float/Decimal
        return format_float(obj)

    if isinstance(obj, str):
        # Normalize NFC
        norm_str = normalize_unicode(obj)
        # JSON escape. json.dumps adds quotes and escapes.
        # ensure_ascii=False allows non-ascii chars.
        return json.dumps(norm_str, ensure_ascii=False)

    if isinstance(obj, (list, tuple)):
        # Preserve order
        items = [_serialize_canonical(item) for item in obj]
        return "[" + ",".join(items) + "]"

    if isinstance(obj, dict):
        # Sort keys
        sorted_keys = sorted(obj.keys())
        items = []
        for k in sorted_keys:
            # Keys must be strings for JSON
            if not isinstance(k, str):
                raise TypeError(f"Dict keys must be strings, got {type(k)}")

            # Serialize key (quoted) and value
            # key is string, so standard json dump is fine (with NFC)
            key_str = json.dumps(normalize_unicode(k), ensure_ascii=False)
            val_str = _serialize_canonical(obj[k])
            items.append(f"{key_str}:{val_str}")

        return "{" + ",".join(items) + "}"

    raise TypeError(f"Type {type(obj)} not supported for canonical serialization")


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
                # If any component is missing (though row.get usually returns None or NaN if missing in index?)
                # In DataFrame apply(axis=1), row has all columns.
                # But we should check if the value itself effectively means "missing" if that's the logic.
                # The old logic: if field not in record -> return None.
                # Here the column exists in DF, but value might be None/NaN.
                # Standard logic: just take the value (None/NaN handling in serializer).
                # But wait, compute_hash_business_key returned None if key missing.
                # Here we assume columns exist in DF.
                values.append(val)
            
            serialized = _serialize_canonical(values)
            return blake2b_hash_hex(serialized.encode("utf-8"))

        return df.apply(_hash_vals, axis=1)
