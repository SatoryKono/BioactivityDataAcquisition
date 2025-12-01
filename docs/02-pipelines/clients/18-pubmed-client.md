# 18 PubMed Client

## Описание

`PubMedClient` — клиент для API PubMed на базе унифицированного интерфейса. Наследует `ConfiguredHttpClient` (то есть `BaseClient`) и предоставляет фабричный метод формирования запроса для статей PubMed.

## Модуль

`src/bioetl/clients/pubmed/client.py`

## Наследование

Клиент наследуется от `BaseClient` через `ConfiguredHttpClient` и использует общую инфраструктуру HTTP-клиентов.

## Использование

Клиент использует реализации `BaseClient` по умолчанию для работы с API PubMed:

- `fetch_one(request)` — получение одной статьи
- `iter_records(request)` — итерация по статьям
- `iter_pages(request)` — постраничная итерация

## Фабричный метод

Клиент предоставляет фабричный метод для формирования запросов к PubMed API с учётом специфики формата запросов PubMed.

## Related Components

- **BaseClient**: базовый класс клиентов данных
- **ConfiguredHttpClient**: базовая реализация настроенного клиента (см. `docs/02-pipelines/clients/21-configured-http-client.md`)
- **ChemblDocumentPipeline**: использует клиент для обогащения документов (см. `docs/02-pipelines/chembl/document/00-document-chembl-overview.md`)

