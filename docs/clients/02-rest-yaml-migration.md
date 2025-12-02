# 02 REST YAML Migration

## Сводка

**Статус:** ✅ Миграция выполнена

- Все параметры REST-вызовов (base_url, пути, методы, заголовки, схема ответа, поля) вынесены в YAML per-source в `src/bioetl/clients/config/yaml/`
- Клиенты являются конфигурационными обёртками, читающими `SourceConfig` из YAML
- Общие pydantic-модели `SourceConfig`/`ResourceConfig`/`PagingConfig` и загрузчики YAML обеспечивают единообразие и раннюю валидацию
- Фабрика `ClientFactory` создаёт клиентов по имени источника, подключая общий `HttpBackend`; в коде клиентов нет захардкоженных URL или параметров

## Структура YAML-конфигов для REST

```yaml
source: chembl
protocol: http
base_url: "https://www.ebi.ac.uk/chembl/api/data"
default_timeout: 30.0
auth:
  type: none  # none | api_key | bearer | basic | custom
rate_limit:
  requests_per_minute: 60
resources:
  activity:
    path: "/activity"
    method: GET
    query:
      fixed:
        format: json
      allowed_params:
        - target_chembl_id
        - assay_chembl_id
    paging:
      type: page           # page | offset | cursor | link | none
      page_param: page
      page_size_param: page_size
      default_page_size: 1000
      max_page_size: 1000
    response:
      format: json         # json | xml
      record_path: activities
      fields:
        - name: activity_id
          path: activity_id
          type: int        # str | int | float | bool | any
      extra_metadata:
        - name: page
          path: page_info.page
          type: int
```

Ключевые поля:

- `source`, `protocol`, `base_url`, `default_timeout`, `auth`, `rate_limit` — общие настройки источника
- `resources` — словарь маршрутов: `path`, `method`, `headers`, `auth` (override), `query.fixed/allowed/rename`, `paging` с разными стратегиями, `response` с `record_path` и описанием полей
- Все маршруты, параметры и схема ответа описаны в YAML; код клиентов ничего не знает о конкретных эндпоинтах

## Python-модели конфигурации

- Пакет `bioetl.clients.config` содержит pydantic-модели (`SourceConfig`, `ResourceConfig`, `PagingConfig`, `ResponseConfig`, `FieldConfig`, `AuthConfig`, `RateLimitConfig`, `QueryConfig`) и загрузчики YAML (`load_source_config`, `load_all_sources`)
- Жёсткая валидация: `extra="forbid"`, обязательные поля для выбранной стратегии пагинации (например, `page_param` для `type=page`)
- Базовые значения по умолчанию: `protocol="http"`, `auth.type="none"`, `response.format="json"`, пустые заголовки/фиксированные параметры

Пример использования:

```python
from bioetl.clients.config import load_source_config

cfg = load_source_config("chembl")
print(cfg.resources["activity"].paging.page_size_param)  # -> "page_size"
```

## Фабрика REST-клиентов

- Модуль `bioetl.clients.factory` предоставляет `ClientFactory` и `ConfiguredHttpClient`
- Фабрика загружает `SourceConfig` из YAML (если не передан), получает/создаёт `HttpBackend` и строит `ConfiguredHttpClient`, который делегирует вызовы `fetch_one`/`iter_records`/`iter_pages` HTTP-бэкенду через `ResourceConfig`
- Через `ClientFactory.registry` можно зарегистрировать кастомный билдер для источника, не меняя сигнатуры контракта

## Что нельзя держать в клиентах

- Доменные нормализации, маппинг на модели, фильтрации и агрегации — выносятся в пайплайн/сервисы
- Константы эндпоинтов, заголовков, query/пагинации — только в YAML
- Логика ретраев/логирования/трассировки — реализуется на уровне общего `HttpBackend`

## Текущее состояние

Миграция на YAML-конфигурации **выполнена**. YAML-файлы находятся в `src/bioetl/clients/config/yaml/` и автоматически загружаются через `load_source_config()`.

**Расположение конфигураций:**

- YAML-файлы: `src/bioetl/clients/config/yaml/<source>.yml`
- Загрузчик: `bioetl.clients.config.loader.load_source_config()`
- Модели: `bioetl.clients.config.models.SourceConfig`

**Реализованные источники:**

- ChEMBL (`chembl.yml`)
- PubChem (`pubchem.yml`)
- PubMed (`pubmed.yml`)
- OpenAlex (`openalex.yml`)
- Crossref (`crossref.yml`)
- Semantic Scholar (`semantic_scholar.yml`)
- UniProt (`uniprot.yml`)

## Структура YAML-конфигураций

Все YAML-файлы находятся в `src/bioetl/clients/config/yaml/` и следуют единой схеме `SourceConfig`.

**Пример структуры файла:**

```yaml
source: chembl
protocol: http
base_url: "https://www.ebi.ac.uk/chembl/api/data"
default_timeout: 30.0
auth:
  type: none
rate_limit:
  requests_per_minute: 60
resources:
  activity:
    path: "/activity"
    method: GET
    query:
      fixed:
        format: json
      allowed_params:
        - target_chembl_id
        - assay_chembl_id
    paging:
      type: page
      page_param: page
      page_size_param: page_size
      default_page_size: 1000
      max_page_size: 1000
    response:
      format: json
      record_path: activities
```

**Доступные источники:**

| Источник | YAML-файл | Статус |
| --- | --- | --- |
| ChEMBL | `chembl.yml` | ✅ Реализовано |
| PubChem | `pubchem.yml` | ✅ Реализовано |
| PubMed | `pubmed.yml` | ✅ Реализовано |
| OpenAlex | `openalex.yml` | ✅ Реализовано |
| Crossref | `crossref.yml` | ✅ Реализовано |
| Semantic Scholar | `semantic_scholar.yml` | ✅ Реализовано |
| UniProt | `uniprot.yml` | ✅ Реализовано |

## Валидация и health-checks конфигураций

- Схемы YAML валидируются pydantic-моделями (`extra="forbid"`, обязательные поля для выбранной пагинации, запрет пустого `resources`)
- Автоматические проверки:
  - загрузка всех YAML через `load_all_sources` в CI для раннего обнаружения ошибок формата
  - проверка `method` ∈ {GET, POST, PUT, DELETE, PATCH}, `protocol` = http
  - проверка, что `record_path` и `fields.path` присутствуют в примере ответа (health-check скрипт выполняет тестовый запрос через общий `HttpBackend` в sandbox-окружении)
  - smoke-test: `create_client(<source>)` с тестовым backend выполняет один запрос и убеждается, что пагинация даёт ожидаемую схему `Page`/`Record` без нормализации

## Related Components

- **ConfiguredHttpClient**: базовая реализация клиента (см. `docs/02-pipelines/clients/03-configured-http-client.md`)
- **ClientFactory**: фабрика клиентов (см. `docs/clients/00-clients-overview.md`)
