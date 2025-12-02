from abc import ABC, abstractmethod
from typing import Any, Self


class LoggerAdapterABC(ABC):
    """
    Интерфейс структурированного логгера.
    """

    @abstractmethod
    def info(self, msg: str, **ctx: Any) -> None:
        """Log info message."""

    @abstractmethod
    def error(self, msg: str, **ctx: Any) -> None:
        """Log error message."""

    @abstractmethod
    def debug(self, msg: str, **ctx: Any) -> None:
        """Log debug message."""

    @abstractmethod
    def warning(self, msg: str, **ctx: Any) -> None:
        """Log warning message."""

    @abstractmethod
    def bind(self, **ctx: Any) -> Self:
        """Возвращает логгер с привязанным контекстом."""


class ProgressReporterABC(ABC):
    """
    Интерфейс отчетности о прогрессе.
    """

    @abstractmethod
    def start(self, total: int, description: str = "") -> None:
        """Начинает отслеживание прогресса."""

    @abstractmethod
    def update(self, n: int = 1) -> None:
        """Обновляет прогресс на n единиц."""

    @abstractmethod
    def finish(self) -> None:
        """Завершает отслеживание."""


class TracerABC(ABC):
    """
    Интерфейс распределенной трассировки.
    """

    @abstractmethod
    def start_span(self, name: str) -> Any:
        """Начинает спан."""

    @abstractmethod
    def end_span(self, span: Any) -> None:
        """Завершает спан."""

    @abstractmethod
    def inject_context(self, headers: dict[str, str]) -> None:
        """Внедряет контекст трассировки в заголовки."""

