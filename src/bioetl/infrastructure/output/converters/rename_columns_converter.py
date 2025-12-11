"""DataFrame converter that standardizes column names to kebab-case."""

from __future__ import annotations

import pandas as pd

from bioetl.domain.clients.base.output.contracts import OutputFrameConverterABC


class RenameColumnsConverter(OutputFrameConverterABC):
    """Convert column names to kebab-case for downstream outputs."""

    def convert(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a copy with columns lowercased and underscores replaced by dashes."""
        return df.rename(columns=lambda c: str(c).replace("_", "-").lower())


__all__ = ["RenameColumnsConverter"]
