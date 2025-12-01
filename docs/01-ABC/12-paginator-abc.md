# 12 Paginator ABC

## Описание

PaginatorABC определяет стратегию постраничного обхода при получении данных. Он принимает предыдущий запрос и последний ответ, возвращая запрос для следующей страницы или None, если страниц больше нет. Стратегия инкапсулирует логику извлечения курсора из ответа и построения следующего запроса, что позволяет абстрагироваться от конкретного формата пагинации API (offset-based, cursor-based, token-based).

## Interface

```python
from typing import Generic, TypeVar, Optional

RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")

class PaginatorABC(Generic[RequestT, ResponseT]):
    def get_next_request(
        self, 
        prev_request: RequestT, 
        last_response: ResponseT
    ) -> Optional[RequestT]:
        """Вычислить запрос следующей страницы."""
        raise NotImplementedError
```

## Related Components

- **RequestBuilderABC**: может использоваться для построения запросов
- **ResponseParserABC**: используется для извлечения курсора из ответа
- **SourceClientABC**: использует paginator для постраничного обхода

