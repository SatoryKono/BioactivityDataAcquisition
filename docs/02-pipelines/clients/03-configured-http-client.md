# 03 Configured HTTP Client

## Описание

`ConfiguredHttpClient` — базовая реализация клиента данных, настроенного конфигурацией источника и HTTP-бэкендом. Делегирует выполнение запросов объекту `HttpBackend`.

## Модуль

`src/bioetl/clients/factory.py`

## Наследование

Клиент наследуется от `BaseClient` и предоставляет базовую реализацию для всех настроенных HTTP-клиентов. Базовая реализация клиента данных, настроенного конфигурацией источника и HTTP-бэкендом.

## Основные методы

### `fetch_one(self, request: ClientRequest) -> Record | None`

Получает одну запись по запросу. Делегирует выполнение HTTP-запроса бэкенду.

**Параметры:**
- `request` — объект запроса

**Возвращает:** запись (Record) или `None`, если запись не найдена.

### `iter_records(self, request: ClientRequest) -> Iterator[Record]`

Итерирует по записям. Делегирует выполнение HTTP-запросов бэкенду.

**Параметры:**
- `request` — объект запроса

**Возвращает:** итератор по записям.

### `iter_pages(self, request: ClientRequest) -> Iterator[Page]`

Итерирует по страницам. Делегирует выполнение HTTP-запросов бэкенду.

**Параметры:**
- `request` — объект запроса

**Возвращает:** итератор по страницам.

### `metadata(self) -> dict[str, object]`

Возвращает метаданные клиента.

**Возвращает:** словарь с метаданными.

### `close(self) -> None`

Закрывает клиент и освобождает ресурсы (например, HTTP-сессию).

## Делегирование бэкенду

Клиент делегирует все HTTP-операции объекту `HttpBackend`, что позволяет:
- Легко переключать реализации транспорта
- Использовать различные HTTP-библиотеки
- Тестировать клиенты с моками бэкенда

## Related Components

- **BaseClient**: базовый класс клиентов данных
- **HttpBackend**: протокол HTTP-бэкенда
- **RequestsBackend**: реализация бэкенда на основе requests (см. `docs/02-pipelines/chembl/common/03-chembl-requests-backend.md`)
- **ChemblClient**: использует ConfiguredHttpClient (см. `docs/02-pipelines/chembl/common/01-chembl-client.md`)

