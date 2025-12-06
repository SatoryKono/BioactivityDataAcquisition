"""Управление вызовами хуков стадий пайплайна."""

from datetime import datetime, timezone
from typing import Iterable

from bioetl.application.pipelines.hooks import PipelineHookABC
from bioetl.domain.models import RunContext, StageResult
from bioetl.domain.providers import ProviderId
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC


class HooksManager:
    """Отвечает за вызовы хуков и измерение времени стадий."""

    def __init__(
        self,
        *,
        logger: LoggerAdapterABC,
        provider_id: ProviderId,
        entity_name: str,
        hooks: Iterable[PipelineHookABC] | None = None,
    ) -> None:
        self._logger = logger
        self._provider_id = provider_id
        self._entity_name = entity_name
        self._hooks: list[PipelineHookABC] = list(hooks or [])
        self._stage_starts: dict[str, datetime] = {}

    @property
    def hooks(self) -> list[PipelineHookABC]:
        """Возвращает список зарегистрированных хуков."""

        return self._hooks

    def reset(self) -> None:
        """Сбрасывает накопленное состояние (например, тайминги стадий)."""

        self._stage_starts.clear()

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
        self._logger.info(
            f"Stage started: {stage}",
            provider=context.provider,
            entity=context.entity_name,
            run_id=context.run_id,
        )
        for hook in self._hooks:
            hook.on_stage_start(stage, context)

    def notify_stage_end(self, stage: str, result: StageResult) -> None:
        """Уведомляет о завершении стадии и логирует событие."""

        self._logger.info(
            f"Stage finished: {stage}",
            records=result.records_processed,
            chunks=result.chunks_processed,
            provider=self._provider_id.value,
            entity=self._entity_name,
        )
        for hook in self._hooks:
            hook.on_stage_end(stage, result)

    def get_stage_start(self, stage: str) -> datetime | None:
        """Возвращает время старта указанной стадии, если оно зафиксировано."""

        return self._stage_starts.get(stage)
