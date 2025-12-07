"""Контракт стадии validate."""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from bioetl.domain.models import RunContext


class ValidateStageProtocol(Protocol):
    """Абстракция валидации данных.

    Вход:
        df: pd.DataFrame — данные после transform.
        context: RunContext — контекст выполнения без внешнего состояния.
    Выход:
        pd.DataFrame — валидированные данные, готовые к записи.
    """

    def validate(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        """Проверяет корректность и схему данных."""


__all__ = ["ValidateStageProtocol"]
