# 20 PubChem Client

## Описание

`PubChemClient` — клиент для PubChem, предоставляющий доступ к данным соединений. Реализован через общий `ConfiguredHttpClient` для унификации работы с REST API.

## Модуль

`src/bioetl/clients/pubchem/client.py`

## Наследование

Клиент наследуется от `BaseClient` через `ConfiguredHttpClient` и использует общую инфраструктуру HTTP-клиентов.

## Использование

Клиент использует реализации `BaseClient` по умолчанию для работы с API PubChem:

- `fetch_one(request)` — получение одного соединения
- `iter_records(request)` — итерация по соединениям
- `iter_pages(request)` — постраничная итерация

## Доступ к данным

Клиент предоставляет доступ к различным типам данных PubChem:
- Молекулярные свойства
- Структурные данные
- Идентификаторы соединений
- Биологическая активность

## Related Components

- **BaseClient**: базовый класс клиентов данных
- **ConfiguredHttpClient**: базовая реализация настроенного клиента (см. `docs/02-pipelines/clients/21-configured-http-client.md`)
- **TestItemChemblPipeline**: использует клиент для обогащения testitem (см. `docs/02-pipelines/chembl/testitem/00-testitem-chembl-overview.md`)

