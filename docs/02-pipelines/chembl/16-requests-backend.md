# 16 Requests Backend

## Описание

`RequestsBackend` — реализация HTTP-бэкенда на базе библиотеки `requests`. Обеспечивает HTTP-вызовы к REST API ChEMBL, включая получение одиночного объекта или итерацию по записям и страницам, а также закрытие HTTP-сессии.

## Модуль

`src/bioetl/clients/chembl/factories.py`

## Наследование

Класс реализует протокол `HttpBackend` (Protocol) и предоставляет реализацию на основе библиотеки `requests`. Отвечает за выполнение HTTP-запросов к REST API ChEMBL: реализует методы для получения одной записи, итерирования по записям и страницам, а также закрытия соединения.

## Основные методы

### `__init__(self)`

Инициализирует бэкенд, создавая сессию `requests.Session` для управления HTTP-соединениями.

### `fetch_one(self, *, source: SourceConfig, resource: ResourceConfig, request: ClientRequest, context: RequestContext | None = None) -> Record | None`

Выполняет единичный HTTP-запрос (GET/POST) для ресурса и возвращает один результат (JSON). Реализует метод для получения одной записи из ChEMBL API.

**Параметры:**
- `source` — конфигурация источника данных
- `resource` — конфигурация ресурса
- `request` — объект запроса
- `context` — контекст запроса (опционально)

**Возвращает:** запись (Record) с данными или `None`, если запись не найдена.

### `iter_records(self, *, source: SourceConfig, resource: ResourceConfig, request: ClientRequest, context: RequestContext | None = None) -> Iterator[Record]`

Выполняет запрос(ы) и итеративно возвращает записи (для ChEMBL объединяет результаты, напр. для списка *activities*). Реализует метод для итерирования по записям из ChEMBL API.

**Параметры:**
- `source` — конфигурация источника данных
- `resource` — конфигурация ресурса
- `request` — объект запроса
- `context` — контекст запроса (опционально)

**Возвращает:** итератор по записям.

### `iter_pages(self, *, source: SourceConfig, resource: ResourceConfig, request: ClientRequest, context: RequestContext | None = None) -> Iterator[Page]`

Возвращает итератор по страницам ответа. Реализует метод для итерирования по страницам из ChEMBL API.

**Параметры:**
- `source` — конфигурация источника данных
- `resource` — конфигурация ресурса
- `request` — объект запроса
- `context` — контекст запроса (опционально)

**Возвращает:** итератор по страницам.

### `metadata(self, *, source: SourceConfig) -> dict[str, object]`

Возвращает метаданные backend (например, тип "requests").

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

