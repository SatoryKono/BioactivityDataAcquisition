# 01 Crossref Client

## Описание

`CrossrefClient` — клиент для API CrossRef, реализующий общий контракт клиентов данных. Наследует базовую реализацию и предоставляет метод для формирования запроса по рабочим записям (works).

## Модуль

`src/bioetl/clients/crossref/client.py`

## Наследование

Клиент наследуется от `BaseClient` через `ConfiguredHttpClient` и использует общую инфраструктуру HTTP-клиентов.

## Использование

Клиент использует реализации `BaseClient` по умолчанию для работы с API CrossRef:

- `fetch_one(request)` — получение одной записи
- `iter_records(request)` — итерация по записям
- `iter_pages(request)` — постраничная итерация

## Формирование запросов

Клиент предоставляет метод для формирования запросов по рабочим записям (works) с учётом специфики API CrossRef.

## Related Components

- **BaseClient**: базовый класс клиентов данных
- **ConfiguredHttpClient**: базовая реализация настроенного клиента (см. `docs/02-pipelines/clients/03-configured-http-client.md`)
- **ChemblDocumentPipeline**: использует клиент для обогащения документов (см. `docs/02-pipelines/chembl/document/00-document-chembl-overview.md`)

