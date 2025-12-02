# 01 Cache ABC

## Описание

CacheABC предоставляет интерфейс кэша для промежуточных данных. Предоставляет унифицированный доступ к механизму сохранения и повторного использования данных между запусками или между этапами (например, кэширование результатов запросов к API, чтобы не дублировать вызовы). Реализация может использовать различные механизмы хранения (память, файловая система, внешние кэш-системы) и стратегии инвалидации. Интерфейс не навязывает конкретную реализацию, но гарантирует базовые операции получения, установки и инвалидации значений по ключу. Метод `get()` возвращает значение из кэша по ключу или None, если такой записи нет. Метод `set()` сохраняет значение по заданному ключу (перезапись существующей записи, если она была). Метод `invalidate()` удаляет запись из кэша по ключу.

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

