# 04 Semantic Scholar Client

## Описание

`SemanticScholarClient` — клиент для API Semantic Scholar, реализованный на базе `BaseClient`. Наследует типовой HTTP-клиент и определяет источник (`source`) как "semantic_scholar".

## Модуль

`src/bioetl/clients/semantic_scholar/client.py`

## Наследование

Клиент наследуется от `BaseClient` через `ConfiguredHttpClient` и использует общую инфраструктуру HTTP-клиентов.

## Использование

Клиент использует реализации `BaseClient` по умолчанию для работы с API Semantic Scholar:

- `fetch_one(request)` — получение одной статьи
- `iter_records(request)` — итерация по статьям
- `iter_pages(request)` — постраничная итерация

## Источник данных

Клиент определяет источник как `"semantic_scholar"` для идентификации в системе.

## Related Components

- **BaseClient**: базовый класс клиентов данных
- **ConfiguredHttpClient**: базовая реализация настроенного клиента (см. `docs/02-pipelines/clients/03-configured-http-client.md`)
- **ChemblDocumentPipeline**: использует клиент для обогащения документов (см. `docs/02-pipelines/chembl/document/00-document-chembl-overview.md`)

