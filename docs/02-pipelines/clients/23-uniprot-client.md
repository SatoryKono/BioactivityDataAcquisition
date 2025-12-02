# 23 UniProt Client

## Описание

`UniProtClient` — клиент для REST API UniProt, реализованный в общей архитектуре клиентов. Наследует *ConfiguredHttpClient* аналогично ChemblClient, при создании загружает конфиг источника UniProt и использует *HttpBackend* для запросов. Предоставляет метод для формирования запроса на получение данных белков.

## Модуль

`src/bioetl/clients/uniprot/client.py`

## Наследование

Класс наследуется от `ConfiguredHttpClient`.

## Основные методы

### `__init__(self, backend: HttpBackend, *, config: SourceConfig | None = None)`

Инициализация клиента UniProt; загружает конфигурацию UniProt (если не передана) и вызывает базовый инициализатор с данным backend.

**Параметры:**
- `backend` — HTTP-бэкенд для выполнения запросов
- `config` — конфигурация источника данных (опционально)

**Процесс:**
1. Загрузка конфигурации источника UniProt (если не передана)
2. Вызов базового конструктора `ConfiguredHttpClient`

### `request_proteins(self, *, ids: Sequence[str] | None = None, filters: Mapping[str, object] | None = None, pagination: PaginationParams | None = None, context: RequestContext | None = None) -> ClientRequest`

Формирует *ClientRequest* для получения данных о белках (маршрут `"protein"`, с заданными идентификаторами, фильтрами и пагинацией).

**Параметры:**
- `ids` — последовательность UniProt IDs для запроса (опционально)
- `filters` — фильтры для запроса (опционально)
- `pagination` — параметры пагинации (опционально)
- `context` — контекст запроса (опционально)

**Возвращает:** объект `ClientRequest` для выполнения запроса к UniProt API.

## Использование

Клиент используется в пайплайнах для обогащения данных target информацией из UniProt:

```python
client = UniProtClient(backend=requests_backend, config=source_config)
request = client.request_proteins(ids=["P12345"])
```

## Related Components

- **ConfiguredHttpClient**: базовый класс унифицированного HTTP-клиента (см. `docs/02-pipelines/clients/21-configured-http-client.md`)
- **ChemblTargetPipeline**: использует клиент для обогащения данных (см. `docs/02-pipelines/chembl/target/00-target-chembl-overview.md`)

