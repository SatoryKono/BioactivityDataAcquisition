from datetime import datetime, timezone
import hashlib
import json
from typing import Callable

import pandas as pd

from bioetl.domain.transform.contracts import HasherABC, HashServiceABC

__all__ = ["HashService", "HashServiceImpl"]


class HashServiceImpl(HashServiceABC):
    """
    Реализация фасада хеш-сервиса.
    """

    def __init__(
        self,
        hasher: HasherABC | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        if hasher is None:
            hasher = _FallbackHasher()

        self._hasher = hasher
        self._index_counter = 0
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self._extracted_at: str | None = None

    def add_hash_columns(
        self, df: pd.DataFrame, business_key_cols: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Добавляет столбцы hash_row и hash_business_key.

        Logic:
        1. Calculate hash_business_key (if configured) based on specific columns.
        2. Add hash_business_key to DataFrame.
        3. Calculate hash_row based on ALL columns as canonical JSON.
        """
        df = df.copy()

        # 1. hash_business_key
        if business_key_cols:
            # Ensure columns exist before hashing
            cols_to_hash = [c for c in business_key_cols if c in df.columns]
            if cols_to_hash:
                # Uses hash_columns -> list hashing (canonical list)
                df["hash_business_key"] = self._hasher.hash_columns(df, cols_to_hash)
            else:
                df["hash_business_key"] = None
        else:
            df["hash_business_key"] = None

        # 2. hash_row
        # Uses hash_row -> dict hashing (canonical object) of the full row
        # Note: This includes 'hash_business_key' which was just added/set.
        df["hash_row"] = df.apply(self._hasher.hash_row, axis=1)

        return df

    def add_index_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавляет колонку 'index' с порядковым номером строки (int), начиная с 0.
        Возвращает копию df.
        """
        df = df.copy()
        start_index = self._index_counter
        end_index = start_index + len(df)
        df["index"] = list(range(start_index, end_index))
        self._index_counter = end_index
        return df

    def add_database_version_column(
        self, df: pd.DataFrame, database_version: str
    ) -> pd.DataFrame:
        """
        Добавляет колонку 'database_version' со значением database_version (str).
        Возвращает копию df.
        """
        df = df.copy()
        df["database_version"] = str(database_version)
        return df

    def add_fulldate_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавляет колонку 'extracted_at' — метку времени извлечения в ISO-8601 (UTC).
        Значение одинаковое для всех строк.
        Возвращает копию df.
        """
        df = df.copy()
        if self._extracted_at is None:
            self._extracted_at = self._now_provider().isoformat()
        df["extracted_at"] = self._extracted_at
        return df

    def reset_state(self) -> None:
        """Сбрасывает внутреннее состояние между запусками."""

        self._index_counter = 0
        self._extracted_at = None


# Alias for compatibility with existing imports/tests.
HashService = HashServiceImpl


class _FallbackHasher(HasherABC):
    """Простая встроенная реализация Hasher для доменных тестов."""

    @property
    def algorithm(self) -> str:
        return "blake2b_256"

    def hash_row(self, row: pd.Series) -> str:
        record = row.to_dict()
        serialized = json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.blake2b(serialized.encode("utf-8"), digest_size=32).hexdigest()

    def hash_columns(self, df: pd.DataFrame, columns: list[str]) -> pd.Series:
        if not columns:
            return pd.Series([None] * len(df), index=df.index, dtype=object)

        def _hash(row: pd.Series) -> str:
            values = [row.get(col) for col in columns]
            serialized = json.dumps(values, ensure_ascii=False, default=str)
            return hashlib.blake2b(serialized.encode("utf-8"), digest_size=32).hexdigest()

        return df.apply(_hash, axis=1)
