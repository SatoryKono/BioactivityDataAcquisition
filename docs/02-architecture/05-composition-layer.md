# Слой Composition (Композиция)

**Расположение:** `src/bioetl/composition/`

## 1. Назначение

Слой `Composition` (также известный как **Composition Root**) — это мозг системы сборки. Его единственная задача — соединить компоненты из разных слоев (`Domain`, `Application`, `Infrastructure`) в работающее приложение. 

Согласно архитектурному решению ADR-005, этот код был вынесен в отдельный слой, чтобы избавить слои `Interfaces` и `Application` от ответственности за создание конкретных реализаций адаптеров.

**Ключевые характеристики:**
- **Глобальная осведомленность:** Единственный слой (наряду с `Interfaces`), который "знает" обо всех остальных слоях. Ему разрешено импортировать из `infrastructure`, `application` и `domain`.
- **Сборка зависимостей:** Здесь происходит внедрение зависимостей (Dependency Injection).
- **Конфигурация:** Преобразует сырые настройки из YAML или переменных окружения в доменные объекты конфигурации.

## 2. Ключевые Компоненты

### 2.1. `bootstrap/` — Процесс инициализации

**Расположение:** `src/bioetl/composition/bootstrap/`

Пакет содержит модули для высокоуровневой сборки основных сервисов:

```
composition/bootstrap/
├── assembly/            # Сборка компонентов (checkpoint, storage)
├── cli/                 # CLI-специфичная сборка (health, lock, config, metrics, noop)
└── runtime/             # Runtime assembly
    ├── assembly.py      # Главная сборка компонентов
    ├── composite.py     # Bootstrap для Composite Pipeline (ADR-026)
    ├── observability.py # Сборка observability
    ├── pipeline.py      # Сборка pipeline
    └── runner.py        # Сборка runner
```

- `bootstrap_pipeline()`: Основная точка входа для создания полностью готового к работе экземпляра пайплайна. **Deprecated** — предпочтителен прямой вызов `runtime/pipeline.py`.
- `bootstrap/runtime/composite.py`: Bootstrap для Composite Pipeline (ADR-026).

### 2.2. `factories/` — Фабрики компонентов

В v5.1+ логика создания компонентов централизована в специализированных фабриках:

**Расположение:** `src/bioetl/composition/factories/` (12 файлов)

| Файл | Фабрика | Назначение |
|------|---------|------------|
| `pipeline_factory.py` | `GenericPipelineFactory` | Универсальный конструктор пайплайнов (декларативно) |
| `pipeline_factories.py` | Реестр фабрик | Все зарегистрированные pipeline factories |
| `data_source_factory.py` | `DataSourceFactory` | Создает `DataSourcePort` для провайдера |
| `http_client_factory.py` | `HttpClientFactory` | Настроенные `UnifiedHTTPClient` с Rate Limits, Circuit Breaker |
| `storage_factory.py` | `StorageFactory` | Сборка `StoragePort` (Bronze + Silver + Gold) |
| `storage_adapter.py` | `StorageAdapterFactory` | Создание отдельных storage адаптеров |
| `storage.py` | Storage helpers | Вспомогательные функции для storage |
| `runner_factory.py` | `RunnerFactory` | Создание `PipelineRunner` с DI |
| `services_factory.py` | `ServicesFactory` | Создание `PipelineServices` bundle |
| `transformer_factory.py` | `TransformerFactory` | Создание трансформеров по провайдеру |
| `dq_factory.py` | `DQFactory` | Создание Data Quality компонентов |

### 2.3. `providers/` — Реестр провайдеров

**Расположение:** `src/bioetl/composition/providers/`

Централизованная регистрация всех провайдеров данных:

- **`ProviderRegistry`**: Главный реестр провайдеров. Хранит конфигурацию каждого провайдера (data source creator, transformer class, pipelines).
- **`DataSourceRegistry`**: Фасад для backward compatibility. Делегирует создание в `ProviderRegistry`.

**Пример использования:**
```python
# Получение data source creator
creator = DataSourceRegistry.get("chembl")
data_source = creator(settings, config, logger)

# Или напрямую через ProviderRegistry
data_source = ProviderRegistry.create_data_source(
    "chembl", settings, config, logger
)
```

**Зарегистрированные провайдеры (7 шт):**
| Provider | Data Sources | Pipelines | Rate Limit |
|----------|--------------|-----------|------------|
| chembl | ChemblAdapter | activity, assay, molecule, target, document, target_component (13) | None |
| pubchem | PubChemAdapter | compound | 5 req/sec |
| uniprot | UniProtAdapter | protein | 100 req/sec |
| pubmed | PubMedAdapter | publications | 3 req/sec |
| crossref | CrossRefAdapter | publication | Polite pool |
| openalex | OpenAlexAdapter | publication | 10 req/sec |
| semanticscholar | SemanticScholarAdapter | publication | 100 req/5min |

### 2.3. `registry.py` — Реестр пайплайнов

Предоставляет механизмы для динамического поиска и регистрации пайплайнов. Это позволяет CLI находить доступные пайплайны по их именам (например, `chembl_activity`).

## 3. Принципы Работы

- **Composition Root:** Вся логика создания объектов должна находиться как можно ближе к точке входа в приложение. В BioETL это `src/bioetl/composition/`.
- **Dependency Injection (DI):** Объекты никогда не создают свои зависимости сами. Если пайплайну нужен доступ к базе данных, он запрашивает `StoragePort` в конструкторе, а фабрика из слоя Composition предоставляет ему конкретную реализацию.
- **Декларативность:** Использование `GenericPipelineFactory` позволяет добавлять новые пайплайны простым объявлением в `pipeline_factories.py` без написания шаблонного кода сборки.

### 3.1. Composite Pipeline Bootstrap (ADR-026)

Для композитных пайплайнов доступна функция `bootstrap_composite_pipeline()`:

```python
from bioetl.composition.bootstrap.runtime.composite import bootstrap_composite_pipeline

runner = await bootstrap_composite_pipeline(
    "composite_publication",
    limit=1000,
)
result = await runner.run()
```

См. [ADR-026: Composite Pipeline Pattern](decisions/ADR-026-composite-pipeline-pattern.md) для деталей.

---

## 4. Связанные Материалы

### Навигация по Слоям

| ← Предыдущий | Текущий | Следующий → |
|--------------|---------|-------------|
| [Interfaces Layer](04-interfaces-layer.md) | **Composition** | — |

### Связанные Диаграммы

| Диаграмма | Файл | Описание |
|-----------|------|----------|
| Composition Root | [diagrams/mermaid/11_composition_root.mmd](diagrams/mermaid/11_composition_root.mmd) | DI container, factories, bootstrap |
| Factory Pattern | [diagrams/mermaid/20_factory_pattern_usage.mmd](diagrams/mermaid/20_factory_pattern_usage.mmd) | Использование Factory паттерна |
| Five Layer Architecture | [diagrams/mermaid/01_five_layer_architecture.mmd](diagrams/mermaid/01_five_layer_architecture.mmd) | Composition слой в архитектуре |
| Layers Interaction | [05-layers-interaction.mermaid](diagrams/05-layers-interaction.mermaid) | Bootstrap → Factories → Runner |

### Связанные ADR

| ADR | Тема |
|-----|------|
| [ADR-005](decisions/ADR-005-composition-layer-separation.md) | Composition Layer Separation |
| [ADR-025](decisions/ADR-025-pipeline-config-unification.md) | Pipeline Config Unification |
| [ADR-026](decisions/ADR-026-composite-pipeline-pattern.md) | Composite Pipeline Pattern |

### Смежные Разделы Документации

- [Interfaces Layer](04-interfaces-layer.md) — CLI использует bootstrap
- [Application Layer](02-application-layer.md) — пайплайны, создаваемые фабриками
- [Infrastructure Layer](03-infrastructure-layer.md) — адаптеры, регистрируемые в ProviderRegistry
- [API Reference: Composition](../04-reference/api/composition.md) — API документация слоя
