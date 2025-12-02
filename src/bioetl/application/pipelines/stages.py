from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


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

