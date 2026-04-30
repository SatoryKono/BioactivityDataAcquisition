______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Слой Composition (Композиция)

**Расположение:** `src/bioetl/composition/`

## 1. Назначение

Слой `Composition` (также известный как **Composition Root**) — это мозг системы сборки. Его единственная задача — соединить компоненты из разных слоев (`Domain`, `Application`, `Infrastructure`) в работающее приложение.

Согласно архитектурному решению ADR-005, этот код был вынесен в отдельный слой, чтобы избавить слои `Interfaces` и `Application` от ответственности за создание конкретных реализаций адаптеров.

**Ключевые характеристики:**

- **Глобальная осведомленность:** Единственный слой (наряду с `Interfaces`), который "знает" обо всех остальных слоях. Ему разрешено импортировать из `infrastructure`, `application` и `domain`.
- **Сборка зависимостей:** Здесь происходит внедрение зависимостей (Dependency Injection). Канонические first-party public seams проходят через `entrypoints.py`, `execution_api.py`, `registry_api.py`, `control_plane_api.py`, `health_api.py`, `maintenance_api.py`, `composite_api.py`, `observability_api.py`; `services_api.py` и `resources_api.py` остаются compatibility-only façades и не являются целевым import surface для нового first-party кода.
- **Конфигурация:** Потребляет уже загруженные и нормализованные конфигурации. Канонический owner для YAML I/O, merge и normalization находится в `bioetl.infrastructure.config`, а `composition` сохраняет только thin public access / compat seams (`load_pipeline_config()`, `load_composite_config()`) для стабильных runtime entrypoints.

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
│   ├── adr.py           # ADR-related CLI bootstrap
│   └── run_manifest.py  # Run-manifest inspection bootstrap
└── runtime/             # Runtime assembly
```

- `bootstrap_pipeline_runner()`: Каноническая точка входа для создания `PipelineRunner` в runtime-сценариях.
- `bootstrap_composite_runner()`: Каноническая точка входа для сборки `CompositePipelineRunner`.
- `bootstrap/runtime/composite.py`: Bootstrap для Composite Pipeline (ADR-026).

#### 2.1.1. `runtime/` — Runtime Assembly

**Core assembly:**

| Файл                                                                      | Назначение                                                           |
| ------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `assembly.py`                                                             | Pure assembly functions (vacuum, filter, runtime config)             |
| `pipeline.py`                                                             | Сборка pipeline (main entry point)                                   |
| `runner.py`                                                               | Сборка `PipelineRunner`                                              |
| `runner_assembly.py`                                                      | Runner assembly helpers                                              |
| `infrastructure/config/{pipeline_config_api.py, composite_config_api.py}` | Канонические public seams для загрузки и валидации YAML-конфигураций |
| `runtime_basics.py`                                                       | Базовые runtime утилиты                                              |

`composition.bootstrap.runtime` больше не владеет raw config-loading логикой:
runtime bootstrap использует канонические config-owner seams из
`bioetl.infrastructure.config`, а в `composition` остаются только тонкие
public access / compatibility wrappers там, где нужно удерживать стабильные
import paths.

**Composite pipeline bootstrap:**

| Файл                                     | Назначение                                    |
| ---------------------------------------- | --------------------------------------------- |
| `composite.py`                           | Bootstrap `CompositePipelineRunner` (ADR-026) |
| `composite_bootstrap_builders.py`        | Builders для composite компонентов            |
| `composite_filter_extraction_service.py` | Bootstrap filter extraction для composite     |
| `composite_support_helpers.py`           | Вспомогательные функции composite bootstrap   |
| `composite_support_service_builders.py`  | Builders для composite support services       |
| `composite_support_services_factory.py`  | Фабрика composite support services            |

**Observability bootstrap:**

| Файл                      | Назначение                              |
| ------------------------- | --------------------------------------- |
| `observability.py`        | Сборка полного observability bundle     |
| `observability_bundle.py` | ObservabilityBundle dataclass           |
| `logger_bootstrap.py`     | Bootstrap structured logger (structlog) |
| `metrics_bootstrap.py`    | Bootstrap metrics (Prometheus)          |
| `tracing_bootstrap.py`    | Bootstrap tracing (OpenTelemetry)       |

**Service bootstrap:**

| Файл                                   | Назначение                         |
| -------------------------------------- | ---------------------------------- |
| `dq_bootstrap.py`                      | Bootstrap Data Quality компонентов |
| `pipeline_runner_service_bootstrap.py` | Bootstrap `PipelineRunnerService`  |
| `runner_factory_builder_service.py`    | Builder для runner factory         |
| `classification_init.py`               | Инициализация error classification |

### 2.2. `factories/` — Фабрики компонентов

В v6.0+ логика создания компонентов централизована в специализированных фабриках, организованных в подпакеты:

**Расположение:** `src/bioetl/composition/factories/`

Ключевой класс этого слоя: `GenericPipelineFactory`. Он служит канонической декларативной factory для сборки pipeline instance и runner assembly через DI.

| Подпакет / Файл                     | Ключевые компоненты                             | Назначение                                                     |
| ----------------------------------- | ----------------------------------------------- | -------------------------------------------------------------- |
| `pipeline/assembler.py`             | `GenericPipelineFactory`                        | Универсальный конструктор пайплайнов (декларативно)            |
| `pipeline/registry.py`              | Реестр фабрик                                   | Все зарегистрированные pipeline factories                      |
| `pipeline/runner.py`                | `RunnerFactory`                                 | Создание `PipelineRunner` с DI                                 |
| `datasource/data_source_factory.py` | `DataSourceFactory`                             | Создает `DataSourcePort` для провайдера                        |
| `datasource/http_client.py`         | `HttpClientFactory`                             | Настроенные `UnifiedHTTPClient` с Rate Limits, Circuit Breaker |
| `storage/factory.py`                | `StorageFactory`                                | Сборка `StoragePort` (Bronze + Silver + Gold)                  |
| `storage/adapter.py`                | `StorageAdapter`                                | Создание отдельных storage адаптеров                           |
| `services/factory.py`               | `BaseServicesFactory`                           | Создание core сервисов                                         |
| `services/builder.py`               | `ServicesBuilder`                               | Создание `PipelineService` bundle                              |
| `services/port_factories.py`        | Port factory functions                          | Boundary-validated port creation                               |
| `dq/factory.py`                     | `DQServicesFactory`                             | Создание Data Quality компонентов                              |
| `transformer_factory.py`            | `register_transformer() / create_transformer()` | Создание трансформеров по провайдеру                           |

Часть модулей в `composition/factories/`, `composition/services/` и `composition/runtime_builders/`
сохраняет compatibility facade / shim роль ради стабильности import-paths во время рефакторинга.
Новый first-party код должен предпочитать canonical owners напрямую, а не добавлять новые multi-hop imports.
Курируемый список таких модулей, их status-модель и exit criteria ведутся в
[Compatibility Facade Inventory](07-compatibility-facade-inventory.md).

**Декомпозиция BasePublicationTransformer:**
Сборка `BasePublicationTransformer` теперь использует паттерн Стратегия вместо Template Method. При инстанцировании через `GenericPipelineFactory` могут быть внедрены `DataExtractorStrategy`, `IdentifierResolverStrategy` и `PublicationMetadataStrategy`, что устраняет проблему "God Object" и позволяет переиспользовать логику между провайдерами без наследования.

Начиная с `RF-014`, composition также остаётся канонической точкой сборки
`TransformerDependencyContext`: `NoOp` observability ports, `IdentityService`,
`DataNormalizationService` и `ContractPolicyPort` должны собираться здесь, а не
неявно внутри `BaseTransformer`.

**Root-level файлы и публичные seams:**

Также в корне `composition/` находятся:
`bootstrap_contexts.py`, `bootstrap_logger.py`, `builders.py`, `entrypoints.py`,
`execution_api.py`, `registry_api.py`, `control_plane_api.py`, `health_api.py`,
`maintenance_api.py`, `services_api.py`, `resources_api.py`, `composite_api.py`,
`observability_api.py`, `observability.py`, `registry.py`, `types.py`,
`_pipeline_execution.py`, `_resource_management.py`, `_services.py`.

Политика использования root-level composition seams:

- `entrypoints.py` — `public-entrypoint` и стабильный публичный composition seam.
- `execution_api.py`, `registry_api.py`, `control_plane_api.py`, `health_api.py`,
  `maintenance_api.py`, `composite_api.py`, `observability_api.py` — канонический
  first-party composition import surface для `src/`.
- `services_api.py`, `resources_api.py`, package root `bioetl.composition` и
  package root `bioetl.composition.bootstrap` — compatibility-only façades;
  они остаются стабильными для внешнего import/patch contract, но новые
  first-party `src/` imports туда не добавляются.
- `composite_api.py`, `observability_api.py` — узкие façade-модули для composite runtime
  и observability-related call sites; `observability_api.py` является каноническим
  public seam для metrics bootstrap, Pushgateway publication и operator diagnostics bundle.
  Metrics publication route проходит через `MetricsService` и composition-owned
  publisher adapter, а selection `NoOpMetrics` / `NoOpTracing` централизована в
  `observability_resolution.py`.
- `_pipeline_execution.py`, `_resource_management.py`, `_services.py` — internal implementation
  modules; прямые импорты вне `composition/` запрещены policy-тестами.

Текущий governance status для этих модулей фиксируется в
[Compatibility Facade Inventory](07-compatibility-facade-inventory.md).

**Дополнительные пакеты:**

| Пакет               | Ключевые модули                                                                                                             | Назначение                                                                           |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `providers/`        | `provider_registry.py`, `loader.py`, `registration.py`, `_default_registry.py`, `_loading.py`, `_registration_contracts.py` | Реестр провайдеров, canonical loader lifecycle и leaf registration/loading contracts |
| `services/`         | `__init__.py`, `versioning.py`                                                                                              | Тонкий re-export layer для `MetadataCoordinator` и versioning utilities              |
| `runtime_builders/` | `runner_builder.py`, `control_plane.py`, `observability_builder.py`, `inputs_resolver.py`                                   | Builders для runtime assembly, включая manifest/ledger attachment                    |

`runtime_builders/control_plane.py` собирает control-plane collaborators вокруг
runtime bootstrap: создаёт immutable manifest до assembly runner, при наличии
ledger связывает `PipelineRunner` и metadata writers с append-only lifecycle /
artifact events и прокидывает `manifest_id` в execution context.

### 2.3. ProviderRegistry и канонический data-source creator path

**Расположение:** `src/bioetl/composition/factories/datasource/` (`DataSourceFactory`, `get_data_source_creator`) и `src/bioetl/composition/providers/` (`ProviderRegistry`).

Централизованная регистрация всех провайдеров данных (8 провайдеров, включая `uniprot_idmapping`):

- **`ProviderRegistry`**: Thread-safe instance-scoped реестр provider metadata и creation callbacks. Class-level методы сохраняются как compatibility facade над shared default registry.
- **`ensure_providers_loaded()`**: Канонический lifecycle boundary для shared runtime/bootstrap registration state.
- **`get_data_source_creator()`**: Каноническая точка получения provider-bound creator callback для data source assembly.
- **`DataSourceFactory`**: Канонический façade для создания `DataSourcePort` через `ProviderRegistry`; local factory seams при необходимости принимают explicit `provider_registry`.

Legacy registry façade сохраняется только для explicit compatibility coverage.
Полная deprecation/inventory картина по этому compatibility surface и соседним compat-модулям описана в
[Compatibility Facade Inventory](07-compatibility-facade-inventory.md).

**Пример использования:**

```python
# Получение канонического data source creator
creator = get_data_source_creator("chembl")
data_source = creator(settings, config, logger)

# Или напрямую через DataSourceFactory
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
- **Декларативность:** `GenericPipelineFactory`, `PIPELINE_CONFIGS` и `factories/pipeline/registry.py` позволяют добавлять новые пайплайны без дублирования шаблонного assembly-кода.

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

______________________________________________________________________

## 4. Связанные Материалы

### Навигация по Слоям

| ← Предыдущий                               | Текущий         | Следующий → |
| ------------------------------------------ | --------------- | ----------- |
| [Interfaces Layer](04-interfaces-layer.md) | **Composition** | —           |

### Связанные Диаграммы

| Диаграмма               | Файл                                                                                     | Описание                           |
| ----------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------- |
| Composition Root        | [28-composition-root-di-graph.mmd](diagrams/foundation/28-composition-root-di-graph.mmd) | DI container, factories, bootstrap |
| Factory Pattern         | [38-runtime-assembly-sequence.mmd](diagrams/foundation/38-runtime-assembly-sequence.mmd) | Использование Factory паттерна     |
| Five Layer Architecture | [01-high-level.mmd](diagrams/foundation/01-high-level.mmd)                               | Composition слой в архитектуре     |
| Layers Interaction      | [05-layers-interaction.mmd](diagrams/foundation/05-layers-interaction.mmd)               | Bootstrap → Factories → Runner     |

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
