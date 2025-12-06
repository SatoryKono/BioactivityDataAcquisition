"""
Pipeline lifecycle hooks.
"""
from abc import ABC, abstractmethod
from typing import Any

from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import StageResult


class PipelineHookABC(ABC):
    """
    Хуки жизненного цикла пайплайна.
    """

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
    """
    Политика обработки ошибок.
    """

    @abstractmethod
    def handle(self, error: PipelineStageError, context: Any) -> ErrorAction:
        """Определяет действие при ошибке."""

    @abstractmethod
    def should_retry(self, error: PipelineStageError) -> bool:
        """Проверяет, стоит ли повторять операцию."""
