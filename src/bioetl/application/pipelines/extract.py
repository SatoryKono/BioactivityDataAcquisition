"""Контракт стадии extract."""

from __future__ import annotations

from typing import Any, Iterable, Protocol

import pandas as pd

from bioetl.domain.models import RunContext


class ExtractStageProtocol(Protocol):
    """Абстракция извлечения данных.

    Вход:
        context: RunContext — контекст запуска без глобальных зависимостей.
        **kwargs: дополнительные параметры для источника.
    Выход:
        Iterable[pd.DataFrame] | pd.DataFrame | None — поток чанков с сырыми данными.
    """

    def extract(
        self, context: RunContext | None = None, **kwargs: Any
    ) -> Iterable[pd.DataFrame] | pd.DataFrame | None:
        """Выполняет извлечение данных."""


__all__ = ["ExtractStageProtocol"]
