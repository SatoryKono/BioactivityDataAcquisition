# 17 Request Builder ABC

## Описание

RequestBuilderABC определяет интерфейс построения транспортных запросов к источникам данных. Он предоставляет методы для создания начального запроса и запросов для конкретных страниц (с курсором). Это позволяет абстрагироваться от конкретного формата запросов API и инкапсулировать логику построения параметров, заголовков, тела запроса. Интерфейс не навязывает конкретный тип запроса, но гарантирует, что построенные запросы могут быть отправлены через SourceClientABC.

## Interface

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional

RequestT = TypeVar("RequestT")

class RequestBuilderABC(Generic[RequestT], ABC):
    @abstractmethod
    def build_initial(self) -> RequestT:
        """Построить начальный запрос."""
        ...

    @abstractmethod
    def build_for_page(self, cursor: Optional[str]) -> RequestT:
        """Построить запрос для страницы с курсором."""
        ...
```

## Related Components

- **SourceClientABC**: использует builder для создания запросов
- **PaginatorABC**: может использовать builder для построения следующего запроса

