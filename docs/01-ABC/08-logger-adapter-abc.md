# 08 Logger Adapter ABC

## Описание

LoggerAdapterABC определяет интерфейс структурированного логгера. Он предоставляет методы для логирования сообщений с дополнительными полями (structured logging), что позволяет агрегировать и анализировать логи в системах мониторинга. Интерфейс не навязывает конкретную реализацию логирования, но гарантирует поддержку структурированных полей и уровней логирования.

## Interface

```python
from abc import ABC, abstractmethod
from typing import Any

class LoggerAdapterABC(ABC):
    """Интерфейс структурированного логгера."""
    
    @abstractmethod
    def info(self, message: str, **fields: Any) -> None:
        """Логировать информационное сообщение."""
        pass

    @abstractmethod
    def warning(self, message: str, **fields: Any) -> None:
        """Логировать предупреждение."""
        pass

    @abstractmethod
    def error(self, message: str, **fields: Any) -> None:
        """Логировать ошибку."""
        pass
```

## Related Components

- **PipelineHookABC**: использует логгер для уведомлений о событиях
- **ErrorPolicyABC**: использует логгер для записи ошибок

