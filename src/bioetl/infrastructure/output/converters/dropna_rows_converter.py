"""Конвертер для удаления полностью пустых строк из DataFrame."""

from __future__ import annotations

import pandas as pd

from bioetl.domain.clients.base.output.contracts import OutputFrameConverterABC


class DropNaRowsConverter(OutputFrameConverterABC):
    """Удаляет строки, где все значения являются NaN."""

    def convert(self, df: pd.DataFrame) -> pd.DataFrame:
        """Удаляет строки, где все значения являются NaN."""
        return df.dropna(how="all")


__all__ = ["DropNaRowsConverter"]
