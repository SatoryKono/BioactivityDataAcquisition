# 18 Response Parser ABC

## Описание

ResponseParserABC определяет интерфейс для разбора транспортных ответов во входные записи и курсоры. Он предоставляет методы для извлечения элементов данных из ответа и курсора для пагинации. Это позволяет абстрагироваться от конкретного формата ответов API (JSON, XML, бинарный) и инкапсулировать логику парсинга. Интерфейс не навязывает конкретный тип ответа или записи, но гарантирует, что парсер может извлечь данные и курсор из любого ответа, который может вернуть SourceClientABC.

## Interface

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Iterable, Optional

ResponseT = TypeVar("ResponseT")
ParsedItemT = TypeVar("ParsedItemT")

class ResponseParserABC(Generic[ResponseT, ParsedItemT], ABC):
    @abstractmethod
    def parse_items(self, response: ResponseT) -> Iterable[ParsedItemT]:
        """Извлечь элементы данных из ответа."""
        ...

    @abstractmethod
    def extract_cursor(self, response: ResponseT) -> Optional[str]:
        """Извлечь курсор для следующей страницы из ответа."""
        ...
```

## Related Components

- **SourceClientABC**: использует parser для разбора ответов
- **PaginatorABC**: использует parser для извлечения курсора

