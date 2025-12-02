import hashlib
import pandas as pd

from bioetl.domain.transform.contracts import HasherABC


class HasherImpl(HasherABC):
    """
    Реализация хеширования (SHA256).
    """

    @property
    def algorithm(self) -> str:
        return "sha256"

    def hash_row(self, row: pd.Series) -> str:
        # Convert row to string representation, handle sorting for determinism
        # Simplification: convert to JSON-like string sorted by index
        row_str = row.sort_index().to_json(date_format="iso")
        return hashlib.sha256(row_str.encode("utf-8")).hexdigest()

    def hash_columns(self, df: pd.DataFrame, columns: list[str]) -> pd.Series:
        if not columns:
            return pd.Series([""] * len(df), index=df.index)
            
        # Hash combined columns
        # lambda row: self.hash_row(row[columns])
        # Optimized vector approach usually preferred, but apply is easier for now
        return df[columns].apply(self.hash_row, axis=1)

