# 20 Schema Provider ABC

## Описание

SchemaProviderABC поставляет объект схемы данных SchemaT, используемый для валидации. Схема может быть статической (загруженной из файла) или динамической (построенной на основе конфигурации или метаданных источника). Интерфейс не навязывает конкретный формат схемы, но гарантирует, что предоставленная схема может быть использована ValidatorABC для проверки записей. Это позволяет абстрагироваться от конкретной библиотеки валидации (Pandera, Pydantic, JSON Schema) и обеспечивать гибкость в выборе инструментов.

## Interface

```python
from typing import Generic, TypeVar

SchemaT = TypeVar("SchemaT")

class SchemaProviderABC(Generic[SchemaT]):
    def get_schema(self) -> SchemaT:
        """Вернуть схему для валидации."""
        raise NotImplementedError
```

## Related Components

- **ValidatorABC**: использует provider для получения схемы
- **ConfigResolverABC**: может использоваться для загрузки конфигурации схемы

