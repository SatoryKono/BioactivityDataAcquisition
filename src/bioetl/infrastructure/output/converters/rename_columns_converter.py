from __future__ import annotations

import pandas as pd

from bioetl.domain.clients.base.output.contracts import OutputFrameConverterABC


class RenameColumnsConverter(OutputFrameConverterABC):
    def convert(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.rename(columns=lambda c: str(c).replace("_", "-").lower())


__all__ = ["RenameColumnsConverter"]

