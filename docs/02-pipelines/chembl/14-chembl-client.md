# 14 ChEMBL Client

## Описание

`ChemblClient` — высокоуровневый REST-клиент для ChEMBL API. Наследует унифицированный HTTP-клиент (`ConfiguredHttpClient`) и инкапсулирует логику обращения к ChEMBL (параметры API, сборка запросов и т.д.). В частности, содержит именованный источник `"chembl"` и генератор запросов `ChemblRequestBuilder`.

## Модуль

`bioetl/clients/chembl/client.py`

## Инициализация

### `__init__(self, backend: HttpBackend, *, config: SourceConfig | None = None) -> None`

Инициализирует клиент с конфигурацией источника и HTTP-бэкендом.

**Параметры:**
- `backend` — HTTP-бэкенд для выполнения запросов
- `config` — конфигурация источника данных (опционально)

## Основные методы

### `request_activity(self, *, ids: Sequence[str] | None = None, filters: Mapping[str, object] | None = None, pagination: PaginationParams | None = None, context: RequestContext | None = None) -> ClientRequest`

Конструирует `ClientRequest` для маршрута `"activity"` с заданными идентификаторами/фильтрами.

**Параметры:**
- `ids` — последовательность ChEMBL IDs для запроса (опционально)
- `filters` — фильтры для запроса (опционально)
- `pagination` — параметры пагинации (опционально)
- `context` — контекст запроса (опционально)

**Возвращает:** объект `ClientRequest` для выполнения запроса к ChEMBL API.

## Использование

Клиент используется в `ActivityExtractor` для выполнения запросов к ChEMBL API:

```python
client = ChemblClient(backend=requests_backend, config=source_config)
request = client.request_activity(ids=["CHEMBL123"], filters={"assay_type": "B"})
```

## Related Components

- **ConfiguredHttpClient**: базовый класс унифицированного HTTP-клиента
- **ChemblRequestBuilder**: построитель запросов для ChEMBL (см. `docs/02-pipelines/chembl/15-chembl-request-builder.md`)
- **RequestsBackend**: HTTP-бэкенд на основе requests (см. `docs/02-pipelines/chembl/16-requests-backend.md`)
- **ActivityExtractor**: использует клиент для извлечения данных (см. `docs/02-pipelines/chembl/activity/01-activity-chembl-extract.md`)

