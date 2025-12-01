# 01 Cache ABC

## Описание

CacheABC предоставляет абстрактный интерфейс для кэширования данных. Реализация может использовать различные механизмы хранения (память, файловая система, внешние кэш-системы) и стратегии инвалидации. Интерфейс не навязывает конкретную реализацию, но гарантирует базовые операции получения, установки и инвалидации значений по ключу.

## Interface

```python
from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic

CacheKeyT = TypeVar('CacheKeyT')
CacheValueT = TypeVar('CacheValueT')

class CacheABC(Generic[CacheKeyT, CacheValueT], ABC):
    """Абстрактный кэш."""
    
    @abstractmethod
    def get(self, key: CacheKeyT) -> Optional[CacheValueT]:
        """Получить значение по ключу."""
        pass

    @abstractmethod
    def set(self, key: CacheKeyT, value: CacheValueT) -> None:
        """Установить значение по ключу."""
        pass

    @abstractmethod
    def invalidate(self, key: CacheKeyT) -> None:
        """Инвалидировать значение по ключу."""
        pass
```

## Related Components

- **SourceClientABC**: может использовать кэш для кэширования ответов
- **SideInputProviderABC**: может использовать кэш для сайд-инпутов

