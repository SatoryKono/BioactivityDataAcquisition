"""Управление вызовами хуков стадий пайплайна."""

from datetime import datetime, timezone
from typing import Iterable

from bioetl.clients.base.logging.contracts import LoggerAdapterABC
from bioetl.domain.models import RunContext, StageResult
from bioetl.domain.pipelines.contracts import PipelineHookABC
from bioetl.domain.providers import ProviderId


class HooksManager:
    """Отвечает за вызовы хуков и измерение времени стадий."""

    def __init__(
        self,
        *,
        logger: LoggerAdapterABC,
        provider_id: ProviderId,
        entity_name: str,
        hooks: Iterable[PipelineHookABC] | None = None,
        pipeline_id: str | None = None,
    ) -> None:
        self._logger = logger
        self._provider_id = provider_id
        self._entity_name = entity_name
        self._hooks: list[PipelineHookABC] = list(hooks or [])
        self._stage_starts: dict[str, datetime] = {}
        self._pipeline_id = pipeline_id
        self._current_run_id: str | None = None

    @property
    def hooks(self) -> list[PipelineHookABC]:
        """Возвращает список зарегистрированных хуков."""

        return self._hooks

    def reset(self) -> None:
        """Сбрасывает накопленное состояние (например, тайминги стадий)."""

        self._stage_starts.clear()
        self._current_run_id = None

    def add_hook(self, hook: PipelineHookABC) -> None:
        """Добавляет хук выполнения."""

        self._hooks.append(hook)

    def add_hooks(self, hooks: Iterable[PipelineHookABC]) -> None:
        """Добавляет список хуков выполнения."""

        for hook in hooks:
            self.add_hook(hook)

    def notify_stage_start(self, stage: str, context: RunContext) -> None:
        """Уведомляет о старте стадии и логирует событие."""

        self._stage_starts[stage] = datetime.now(timezone.utc)
        self._current_run_id = context.run_id
        self._logger.info(
            "Stage started",
            provider=context.provider,
            entity=context.entity_name,
            run_id=context.run_id,
            stage=stage,
            pipeline=self._pipeline_id,
        )
        for hook in self._hooks:
            hook.on_stage_start(stage, context)

    def notify_stage_end(self, stage: str, result: StageResult) -> None:
        """Уведомляет о завершении стадии и логирует событие."""

        self._logger.info(
            "Stage finished",
            records=result.records_processed,
            chunks=result.chunks_processed,
            provider=self._provider_id.value,
            entity=self._entity_name,
            stage=stage,
            pipeline=self._pipeline_id,
            run_id=self._current_run_id,
            outcome="success" if result.success else "error",
        )
        for hook in self._hooks:
            hook.on_stage_end(stage, result)

    def get_stage_start(self, stage: str) -> datetime | None:
        """Возвращает время старта указанной стадии, если оно зафиксировано."""

        return self._stage_starts.get(stage)

    def set_logger(self, logger: LoggerAdapterABC) -> None:
        """Обновляет логгер для хуков."""

        self._logger = logger
