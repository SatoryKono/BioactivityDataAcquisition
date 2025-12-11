"""Converter for removing completely empty rows from DataFrame."""

from __future__ import annotations

import pandas as pd

from bioetl.domain.clients.base.output.contracts import OutputFrameConverterABC


class DropNaRowsConverter(OutputFrameConverterABC):
    """Remove rows where all values are NaN."""

    def convert(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows where all values are NaN."""
        return df.dropna(how="all")


__all__ = ["DropNaRowsConverter"]
