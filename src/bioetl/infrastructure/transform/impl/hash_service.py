"""Infrastructure implementation of HashService using BLAKE2b."""

from __future__ import annotations

import pandas as pd

from bioetl.domain.transform.contracts import HasherABC, HashServiceABC


class Blake2bHashService(HashServiceABC):
    """
    Stateless хеш-сервис на основе BLAKE2b-256.

    Использует HasherABC для вычисления хешей.
    Не содержит никакого состояния - чистые функции хеширования.
    """

    def __init__(self, hasher: HasherABC) -> None:
        """
        Args:
            hasher: Реализация алгоритма хеширования.
        """
        self._hasher = hasher

    def hash_row(self, row: dict) -> str:
        """Вычисляет хеш строки как полного объекта."""
        series = pd.Series(row)
        return self._hasher.compute_hash_row(series)

    def hash_business_key(self, row: dict, key_columns: list[str]) -> str:
        """Вычисляет хеш бизнес-ключа (выбранных колонок)."""
        df = pd.DataFrame([row])
        result = self._hasher.compute_hash_columns(df, key_columns)
        return result.iloc[0]

    def add_hash_columns(
        self, df: pd.DataFrame, business_key_cols: list[str] | None = None
    ) -> pd.DataFrame:
        """Добавляет hash_row и hash_business_key колонки к DataFrame."""
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


__all__ = ["Blake2bHashService"]
