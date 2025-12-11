# План рефакторинга архитектуры BioETL v6

**Дата создания:** 2025-12-11
**Базовый документ:** [REFACTORING_PLAN_v5.md](./REFACTORING_PLAN_v5.md)
**Интегральный балл архитектуры (текущий):** 6.42/10
**Целевой балл:** 8.0+
**Статус:** Планирование

---

## Оглавление

1. [Краткое резюме](#краткое-резюме)
2. [Текущее состояние архитектуры](#текущее-состояние-архитектуры)
3. [Выявленные проблемы по категориям](#выявленные-проблемы-по-категориям)
4. [Блокирующие задачи](#блокирующие-задачи)
5. [Крупные задачи](#крупные-задачи)
6. [Минорные задачи](#минорные-задачи)
7. [Метрики и проверки](#метрики-и-проверки)
8. [Риски и митигация](#риски-и-митигация)
9. [Ожидаемые результаты](#ожидаемые-результаты)

---

## Краткое резюме

Проект разделён на слои **domain**, **application**, **infrastructure** и **interfaces** согласно принципам Hexagonal Architecture и DDD. Однако имеются существенные отклонения от идеальной архитектуры:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ТЕКУЩИЕ ПРОБЛЕМЫ АРХИТЕКТУРЫ                     │
├─────────────────────────────────────────────────────────────────────┤
│  ⚠️  Глобальные синглтоны в interfaces (_context, _factory)         │
│  ⚠️  Прямые импорты infrastructure в application (orchestrator)     │
│  ⚠️  Обращение к приватным методам (._get_extract_callable)        │
│  ⚠️  Классовое состояние в infrastructure (MetricsServerManager)    │
│  ⚠️  Синглтон паттерн в model_registry (_RegistryHolder)           │
├─────────────────────────────────────────────────────────────────────┤
│  ✓  domain/provider_registry.py - чистые абстракции (OK)           │
│  ✓  infrastructure/validation/schemas/generator.py - правильное    │
│      расположение Pandera/YAML (OK)                                 │
└─────────────────────────────────────────────────────────────────────┘
```

**Ключевое наблюдение:** Анализ показал, что:
- `domain/provider_registry.py` уже содержит только абстракции (ABC, Protocol) — это корректно
- Файл `generator.py` с Pandera/YAML находится в `infrastructure/validation/schemas/`, не в domain — это правильное расположение

---

## Текущее состояние архитектуры

### Структура слоёв

```
src/bioetl/
├── domain/                  # Чистая бизнес-логика
│   ├── aggregates/          # DDD агрегаты
│   ├── clients/             # Абстрактные контракты
│   ├── observability/       # Контракты логирования/метрик
│   ├── output/              # Контракты вывода
│   ├── ports/               # Порты (интерфейсы)
│   ├── provider_registry.py # ✓ Только абстракции
│   ├── schemas/             # Доменные схемы
│   └── value_objects/       # Value Objects
│
├── application/             # Оркестрация и use cases
│   ├── orchestrator.py      # ⚠️ Импортирует infrastructure
│   ├── pipelines/           # Конвейеры обработки
│   ├── services/            # Сервисы приложения
│   └── use_cases/           # Use cases
│
├── infrastructure/          # Реализация портов
│   ├── chembl/
│   │   └── model_registry.py # ⚠️ Синглтон паттерн
│   ├── clients/             # HTTP клиенты
│   ├── observability/
│   │   └── server.py        # ⚠️ Классовое состояние
│   └── validation/
│       └── schemas/
│           └── generator.py # ✓ Pandera/YAML здесь корректно
│
└── interfaces/              # Композиция и точки входа
    ├── application_context.py  # ⚠️ Module-level singleton
    ├── composition_root.py     # ⚠️ Lazy-loaded state
    └── use_case_factory.py     # Зависит от синглтона
```

### Оценка архитектуры

| Категория | Вес | Текущая | Целевая |
|-----------|:---:|:-------:|:-------:|
| Слоистая архитектура | 0.12 | 7 | 8.5 |
| Ports & Adapters / DDD | 0.10 | 6 | 8 |
| Границы модулей | 0.10 | 6 | 8 |
| Качество доменной модели | 0.10 | 7 | 7.5 |
| Контракты и конфигурация | 0.08 | 6 | 7.5 |
| Обработка ошибок | 0.10 | 6 | 7 |
| Тестирование и QA | 0.10 | 6 | 8 |
| Валидация данных | 0.10 | 7 | 7.5 |
| Документация | 0.10 | 7 | 7.5 |
| Сопровождаемость | 0.10 | 6 | 8 |
| **Интегральный балл** | **1.00** | **6.42** | **8.0+** |

---

## Выявленные проблемы по категориям

### Категория 1: Нарушение слоистых зависимостей

| Файл | Проблема | Критичность |
|------|----------|:-----------:|
| `application/orchestrator.py:67` | Импорт `InMemoryProviderRegistry` из infrastructure | Высокая |
| `application/orchestrator.py:156-159` | Обращение к `pipeline._get_extract_callable()` | Высокая |

### Категория 2: Глобальное состояние в interfaces

| Файл | Проблема | Критичность |
|------|----------|:-----------:|
| `interfaces/application_context.py:35` | Глобальная переменная `_context` | Высокая |
| `interfaces/composition_root.py` | Lazy-loaded `_provider_registry` | Средняя |

### Категория 3: Глобальное состояние в infrastructure

| Файл | Проблема | Критичность |
|------|----------|:-----------:|
| `infrastructure/observability/server.py` | Классовое состояние `MetricsServerManager._started` | Средняя |
| `infrastructure/chembl/model_registry.py` | Синглтон `_RegistryHolder._instance` | Средняя |

---

## Блокирующие задачи

### Задача B1: Удаление fallback импорта infrastructure в orchestrator

**Цель:** Убрать прямой импорт `InMemoryProviderRegistry` из application слоя.

**Файлы:**
- `src/bioetl/application/orchestrator.py`
- `src/bioetl/interfaces/factories/provider_registry.py`
- `src/bioetl/interfaces/composition_root.py`

**Изменения:**

```python
# orchestrator.py — УДАЛИТЬ:
def _get_default_registry_factory() -> ProviderRegistryFactory:
    from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
    return InMemoryProviderRegistry

# orchestrator.py — ИЗМЕНИТЬ:
class PipelineOrchestrator:
    def __init__(
        self,
        ...
        provider_registry_factory: ProviderRegistryFactory,  # Обязательный!
    ) -> None:
        self._provider_registry_factory = provider_registry_factory
```

**Критерии готовности:**
- [ ] Функция `_get_default_registry_factory()` удалена из orchestrator.py
- [ ] `provider_registry_factory` — обязательный параметр
- [ ] В `application/` нет импортов `bioetl.infrastructure.*`
- [ ] Тесты обновлены на явную инъекцию

**Риски:** Поломка существующих вызовов orchestrator без явного DI.

---

### Задача B2: Публичный API для extract-only режима

**Цель:** Устранить обращения к приватным методам `_get_extract_callable` и `_normalize_extract_result`.

**Файлы:**
- `src/bioetl/application/pipelines/base.py`
- `src/bioetl/application/orchestrator.py`
- `src/bioetl/domain/models.py`

**Изменения:**

```python
# domain/models.py — ДОБАВИТЬ:
@dataclass(frozen=True)
class ExtractOnlyResult:
    """Result of extract-only pipeline execution."""
    total_rows: int
    total_chunks: int

# pipelines/base.py — ДОБАВИТЬ публичный метод:
class PipelineBase(ABC):
    def run_extract_only(self, **kwargs: Any) -> ExtractOnlyResult:
        """Execute only the extract stage and return statistics."""
        extract_callable = self._get_extract_callable()
        iterator = self._normalize_extract_result(extract_callable(**kwargs))

        total_rows = 0
        total_chunks = 0
        for chunk in iterator:
            if chunk is not None:
                total_rows += len(chunk)
                total_chunks += 1

        return ExtractOnlyResult(
            total_rows=total_rows,
            total_chunks=max(total_chunks, 1),
        )

# orchestrator.py — ИЗМЕНИТЬ:
if effective_type == PipelineType.EXTRACT_ONLY:
    context = self._build_simple_context()
    extract_result = pipeline.run_extract_only()  # Публичный API!
```

**Критерии готовности:**
- [ ] Метод `run_extract_only()` добавлен в `PipelineBase`
- [ ] `ExtractOnlyResult` добавлен в `domain/models.py`
- [ ] Удалены комментарии `noqa: SLF001` в orchestrator
- [ ] Новый метод покрыт тестами

---

## Крупные задачи

### Задача C1: Консолидация синглтонов в interfaces (ApplicationContext)

**Цель:** Объединить разрозненные синглтоны в единый контейнер с thread-safe управлением через `contextvars`.

**Файлы:**
- `src/bioetl/interfaces/application_context.py`
- `src/bioetl/interfaces/composition_root.py`
- `src/bioetl/interfaces/context_manager.py`

**Текущее состояние:**

```python
# application_context.py — ТЕКУЩЕЕ:
_context: ApplicationContext | None = None

def get_application_context() -> ApplicationContext:
    global _context
    if _context is None:
        _context = ApplicationContext.create_default()
    return _context
```

**Целевое состояние:**

```python
# application_context.py — ЦЕЛЕВОЕ:
from contextvars import ContextVar

_context_var: ContextVar[ApplicationContext | None] = ContextVar(
    "application_context", default=None
)

def get_application_context() -> ApplicationContext:
    """Get the current application context (thread-safe)."""
    ctx = _context_var.get()
    if ctx is None:
        ctx = ApplicationContext.create_default()
        _context_var.set(ctx)
    return ctx

@contextmanager
def application_context(ctx: ApplicationContext) -> Iterator[ApplicationContext]:
    """Context manager for temporary context override.

    Usage:
        with application_context(test_ctx):
            # code uses test_ctx
        # original context restored
    """
    token = _context_var.set(ctx)
    try:
        yield ctx
    finally:
        _context_var.reset(token)
```

**Критерии готовности:**
- [ ] Глобальная переменная `_context` заменена на `ContextVar`
- [ ] Добавлен контекстный менеджер `application_context()`
- [ ] CLI и REST обновлены для работы с новым API
- [ ] Тесты легко подменяют контекст через `application_context()`

---

### Задача C2: Усиление архитектурных тестов

**Цель:** Закрепить правила ARCHITECTURE.md автоматическими тестами.

**Файлы:**
- `tests/architecture/test_layer_dependencies.py`
- `tests/project_rules/test_no_global_state.py`

**Новые тесты:**

```python
# test_layer_dependencies.py — ДОБАВИТЬ:

def test_application_has_no_infrastructure_imports() -> None:
    """Verify application layer has no direct infrastructure imports."""
    violations: list[str] = []

    for file_path in sorted(APPLICATION_ROOT.rglob("*.py")):
        for reference in _collect_imports(file_path):
            if reference.module.startswith("bioetl.infrastructure"):
                violations.append(
                    f"{file_path}:{reference.lineno}: "
                    f"application must not import {reference.module}"
                )

    assert not violations, "\n".join(violations)


def test_no_cross_module_private_access() -> None:
    """Verify no module accesses private methods of other modules."""
    import re
    pattern = re.compile(r"(?<!self)(?<!cls)\._[a-z_]+\(")
    violations: list[str] = []

    for file_path in sorted(APPLICATION_ROOT.rglob("*.py")):
        content = file_path.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), 1):
            if pattern.search(line) and "self._" not in line and "cls._" not in line:
                violations.append(f"{file_path}:{line_no}: {line.strip()}")

    assert not violations, "\n".join(violations)
```

**Критерии готовности:**
- [ ] Тест `test_application_has_no_infrastructure_imports` добавлен и проходит
- [ ] Тест `test_no_cross_module_private_access` добавлен и проходит
- [ ] ruff правило SLF001 включено без исключений

---

### Задача C3: Устранение прямых импортов (import-linter)

**Цель:** Сократить количество исключений в `.importlinter` до ≤3.

**Текущее состояние .importlinter:**
- Правила определены, но есть неявные нарушения
- Необходимо добавить явные запреты

**План действий:**

1. **Выносить функциональность в доменные контракты:**
   ```python
   # domain/output/contracts.py — ДОБАВИТЬ:
   class OutputWriterABC(ABC):
       @abstractmethod
       def write(self, data: DataFrame, path: Path) -> None: ...

   # domain/observability/contracts.py — ДОБАВИТЬ:
   class MetricsHookABC(Protocol):
       def on_stage_complete(self, stage: str, duration: float) -> None: ...
   ```

2. **Перенести реализации в infrastructure:**
   - `UnifiedFileWriter` → реализует `OutputWriterABC`
   - `MetricsHook` → реализует `MetricsHookABC`

3. **Обновить пайплайны и orchestrator:**
   - Использовать интерфейсы вместо конкретных реализаций
   - Получать зависимости через DI

**Критерии готовности:**
- [ ] `lint-imports` проходит без ошибок
- [ ] Количество игнорируемых импортов ≤3
- [ ] Golden tests пайплайнов проходят

---

## Минорные задачи

### Задача M1: Очистка глобального состояния в infrastructure

**Цель:** Убрать глобальные переменные и классовое состояние.

#### M1.1: infrastructure/observability/server.py

```python
# ТЕКУЩЕЕ:
class MetricsServerManager:
    _started: bool = False  # Классовое состояние
    _lock: Lock = Lock()

# ЦЕЛЕВОЕ — использовать instance-level состояние:
class MetricsServerManager:
    def __init__(self) -> None:
        self._started: bool = False
        self._lock: Lock = Lock()

# Или через контекстный менеджер:
@contextmanager
def metrics_server(enabled: bool, port: int, address: str) -> Iterator[None]:
    """Context manager for metrics server lifecycle."""
    if enabled:
        start_http_server(port, addr=address)
    try:
        yield
    finally:
        # cleanup if needed
        pass
```

#### M1.2: infrastructure/chembl/model_registry.py

```python
# ТЕКУЩЕЕ:
class _RegistryHolder:
    _instance: ChemblEntityModelRegistry | None = None

# ЦЕЛЕВОЕ — lazy-инициализация через фабрику:
def create_chembl_model_registry() -> ChemblEntityModelRegistry:
    """Factory function for creating registry instance."""
    return ChemblEntityModelRegistry()

# Управление временем жизни — через composition root
```

**Критерии готовности:**
- [ ] `MetricsServerManager` не использует классовые переменные
- [ ] `_RegistryHolder` удалён, используется фабрика
- [ ] Тесты на изоляцию инфраструктуры проходят

---

### Задача M2: Обновление документации

**Файлы:**
- `docs/architecture/architecture.md`
- `docs/migration/v6.0-refactoring.md` (создать)

**Содержание:**
- Описание новой архитектуры
- Гайд по миграции для пользователей API
- Примеры использования нового DI

---

## Метрики и проверки

### Целевые метрики

| Метрика | Текущее | Целевое | Команда проверки |
|---------|:-------:|:-------:|------------------|
| Инфра-импорты в application | >0 | 0 | `grep -rn "bioetl.infrastructure" src/bioetl/application/` |
| Приватные методы cross-module | >0 | 0 | `grep -rn "\._[a-z_]*(" src/bioetl/application/ \| grep -v "self\._\|cls\._"` |
| `noqa: SLF001` в orchestrator | 2 | 0 | `grep -c "noqa: SLF001" src/bioetl/application/orchestrator.py` |
| Глобальные переменные в interfaces | 3 | 0 | `grep -rn "^_[a-z].*=" src/bioetl/interfaces/` |
| Глобальные переменные в infra | 2 | 0 | `grep -rn "^_[a-z].*=" src/bioetl/infrastructure/` |
| Архитектурные тесты | pass | pass | `pytest tests/architecture/ tests/project_rules/ -v` |
| Test coverage | ≥85% | ≥85% | `pytest --cov` |

### Команды проверки после каждого этапа

```bash
#!/bin/bash
# Скрипт проверки архитектуры

echo "=== Проверка инфра-импортов в application ==="
grep -rn "from bioetl.infrastructure" src/bioetl/application/ || echo "✓ OK"
grep -rn "import bioetl.infrastructure" src/bioetl/application/ || echo "✓ OK"

echo "=== Проверка приватных методов ==="
grep -rn "\._[a-z_]*(" src/bioetl/application/ | grep -v "self\._\|cls\._" || echo "✓ OK"

echo "=== Проверка noqa комментариев ==="
grep -rn "noqa: SLF001" src/bioetl/application/ || echo "✓ OK"

echo "=== Проверка глобальных переменных в interfaces ==="
grep -rn "^_[a-z].*: .*= " src/bioetl/interfaces/*.py || echo "✓ OK"

echo "=== Import linter ==="
lint-imports

echo "=== Архитектурные тесты ==="
pytest tests/architecture/ tests/project_rules/ -v --tb=short

echo "=== Полный тестовый прогон ==="
pytest --cov=bioetl --cov-fail-under=85
```

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|:-----------:|:-------:|-----------|
| Поломка существующих вызовов orchestrator | Высокая | Среднее | Deprecation warnings + обновление документации |
| Регрессии в пайплайнах | Средняя | Высокое | Golden tests + интеграционные тесты |
| Ложные срабатывания архитектурных тестов | Средняя | Низкое | Whitelist для допустимых случаев |
| Несовместимость CLI/REST | Средняя | Среднее | Обновить вместе с composition root |
| Thread-safety при переходе на ContextVar | Низкая | Среднее | Thorough testing в concurrent сценариях |

### Стратегия миграции

```
Фаза 1: Deprecation (1 релиз)
├── Добавить DeprecationWarning в fallback функции
├── Обновить документацию
└── Анонсировать изменения в CHANGELOG

Фаза 2: Параллельная поддержка (1 релиз)
├── Новый API работает
├── Старый API deprecated но работает
└── Миграционный гайд готов

Фаза 3: Удаление (следующий major релиз)
├── Удалить deprecated код
├── Сделать параметры обязательными
└── Финальное обновление документации
```

---

## Ожидаемые результаты

### Прогноз улучшения оценок

| Категория | Текущая | После v6 | Прирост |
|-----------|:-------:|:--------:|:-------:|
| Слоистая архитектура | 7 | 8.5 | +1.5 |
| Ports & Adapters / DDD | 6 | 8 | +2 |
| Границы модулей | 6 | 8 | +2 |
| Тестирование и QA | 6 | 8 | +2 |
| Сопровождаемость | 6 | 8 | +2 |

**Прогноз интегрального балла после v6:** **8.0+**

### Диаграмма целевой архитектуры

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INTERFACES                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ApplicationContext (ContextVar-based, thread-safe)         │   │
│  │  CompositionRoot (creates all dependencies via DI)          │   │
│  │  UseCaseFactory (receives context via DI)                   │   │
│  │  CLI / REST (use ApplicationContext)                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
├─────────────────────────────────────────────────────────────────────┤
│                        APPLICATION                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  PipelineOrchestrator (all deps injected, no fallbacks)     │   │
│  │  PipelineBase (public API: run_extract_only())              │   │
│  │  UseCases (operate on domain types and ports)               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│              Uses interfaces │ (ports/ABCs)                         │
│                              ▼                                       │
├─────────────────────────────────────────────────────────────────────┤
│                          DOMAIN                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ProviderRegistryABC, OutputWriterABC, MetricsHookABC       │   │
│  │  Models, Value Objects, Domain Services                      │   │
│  │  NO infrastructure dependencies, NO global state             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ▲                                       │
│              Implements      │ (ports/ABCs)                         │
├─────────────────────────────────────────────────────────────────────┤
│                      INFRASTRUCTURE                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  InMemoryProviderRegistry implements ProviderRegistryABC    │   │
│  │  UnifiedFileWriter implements OutputWriterABC               │   │
│  │  MetricsServerManager (instance-based, no class state)      │   │
│  │  ChemblModelRegistry (factory-based, no singleton)          │   │
│  │  Pandera schemas, HTTP clients, etc.                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## План выполнения

```
БЛОКИРУЮЩИЕ ЗАДАЧИ (ПРИОРИТЕТ 1)
════════════════════════════════════════════════════════════════

B1: Удаление fallback импорта в orchestrator
├── Этап B1.1: Удалить _get_default_registry_factory()
├── Этап B1.2: Сделать provider_registry_factory обязательным
├── Этап B1.3: Обновить CompositionRoot
└── Этап B1.4: Обновить тесты

B2: Публичный API для extract-only режима
├── Этап B2.1: Добавить ExtractOnlyResult в domain/models.py
├── Этап B2.2: Добавить run_extract_only() в PipelineBase
├── Этап B2.3: Обновить orchestrator
└── Этап B2.4: Покрыть тестами


КРУПНЫЕ ЗАДАЧИ (ПРИОРИТЕТ 2)
════════════════════════════════════════════════════════════════

C1: Консолидация синглтонов в interfaces
├── Этап C1.1: Заменить _context на ContextVar
├── Этап C1.2: Добавить контекстный менеджер
├── Этап C1.3: Обновить CLI/REST
└── Этап C1.4: Обновить тесты

C2: Усиление архитектурных тестов
├── Этап C2.1: Тест на инфра-импорты
├── Этап C2.2: Тест на приватные методы
└── Этап C2.3: Интеграция с ruff

C3: Устранение прямых импортов
├── Этап C3.1: Создать OutputWriterABC
├── Этап C3.2: Создать MetricsHookABC
├── Этап C3.3: Обновить пайплайны
└── Этап C3.4: Обновить .importlinter


МИНОРНЫЕ ЗАДАЧИ (ПРИОРИТЕТ 3)
════════════════════════════════════════════════════════════════

M1: Очистка глобального состояния в infrastructure
├── M1.1: Рефакторинг MetricsServerManager
└── M1.2: Рефакторинг model_registry

M2: Обновление документации
├── M2.1: Обновить architecture.md
└── M2.2: Создать migration guide
```

---

## Ссылки

- [REFACTORING_PLAN_v5.md](./REFACTORING_PLAN_v5.md)
- [architecture.md](./architecture.md)
- [.importlinter](../../.importlinter)
- [PipelineOrchestrator](../../src/bioetl/application/orchestrator.py)
- [PipelineBase](../../src/bioetl/application/pipelines/base.py)
- [ApplicationContext](../../src/bioetl/interfaces/application_context.py)
- [CompositionRoot](../../src/bioetl/interfaces/composition_root.py)
- [test_layer_dependencies.py](../../tests/architecture/test_layer_dependencies.py)
- [test_no_global_state.py](../../tests/project_rules/test_no_global_state.py)
