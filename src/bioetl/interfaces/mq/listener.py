"""Заглушка слушателя очереди для интеграции с MQ-провайдерами."""
from __future__ import annotations

from bioetl.domain.models import RunResult
from bioetl.interfaces.mq.handler import MQJob, MQJobHandler


class MQListener:
    """Минимальный слушатель очереди, делегирующий выполнение обработчику."""

    def __init__(self, handler: MQJobHandler) -> None:
        self._handler = handler

    def start(self) -> None:
        """Запуск основного цикла слушателя (заглушка)."""
        raise NotImplementedError("Queue listening is not implemented; provide MQ integration")

    def process_job(self, job: MQJob) -> RunResult:
        """Обрабатывает одиночное задание."""
        return self._handler.handle(job)


__all__ = ["MQListener"]
