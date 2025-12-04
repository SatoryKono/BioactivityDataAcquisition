from abc import ABC
from dataclasses import dataclass, field
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
    records_processed: int = 0
    chunks_processed: int = 0
    duration_sec: float = 0.0
    errors: list[str] = field(default_factory=list)


class PipelineHookABC(ABC):
    """Интерфейс для хуков пайплайна."""

    def on_stage_start(self, stage: str, context: Any) -> None:
        """Вызывается перед началом стадии."""
        pass

    def on_stage_end(self, stage: str, result: StageResult) -> None:
        """Вызывается после завершения стадии."""
        pass

    def on_error(self, stage: str, error: Exception) -> None:
        """Вызывается при ошибке."""
        pass
