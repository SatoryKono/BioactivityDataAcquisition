from __future__ import annotations

import pandas as pd

from bioetl.domain.clients.base.output.contracts import OutputFrameConverterABC


class DropNaRowsConverter(OutputFrameConverterABC):
    def convert(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.dropna(how="all")


__all__ = ["DropNaRowsConverter"]

