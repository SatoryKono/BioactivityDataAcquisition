# 25 Tracer ABC

## Описание

TracerABC определяет интерфейс трассировки метрик. Он предоставляет методы для записи времени выполнения операций и счётчиков событий. Реализация может отправлять метрики в различные системы мониторинга (Prometheus, Datadog, CloudWatch) или агрегировать их локально. Интерфейс не навязывает конкретный формат метрик, но гарантирует, что метрики могут быть записаны и использованы для анализа производительности и диагностики проблем.

## Interface

```python
from abc import ABC, abstractmethod

class TracerABC(ABC):
    """Интерфейс трассировки метрик."""
    
    @abstractmethod
    def record_timing(self, name: str, duration: float) -> None:
        """Записать время выполнения операции."""
        pass

    @abstractmethod
    def record_counter(self, name: str, count: int = 1) -> None:
        """Записать счётчик события."""
        pass
```

## Related Components

- **PipelineHookABC**: может использовать tracer для записи метрик событий
- **SourceClientABC**: может использовать tracer для метрик запросов
- **StageABC**: может использовать tracer для метрик стадий

