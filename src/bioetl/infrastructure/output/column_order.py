"""Column order helper utilities."""

from __future__ import annotations

import pandas as pd

__all__ = ["apply_column_order"]


def apply_column_order(
    df: pd.DataFrame, column_order: list[str] | None, *, fill_missing: bool = True
) -> pd.DataFrame:
    """Reorder dataframe columns and optionally fill missing ones with ``None``."""

    if not column_order:
        return df

    df_prepared = df.copy()

    if fill_missing:
        for col in column_order:
            if col not in df_prepared.columns:
                df_prepared[col] = None

    return df_prepared[column_order]
