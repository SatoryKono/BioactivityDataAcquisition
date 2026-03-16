# Слой Composition (Композиция)

**Расположение:** `src/bioetl/composition/`

## 1. Назначение

Слой `Composition` (также известный как **Composition Root**) — это мозг системы сборки. Его единственная задача — соединить компоненты из разных слоев (`Domain`, `Application`, `Infrastructure`) в работающее приложение.

Согласно архитектурному решению ADR-005, этот код был вынесен в отдельный слой, чтобы избавить слои `Interfaces` и `Application` от ответственности за создание конкретных реализаций адаптеров.

**Ключевые характеристики:**

- **Глобальная осведомленность:** Единственный слой (наряду с `Interfaces`), который "знает" обо всех остальных слоях. Ему разрешено импортировать из `infrastructure`, `application` и `domain`.
- **Сборка зависимостей:** Здесь происходит внедрение зависимостей (Dependency Injection). Центральный класс — `GenericPipelineFactory`, обеспечивающий декларативное создание пайплайнов.
- **Конфигурация:** Преобразует сырые настройки из YAML или переменных окружения в доменные объекты конфигурации.

## 2. Ключевые Компоненты

### 2.1. `bootstrap/` — Процесс инициализации

**Расположение:** `src/bioetl/composition/bootstrap/`

Пакет содержит модули для высокоуровневой сборки основных сервисов:

```
composition/bootstrap/
├── assembly/            # Сборка компонентов (checkpoint, storage)
│   ├── checkpoint.py    # Checkpoint assembly
│   └── storage.py       # Storage assembly
├── cli/                 # CLI-специфичная сборка
│   ├── health.py        # Health check CLI bootstrap
│   ├── lock.py          # Lock CLI bootstrap
│   ├── config.py        # Config CLI bootstrap
│   ├── metrics.py       # Metrics CLI bootstrap
│   ├── noop.py          # NoOp implementations для CLI
│   ├── storage.py       # Storage CLI bootstrap
│   ├── checkpoint.py    # Checkpoint CLI bootstrap
│   └── adr.py           # ADR-related CLI bootstrap
└── runtime/             # Runtime assembly (23 модуля)
```

- `bootstrap_pipeline()`: Основная точка входа для создания полностью готового к работе экземпляра пайплайна. **Deprecated** — предпочтителен прямой вызов `runtime/pipeline.py`.
- `bootstrap/runtime/composite.py`: Bootstrap для Composite Pipeline (ADR-026).

#### 2.1.1. `runtime/` — Runtime Assembly (23 модуля)

**Core assembly:**

| Файл                 | Назначение                                                |
| -------------------- | --------------------------------------------------------- |
| `assembly.py`        | Pure assembly functions (vacuum, filter, runtime config)  |
| `pipeline.py`        | Сборка pipeline (main entry point)                        |
| `runner.py`          | Сборка `PipelineRunner`                                   |
| `runner_assembly.py` | Runner assembly helpers                                   |
| `config_loader.py`   | Загрузка и валидация YAML-конфигураций                    |
| `runtime_basics.py`  | Базовые runtime утилиты                                   |

**Composite pipeline bootstrap:**

| Файл                                   | Назначение                                        |
| --------------------------------------- | ------------------------------------------------- |
| `composite.py`                          | Bootstrap `CompositePipelineRunner` (ADR-026)     |
| `composite_bootstrap_builders.py`       | Builders для composite компонентов                |
| `composite_dq_loader.py`               | Загрузка DQ конфигурации для composite            |
| `composite_filter_extraction_service.py`| Bootstrap filter extraction для composite         |
| `composite_support_helpers.py`          | Вспомогательные функции composite bootstrap       |
| `composite_support_service_builders.py` | Builders для composite support services           |
| `composite_support_services_factory.py` | Фабрика composite support services               |

**Observability bootstrap:**

| Файл                    | Назначение                                       |
| ----------------------- | ------------------------------------------------ |
| `observability.py`      | Сборка полного observability bundle              |
| `observability_bundle.py`| ObservabilityBundle dataclass                   |
| `logger_bootstrap.py`   | Bootstrap structured logger (structlog)          |
| `metrics_bootstrap.py`  | Bootstrap metrics (Prometheus)                   |
| `tracing_bootstrap.py`  | Bootstrap tracing (OpenTelemetry)                |

**Service bootstrap:**

| Файл                                  | Назначение                                    |
| -------------------------------------- | --------------------------------------------- |
| `dq_bootstrap.py`                     | Bootstrap Data Quality компонентов            |
| `pipeline_runner_service_bootstrap.py` | Bootstrap `PipelineRunnerService`             |
| `runner_factory_builder_service.py`    | Builder для runner factory                    |
| `classification_init.py`              | Инициализация error classification            |

### 2.2. `factories/` — Фабрики компонентов

В v6.0+ логика создания компонентов централизована в специализированных фабриках, организованных в подпакеты:

**Расположение:** `src/bioetl/composition/factories/` (56 .py файлов в 5 подпакетах)

| Подпакет / Файл             | Ключевые компоненты                          | Назначение                                                     |
| --------------------------- | -------------------------------------------- | -------------------------------------------------------------- |
| `pipeline/assembler.py`     | `GenericPipelineFactory`                     | Универсальный конструктор пайплайнов (декларативно)            |
| `pipeline/pipeline_assembler.py` | Public entrypoint                        | Публичный entrypoint для pipeline assembly                     |
| `pipeline/registry.py`      | Реестр фабрик                                | Все зарегистрированные pipeline factories                      |
| `pipeline/runner.py`        | `RunnerFactory`                              | Создание `PipelineRunner` с DI                                 |
| `datasource/factory.py`     | `DataSourceFactory`                          | Создает `DataSourcePort` для провайдера                        |
| `datasource/http_client.py` | `HttpClientFactory`                          | Настроенные `UnifiedHTTPClient` с Rate Limits, Circuit Breaker |
| `storage/factory.py`        | `StorageFactory`                             | Сборка `StoragePort` (Bronze + Silver + Gold)                  |
| `storage/adapter.py`        | `StorageAdapter`                             | Создание отдельных storage адаптеров                           |
| `services/factory.py`       | `ServicesFactory`                            | Создание core сервисов                                         |
| `services/builder.py`       | `ServicesBuilder`                            | Создание `PipelineServices` bundle                             |
| `services/port_factories.py`| Port factory functions                       | Boundary-validated port creation                               |
| `dq/factory.py`             | `DQServicesFactory`                          | Создание Data Quality компонентов                              |
| `transformer_factory.py`    | `register_transformer() / create_transformer()` | Создание трансформеров по провайдеру                        |

Часть модулей в `composition/factories/`, `composition/services/` и `composition/runtime_builders/`
сохраняет compatibility facade / shim роль ради стабильности import-paths во время рефакторинга.
Курируемый список таких модулей, их status-модель и exit criteria ведутся в
[Compatibility Facade Inventory](07-compatibility-facade-inventory.md).

Начиная с `RF-014`, composition также остаётся канонической точкой сборки
`TransformerDependencyContext`: `NoOp` observability ports, `IdentityService`,
`DataNormalizationService` и `ContractPolicyPort` должны собираться здесь, а не
неявно внутри `BaseTransformer`.

**Root-level файлы:**

Также в корне `composition/` находятся: `bootstrap_contexts.py`, `bootstrap_logger.py`, `builders.py`, `entrypoints.py`, `observability.py`, `registry.py`, `types.py`, `_pipeline_execution.py`, `_resource_management.py`, `_services.py`.

**Дополнительные пакеты:**

| Пакет              | Ключевые модули                                         | Назначение                                           |
| ------------------ | ------------------------------------------------------- | ---------------------------------------------------- |
| `providers/`       | `provider_registry.py`, `loader.py`, `registration.py`, internal provider config builders | Реестр провайдеров, canonical loader lifecycle и internal registration helpers |
| `services/`        | `__init__.py`, `versioning.py` | Composition-level re-exports для metadata coordination и versioning utilities |
| `runtime_builders/`| `runner_builder.py`, `observability_builder.py`, `inputs_resolver.py` | Builders для runtime assembly                        |

### 2.3. ProviderRegistry и канонический data-source creator path

**Расположение:** `src/bioetl/composition/factories/datasource/` (`DataSourceFactory`, `get_data_source_creator`) и `src/bioetl/composition/providers/` (`ProviderRegistry`).

Централизованная регистрация всех провайдеров данных (8 провайдеров, включая `uniprot_idmapping`):

- **`ProviderRegistry`**: Главный реестр провайдеров. Хранит конфигурацию каждого провайдера (data source creator, transformer class, pipelines).
- **`get_data_source_creator()`**: Каноническая точка получения provider-bound creator callback для data source assembly.
- **`DataSourceFactory`**: Канонический façade для создания `DataSourcePort` через `ProviderRegistry`.

Legacy registry façade сохраняется только для explicit compatibility coverage.
Полная deprecation/inventory картина по этому compatibility surface и соседним compat-модулям описана в
[Compatibility Facade Inventory](07-compatibility-facade-inventory.md).

**Пример использования:**

```python
# Получение канонического data source creator
creator = get_data_source_creator("chembl")
data_source = creator(settings, config, logger)

# Или напрямую через DataSourceFactory / ProviderRegistry
data_source = DataSourceFactory.create("chembl", settings=settings, logger=logger)
```

**Зарегистрированные провайдеры (8 шт, включая uniprot_idmapping):**

| Provider          | Data Sources           | Pipelines                                                                                                                                                                                                  | Rate Limit   |
| ----------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| chembl            | ChemblAdapter          | activity, assay, assay-parameters, cell-line, compound-record, molecule, target, target-component, protein-class, publication, publication-similarity, publication-term, tissue, subcellular-fraction (14) | None         |
| pubchem           | PubChemAdapter         | compound                                                                                                                                                                                                   | 5 req/sec    |
| uniprot           | UniProtAdapter         | protein                                                                                                                                                                                                    | 100 req/sec  |
| uniprot_idmapping | IDMappingDataSource    | id-mapping                                                                                                                                                                                                 | —            |
| pubmed            | PubMedAdapter          | publications                                                                                                                                                                                               | 3 req/sec    |
| crossref          | CrossRefAdapter        | publication                                                                                                                                                                                                | Polite pool  |
| openalex          | OpenAlexAdapter        | publication                                                                                                                                                                                                | 10 req/sec   |
| semanticscholar   | SemanticScholarAdapter | publication                                                                                                                                                                                                | 100 req/5min |

### 2.4. `registry.py` — Реестр пайплайнов

Предоставляет механизмы для динамического поиска и регистрации пайплайнов. Это позволяет CLI находить доступные пайплайны по их именам (например, `chembl_activity`).

## 3. Принципы Работы

- **Composition Root:** Вся логика создания объектов должна находиться как можно ближе к точке входа в приложение. В BioETL это `src/bioetl/composition/`.
- **Dependency Injection (DI):** Объекты никогда не создают свои зависимости сами. Если пайплайну нужен доступ к базе данных, он запрашивает `StoragePort` в конструкторе, а фабрика из слоя Composition предоставляет ему конкретную реализацию.
- **Декларативность:** Использование `GenericPipelineFactory` позволяет добавлять новые пайплайны простым объявлением в `factories/pipeline/registry.py` без написания шаблонного кода сборки.

### 3.1. Composite Pipeline Bootstrap (ADR-026)

Для композитных пайплайнов доступна функция `bootstrap_composite_runner()`:

```python
from bioetl.composition.bootstrap.runtime.composite import bootstrap_composite_runner
from bioetl.domain.composite.config import CompositeConfig
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig

runner = bootstrap_composite_runner(
    config=CompositeConfig(...),
    runtime=CompositeRuntimeConfig(...),
)
# -> CompositePipelineRunner
```

См. [ADR-026: Composite Pipeline Pattern](decisions/ADR-026-composite-pipeline-pattern.md) для деталей.

----------------------------------------------------------------------

## 4. Связанные Материалы

### Навигация по Слоям

| ← Предыдущий                               | Текущий         | Следующий → |
| ------------------------------------------ | --------------- | ----------- |
| [Interfaces Layer](04-interfaces-layer.md) | **Composition** | —           |

### Связанные Диаграммы

| Диаграмма               | Файл                                                                                               | Описание                           |
| ----------------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------- |
| Composition Root        | [28-composition-root-di-graph.mermaid](mmd-diagrams/foundation/28-composition-root-di-graph.mmd)     | DI container, factories, bootstrap |
| Factory Pattern         | [38-runtime-assembly-sequence.mermaid](mmd-diagrams/foundation/38-runtime-assembly-sequence.mmd)            | Использование Factory паттерна     |
| Five Layer Architecture | [01-high-level.mermaid](mmd-diagrams/foundation/01-high-level.mmd)                                   | Composition слой в архитектуре     |
| Layers Interaction      | [05-layers-interaction.mermaid](mmd-diagrams/foundation/05-layers-interaction.mmd)                    | Bootstrap → Factories → Runner     |

### Связанные ADR

| ADR                                                          | Тема                         |
| ------------------------------------------------------------ | ---------------------------- |
| [ADR-005](decisions/ADR-005-composition-layer-separation.md) | Composition Layer Separation |
| [ADR-025](decisions/ADR-025-pipeline-config-unification.md)  | Pipeline Config Unification  |
| [ADR-026](decisions/ADR-026-composite-pipeline-pattern.md)   | Composite Pipeline Pattern   |

### Смежные Разделы Документации

- [Interfaces Layer](04-interfaces-layer.md) — CLI использует bootstrap
- [Application Layer](02-application-layer.md) — пайплайны, создаваемые фабриками
- [Infrastructure Layer](03-infrastructure-layer.md) — адаптеры, регистрируемые в ProviderRegistry
- [Compatibility Facade Inventory](07-compatibility-facade-inventory.md) — статус и план вывода compat-модулей
- [API Reference: Composition](../04-reference/api/composition.md) — API документация слоя
