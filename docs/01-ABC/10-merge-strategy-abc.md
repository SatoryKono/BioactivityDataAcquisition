# 10 Merge Strategy ABC

## Описание

MergeStrategyABC объединяет дубликаты с одним бизнес-ключом в итоговую запись. Он принимает итератор записей с одинаковым бизнес-ключом и возвращает одну объединённую запись. Стратегия может использовать различные правила слияния: приоритет последней записи, объединение полей, выбор наиболее полной записи, применение специальных правил для конфликтующих значений. Интерфейс не навязывает конкретную стратегию, но гарантирует, что результат слияния является валидной записью.

## Interface

```python
from typing import Generic, TypeVar, Iterable

RecordT = TypeVar("RecordT")
BusinessKeyT = TypeVar("BusinessKeyT")

class MergeStrategyABC(Generic[RecordT, BusinessKeyT]):
    def merge(
        self, 
        records: Iterable[RecordT], 
        business_key: BusinessKeyT
    ) -> RecordT:
        """Объединить дубликаты в одну запись."""
        raise NotImplementedError
```

## Related Components

- **BusinessKeyDeriverABC**: используется для определения дубликатов
- **DeduplicatorABC**: может использовать стратегию для объединения

