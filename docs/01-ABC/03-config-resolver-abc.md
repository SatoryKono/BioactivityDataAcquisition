# 03 Config Resolver ABC

## Описание

ConfigResolverABC отвечает за загрузку и объединение конфигурации из различных источников. Он принимает профиль конфигурации и переопределения (overrides) и возвращает финальный объект конфигурации типа ConfigT. Реализация может загружать конфигурацию из файлов, переменных окружения, внешних сервисов или их комбинации, обеспечивая единообразный интерфейс доступа к настройкам пайплайна.

## Interface

```python
from abc import ABC, abstractmethod
from typing import Any, Mapping, TypeVar, Generic

ConfigT = TypeVar('ConfigT')

class ConfigResolverABC(Generic[ConfigT], ABC):
    """Загрузка и объединение конфигурации."""
    
    @abstractmethod
    def resolve(self, profile: str, overrides: Mapping[str, Any]) -> ConfigT:
        """Разрешить конфигурацию для профиля с переопределениями."""
        pass
```

## Related Components

- **PipelineBase**: использует resolver для загрузки конфигурации
- **CLICommandABC**: может использовать resolver для получения настроек

