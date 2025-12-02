# 03 ChEMBL Requests Backend

## Описание

`RequestsBackend` — реализация HTTP-бэкенда на базе библиотеки `requests` для ChEMBL API. Обеспечивает транспортный уровень: выполнение HTTP-запросов (GET/POST), управление сессией (cookies, keep-alive) и возвращение сырых данных.

## Модуль

`src/bioetl/clients/chembl/impl/requests_backend.py`

## Наследование

Класс реализует протокол `HttpBackend` (Protocol) и предоставляет реализацию на основе библиотеки `requests`.

## Основные методы

### `__init__(self)`

Инициализирует бэкенд, создавая сессию `requests.Session` для управления HTTP-соединениями.

### `fetch_one(self, *, source: SourceConfig, resource: ResourceConfig, request: ClientRequest, context: RequestContext | None = None) -> Record | None`

Выполняет единичный HTTP-запрос для ресурса и возвращает один результат (JSON). Используется для получения одиночных записей по ID.

**Параметры:**
- `source`: конфигурация источника.
- `resource`: конфигурация ресурса.
- `request`: объект запроса (URL, параметры).

**Возвращает:** словарь с данными или `None`.

### `iter_records(self, *, source: SourceConfig, resource: ResourceConfig, request: ClientRequest, context: RequestContext | None = None) -> Iterator[Record]`

Выполняет запрос и возвращает итератор по записям.
Если API возвращает пагинированный список, метод итерируется по страницам и элементам внутри них, скрывая механику пагинации.

### `iter_pages(self, *, source: SourceConfig, resource: ResourceConfig, request: ClientRequest, context: RequestContext | None = None) -> Iterator[Page]`

Возвращает итератор по страницам ("сырым" ответам API), не разворачивая их в отдельные записи.

### `close(self) -> None`

Закрывает сессию `requests.Session`, освобождая сокеты.

## Управление сессией

Бэкенд использует `requests.Session` для:
- Переиспользования TCP-соединений (Keep-Alive).
- Управления глобальными заголовками (User-Agent).
- Корректного завершения работы (cleanup).

## Related Components

- **HttpBackend**: протокол HTTP-бэкенда
- **ChemblClient**: клиент, использующий данный бэкенд (см. `docs/02-pipelines/chembl/common/14-chembl-client.md`)

