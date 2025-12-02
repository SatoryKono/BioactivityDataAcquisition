# 11 Metadata Writer ABC

## Описание

MetadataWriterABC сохраняет служебные метаданные рядом с основным результатом пайплайна. Метаданные могут включать информацию о версии пайплайна, времени выполнения, количестве записей, checksums, схемах данных, конфигурации. Интерфейс не навязывает конкретный формат метаданных, но гарантирует, что метаданные сохраняются атомарно и могут быть прочитаны для воспроизводимости и аудита.

## Interface

```python
from pathlib import Path
from typing import Generic, TypeVar

MetadataT = TypeVar("MetadataT")

class MetadataWriterABC(Generic[MetadataT]):
    def write_metadata(self, target_path: Path, metadata: MetadataT) -> None:
        """Сохранить метаданные по указанному пути."""
        raise NotImplementedError
```

## Related Components

- **WriterABC**: может использовать metadata writer для сохранения метаданных
- **ProgressReporterABC**: может предоставлять данные для метаданных

