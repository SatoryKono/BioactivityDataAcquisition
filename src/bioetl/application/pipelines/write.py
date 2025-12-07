"""Контракт стадии write."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd

from bioetl.domain.clients.base.output.contracts import WriteResult
from bioetl.domain.models import RunContext


class WriteStageProtocol(Protocol):
    """Абстракция записи данных.

    Вход:
        df: pd.DataFrame — валидированные данные.
        output_path: Path — путь назначения.
        context: RunContext — контекст запуска без глобальных зависимостей.
    Выход:
        WriteResult — сведения о записанных строках и артефактах.
    """

    def write(
        self, df: pd.DataFrame, output_path: Path, context: RunContext | None = None
    ) -> WriteResult | None:
        """Сохраняет данные в целевое хранилище."""


__all__ = ["WriteStageProtocol"]
