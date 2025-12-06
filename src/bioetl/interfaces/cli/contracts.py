from abc import ABC, abstractmethod
from typing import Any


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
