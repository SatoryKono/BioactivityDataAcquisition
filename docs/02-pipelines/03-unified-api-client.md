# 03 Unified API Client

## Описание

`UnifiedAPIClient` — унифицированный клиент для работы с внешними REST API, который объединяет исполнитель запросов, построитель запросов и стратегию пагинации. Класс предоставляет высокоуровневые методы (`get_json`, `paginate_json`, `fetch_one`, `fetch_batch` и др.), которые изолируют взаимодействие с конкретными API и возвращают Python-структуры данных. Такой подход позволяет легко переключать реализацию транспорта или добавлять кэширование без изменения кода, использующего клиент.

## Архитектура

`UnifiedAPIClient` объединяет три основных компонента:

1. **Исполнитель запросов (Request Executor/Transport)** — низкоуровневая реализация отправки HTTP-запросов
2. **Построитель запросов (RequestBuilderABC)** — создание запросов с параметрами, заголовками и телом
3. **Стратегия пагинации (PaginatorABC)** — определение следующей страницы данных

## Основные методы

### `get_json(url, params=None, headers=None) -> dict`

Выполняет GET-запрос и возвращает JSON-ответ как Python-словарь.

```python
client = UnifiedAPIClient(...)
response = client.get_json(
    url="/api/endpoint",
    params={"filter": "value"},
    headers={"Authorization": "Bearer token"}
)
```

### `paginate_json(url, params=None, headers=None) -> Iterator[dict]`

Итератор по страницам данных. Прозрачно подгружает очередные записи до тех пор, пока есть данные. Автоматически обрабатывает пагинацию согласно стратегии, заданной в `PaginatorABC`.

```python
client = UnifiedAPIClient(...)
for page in client.paginate_json("/api/endpoint", params={"limit": 100}):
    for record in page.get("records", []):
        process_record(record)
```

**Особенности:**

- Ленивая загрузка: следующая страница загружается только при итерации
- Прозрачная пагинация: клиент автоматически определяет наличие следующей страницы
- Обработка различных форматов: поддержка offset-based, cursor-based, token-based пагинации

### `fetch_one(url, params=None, headers=None) -> dict | None`

Получает одну запись по запросу. Возвращает запись как словарь или `None`, если запись не найдена.

```python
record = client.fetch_one("/api/record/123")
if record:
    process_record(record)
```

### `fetch_batch(url, params=None, headers=None, batch_size=100) -> Iterator[list[dict]]`

Получает данные батчами заданного размера. Полезно для обработки больших объёмов данных с контролем размера батча.

```python
for batch in client.fetch_batch("/api/endpoint", batch_size=50):
    process_batch(batch)
```

## Пагинация

### Метод `paginate_json`

Метод `paginate_json` реализует прозрачную пагинацию:

1. Выполняет начальный запрос через `RequestBuilderABC`
2. Получает ответ через исполнитель запросов
3. Извлекает данные из ответа через `ResponseParserABC`
4. Использует `PaginatorABC` для определения следующей страницы
5. Автоматически загружает следующую страницу при итерации
6. Прекращает итерацию, когда `PaginatorABC` возвращает `None`

**Пример использования:**

```python
# Автоматическая итерация по всем страницам
for page_data in client.paginate_json("/api/activities"):
    # page_data содержит данные одной страницы
    records = page_data.get("results", [])
    for record in records:
        yield transform_record(record)
```

## Изоляция взаимодействия с API

`UnifiedAPIClient` изолирует детали взаимодействия с конкретными API:

- **Формат запросов**: построение запросов инкапсулировано в `RequestBuilderABC`
- **Формат ответов**: парсинг ответов инкапсулирован в `ResponseParserABC`
- **Стратегия пагинации**: логика пагинации инкапсулирована в `PaginatorABC`
- **Транспорт**: низкоуровневая отправка запросов изолирована в исполнителе запросов

Это позволяет:

- Легко переключать реализацию транспорта (HTTP, gRPC, моки для тестов)
- Добавлять кэширование на уровне транспорта
- Изменять формат запросов/ответов без изменения кода клиента
- Тестировать клиент с моками транспорта

## HTTP адаптеры

HTTP-адаптеры реализуют низкоуровневый транспорт для отправки HTTP-запросов. Они инкапсулируют:

- Управление HTTP-сессиями
- Обработку таймаутов
- Обработку ошибок HTTP
- Повторные попытки (через `RetryPolicyABC`)
- Ограничение частоты запросов (через `RateLimiterABC`)
- Кэширование ответов (через `CacheABC`)

**Пример реализации HTTP-адаптера:**

```python
class HTTPAdapter:
    def __init__(
        self,
        base_url: str,
        retry_policy: RetryPolicyABC,
        rate_limiter: RateLimiterABC,
        cache: CacheABC | None = None
    ):
        self.base_url = base_url
        self.retry_policy = retry_policy
        self.rate_limiter = rate_limiter
        self.cache = cache
        self.session = requests.Session()
    
    def execute(self, request: HTTPRequest) -> HTTPResponse:
        # Применение rate limiting
        self.rate_limiter.wait_if_needed()
        
        # Проверка кэша
        if self.cache:
            cached = self.cache.get(request)
            if cached:
                return cached
        
        # Выполнение запроса с retry
        response = self.retry_policy.execute(
            lambda: self._send_request(request)
        )
        
        # Сохранение в кэш
        if self.cache:
            self.cache.set(request, response)
        
        return response
```

## Переключение транспорта

Благодаря изоляции транспорта, можно легко переключать реализацию:

```python
# Использование реального HTTP-транспорта
http_adapter = HTTPAdapter(...)
client = UnifiedAPIClient(
    executor=http_adapter,
    request_builder=chembl_request_builder,
    paginator=chembl_paginator
)

# Использование мока для тестов
mock_adapter = MockHTTPAdapter(...)
test_client = UnifiedAPIClient(
    executor=mock_adapter,
    request_builder=chembl_request_builder,
    paginator=chembl_paginator
)

# Использование кэшированного транспорта
cached_adapter = CachedHTTPAdapter(
    base_adapter=http_adapter,
    cache=redis_cache
)
cached_client = UnifiedAPIClient(
    executor=cached_adapter,
    request_builder=chembl_request_builder,
    paginator=chembl_paginator
)
```

## Добавление кэширования

Кэширование можно добавить на уровне транспорта без изменения кода клиента:

```python
# Транспорт с кэшированием
class CachedHTTPAdapter:
    def __init__(self, base_adapter: HTTPAdapter, cache: CacheABC):
        self.base_adapter = base_adapter
        self.cache = cache
    
    def execute(self, request: HTTPRequest) -> HTTPResponse:
        # Проверка кэша
        cached = self.cache.get(request)
        if cached:
            return cached
        
        # Выполнение запроса
        response = self.base_adapter.execute(request)
        
        # Сохранение в кэш
        self.cache.set(request, response)
        return response
```

## Модуль

`src/bioetl/core/api/unified_client.py` (предполагаемый путь)

## Related Components

- **RequestBuilderABC**: построение запросов к API (см. `docs/01-ABC/17-request-builder-abc.md`)
- **PaginatorABC**: стратегия пагинации (см. `docs/01-ABC/12-paginator-abc.md`)
- **ResponseParserABC**: разбор ответов API (см. `docs/01-ABC/18-response-parser-abc.md`)
- **SourceClientABC**: высокоуровневый интерфейс клиента источника данных (см. `docs/01-ABC/23-source-client-abc.md`)
- **BaseExternalDataClient**: базовый класс для клиентов внешних API (см. `docs/02-pipelines/01-base-external-data-client.md`)
- **RetryPolicyABC**: политика повторных попыток
- **RateLimiterABC**: ограничение частоты запросов
- **CacheABC**: кэширование ответов
