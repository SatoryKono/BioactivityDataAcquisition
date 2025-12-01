# 04 Deduplicator ABC

## Описание

DeduplicatorABC удаляет дубликаты из потока записей по бизнес-ключу. Он принимает итератор записей и функцию извлечения ключа, возвращая поток уникальных записей. Реализация может использовать различные стратегии: сохранение первой встреченной записи, последней, или делегирование выбора MergeStrategyABC. Интерфейс не навязывает конкретный алгоритм дедупликации, но гарантирует, что для каждого уникального бизнес-ключа в выходном потоке будет только одна запись.

## Interface

```python
from typing import Generic, TypeVar, Iterable, Callable

RecordT = TypeVar("RecordT")
BusinessKeyT = TypeVar("BusinessKeyT")

class DeduplicatorABC(Generic[RecordT, BusinessKeyT]):
    def deduplicate(
        self, 
        records: Iterable[RecordT], 
        key_fn: Callable[[RecordT], BusinessKeyT]
    ) -> Iterable[RecordT]:
        """Удалить дубликаты из потока записей по бизнес-ключу."""
        raise NotImplementedError
```

## Related Components

- **BusinessKeyDeriverABC**: используется для вычисления ключей
- **MergeStrategyABC**: может использоваться для объединения дубликатов

