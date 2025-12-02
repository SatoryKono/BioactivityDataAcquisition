from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorAction(Enum):
    """Действия при ошибке."""
    FAIL = "fail"
    SKIP = "skip"
    RETRY = "retry"


@dataclass
class StageResult:
    """Результат выполнения стадии."""
    stage_name: str
    success: bool
    records_processed: int
    duration_sec: float
    errors: list[str]


class StageABC(ABC):
    """
    Абстракция стадии пайплайна.
    """

    @abstractmethod
    def run(self, context: Any) -> StageResult:
        """Запускает стадию."""

    @abstractmethod
    def close(self) -> None:
        """Освобождает ресурсы стадии."""


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
    def on_error(self, stage: str, error: Exception) -> None:
        """Вызывается при ошибке."""


class ErrorPolicyABC(ABC):
    """
    Политика обработки ошибок.
    """

    @abstractmethod
    def handle(self, error: Exception, context: Any) -> ErrorAction:
        """Определяет действие при ошибке."""

    @abstractmethod
    def should_retry(self, error: Exception) -> bool:
        """Проверяет, стоит ли повторять операцию."""


class CLICommandABC(ABC):
    """
    Интерфейс команды CLI.
    """

    @abstractmethod
    def register(self, app: Any) -> None:
        """Регистрирует команду в приложении Typer."""

    @abstractmethod
    def run_pipeline(self, config: Any, options: dict[str, Any]) -> Any:
        """Запускает пайплайн с конфигурацией."""

