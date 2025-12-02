# 14 ChEMBL Client

## Описание

`ChemblClient` — API-клиент ChEMBL (новая архитектура). Наследует общий HTTP-клиент (`ConfiguredHttpClient`) и предоставляет методы для формирования запросов к ChEMBL. При инициализации загружает конфигурацию источника и использует `ChemblRequestBuilder` для создания запросов.

## Модуль

`bioetl/clients/chembl/client.py`

## Инициализация

### `__init__(self, backend: HttpBackend, *, config: SourceConfig | None = None)`

Инициализирует клиент ChEMBL; загружает конфиг источника (если не предоставлен) и вызывает `ConfiguredHttpClient.__init__`, привязывая backend.

**Параметры:**
- `backend` — HTTP-бэкенд для выполнения запросов
- `config` — конфигурация источника данных (опционально)

**Параметры:**
- `backend` — HTTP-бэкенд для выполнения запросов
- `config` — конфигурация источника данных (опционально)

**Процесс:**
1. Загрузка конфигурации источника ChEMBL (если не предоставлена)
2. Вызов базового конструктора `ConfiguredHttpClient` с backend

## Основные методы

### `request_activity(self, *, ids: Sequence[str] | None = None, filters: Mapping[str, object] | None = None, pagination: PaginationParams | None = None, context: RequestContext | None = None) -> ClientRequest`

Формирует запрос для получения *activity*: возвращает объект *ClientRequest* с установленным маршрутом `"activity"`, списком ID, фильтрами и параметрами пагинации (фактическое выполнение запроса происходит при вызове методов backend через `iter_records`).

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

