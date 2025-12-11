# План рефакторинга BioactivityDataAcquisition к принципам Hexagonal Architecture и DDD

**Версия:** 2.0
**Дата обновления:** 2025-12-11
**Текущий интегральный балл:** 7.1/10
**Целевой интегральный балл:** ≥7.5/10

---

## Обзор текущего состояния

### Архитектурные метрики

| Категория | Балл | Статус | Комментарий |
|-----------|------|--------|-------------|
| Слоистая архитектура | 8/10 | ✅ | 7 контрактов import-linter |
| Ports & Adapters | 7/10 | ⚠️ | 26 прямых импортов interfaces→infrastructure |
| Модульность | 7/10 | ✅ | Хорошее разделение |
| Доменная модель | 7/10 | ⚠️ | Pydantic в domain configs |
| Конфигурация | 6/10 | ⚠️ | Fallback политика размазана |
| Тестирование архитектуры | 8/10 | ✅ | 8 тестов, CI настроен |
| Обработка ошибок | 7/10 | ✅ | Domain errors defined |
| Документация | 8/10 | ✅ | Отлично |
| Наблюдаемость | 7/10 | ✅ | Порты реализованы |
| Технический долг | 6/10 | ⚠️ | Legacy convenience functions |

### Что уже полностью реализовано

| Компонент | Файл | Примечание |
|-----------|------|------------|
| **Слоёная архитектура** | `.importlinter` | 7 контрактов |
| **CI для архитектуры** | `.github/workflows/import-linter.yml` | 4 уровня проверки |
| **Composition Root** | `interfaces/composition_root.py` | 566 строк, lazy init |
| **ApplicationContext** | `interfaces/application_context.py` | Unified singleton |
| **Thread-safe Context** | `interfaces/context_manager.py` | contextvars, 135 строк |
| **Provider Registry Port** | `domain/provider_registry.py` | ABC + InMemory impl |
| **Schema Registry** | `domain/schemas/registry.py` | Lazy generation support |
| **Observability Ports** | `domain/observability/contracts.py` | Logger, Metrics, Tracing, Progress |
| **Value Objects** | `domain/value_objects/` | RunId, EntityName, ChemblId, etc. |
| **Pandera Schemas** | `infrastructure/validation/schemas/` | 7 entity schemas |
| **Архитектурные тесты** | `tests/architecture/` | 8 файлов тестов |

### Выявленные проблемы (требуют исправления)

| Проблема | Критичность | Файлы | План |
|----------|-------------|-------|------|
| interfaces → infrastructure импорты | 🔴 Высокая | 8 файлов, 26 импортов | REFACTORING_PLAN.md Фаза 1 |
| Pydantic в domain configs | 🟡 Средняя | 15+ классов | Task 7 (низкий приоритет) |
| Fallback политика размазана | 🟡 Средняя | 3 места | Task 9 |
| Legacy convenience functions | 🟢 Низкая | ~10 функций | Task 2 |

---

## Task 1. Enforce Layered Architecture and Import Rules

### Текущее состояние: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**Что сделано:**
- ✅ `.importlinter` с 7 контрактами
- ✅ CI pipeline в `.github/workflows/import-linter.yml`
- ✅ 8 архитектурных тестов в `tests/architecture/`
- ✅ AST-анализ в `test_layer_dependencies.py`
- ✅ Domain isolation в `test_domain_isolation.py`

**Текущие контракты:**
```ini
[contract:domain_purity]              # Domain не зависит от других слоёв
[contract:application_no_infrastructure]  # Application ≠ infrastructure
[contract:application_no_interfaces]      # Application ≠ interfaces
[contract:infrastructure_no_application]  # Infrastructure ≠ application
[contract:infrastructure_no_interfaces]   # Infrastructure ≠ interfaces
[contract:no_direct_impl_imports]         # No impl/ imports from app
[contract:interfaces_controls_wiring]     # Only interfaces does composition
```

### Оставшаяся работа: **НЕТ**

Задача полностью выполнена. Дополнительные контракты добавляются по мере необходимости.

---

## Task 2. Establish Composition Root (ApplicationContext)

### Текущее состояние: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**Что сделано:**
- ✅ `CompositionRoot` — единая точка сборки (566 строк)
- ✅ `ApplicationContext` — unified singleton с injection support
- ✅ `context_manager.py` — thread-safe/async-safe через contextvars
- ✅ Lazy initialization всех компонентов
- ✅ Factory injection для тестирования

**Архитектура:**
```
┌─────────────────────────────────────────┐
│ ApplicationContext (singleton)          │
│  - logger: LoggingPortABC               │
│  - metrics: MetricsPortABC              │
│  - config_loader: Protocol              │
│  - composition_root: CompositionRoot    │
│  - use_case_factory (property)          │
└─────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────┐
│ context_manager.py (contextvars)        │
│  get_current_context()                  │
│  application_context(ctx) [CM]          │
│  reset_current_context()                │
└─────────────────────────────────────────┘
```

### Оставшаяся работа: Deprecation warnings (низкий приоритет)

**Рекомендация:** Добавить deprecation для legacy функций в v3.0:
```python
def build_default_container(...):
    warnings.warn("Use get_application_context()...", DeprecationWarning)
```

---

## Task 3. Pipeline Orchestration vs. Factory Pattern

### Текущее состояние: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**Что сделано:**
- ✅ `PipelineOrchestrator` — facade для управления пайплайнами
- ✅ `PipelineFactory` pattern с registry в `application/pipelines/registry.py`
- ✅ Template Method в `PipelineBase` (`run()` → `extract()` → `transform()` → `validate()` → `write()`)
- ✅ `ProviderRegistryResolver` для разрешения провайдеров

**Паттерны:**
| Паттерн | Использование | Файл |
|---------|---------------|------|
| Factory | Создание pipelines | `pipelines/registry.py` |
| Template Method | Execution flow | `pipelines/base.py` |
| Facade | Orchestration | `orchestrator.py` |
| Resolver | Registry lookup | `provider_registry_resolver.py` |

### Оставшаяся работа: **НЕТ**

Задача полностью выполнена. Документация паттернов опциональна.

---

## Task 4. Manage DI Lifecycle and Reset

### Текущее состояние: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**Что сделано:**
- ✅ `contextvars` для thread-safe/async-safe scoping
- ✅ `application_context()` context manager
- ✅ `reset_current_context()` для сброса
- ✅ Scoped context поддерживает async tasks

**Пример использования:**
```python
# Thread-safe scoping для тестов
with application_context(mock_ctx):
    result = function_under_test()
# Контекст восстановлен

# Async-safe
async def process_request():
    ctx = get_current_context()  # Изолирован для каждой async task
```

### Оставшаяся работа: Request-scoped DI (низкий приоритет)

**Опционально:** Для REST API можно добавить middleware:
```python
# interfaces/rest/middleware.py
class RequestContextMiddleware:
    async def __call__(self, request, call_next):
        with application_context(create_request_context()):
            return await call_next(request)
```

---

## Task 5. Define Registry Port and Implementations

### Текущее состояние: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**Что сделано:**
- ✅ `ProviderRegistryABC` в `domain/provider_registry.py`
- ✅ `InMemoryProviderRegistry` в `infrastructure/provider_registry.py`
- ✅ `SchemaRegistry` в `domain/schemas/registry.py` (с lazy generation)
- ✅ Factory injection через `create_provider_registry_factory()`
- ✅ `ProviderRegistryLoader` для загрузки из YAML

**ABC контракты:**
```python
class ProviderRegistryABC(ABC):
    def register_provider(definition: ProviderDefinition) -> None
    def get_provider(provider_id: ProviderId) -> ProviderDefinition
    def list_providers() -> list[ProviderDefinition]
    def reset_provider_registry() -> None
    def restore_provider_registry(definitions) -> None
```

### Оставшаяся работа: **НЕТ**

---

## Task 6. Pandera/YAML Schema Generation

### Текущее состояние: 🟡 **ЧАСТИЧНО РЕАЛИЗОВАНО**

**Что сделано:**
- ✅ Pandera schemas в `infrastructure/validation/schemas/chembl/`
- ✅ `BaseGeneratedColumnsModel` с hash, index, timestamp
- ✅ `build_output_column_order()` helper
- ✅ Schema contracts в `configs/pipeline_contracts.yaml`
- ✅ `load_column_order_from_yaml()` в generator.py
- ⚠️ YAML export из Pandera schemas — не реализован

**Текущая структура:**
```
infrastructure/validation/schemas/
├── pandera_base.py          # BaseGeneratedColumnsModel
├── generator.py             # load_column_order_from_yaml()
├── adapter.py               # Schema adaptation
└── chembl/
    ├── activity.py          # ActivityTableSchema (224 строки)
    ├── assay.py             # AssayTableSchema
    ├── molecule.py          # MoleculeTableSchema
    ├── target.py            # TargetTableSchema
    ├── publication.py       # PublicationTableSchema
    ├── cell.py              # CellTableSchema
    └── tissue.py            # TissueTableSchema
```

### Оставшаяся работа: YAML export (низкий приоритет)

**Создать скрипт:**
```python
# scripts/generate_schema_yaml.py
def schema_to_yaml(schema_class) -> dict:
    return {
        "columns": {
            name: {"type": str(f.dtype), "nullable": f.nullable}
            for name, f in schema_class.to_schema().columns.items()
        }
    }
```

---

## Task 7. Domain Value Objects and Static Typing

### Текущее состояние: 🟡 **ЧАСТИЧНО РЕАЛИЗОВАНО**

**Что сделано:**
- ✅ Value Objects в `domain/value_objects/` — чистые классы с `__slots__`
- ✅ Валидация в конструкторе
- ✅ Immutability через `__setattr__` override
- ⚠️ Pydantic integration через `__get_pydantic_core_schema__`
- ⚠️ Domain configs используют `pydantic.BaseModel`

**Текущие Value Objects:**
```python
# domain/value_objects/identifiers.py
class RunId:
    __slots__ = ("_value",)
    _pattern = re.compile(r"^[0-9a-f]{8}-...")

    def __init__(self, value: str) -> None:
        if not self._pattern.match(value.lower()):
            raise ValueError(f"Invalid RunId: {value}")
        self._value = value.lower()

    # Pydantic hook (can be moved to infrastructure)
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.no_info_after_validator_function(...)
```

### Оставшаяся работа: Pydantic separation (очень низкий приоритет)

**Долгосрочная цель:** Вынести Pydantic hooks в infrastructure:
```
infrastructure/adapters/pydantic_adapters.py
```

**Примечание:** Текущий подход допустим, т.к.:
1. Value Objects не импортируют Pydantic напрямую (только pydantic_core)
2. Domain configs — это по сути DTOs, не core business logic
3. Рефакторинг потребует значительных усилий с минимальной отдачей

---

## Task 8. LoggingPort and MetricsPort Abstractions

### Текущее состояние: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**Что сделано:**
- ✅ `LoggingPortABC` с structured logging (`apply_bind`)
- ✅ `MetricsPortABC` с counters и histograms
- ✅ `TracingPortABC` (экспериментально)
- ✅ `ProgressReporterABC` для progress bars
- ✅ `DefaultObservabilityFactory` для создания

**Порты:**
```python
class LoggingPortABC(ABC):
    def info(self, msg: str, **ctx) -> None
    def error(self, msg: str, **ctx) -> None
    def debug(self, msg: str, **ctx) -> None
    def warning(self, msg: str, **ctx) -> None
    def apply_bind(self, **ctx) -> Self  # Structured context

class MetricsPortABC(ABC):
    def inc_counter(self, name: str, labels: dict) -> None
    def observe_histogram(self, name: str, value: float, labels: dict) -> None
    def update_stage_duration(*, pipeline, provider, entity, stage, outcome, duration_sec)
    def update_stage_total(*, pipeline, provider, entity, stage, outcome)
```

### Оставшаяся работа: ObservabilityContext aggregate (низкий приоритет)

**Опционально:** Добавить unified aggregate:
```python
@dataclass(frozen=True)
class ObservabilityContext:
    logger: LoggingPortABC
    metrics: MetricsPortABC
    tracer: TracingPortABC | None = None

    def with_context(self, **kwargs) -> "ObservabilityContext":
        return ObservabilityContext(
            logger=self.logger.apply_bind(**kwargs),
            metrics=self.metrics,
            tracer=self.tracer,
        )
```

---

## Task 9. Pipeline Contract Fallback: Config vs Domain

### Текущее состояние: 🟡 **ЧАСТИЧНО РЕАЛИЗОВАНО**

**Что сделано:**
- ✅ Schema contracts в `configs/pipeline_contracts.yaml`
- ✅ Default values в Pydantic models (`default_factory`)
- ⚠️ Hardcoded fallbacks в `domain/schemas/pipeline_contracts.py`
- ⚠️ HTTP fallbacks в `infrastructure/clients/chembl/impl/`

**Текущие места fallback:**
| Место | Тип | Пример |
|-------|-----|--------|
| `domain/configs/pipeline.py` | Field defaults | `batch_size: int = 25` |
| `configs/pipeline_contracts.yaml` | Schema contracts | column orders |
| `domain/schemas/pipeline_contracts.py` | Hardcoded fallback | PIPELINE_CONTRACTS dict |
| `infrastructure/clients/.../impl/` | HTTP fallbacks | retry strategies |

### Оставшаяся работа: Централизация (средний приоритет)

**Создать `domain/configs/defaults.py`:**
```python
class DomainDefaults:
    """Single source of truth for domain defaults."""
    BATCH_SIZE: int = 25
    MAX_RETRIES: int = 3
    HASH_ALGORITHM: str = "blake2b"
    HTTP_TIMEOUT: float = 30.0
```

**Создать документацию:** `docs/architecture/fallback_policy.md`

---

## Task 10. Validation and Architectural Test Controls

### Текущее состояние: ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО**

**Что сделано:**
- ✅ CI pipeline `.github/workflows/import-linter.yml`
- ✅ 8 архитектурных тестов (100% coverage критических правил)
- ✅ `lint-imports` в CI
- ✅ `pytest tests/architecture/` в CI
- ✅ Coverage requirements: 80% overall, 90% domain/application

**Архитектурные тесты:**
| Тест | Назначение | Строк |
|------|-----------|-------|
| `test_layer_dependencies.py` | AST-анализ импортов | ~100 |
| `test_domain_boundaries.py` | Запрет pandas/yaml в domain | ~50 |
| `test_domain_isolation.py` | Чистота domain | ~80 |
| `test_architecture_rules.py` | Общие правила | ~530 |
| `test_architecture_policies.py` | Policy enforcement | ~100 |
| `test_pandera_coverage.py` | Pandera schema coverage | ~50 |
| `test_naming_conventions.py` | Naming conventions | ~80 |
| `test_type_annotations.py` | Type annotation coverage | ~60 |

### Оставшаяся работа: **НЕТ**

---

## Связь с основным планом рефакторинга

### Критическая задача: Устранение 26 импортов

**Детальный план в:** `docs/REFACTORING_PLAN.md`

| Файл | Нарушений | Статус |
|------|-----------|--------|
| `interfaces/composition_root.py` | 10 | 🔴 TODO |
| `interfaces/bootstrap_factory.py` | 2 | 🔴 TODO |
| `interfaces/factories/infrastructure.py` | 4 | 🔴 TODO |
| `interfaces/factories/observability.py` | 2 | 🔴 TODO |
| `interfaces/cli/app.py` | 2 | 🔴 TODO |
| `interfaces/use_case_factory.py` | 2 | 🔴 TODO |
| `interfaces/application_context.py` | 1 | 🔴 TODO |
| `interfaces/monitoring/__init__.py` | 3 | 🔴 TODO |
| **Итого** | **26** | |

**Решение (из REFACTORING_PLAN.md):**
1. Создать порты в `application/ports/` (ConfigLoaderPort, InfrastructureFactoryPort, etc.)
2. Создать адаптеры в `infrastructure/adapters/`
3. Рефакторинг CompositionRoot для использования портов

---

## Приоритеты и дорожная карта

### Фаза 1: Критические (следующий спринт)

| Задача | Статус | Приоритет | Документ |
|--------|--------|-----------|----------|
| Устранение 26 импортов | 🔴 TODO | Критический | REFACTORING_PLAN.md |

### Фаза 2: Средние (2-3 спринта)

| Задача | Статус | Приоритет |
|--------|--------|-----------|
| Task 9: Centralized fallbacks | 🟡 Partial | Средний |
| Request-scoped DI | 🟡 Optional | Низкий |
| ObservabilityContext | 🟡 Optional | Низкий |

### Фаза 3: Опциональные (backlog)

| Задача | Статус | Приоритет |
|--------|--------|-----------|
| Task 6: YAML schema export | 🟡 Partial | Низкий |
| Task 7: Pydantic separation | 🔴 TODO | Очень низкий |
| Deprecation warnings | 🔴 TODO | Низкий |

---

## Критерии успеха

### Целевые метрики

| Метрика | Текущее | Целевое | Дельта |
|---------|---------|---------|--------|
| Интегральный балл | 7.1 | ≥7.5 | +0.4 |
| interfaces→infrastructure | 26 | 3* | -23 |
| Domain purity | 95% | 100% | +5% |
| Test coverage | 85% | ≥80% | ✅ |

*3 разрешённых импорта адаптеров в composition_root.py

### Definition of Done

- [ ] Import-linter: 0 нарушений
- [ ] Архитектурные тесты: все проходят
- [ ] CI: зелёный
- [ ] Code review: проведён
- [ ] Документация: обновлена

---

## Ссылки

### Внутренние документы
- `docs/REFACTORING_PLAN.md` — детальный план по 26 импортам (Фазы 1-4)
- `docs/PIPELINE_IMPLEMENTATION_GUIDE.md` — guide для разработчиков
- `docs/refactoring/config-dependency-map.md` — карта зависимостей

### Внешние ресурсы
- [Hexagonal Architecture - AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/hexagonal-architecture.html)
- [Import Linter](https://roman.pt/posts/python-architecture-linter/)
- [Composition Root](https://stackoverflow.com/questions/6277771/what-is-a-composition-root-in-the-context-of-dependency-injection)
- [Value Objects in Python](https://blog.szymonmiks.pl/p/value-objects-with-python/)
