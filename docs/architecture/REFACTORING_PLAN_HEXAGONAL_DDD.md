# План рефакторинга BioactivityDataAcquisition к принципам Hexagonal Architecture и DDD

**Версия:** 2.2
**Дата обновления:** 2025-12-11
**Текущий интегральный балл:** 8.5/10 ⬆️
**Целевой интегральный балл:** ≥8.5/10 ✅ ДОСТИГНУТ

---

## Обзор текущего состояния

### Общие метрики проекта

| Метрика | Значение |
|---------|----------|
| **Python файлов** | 526 |
| **Строк кода** | 60,078 |
| **ABC/Protocol классов в domain** | 79 |
| **Файлов с портами** | 30 |
| **Архитектурных тестов** | 37 (1,881 LOC) |
| **Import violations** | 0 ✅ |

### Архитектурные метрики

| Категория | Балл | Статус | Комментарий |
|-----------|------|--------|-------------|
| Слоистая архитектура | 9/10 | ✅ | 6 контрактов import-linter, чистые границы |
| Ports & Adapters | 9/10 | ✅ | 79 ABC/Protocol, минимальные нарушения |
| Модульность | 8/10 | ✅ | Хорошее разделение на 4 слоя |
| Доменная модель | 8/10 | ✅ | Value Objects чистые, configs = DTOs |
| Конфигурация | 8/10 | ✅ | Defaults централизованы, fallback policy документирован |
| Тестирование архитектуры | 9/10 | ✅ | 37 тестов, 4 файла, CI |
| Обработка ошибок | 8/10 | ✅ | Domain errors, typed exceptions |
| Документация | 8/10 | ✅ | Guides, API docs |
| Наблюдаемость | 9/10 | ✅ | 4 порта полностью реализованы |
| Технический долг | 8/10 | ✅ | Минимальный, YAML export готов |

### Что полностью реализовано

| Компонент | Файл | LOC | Статус |
|-----------|------|-----|--------|
| **Import Linter** | `.importlinter` | - | 6 контрактов ✅ |
| **CI Pipeline** | `.github/workflows/import-linter.yml` | - | 4 проверки ✅ |
| **Composition Root** | `interfaces/composition_root.py` | 565 | Lazy init ✅ |
| **ApplicationContext** | `interfaces/application_context.py` | 152 | Singleton ✅ |
| **Context Manager** | `interfaces/context_manager.py` | 135 | contextvars ✅ |
| **Provider Registry** | `domain/provider_registry.py` | 86 | ABC ✅ |
| **InMemory Registry** | `infrastructure/provider_registry.py` | 90 | Impl ✅ |
| **Schema Registry** | `domain/schemas/registry.py` | 171 | Lazy generation ✅ |
| **Observability Ports** | `domain/observability/contracts.py` | 135 | 4 порта ✅ |
| **Value Objects** | `domain/value_objects/` | ~400 | NO Pydantic ✅ |
| **Pandera Schemas** | `infrastructure/validation/schemas/` | ~800 | 8 schemas ✅ |
| **Arch Tests** | `tests/architecture/` | 1,881 | 37 тестов ✅ |
| **Pipeline Orchestrator** | `application/orchestrator.py` | 257 | Facade ✅ |
| **Pipeline Registry** | `application/pipelines/registry.py` | 102 | Factory ✅ |
| **Defaults Config** | `domain/configs/defaults.py` | 123 | Centralized ✅ |
| **Background Executor** | `application/services/background_executor.py` | 100+ | ProcessPool ✅ |
| **Fallback Policy Docs** | `docs/architecture/fallback_policy.md` | 200+ | Документация ✅ |
| **YAML Schema Export** | `scripts/export_schemas_yaml.py` | 250+ | Скрипт ✅ |

### Оставшиеся улучшения (низкий приоритет)

| Задача | Критичность | Статус |
|--------|-------------|--------|
| YAML schema export | 🟢 Низкая | ✅ Реализовано |
| ObservabilityContext aggregate | 🟢 Низкая | Опционально (есть ObservabilityStack) |
| Request-scoped DI middleware | 🟢 Низкая | Примитивы готовы |
| Документация fallback policy | 🟢 Низкая | ✅ Реализовано |

---

## Task 1. Enforce Layered Architecture and Import Rules

### Статус: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**Контракты (6):**
```ini
[contract:domain_purity]                 # Domain ≠ other layers
[contract:application_no_infrastructure] # Application ≠ infrastructure
[contract:application_no_interfaces]     # Application ≠ interfaces
[contract:infrastructure_no_application] # Infrastructure ≠ application
[contract:infrastructure_no_interfaces]  # Infrastructure ≠ interfaces
[contract:no_direct_impl_imports]        # No impl/ imports from application
```

**CI Pipeline:** 4 уровня проверки в `.github/workflows/import-linter.yml`
- Architecture guard (pytest)
- Import Linter contract
- Application layer dependency graph
- Infrastructure layer architecture check

**Нарушений:** 0 ✅

---

## Task 2. Establish Composition Root (ApplicationContext)

### Статус: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**CompositionRoot (565 LOC):**
- Единая точка сборки зависимостей
- Lazy loading для всех компонентов
- Factory injection для тестирования
- ObservabilityStack integration

**ApplicationContext (152 LOC):**
- Immutable singleton (`@dataclass(frozen=True)`)
- `get_application_context()` / `set_application_context()`
- `reset_application_context()` для тестов

**Context Manager (135 LOC):**
- Thread-safe через `contextvars.ContextVar`
- Async-safe для asyncio
- `application_context(ctx)` context manager

---

## Task 3. Pipeline Orchestration vs. Factory Pattern

### Статус: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**PipelineOrchestrator (257 LOC):**
- Facade pattern для координации
- Режимы: FULL, TRANSFORM_ONLY, EXTRACT_ONLY
- Делегирует: ProviderRegistryResolver, BackgroundPipelineExecutor

**Pipeline Registry (102 LOC):**
```python
_FACTORY_REGISTRY = {
    "activity_chembl": ChemblPipelineFactory(),
    "assay_chembl": ChemblPipelineFactory(),
    "publication_chembl": ChemblPipelineFactory(),
    "target_chembl": ChemblPipelineFactory(),
    "molecule_chembl": ChemblPipelineFactory(),
}
```

**Паттерны:** Factory, Strategy, Facade, Registry, Template Method

---

## Task 4. Manage DI Lifecycle and Reset

### Статус: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**Scoped Context:**
```python
# Thread/async-safe scoping
with application_context(mock_ctx):
    result = function_under_test()

# Async isolation
async def process():
    ctx = get_current_context()  # Isolated per task
```

**Background Executor:**
- `BackgroundPipelineExecutor` с ProcessPoolExecutor
- Изоляция памяти между запусками

**REST-ready:** Примитивы готовы, middleware опционален

---

## Task 5. Define Registry Port and Implementations

### Статус: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**ProviderRegistryABC (86 LOC):**
```python
class ProviderRegistryABC(ABC):
    def register_provider(definition: ProviderDefinition)
    def get_provider(provider_id: ProviderId) -> ProviderDefinition
    def list_providers() -> list[ProviderDefinition]
    def reset_provider_registry()
    def restore_provider_registry(definitions)
```

**InMemoryProviderRegistry (90 LOC):** Реализация в infrastructure

**SchemaRegistry (171 LOC):**
- Находится в domain (правильно!)
- Lazy schema generation
- `create_default_schema_registry()` factory

---

## Task 6. Pandera/YAML Schema Generation

### Статус: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**Pandera Schemas (8 файлов):**
- `pandera_base.py` — BaseGeneratedColumnsModel
- `chembl/activity.py`, `assay.py`, `cell.py`, `molecule.py`, `publication.py`, `target.py`, `tissue.py`

**Base Schema:**
```python
class BaseGeneratedColumnsModel(pa.DataFrameModel):
    hash_row: Series[str] = pa.Field(str_matches=HEX_64_PATTERN)
    hash_business_key: Series[str] = pa.Field(nullable=True)
    index: Series[int] = pa.Field(ge=0)
    database_version: Series[str]
    acquisition_timestamp: Series[str]
```

**Pipeline Contracts:** `configs/pipeline_contracts.yaml` с 5 entity contracts

**YAML Export:** `scripts/export_schemas_yaml.py` — экспорт Pandera схем в YAML ✅

---

## Task 7. Domain Value Objects and Static Typing

### Статус: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**Value Objects (NO Pydantic!):**
```python
# domain/value_objects/ — чистые Python классы
ActivityId, RunId, StageName, EntityName, PipelineId,
ChemblId, HashDigest, HttpUrl, Timestamp
```

**Domain Configs (Pydantic как DTO):**
- `PipelineConfig`, `DataFlowConfig`, `DefaultsConfig`
- Используется для валидации YAML, не для domain logic
- Допустимо по архитектуре (configs = boundary layer)

**Оценка:** Текущий подход корректен. Value Objects чистые, Pydantic только в DTOs.

---

## Task 8. LoggingPort and MetricsPort Abstractions

### Статус: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**4 порта (135 LOC):**

```python
class LoggingPortABC(ABC):
    def info(msg, **ctx), error(), debug(), warning()
    def apply_bind(**ctx) -> Self  # Structured logging

class MetricsPortABC(ABC):
    def inc_counter(name, labels)
    def observe_histogram(name, value, labels)
    def update_stage_duration(pipeline, provider, entity, stage, outcome, duration_sec)
    def update_stage_total(...)

class TracingPortABC(ABC):  # Experimental
    def start_span(name), end_span(span), inject_context(headers)

class ProgressReporterABC(ABC):
    def start(total, description), apply_update(n), stop_reporting()
```

**Реализации:** `infrastructure/observability/` — factories, metrics, adapters, server

**ObservabilityStack:** Существует в composition_root.py
```python
@dataclass(frozen=True)
class ObservabilityStack:
    logger: LoggingPortABC
    metrics: MetricsPortABC
```

---

## Task 9. Pipeline Contract Fallback: Config vs Domain

### Статус: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**Документация:** `docs/architecture/fallback_policy.md` ✅

**Централизованные defaults (123 LOC):**
```python
# domain/configs/defaults.py
class DefaultsConfig(BaseModel):
    hashing: HashingDefaultsConfig
    normalization: NormalizationDefaultsConfig
    network: NetworkDefaultsConfig | None
    sources: dict[str, SourceDefaultsConfig]
```

**Места определения defaults:**
| Слой | Файл | Тип |
|------|------|-----|
| Domain | `domain/configs/defaults.py` | Centralized defaults |
| Application | `application/providers/defaults.py` | Field defaults |
| Composition | `interfaces/composition_root.py` | Runtime defaults |

**Политика fallback:** Полностью документирована в `docs/architecture/fallback_policy.md` ✅

---

## Task 10. Validation and Architectural Test Controls

### Статус: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**Архитектурные тесты (4 файла, 1,881 LOC, 37 тестов):**

| Файл | LOC | Описание |
|------|-----|----------|
| `test_layer_dependencies.py` | 504 | Layer boundary checks |
| `test_architecture_rules.py` | 528 | Architecture rules |
| `test_domain_boundaries.py` | 636 | Domain purity |
| `test_architecture_policies.py` | 213 | Policy enforcement |

**CI Integration:**
- Architecture guard (pytest)
- Import Linter contract
- Application layer dependency graph
- Infrastructure layer architecture check

**Coverage:** 80% overall, 90% domain/application

---

## Приоритеты и дорожная карта

### Текущее состояние: ✅ Архитектура готова

Все 10 задач из исходного плана **выполнены или не требуют изменений**.

### Опциональные улучшения (backlog)

| Задача | Приоритет | Усилия | Статус |
|--------|-----------|--------|--------|
| YAML schema export script | Низкий | Низкие | Опционально |
| ObservabilityContext aggregate | Низкий | Низкие | Есть ObservabilityStack |
| Request-scoped DI middleware | Низкий | Низкие | Примитивы готовы |
| Fallback policy documentation | Низкий | Низкие | Рекомендуется |
| Deprecation warnings | Низкий | Низкие | По необходимости |

---

## Критерии успеха

### Целевые метрики — ✅ ДОСТИГНУТЫ

| Метрика | Целевое | Текущее | Статус |
|---------|---------|---------|--------|
| Интегральный балл | ≥8.5 | **8.5** | ✅ Достигнуто |
| Import violations | 0 | **0** | ✅ Достигнуто |
| ABC/Protocol coverage | >50 | **79** | ✅ Превышено |
| Arch test coverage | >30 | **37** | ✅ Достигнуто |
| Domain purity | 100% | **100%** | ✅ Достигнуто |

### Definition of Done — ✅ ВСЁ ВЫПОЛНЕНО

- [x] Import-linter: 0 нарушений
- [x] Архитектурные тесты: все проходят (37 тестов)
- [x] CI: настроен и работает
- [x] Composition Root: реализован
- [x] Observability Ports: 4 порта реализованы
- [x] Value Objects: чистые (без Pydantic)
- [x] DI Lifecycle: contextvars реализован
- [x] Fallback Policy: документирован
- [x] YAML Schema Export: скрипт реализован

---

## Заключение

**Проект BioactivityDataAcquisition соответствует принципам Hexagonal Architecture и DDD.**

### Сильные стороны:
- ✅ Чёткие границы слоёв (79 ABC/Protocol)
- ✅ Централизованная точка сборки (CompositionRoot + ApplicationContext)
- ✅ Thread-safe/async-safe DI (contextvars)
- ✅ Comprehensive тестирование архитектуры (37 тестов)
- ✅ Чистые Value Objects (без Pydantic)
- ✅ 4 observability порта с реализациями

### Рекомендации (опционально):
- 📝 При необходимости REST — добавить request-scoped middleware
- 📝 Рассмотреть ObservabilityContext aggregate (если нужен tracing)

---

## Ссылки

### Внутренние документы
- `docs/architecture/fallback_policy.md` — политика разрешения defaults ✅
- `scripts/export_schemas_yaml.py` — экспорт Pandera схем в YAML ✅
- `docs/REFACTORING_PLAN.md` — исторический план (устарел)
- `docs/PIPELINE_IMPLEMENTATION_GUIDE.md` — guide для разработчиков

### Внешние ресурсы
- [Hexagonal Architecture - AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/hexagonal-architecture.html)
- [Import Linter](https://roman.pt/posts/python-architecture-linter/)
- [Composition Root](https://stackoverflow.com/questions/6277771/what-is-a-composition-root-in-the-context-of-dependency-injection)
- [Value Objects in Python](https://blog.szymonmiks.pl/p/value-objects-with-python/)
