# 28 Writer ABC

## Описание

WriterABC пишет коллекцию записей в хранилище по заданному пути. Он принимает итератор записей и путь вывода, выполняя запись в атомарном режиме (через временный файл и os.replace). Интерфейс не навязывает конкретный формат вывода (CSV, Parquet, JSON, БД), но гарантирует, что запись выполняется детерминированно: фиксированный порядок записей, стабильная сериализация, атомарность операции. Writer может использовать PathStrategyABC для определения пути записи и MetadataWriterABC для сохранения метаданных.

## Interface

```python
from pathlib import Path
from typing import Generic, TypeVar, Iterable

RecordT = TypeVar("RecordT")

class WriterABC(Generic[RecordT]):
    def write(self, records: Iterable[RecordT], output_path: Path) -> None:
        """Записать коллекцию записей в хранилище."""
        raise NotImplementedError
```

## Related Components

- **PathStrategyABC**: используется для определения пути записи
- **MetadataWriterABC**: может использоваться для сохранения метаданных
- **HasherABC**: может использоваться для вычисления checksums
- **ProgressReporterABC**: может фиксировать количество записанных записей

