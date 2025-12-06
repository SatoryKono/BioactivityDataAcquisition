"""
Модели данных для ядра ETL-пайплайна.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


@dataclass
class StageResult:
    """Результат выполнения стадии."""

    stage_name: str
    success: bool
    records_processed: int
    chunks_processed: int
    duration_sec: float
    errors: list[str]


@dataclass
class RunContext:
    """
    Контекст выполнения пайплайна.
    Содержит информацию о текущем запуске, конфигурации и окружении.
    """

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_name: str = ""
    provider: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    config: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    """
    Результат выполнения пайплайна.
    """

    run_id: str
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
