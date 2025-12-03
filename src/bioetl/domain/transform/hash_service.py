import pandas as pd
from datetime import datetime, timezone

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
        
        Logic:
        1. Calculate hash_business_key (if configured) based on specific columns (values list).
        2. Add hash_business_key to DataFrame.
        3. Calculate hash_row based on ALL columns (including hash_business_key) as a canonical JSON object.
        """
        df = df.copy()

        # 1. hash_business_key
        if business_key_cols:
            # Ensure columns exist before hashing
            cols_to_hash = [
                c for c in business_key_cols if c in df.columns
            ]
            if cols_to_hash:
                # Uses hash_columns -> list hashing (canonical list)
                df["hash_business_key"] = self._hasher.hash_columns(
                    df,
                    cols_to_hash
                )
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
        df["index"] = list(range(len(df)))
        return df

    def add_database_version_column(self, df: pd.DataFrame, database_version: str) -> pd.DataFrame:
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
        now_iso = datetime.now(timezone.utc).isoformat()
        df["extracted_at"] = now_iso
        return df
