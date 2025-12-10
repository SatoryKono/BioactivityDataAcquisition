"""Конвертер для переименования колонок DataFrame (snake_case → kebab-case)."""

from __future__ import annotations

import pandas as pd

from bioetl.domain.clients.base.output.contracts import OutputFrameConverterABC


class RenameColumnsConverter(OutputFrameConverterABC):
    """Переименовывает колонки из snake_case в kebab-case и приводит к lowercase."""

    def convert(self, df: pd.DataFrame) -> pd.DataFrame:
        """Переименовывает колонки: заменяет '_' на '-' и приводит к lowercase."""
        return df.rename(columns=lambda c: str(c).replace("_", "-").lower())


__all__ = ["RenameColumnsConverter"]
