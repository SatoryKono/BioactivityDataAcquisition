"""
Модели данных для ядра ETL-пайплайна.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from bioetl.domain.providers import ProviderId
from bioetl.domain.value_objects import EntityName, RunId, StageName


@dataclass
class StageResult:
    """Результат выполнения стадии.

    Attributes:
        stage_name: Имя стадии (StageName). Принимает str для обратной совместимости.
        success: Успешность выполнения.
        records_processed: Количество обработанных записей.
        chunks_processed: Количество обработанных чанков.
        duration_sec: Длительность выполнения в секундах.
        errors: Список ошибок.
    """

    stage_name: StageName
    success: bool
    records_processed: int
    chunks_processed: int
    duration_sec: float
    errors: list[str]

    def __post_init__(self) -> None:
        """Coerce str to StageName for backwards compatibility."""
        if isinstance(self.stage_name, str):
            object.__setattr__(self, "stage_name", StageName(self.stage_name))


@dataclass
class RunContext:
    """
    Контекст выполнения пайплайна.
    Содержит информацию о текущем запуске, конфигурации и окружении.

    Attributes:
        run_id: Уникальный идентификатор запуска (RunId).
        entity_name: Имя сущности (EntityName). Принимает str для обратной совместимости.
        provider: Идентификатор провайдера (ProviderId). Принимает str для обратной совместимости.
        started_at: Время начала выполнения.
        config: Конфигурация запуска.
        dry_run: Флаг тестового запуска.
        metadata: Дополнительные метаданные.
    """

    run_id: RunId = field(default_factory=RunId.generate)
    entity_name: EntityName | None = None
    provider: ProviderId | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    config: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Coerce str to Value Objects for backwards compatibility."""
        if isinstance(self.entity_name, str):
            value = self.entity_name
            if value:
                object.__setattr__(self, "entity_name", EntityName(value))
            else:
                object.__setattr__(self, "entity_name", None)
        if isinstance(self.provider, str):
            value = self.provider
            if value:
                object.__setattr__(self, "provider", ProviderId(value))
            else:
                object.__setattr__(self, "provider", None)


@dataclass
class RunResult:
    """
    Результат выполнения пайплайна.
    """

    run_id: RunId
    success: bool
    entity_name: str
    row_count: int
    output_path: Path | None
    duration_sec: float
    stages: list[StageResult]
    errors: list[str]
    meta: dict[str, Any]


@dataclass
class StageDescriptor:
    """
    Дескриптор стадии пайплайна.
    Описывает стадию, её исполнимый код и метаданные.
    """

    name: str
    callable: Callable[..., Any]
    skip_on_dry_run: bool = False
    required: bool = True
