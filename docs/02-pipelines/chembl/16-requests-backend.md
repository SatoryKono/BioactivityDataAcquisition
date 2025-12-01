# 16 Requests Backend

## Описание

`RequestsBackend` — реализация HTTP-бэкенда на базе библиотеки `requests`. Обеспечивает HTTP-вызовы к REST API ChEMBL, включая получение одиночного объекта или итерацию по записям и страницам, а также закрытие HTTP-сессии.

## Модуль

`bioetl/clients/chembl/factories.py`

## Реализация протокола

RequestsBackend реализует протокол `HttpBackend`, предоставляя методы для работы с HTTP-запросами.

## Основные методы

### `fetch_one(self, *, source: SourceConfig, resource: ResourceConfig, request: ClientRequest, context: RequestContext | None = None) -> Record | None`

Выполняет единичный HTTP-запрос GET на сформированный URL и возвращает JSON как запись.

**Параметры:**
- `source` — конфигурация источника данных
- `resource` — конфигурация ресурса
- `request` — объект запроса
- `context` — контекст запроса (опционально)

**Возвращает:** запись (Record) с данными или `None`, если запись не найдена.

### `iter_records(self, *, source: SourceConfig, resource: ResourceConfig, request: ClientRequest, context: RequestContext | None = None) -> Iterator[Record]`

Итерирует по записям: для ChEMBL реализовано как один запрос с параметром `limit`, возвращающий список результатов.

**Параметры:**
- `source` — конфигурация источника данных
- `resource` — конфигурация ресурса
- `request` — объект запроса
- `context` — контекст запроса (опционально)

**Возвращает:** итератор по записям.

### `iter_pages(self, *, source: SourceConfig, resource: ResourceConfig, request: ClientRequest, context: RequestContext | None = None) -> Iterator[Page]`

Итерирует постранично – для простоты возвращает одну пустую страницу, так как пагинация ChEMBL обрабатывается иначе.

**Параметры:**
- `source` — конфигурация источника данных
- `resource` — конфигурация ресурса
- `request` — объект запроса
- `context` — контекст запроса (опционально)

**Возвращает:** итератор по страницам.

### `metadata(self, *, source: SourceConfig) -> dict[str, object]`

Возвращает метаданные о бэкенде, например тип.

**Параметры:**
- `source` — конфигурация источника данных

**Возвращает:** словарь с метаданными бэкенда.

### `close(self) -> None`

Закрывает сессию `requests.Session`.

## Управление сессией

Бэкенд использует `requests.Session` для управления HTTP-соединениями:

- Переиспользование соединений для повышения производительности
- Управление cookies и заголовками
- Закрытие сессии при завершении работы

## Related Components

- **HttpBackend**: протокол HTTP-бэкенда
- **ChemblClient**: использует бэкенд для выполнения запросов (см. `docs/02-pipelines/chembl/14-chembl-client.md`)

