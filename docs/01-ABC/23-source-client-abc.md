# 23 Source Client ABC

## Описание

SourceClientABC определяет интерфейс клиента для общения с внешним источником данных. Он принимает запрос типа RequestT и возвращает ответ типа ResponseT, абстрагируясь от конкретного протокола (HTTP, gRPC, файловая система) и формата данных. Клиент может использовать RateLimiterABC для контроля частоты запросов, RetryPolicyABC для обработки ошибок, CacheABC для кэширования ответов. Интерфейс не навязывает конкретную реализацию транспорта, но гарантирует, что клиент может отправлять запросы и получать ответы.

## Interface

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")

class SourceClientABC(Generic[RequestT, ResponseT], ABC):
    @abstractmethod
    def send(self, request: RequestT) -> ResponseT:
        """Отправить запрос и получить ответ."""
        ...
```

## Related Components

- **RequestBuilderABC**: используется для построения запросов
- **ResponseParserABC**: используется для разбора ответов
- **RateLimiterABC**: используется для контроля частоты
- **RetryPolicyABC**: используется для обработки ошибок
- **SecretProviderABC**: может использоваться для аутентификации

