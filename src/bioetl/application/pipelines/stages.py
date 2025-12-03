from abc import ABC, abstractmethod
from typing import Any

from bioetl.domain.models import StageResult


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

