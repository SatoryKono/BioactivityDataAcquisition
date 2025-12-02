# 00 Clients Overview

Обзор архитектуры клиентского слоя BioETL для работы с внешними источниками данных.

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

## Основные компоненты

### 1. Базовые абстракции (`base/`)

#### `BaseClient` (ABC)

Абстрактный базовый класс для всех клиентов данных.

**Файл:** `base/client_abc.py`

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

**Назначение:** Единый интерфейс для всех клиентов внешних источников данных.

#### `HttpBackend` (Protocol)

Протокол для HTTP-бэкенда, скрывающего детали транспорта.

**Файл:** `base/http_backend.py`

**Методы:**
```python
def fetch_one(*, source: SourceConfig, resource: ResourceConfig, 
              request: ClientRequest, context: RequestContext | None) -> Record | None

def iter_records(*, source: SourceConfig, resource: ResourceConfig,
                 request: ClientRequest, context: RequestContext | None) -> Iterator[Record]

def iter_pages(*, source: SourceConfig, resource: ResourceConfig,
               request: ClientRequest, context: RequestContext | None) -> Iterator[Page]

def metadata(*, source: SourceConfig) -> dict[str, object]

def close(self) -> None
```

**Назначение:** Абстракция HTTP-транспорта, позволяющая подменять реализацию (requests, httpx и т.д.).

#### `ClientRequest`

Нормализованный объект запроса.

**Файл:** `base/client_abc.py`

**Поля:**
```python
route: str                          # Имя ресурса/маршрута
ids: Sequence[str] | None          # Идентификаторы для выборки
filters: Mapping[str, object] | None  # Фильтры запроса
pagination: PaginationParams | None # Параметры пагинации
raw: Mapping[str, object] | None    # Дополнительные параметры
context: RequestContext | None      # Контекст запроса
```

#### `RequestContext`

Контекстная информация для запросов.

**Файл:** `base/client_abc.py`

**Поля:**
```python
source: str | None      # Имя источника
route: str | None       # Имя маршрута
trace_id: str | None    # Идентификатор трассировки
timeout_s: float | None # Таймаут запроса
extra: Mapping[str, object] | None  # Дополнительные данные
```

#### `Page` и `PaginationParams`

Утилиты для работы с пагинацией.

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

### 2. Конфигурация (`config/`)

#### `SourceConfig`

Pydantic-модель конфигурации источника данных.

**Файл:** `config/models.py`

**Основные поля:**
```python
source: str                    # Имя источника
protocol: Literal["http"]     # Протокол (пока только http)
base_url: str                  # Базовый URL API
default_timeout: float | None  # Таймаут по умолчанию
auth: AuthConfig               # Настройки аутентификации
rate_limit: RateLimitConfig | None  # Ограничение частоты запросов
resources: dict[str, ResourceConfig]  # Ресурсы/маршруты
```

#### `ResourceConfig`

Конфигурация конкретного ресурса/эндпоинта.

**Файл:** `config/models.py`

**Поля:**
```python
path: str                      # Путь эндпоинта
method: Literal["GET", "POST", ...]  # HTTP-метод
query: QueryConfig             # Query-параметры
paging: PagingConfig           # Настройки пагинации
response: ResponseConfig        # Схема ответа
```

#### Загрузчики конфигурации

**Файл:** `config/loader.py`

```python
def load_source_config(name: str, root: Path | None = None) -> SourceConfig
def load_all_sources(root: Path | None = None) -> dict[str, SourceConfig]
```

YAML-файлы хранятся в `config/yaml/` и загружаются автоматически.

### 3. Фабрика клиентов (`factory.py`)

#### `ClientFactory`

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

**Назначение:** Единая точка создания клиентов с поддержкой регистрации кастомных билдеров.

#### `ConfiguredHttpClient`

Базовая реализация клиента на основе YAML-конфигурации.

**Файл:** `factory.py`

**Особенности:**
- Автоматически загружает конфигурацию из YAML
- Делегирует выполнение запросов `HttpBackend`
- Поддерживает все методы `BaseClient`

### 4. Реестр клиентов (`registry.py`)

#### `ClientRegistry`

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

### 5. Конкретные клиенты

Каждый источник имеет свой модуль в `clients/<source>/`:

- **chembl/** — ChEMBL API клиент
- **pubchem/** — PubChem API клиент
- **pubmed/** — PubMed API клиент
- **openalex/** — OpenAlex API клиент
- **crossref/** — Crossref API клиент
- **semantic_scholar/** — Semantic Scholar API клиент
- **uniprot/** — UniProt API клиент

Каждый клиент наследуется от `ConfiguredHttpClient` и может добавлять специфичную логику.

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

## Связанная документация

- **02-rest-yaml-migration.md** — Детали миграции на YAML-конфигурации
- **19-clients-diagrams.md** — Инструкция по генерации диаграмм
- **ConfiguredHttpClient**: базовая реализация (см. `docs/02-pipelines/clients/21-configured-http-client.md`)

