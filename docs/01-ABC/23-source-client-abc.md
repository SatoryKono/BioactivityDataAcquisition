# 23 Source Client ABC

## Описание

SourceClientABC определяет интерфейс клиента для общения с внешним источником данных. Он описывает unified API для извлечения данных из внешних систем (REST API, баз данных и т.п.), скрывая детали HTTP/DB запросов. Клиент поддерживает одиночные и пагинированные выборки данных. Интерфейс абстрагируется от конкретного протокола (HTTP, gRPC, файловая система) и формата данных. Клиент может использовать RateLimiterABC для контроля частоты запросов, RetryPolicyABC для обработки ошибок, CacheABC для кэширования ответов. Интерфейс не навязывает конкретную реализацию транспорта, но гарантирует, что клиент может отправлять запросы и получать ответы, а также корректно освобождать ресурсы через метод `dispose()`.

## Interface

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Iterable

RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")
RecordT = TypeVar("RecordT")

class SourceClientABC(Generic[RequestT, ResponseT], ABC):
    @abstractmethod
    def send(self, request: RequestT) -> ResponseT:
        """Отправить запрос и получить ответ."""
        ...
    
    def fetch_one(self, request: RequestT) -> Optional[RecordT]:
        """Получить одну запись по запросу. Возвращает запись или None, если запись не найдена."""
        raise NotImplementedError
    
    def fetch_many(self, request: RequestT) -> Iterable[RecordT]:
        """Получить пагинированные данные по запросу. Возвращает итератор записей с автоматическим разбиением на страницы."""
        raise NotImplementedError
    
    def dispose(self) -> None:
        """Закрыть клиент и освободить ресурсы (например, закрыть HTTP-сессии)."""
        pass
```

## Related Components

- **RequestBuilderABC**: используется для построения запросов
- **ResponseParserABC**: используется для разбора ответов
- **RateLimiterABC**: используется для контроля частоты
- **RetryPolicyABC**: используется для обработки ошибок
- **SecretProviderABC**: может использоваться для аутентификации

