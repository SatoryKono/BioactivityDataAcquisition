"""Domain-level pipeline contracts."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from bioetl.domain.clients.base.output.contracts import WriteResult
from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, StageResult

__all__ = [
    "ErrorPolicyABC",
    "ExtractorABC",
    "LoaderABC",
    "PipelineHookABC",
]


class PipelineHookABC(ABC):
    """Хуки жизненного цикла пайплайна."""

    @abstractmethod
    def on_stage_start(self, stage: str, context: Any) -> None:
        """Вызывается перед началом стадии."""

    @abstractmethod
    def on_stage_end(self, stage: str, result: StageResult) -> None:
        """Вызывается после завершения стадии."""

    @abstractmethod
    def on_error(self, stage: str, error: PipelineStageError) -> None:
        """Вызывается при ошибке."""


class ErrorPolicyABC(ABC):
    """Политика обработки ошибок."""

    @abstractmethod
    def handle(self, error: PipelineStageError, context: Any) -> ErrorAction:
        """Определяет действие при ошибке."""

    @abstractmethod
    def can_retry(self, error: PipelineStageError) -> bool:
        """Проверяет, стоит ли повторять операцию."""


class ExtractorABC(ABC):
    """
    Component responsible for extracting data from source.
    """

    @abstractmethod
    def extract(self, **kwargs: Any) -> Iterable[pd.DataFrame]:
        """
        Yields chunks of data.
        """


class LoaderABC(ABC):
    """
    Component responsible for loading data to destination.
    """

    @abstractmethod
    def load(
        self,
        df: pd.DataFrame,
        output_path: Path,
        context: RunContext,
        *,
        column_order: list[str] | None = None,
    ) -> WriteResult:
        """
        Loads data to destination.
        """
