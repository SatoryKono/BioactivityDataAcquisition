# 07 Client Architecture

Архитектура клиентского слоя BioETL для работы с внешними источниками данных.

## Иерархия клиентов

```
SourceClientABC (ABC)
    │
    ├── BaseClient (Abstract)
    │       │
    │       └── ConfiguredHttpClient
    │               │
    │               ├── ChemblClient
    │               ├── PubChemClient
    │               ├── PubMedClient
    │               ├── CrossrefClient
    │               ├── UniProtClient
    │               └── SemanticScholarClient
    │
    └── BaseExternalDataClient (Legacy)
            │
            └── UnifiedAPIClient
```

## Структура пакета

```
src/bioetl/clients/
├── __init__.py              # Публичное API
├── base/                    # Базовые абстракции и утилиты
│   ├── client_abc.py       # BaseClient, ClientRequest, RequestContext
│   ├── http_backend.py     # HttpBackend Protocol
│   ├── paging.py           # Page, PaginationParams
│   ├── types.py            # Record, Headers, QueryParams, JsonData
│   ├── exceptions.py       # Иерархия исключений
│   └── dbbackend_protocol.py  # DbBackendProtocol (для БД)
├── config/                  # Конфигурация через YAML
│   ├── models.py           # Pydantic-модели (SourceConfig, ResourceConfig и т.д.)
│   ├── loader.py           # Загрузчики YAML
│   └── yaml/               # YAML-конфигурации источников
│       ├── chembl.yml
│       ├── pubchem.yml
│       ├── pubmed.yml
│       └── ...
├── factory.py               # ClientFactory, ConfiguredHttpClient
├── registry.py             # ClientRegistry для регистрации фабрик
└── <source>/               # Конкретные клиенты по источникам
    ├── chembl/
    │   └── client.py       # ChemblClient
    ├── pubchem/
    ├── pubmed/
    ├── openalex/
    ├── crossref/
    ├── semantic_scholar/
    └── uniprot/
```

## Компоненты

### 1. SourceClientABC

**Документация:** `docs/01-ABC/23-source-client-abc.md`

Абстрактный интерфейс для всех клиентов источников данных. Определяет контракт:
- `send(request)` — отправка запроса
- `fetch_one(request)` — получение одной записи
- `fetch_many(request)` — получение множества записей
- `dispose()` — освобождение ресурсов

### 2. BaseClient (ABC)

**Файл:** `base/client_abc.py`

Абстрактный базовый класс для всех клиентов данных.

**Методы:**
```python
@abstractmethod
def fetch_one(self, request: ClientRequest) -> Record | None

@abstractmethod
def iter_records(self, request: ClientRequest) -> Iterator[Record]

@abstractmethod
def iter_pages(self, request: ClientRequest) -> Iterator[Page]

@abstractmethod
def metadata(self) -> Mapping[str, object]

@abstractmethod
def close(self) -> None
```

### 3. ConfiguredHttpClient

**Файл:** `factory.py`  
**Документация:** `docs/02-pipelines/clients/03-configured-http-client.md`

Базовая реализация клиента на основе YAML-конфигурации:
- Автоматическая загрузка конфигурации из `src/bioetl/clients/config/yaml/`
- Делегирование запросов `HttpBackend`
- Поддержка методов `fetch_one`, `iter_records`, `iter_pages`

**Когда использовать:**
- Для новых клиентов внешних API
- Когда конфигурация API описана в YAML

### 4. Конкретные клиенты

Наследуются от `ConfiguredHttpClient` и добавляют специфичную логику:

| Клиент | Источник | Документация |
|--------|----------|--------------|
| ChemblClient | ChEMBL API | `docs/02-pipelines/chembl/common/01-chembl-client.md` |
| PubChemClient | PubChem API | `docs/02-pipelines/clients/02-pubchem-client.md` |
| PubMedClient | PubMed API | `docs/02-pipelines/clients/00-pubmed-client.md` |
| CrossrefClient | Crossref API | `docs/02-pipelines/clients/01-crossref-client.md` |
| UniProtClient | UniProt API | `docs/02-pipelines/clients/05-uniprot-client.md` |
| SemanticScholarClient | Semantic Scholar API | `docs/02-pipelines/clients/04-semantic-scholar-client.md` |

### 5. BaseExternalDataClient (Legacy)

**Документация:** `docs/02-pipelines/01-base-external-data-client.md`

Legacy-класс для клиентов внешних API с встроенной пагинацией. Используется в старом коде.

**Когда использовать:**
- Только для поддержки существующего кода
- Для новых клиентов предпочтительнее `ConfiguredHttpClient`

### 6. UnifiedAPIClient

**Документация:** `docs/02-pipelines/03-unified-api-client.md`

Высокоуровневый клиент, объединяющий:
- Исполнитель запросов (транспорт)
- Построитель запросов (`RequestBuilderABC`)
- Стратегию пагинации (`PaginatorABC`)

**Когда использовать:**
- Когда нужен полный контроль над компонентами
- Для сложных сценариев с кастомной пагинацией

## Типы данных

### ClientRequest

Нормализованный объект запроса.

**Файл:** `base/client_abc.py`

```python
route: str                          # Имя ресурса/маршрута
ids: Sequence[str] | None          # Идентификаторы для выборки
filters: Mapping[str, object] | None  # Фильтры запроса
pagination: PaginationParams | None # Параметры пагинации
raw: Mapping[str, object] | None    # Дополнительные параметры
context: RequestContext | None      # Контекст запроса
```

### RequestContext

Контекстная информация для запросов.

```python
source: str | None      # Имя источника
route: str | None       # Имя маршрута
trace_id: str | None    # Идентификатор трассировки
timeout_s: float | None # Таймаут запроса
extra: Mapping[str, object] | None  # Дополнительные данные
```

### Page и PaginationParams

**Файл:** `base/paging.py`

**PaginationParams:**
```python
page_param: str | None
page_size_param: str | None
cursor_param: str | None
limit_param: str | None
offset_param: str | None
page_size: int | None
max_pages: int | None
```

**Page:**
```python
items: list[Record]
next_cursor: str | int | None
has_next: bool
raw: Any | None
```

## Конфигурация

### SourceConfig

Pydantic-модель конфигурации источника данных.

**Файл:** `config/models.py`

```python
source: str                    # Имя источника
protocol: Literal["http"]     # Протокол (пока только http)
base_url: str                  # Базовый URL API
default_timeout: float | None  # Таймаут по умолчанию
auth: AuthConfig               # Настройки аутентификации
rate_limit: RateLimitConfig | None  # Ограничение частоты запросов
resources: dict[str, ResourceConfig]  # Ресурсы/маршруты
```

### ResourceConfig

Конфигурация конкретного ресурса/эндпоинта.

```python
path: str                      # Путь эндпоинта
method: Literal["GET", "POST", ...]  # HTTP-метод
query: QueryConfig             # Query-параметры
paging: PagingConfig           # Настройки пагинации
response: ResponseConfig        # Схема ответа
```

### Загрузчики конфигурации

**Файл:** `config/loader.py`

```python
def load_source_config(name: str, root: Path | None = None) -> SourceConfig
def load_all_sources(root: Path | None = None) -> dict[str, SourceConfig]
```

## Фабрика и реестр

### ClientFactory

Фабрика для создания клиентов по имени источника.

**Файл:** `factory.py`

```python
@dataclass
class ClientFactory:
    backend_factory: BackendFactory
    registry: MutableMapping[str, ClientBuilder]

    def create(self, source: str, *,
               config: SourceConfig | None = None,
               http_backend: HttpBackend | None = None) -> BaseClient
```

### ClientRegistry

Реестр для регистрации и создания клиентов.

**Файл:** `registry.py`

```python
@dataclass
class ClientRegistry:
    backend_factory: BackendFactory
    builders: MutableMapping[str, ClientBuilder]

    def register(self, source: str, builder: ClientBuilder) -> None
    def create(self, source: str, *,
               config: SourceConfig | None = None,
               http_backend: HttpBackend | None = None) -> BaseClient
```

## Исключения

**Файл:** `base/exceptions.py`

Иерархия исключений:
- `ProviderError` — базовое исключение для ошибок провайдера
- `PaginationError` — ошибки пагинации
- `ConfigurationError` — ошибки конфигурации
- Реэкспорт стандартных исключений `requests`: `RequestException`, `HTTPError`, `Timeout`, `ConnectionError`

## Примеры использования

### Базовое использование

```python
from bioetl.clients import ClientFactory, default_client_builder
from bioetl.clients.base import ClientRequest, RequestContext
from bioetl.clients.config import load_source_config

# Загрузка конфигурации
config = load_source_config("chembl")

# Создание фабрики (нужен backend_factory)
factory = ClientFactory(
    backend_factory=lambda cfg: my_http_backend,
    registry={"chembl": default_client_builder}
)

# Создание клиента
client = factory.create("chembl")

# Использование
request = ClientRequest(
    route="activity",
    filters={"target_chembl_id": "CHEMBL123"},
    context=RequestContext(source="chembl")
)

with client:
    record = client.fetch_one(request)
    for page in client.iter_pages(request):
        for item in page.items:
            print(item)
```

### Использование реестра

```python
from bioetl.clients.registry import get_registry

registry = get_registry(backend_factory=my_backend_factory)
client = registry.create("chembl")
```

### Кастомный клиент

```python
from bioetl.clients.factory import ConfiguredHttpClient
from bioetl.clients.base import BaseClient, ClientRequest
from bioetl.clients.config import load_source_config

class MyCustomClient(ConfiguredHttpClient):
    def __init__(self, backend, **kwargs):
        config = load_source_config("my_source")
        super().__init__(config=config, backend=backend)

    def fetch_one(self, request: ClientRequest):
        # Кастомная логика
        return super().fetch_one(request)
```

### Для тестирования

```python
# Использование мока бэкенда
mock_backend = MockHttpBackend(responses={...})
client = ChemblClient(backend=mock_backend)
```

## Связанные компоненты

- **HttpBackend**: протокол HTTP-транспорта
- **RequestBuilderABC**: построение запросов (`docs/01-ABC/17-request-builder-abc.md`)
- **PaginatorABC**: стратегия пагинации (`docs/01-ABC/12-paginator-abc.md`)
- **RateLimiterABC**: ограничение частоты запросов (`docs/01-ABC/16-rate-limiter-abc.md`)
- **RetryPolicyABC**: политика повторных попыток (`docs/01-ABC/19-retry-policy-abc.md`)
- **CacheABC**: кэширование ответов (`docs/01-ABC/01-cache-abc.md`)

## Related Documentation

- [REST YAML Migration](../clients/02-rest-yaml-migration.md)
- [SourceClientABC](../01-ABC/23-source-client-abc.md)
- [Clients Diagrams](../clients/19-clients-diagrams.md)
