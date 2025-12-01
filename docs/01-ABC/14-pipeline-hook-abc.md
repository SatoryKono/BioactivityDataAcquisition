# 14 Pipeline Hook ABC

## Описание

PipelineHookABC определяет интерфейс хуков наблюдения за выполнением пайплайна. Хуки получают уведомления о старте и завершении пайплайна и стадий, а также об ошибках. Это позволяет реализовать различные механизмы мониторинга, логирования, метрик, уведомлений без изменения основной логики пайплайна. Интерфейс не навязывает конкретную реализацию хуков, но гарантирует, что все ключевые события пайплайна будут уведомлены.

## Interface

```python
from abc import ABC, abstractmethod

class PipelineHookABC(ABC):
    @abstractmethod
    def on_pipeline_start(self, pipeline: "PipelineBase") -> None:
        """Вызывается при старте пайплайна."""
        ...

    @abstractmethod
    def on_pipeline_end(self, pipeline: "PipelineBase", result: "RunResult") -> None:
        """Вызывается при завершении пайплайна."""
        ...

    @abstractmethod
    def on_stage_start(self, stage_name: str) -> None:
        """Вызывается при старте стадии."""
        ...

    @abstractmethod
    def on_stage_end(self, stage_name: str) -> None:
        """Вызывается при завершении стадии."""
        ...

    @abstractmethod
    def on_stage_error(self, stage_name: str, error: Exception) -> None:
        """Вызывается при ошибке на стадии."""
        ...

    @abstractmethod
    def on_pipeline_error(self, error: Exception) -> None:
        """Вызывается при ошибке пайплайна."""
        ...
```

## Related Components

- **LoggerAdapterABC**: может использоваться для логирования событий
- **TracerABC**: может использоваться для записи метрик
- **ProgressReporterABC**: может получать уведомления о прогрессе

