import pandas as pd

from bioetl.domain.transform.contracts import HasherABC
from bioetl.domain.transform.impl.hasher import HasherImpl


class HashService:
    """
    Сервис для вычисления и добавления хеш-сумм.
    """

    def __init__(self, hasher: HasherABC | None = None) -> None:
        self._hasher = hasher or HasherImpl()

    def add_hash_columns(self, df: pd.DataFrame, business_key_cols: list[str] | None = None) -> pd.DataFrame:
        """
        Добавляет столбцы hash_row и hash_business_key.
        """
        df = df.copy()
        df["hash_row"] = self._hasher.hash_columns(df, df.columns.tolist())

        # Always create hash_business_key as nullable
        # (all None if not configured)
        if business_key_cols:
            # Ensure columns exist before hashing
            cols_to_hash = [
                c for c in business_key_cols if c in df.columns
            ]
            if cols_to_hash:
                df["hash_business_key"] = self._hasher.hash_columns(
                    df,
                    cols_to_hash
                )
            else:
                df["hash_business_key"] = None
        else:
            df["hash_business_key"] = None

        return df

