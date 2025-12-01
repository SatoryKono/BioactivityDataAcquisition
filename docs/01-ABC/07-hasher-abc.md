# 07 Hasher ABC

## Описание

HasherABC предоставляет интерфейс хеширования записей и ключей. Он может вычислять хеши для целых записей (для проверки целостности) и для бизнес-ключей (для индексации и дедупликации). Реализация должна гарантировать детерминированность: одинаковые входные данные всегда дают одинаковый хеш. Интерфейс не навязывает конкретный алгоритм хеширования, но подразумевает его стабильность в рамках версии пайплайна.

## Interface

```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic

RecordT = TypeVar('RecordT')
HashT = TypeVar('HashT')

class HasherABC(Generic[RecordT, HashT], ABC):
    """Интерфейс хеширования записей и ключей."""
    
    @abstractmethod
    def hash_record(self, record: RecordT) -> HashT:
        """Вычислить хеш для записи."""
        pass

    @abstractmethod
    def hash_key(self, record: RecordT) -> HashT:
        """Вычислить хеш для бизнес-ключа записи."""
        pass
```

## Related Components

- **BusinessKeyDeriverABC**: может использоваться для вычисления ключа перед хешированием
- **WriterABC**: может использовать хеши для метаданных

