"""Конвертер-заглушка, возвращающий DataFrame без изменений."""

from __future__ import annotations

import pandas as pd

from bioetl.domain.clients.base.output.contracts import OutputFrameConverterABC


class NoopConverter(OutputFrameConverterABC):
    """Конвертер, который не изменяет DataFrame."""

    def convert(self, df: pd.DataFrame) -> pd.DataFrame:
        """Возвращает DataFrame без изменений."""
        return df


__all__ = ["NoopConverter"]
