"""Доменный фасад для хеширования и служебных колонок."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

import pandas as pd

from bioetl.domain.transform.contracts import HasherABC, HashServiceABC


class HashService(HashServiceABC):
    """Фасад для детерминированного хеширования и служебных колонок."""

    def __init__(
        self,
        *,
        hasher: HasherABC | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        if hasher is None:
            raise ValueError("HashService requires a HasherABC instance")
        self._hasher = hasher
        self._index_counter = 0
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self._extracted_at: str | None = None

    def add_hash_columns(
        self, df: pd.DataFrame, business_key_cols: list[str] | None = None
    ) -> pd.DataFrame:
        """Add deterministic row and business-key hashes."""
        df = df.copy()

        if business_key_cols:
            cols_to_hash = [c for c in business_key_cols if c in df.columns]
            if cols_to_hash:
                df["hash_business_key"] = self._hasher.compute_hash_columns(
                    df, cols_to_hash
                )
            else:
                df["hash_business_key"] = None
        else:
            df["hash_business_key"] = None

        df["hash_row"] = df.apply(self._hasher.compute_hash_row, axis=1)
        return df

    def add_index_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """Append sequential index column starting from current state."""
        df = df.copy()
        start_index = self._index_counter
        end_index = start_index + len(df)
        df["index"] = list(range(start_index, end_index))
        self._index_counter = end_index
        return df

    def add_database_version_column(
        self, df: pd.DataFrame, database_version: str
    ) -> pd.DataFrame:
        """Attach database_version column as string."""
        df = df.copy()
        df["database_version"] = str(database_version)
        return df

    def add_fulldate_column(
        self, df: pd.DataFrame, timestamp: datetime | None = None
    ) -> pd.DataFrame:
        """Attach extracted_at in UTC ISO-8601, cached per service instance."""
        df = df.copy()
        if self._extracted_at is None:
            ts = timestamp or self._now_provider()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            self._extracted_at = ts.isoformat()
        df["extracted_at"] = self._extracted_at
        return df

    def reset_state(self) -> None:
        """Reset internal counters and cached timestamps."""
        self._index_counter = 0
        self._extracted_at = None


__all__ = ["HashService"]
