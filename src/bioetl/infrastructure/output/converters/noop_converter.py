"""No-op converter that returns DataFrame unchanged."""

from __future__ import annotations

import pandas as pd

from bioetl.domain.clients.base.output.contracts import OutputFrameConverterABC


class NoopConverter(OutputFrameConverterABC):
    """Converter that does not modify the DataFrame."""

    def convert(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return DataFrame without changes."""
        return df


__all__ = ["NoopConverter"]
