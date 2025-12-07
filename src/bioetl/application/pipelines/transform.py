"""Контракт стадии transform."""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from bioetl.domain.models import RunContext


class TransformStageProtocol(Protocol):
    """Абстракция трансформации данных.

    Вход:
        df: pd.DataFrame — сырые данные.
        context: RunContext — метаданные запуска, не требующие глобального состояния.
    Выход:
        pd.DataFrame — трансформированные данные для последующих стадий.
    """

    def transform(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        """Выполняет бизнес-преобразования."""


__all__ = ["TransformStageProtocol"]
