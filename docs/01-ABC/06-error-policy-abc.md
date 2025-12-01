# 06 Error Policy ABC

## Описание

ErrorPolicyABC определяет стратегию реакции на ошибки в пайплайне. При возникновении исключения политика принимает решение о дальнейших действиях на основе типа ошибки и контекста выполнения. Возможные действия: повторная попытка, пропуск записи, остановка пайплайна, логирование и продолжение. Политика позволяет централизованно управлять обработкой ошибок и адаптировать поведение пайплайна к различным сценариям сбоев.

## Interface

```python
from abc import ABC, abstractmethod
from typing import Mapping, Any

class ErrorPolicyABC(ABC):
    @abstractmethod
    def decide(self, exc: Exception, context: Mapping[str, Any]) -> "ErrorAction":
        """Принять решение о действии при ошибке."""
        ...
```

## Related Components

- **RetryPolicyABC**: может использоваться для определения стратегии повторов
- **LoggerAdapterABC**: используется для логирования ошибок
- **PipelineHookABC**: может получать уведомления об ошибках

