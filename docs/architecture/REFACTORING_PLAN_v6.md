# План рефакторинга архитектуры BioETL v6

**Дата создания:** 2025-12-11
**Дата обновления:** 2025-12-11
**Базовый документ:** [REFACTORING_PLAN_v5.md](./REFACTORING_PLAN_v5.md)
**Интегральный балл архитектуры (текущий):** 7.2/10
**Целевой балл:** 8.0+
**Статус:** В процессе

---

## Оглавление

1. [Краткое резюме](#краткое-резюме)
2. [Текущее состояние — что уже сделано](#текущее-состояние--что-уже-сделано)
3. [Оставшиеся задачи](#оставшиеся-задачи)
4. [Детальный план задач](#детальный-план-задач)
5. [Метрики и проверки](#метрики-и-проверки)
6. [Риски и митигация](#риски-и-митигация)
7. [Ожидаемые результаты](#ожидаемые-результаты)

---

## Краткое резюме

Значительная часть запланированного рефакторинга **уже выполнена**. Архитектура проекта существенно улучшена:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    СТАТУС РЕФАКТОРИНГА                              │
├─────────────────────────────────────────────────────────────────────┤
│  ✅ ЗАВЕРШЕНО:                                                      │
│     • orchestrator.py — нет инфра-импортов, обязательный DI        │
│     • PipelineBase.run_extract_only() — публичный API              │
│     • Нет noqa: SLF001 комментариев в application                  │
│     • context_manager.py — ContextVar для thread-safe контекста    │
│     • domain/provider_registry.py — только абстракции (ABC)        │
│     • Pandera/YAML в infrastructure (правильное расположение)       │
│     • Архитектурные тесты на глобальное состояние                   │
├─────────────────────────────────────────────────────────────────────┤
│  ⚠️  ТРЕБУЕТ ВНИМАНИЯ:                                              │
│     • application_context.py — дублирование (module-level + ContextVar) │
│     • MetricsServerManager — классовое состояние                    │
│     • _RegistryHolder — синглтон паттерн                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Текущее состояние — что уже сделано

### ✅ B1: Удаление fallback импорта infrastructure в orchestrator — ЗАВЕРШЕНО

**Файл:** `src/bioetl/application/orchestrator.py`

**Было:**
```python
def _get_default_registry_factory() -> ProviderRegistryFactory:
    from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
    return InMemoryProviderRegistry
```

**Стало:**
```python
class PipelineOrchestrator:
    def __init__(
        self,
        ...
        provider_registry_factory: ProviderRegistryFactory,  # Обязательный!
    ) -> None:
        # Delegate registry management to ProviderRegistryResolver
        self._registry_resolver = ProviderRegistryResolver(
            provider_registry_factory=provider_registry_factory,
            ...
        )
```

**Проверка:**
```bash
grep -rn "from bioetl.infrastructure" src/bioetl/application/
# Результат: No matches found ✅
```

---

### ✅ B2: Публичный API для extract-only режима — ЗАВЕРШЕНО

**Файл:** `src/bioetl/application/pipelines/base.py:186`

```python
def run_extract_only(self, **kwargs: Any) -> ExtractOnlyResult:
    """Execute only the extract stage and return statistics.

    This method provides a clean public API for extract-only mode,
    encapsulating the internal extraction logic without exposing
    private methods.
    """
    extract_callable = self._get_extract_callable()
    iterator = self._normalize_extract_result(extract_callable(**kwargs))
    ...
```

**Использование в orchestrator:**
```python
def _run_extract_only(self, pipeline: PipelineBase, limit: int | None) -> RunResult:
    extract_result = pipeline.run_extract_only(limit=limit)  # ✅ Публичный API
```

**Проверка:**
```bash
grep -rn "noqa: SLF001" src/bioetl/application/
# Результат: No matches found ✅
```

---

### ✅ C2: Thread-safe контекст через ContextVar — ЧАСТИЧНО ЗАВЕРШЕНО

**Файл:** `src/bioetl/interfaces/context_manager.py`

```python
import contextvars

_current_context: contextvars.ContextVar[ApplicationContext | None] = (
    contextvars.ContextVar("bioetl_app_context", default=None)
)

@contextmanager
def application_context(ctx: ApplicationContext) -> Generator[ApplicationContext, None, None]:
    """Context manager for scoped application context."""
    token = _current_context.set(ctx)
    try:
        yield ctx
    finally:
        _current_context.reset(token)
```

**Примечание:** ContextVar API готов, но `application_context.py` всё ещё использует параллельный module-level синглтон `_context`.

---

### ✅ Архитектурные тесты — РЕАЛИЗОВАНЫ

**Файлы:**
- `tests/project_rules/test_no_global_state.py` — проверка отсутствия глобального состояния
- `tests/project_rules/test_layer_architecture.py` — проверка слоёв
- `tests/project_rules/test_domain_isolation.py` — изоляция домена

**Тесты проверяют:**
- Отсутствие `_PROVIDER_REGISTRY` в domain
- Отсутствие deprecated функций (`set_provider_registry`, `get_provider_registry`)
- Слоистые зависимости (domain не зависит от infrastructure)
- Отсутствие глобальных провайдеров в application

---

## Оставшиеся задачи

### Приоритет: Высокий

#### Задача R1: Унификация ApplicationContext (устранение дублирования)

**Проблема:** Существуют две параллельные системы управления контекстом:

1. `interfaces/application_context.py:109` — module-level singleton:
   ```python
   _context: ApplicationContext | None = None

   def get_application_context() -> ApplicationContext:
       global _context
       if _context is None:
           _context = ApplicationContext.create_default()
       return _context
   ```

2. `interfaces/context_manager.py:39` — ContextVar-based:
   ```python
   _current_context: contextvars.ContextVar[ApplicationContext | None] = (
       contextvars.ContextVar("bioetl_app_context", default=None)
   )
   ```

**Решение:** Мигрировать весь код на использование `context_manager.py` и удалить дублирующий синглтон из `application_context.py`.

**План:**

1. **Обновить `application_context.py`** — делегировать к `context_manager.py`:
   ```python
   # application_context.py — ЦЕЛЕВОЕ СОСТОЯНИЕ:
   from bioetl.interfaces.context_manager import (
       get_current_context,
       set_current_context,
       reset_current_context,
   )

   # Удалить _context и связанные функции
   # Или сделать их алиасами:
   def get_application_context() -> ApplicationContext:
       """Backward-compatible alias for get_current_context()."""
       return get_current_context()
   ```

2. **Найти и обновить все вызовы:**
   ```bash
   grep -rn "get_application_context\|set_application_context\|reset_application_context" src/
   ```

3. **Удалить module-level `_context`** после миграции.

**Критерии готовности:**
- [ ] `_context` удалён из `application_context.py`
- [ ] Все функции делегируют к `context_manager.py`
- [ ] CLI и REST работают корректно
- [ ] Тесты проходят

---

### Приоритет: Средний

#### Задача R2: Рефакторинг MetricsServerManager

**Файл:** `src/bioetl/infrastructure/observability/server.py`

**Текущее состояние:**
```python
class MetricsServerManager:
    _started: bool = False  # Классовое состояние
    _lock: Lock = Lock()    # Классовое состояние

    @classmethod
    def start(cls, *, enabled: bool, port: int, address: str) -> bool:
        with cls._lock:
            if cls._started:
                return False
            start_http_server(port, addr=address)
            cls._started = True
            return True
```

**Проблема:** Классовое состояние (`_started`, `_lock`) нарушает изоляцию тестов.

**Варианты решения:**

**Вариант A: Instance-based состояние (рекомендуется)**
```python
class MetricsServerManager:
    def __init__(self) -> None:
        self._started: bool = False
        self._lock: Lock = Lock()

    def start(self, *, enabled: bool, port: int, address: str) -> bool:
        with self._lock:
            if self._started:
                return False
            start_http_server(port, addr=address)
            self._started = True
            return True

# Фабрика для CompositionRoot
def create_metrics_server_manager() -> MetricsServerManager:
    return MetricsServerManager()
```

**Вариант B: Context manager**
```python
@contextmanager
def metrics_server(enabled: bool, port: int, address: str) -> Iterator[None]:
    if enabled:
        start_http_server(port, addr=address)
    try:
        yield
    finally:
        pass  # Prometheus client не поддерживает остановку
```

**Критерии готовности:**
- [ ] Классовые переменные `_started` и `_lock` заменены на instance-level
- [ ] CompositionRoot управляет жизненным циклом
- [ ] Тесты изолированы

---

#### Задача R3: Рефакторинг _RegistryHolder (model_registry)

**Файл:** `src/bioetl/infrastructure/chembl/model_registry.py`

**Текущее состояние:**
```python
class _RegistryHolder:
    _instance: ChemblEntityModelRegistry | None = None

    @classmethod
    def get_or_create(cls) -> ChemblEntityModelRegistry:
        if cls._instance is None:
            cls._instance = ChemblEntityModelRegistry()
        return cls._instance

def get_chembl_model_registry() -> ChemblEntityModelRegistry:
    return _RegistryHolder.get_or_create()
```

**Проблема:** Синглтон на уровне класса затрудняет тестирование.

**Решение: Factory-based подход**
```python
# Удалить _RegistryHolder полностью

def create_chembl_model_registry() -> ChemblEntityModelRegistry:
    """Factory function for creating registry instance."""
    return ChemblEntityModelRegistry()

# Для обратной совместимости (deprecated):
def get_chembl_model_registry() -> ChemblEntityModelRegistry:
    """Get a new registry instance.

    .. deprecated::
        Use create_chembl_model_registry() or inject via DI.
    """
    import warnings
    warnings.warn(
        "get_chembl_model_registry() is deprecated. "
        "Use create_chembl_model_registry() or inject via CompositionRoot.",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_chembl_model_registry()
```

**Критерии готовности:**
- [ ] `_RegistryHolder` удалён
- [ ] `create_chembl_model_registry()` добавлен
- [ ] `get_chembl_model_registry()` помечен как deprecated
- [ ] Все вызовы обновлены на factory или DI

---

### Приоритет: Низкий

#### Задача R4: Усиление архитектурных тестов

**Добавить тесты:**

1. **Тест на классовое состояние в infrastructure:**
   ```python
   def test_no_class_level_mutable_state_in_infrastructure(bioetl_root: Path) -> None:
       """Verify infrastructure classes don't use class-level mutable state."""
       violations = []
       for py_file in iter_python_files(bioetl_root / "infrastructure"):
           tree = ast.parse(py_file.read_text())
           for node in ast.walk(tree):
               if isinstance(node, ast.ClassDef):
                   for item in node.body:
                       if isinstance(item, ast.AnnAssign):
                           # Проверить на мутабельное классовое состояние
                           pass
       assert not violations
   ```

2. **Тест на единственность контекста:**
   ```python
   def test_single_context_source(bioetl_root: Path) -> None:
       """Verify only one context management mechanism exists."""
       context_files = list((bioetl_root / "interfaces").glob("*context*.py"))
       # Проверить что нет дублирования
   ```

---

## Метрики и проверки

### Текущее состояние метрик

| Метрика | Было | Сейчас | Целевое |
|---------|:----:|:------:|:-------:|
| Инфра-импорты в application | >0 | **0** ✅ | 0 |
| `noqa: SLF001` в orchestrator | 2 | **0** ✅ | 0 |
| Module-level `_context` в interfaces | 1 | 1 | **0** |
| Классовое состояние в infra | 2 | 2 | **0** |
| Синглтоны в infra | 1 | 1 | **0** |
| Архитектурные тесты | pass | **pass** ✅ | pass |

### Команды проверки

```bash
#!/bin/bash
# Скрипт проверки архитектуры

echo "=== [ЗАВЕРШЕНО] Проверка инфра-импортов в application ==="
grep -rn "from bioetl.infrastructure" src/bioetl/application/ || echo "✅ OK"

echo "=== [ЗАВЕРШЕНО] Проверка noqa: SLF001 ==="
grep -rn "noqa: SLF001" src/bioetl/application/ || echo "✅ OK"

echo "=== [ТРЕБУЕТСЯ] Проверка module-level синглтонов в interfaces ==="
grep -rn "^_[a-z].*: .*= " src/bioetl/interfaces/*.py

echo "=== [ТРЕБУЕТСЯ] Проверка классового состояния в infrastructure ==="
grep -rn "_started.*=\|_instance.*=\|_lock.*=" src/bioetl/infrastructure/

echo "=== Архитектурные тесты ==="
pytest tests/project_rules/ tests/architecture/ -v --tb=short
```

---

## Диаграмма текущей и целевой архитектуры

### Текущее состояние

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INTERFACES                                   │
│  ┌───────────────────┐  ┌────────────────────────┐                  │
│  │ application_      │  │ context_manager.py     │                  │
│  │ context.py        │  │ ✅ ContextVar-based    │                  │
│  │ ⚠️ _context       │  │                        │                  │
│  │ (module-level)    │  │ get_current_context()  │                  │
│  └───────────────────┘  └────────────────────────┘                  │
│         ↓ дублирование ↑                                             │
├─────────────────────────────────────────────────────────────────────┤
│                        APPLICATION                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ✅ PipelineOrchestrator (all deps injected, no fallbacks)  │   │
│  │  ✅ PipelineBase (public API: run_extract_only())           │   │
│  │  ✅ Нет импортов из infrastructure                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                      INFRASTRUCTURE                                  │
│  ┌────────────────────────┐  ┌─────────────────────────┐            │
│  │ observability/server   │  │ chembl/model_registry   │            │
│  │ ⚠️ MetricsServerManager│  │ ⚠️ _RegistryHolder      │            │
│  │    _started (class)    │  │    _instance (class)    │            │
│  └────────────────────────┘  └─────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────┘
```

### Целевое состояние

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INTERFACES                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ApplicationContext (delegates to context_manager)          │   │
│  │  context_manager.py (single source: ContextVar)             │   │
│  │  CompositionRoot (creates all dependencies via DI)          │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                        APPLICATION                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ✅ PipelineOrchestrator (all deps injected)                │   │
│  │  ✅ PipelineBase (public API only)                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                      INFRASTRUCTURE                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  MetricsServerManager (instance-based state)                │   │
│  │  ChemblEntityModelRegistry (factory-based, no singleton)    │   │
│  │  Все состояние управляется через DI                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## План выполнения

```
ОСТАВШИЕСЯ ЗАДАЧИ
════════════════════════════════════════════════════════════════

R1: Унификация ApplicationContext                        [ВЫСОКИЙ]
├── Обновить application_context.py → делегация к context_manager
├── Найти и обновить все вызовы get_application_context()
├── Удалить module-level _context
└── Обновить тесты

R2: Рефакторинг MetricsServerManager                    [СРЕДНИЙ]
├── Заменить классовые переменные на instance-level
├── Добавить фабрику create_metrics_server_manager()
└── Обновить CompositionRoot

R3: Рефакторинг _RegistryHolder                         [СРЕДНИЙ]
├── Удалить _RegistryHolder
├── Добавить create_chembl_model_registry()
├── Пометить get_chembl_model_registry() как deprecated
└── Обновить все вызовы

R4: Усиление архитектурных тестов                       [НИЗКИЙ]
├── Тест на классовое состояние
└── Тест на единственность контекста
```

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|:-----------:|:-------:|-----------|
| Поломка CLI/REST при миграции контекста | Средняя | Высокое | Постепенная миграция с aliasing |
| Изменение поведения MetricsServer | Низкая | Среднее | Сохранить семантику one-per-process |
| Регрессии в тестах | Средняя | Низкое | Запуск полного тестового suite |

---

## Ожидаемые результаты

### Прогноз улучшения оценок

| Категория | До рефакторинга | Сейчас | После R1-R4 |
|-----------|:---------------:|:------:|:-----------:|
| Слоистая архитектура | 7 | **7.5** | 8.5 |
| Ports & Adapters / DDD | 6 | **7** | 8 |
| Границы модулей | 6 | **7.5** | 8 |
| Тестирование и QA | 6 | **7** | 8 |
| Сопровождаемость | 6 | **7** | 8 |

**Прогноз интегрального балла:**
- Текущий: **7.2/10**
- После R1-R4: **8.0+/10**

---

## Ссылки

- [REFACTORING_PLAN_v5.md](./REFACTORING_PLAN_v5.md)
- [orchestrator.py](../../src/bioetl/application/orchestrator.py)
- [base.py](../../src/bioetl/application/pipelines/base.py)
- [application_context.py](../../src/bioetl/interfaces/application_context.py)
- [context_manager.py](../../src/bioetl/interfaces/context_manager.py)
- [server.py](../../src/bioetl/infrastructure/observability/server.py)
- [model_registry.py](../../src/bioetl/infrastructure/chembl/model_registry.py)
- [test_no_global_state.py](../../tests/project_rules/test_no_global_state.py)
- [test_layer_architecture.py](../../tests/project_rules/test_layer_architecture.py)
