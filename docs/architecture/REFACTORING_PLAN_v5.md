# План рефакторинга архитектуры BioETL v5

**Дата создания:** 2025-12-11
**Базовый документ:** [REFACTORING_PLAN_v4.md](./REFACTORING_PLAN_v4.md)
**Интегральный балл архитектуры (текущий):** 6.42/10
**Целевой балл:** 7.5–7.8
**Статус:** Планирование

---

## Оглавление

1. [Краткое резюме](#краткое-резюме)
2. [Текущая архитектурная оценка](#текущая-архитектурная-оценка)
3. [Выявленные проблемы](#выявленные-проблемы)
4. [Приоритет 1: Жёсткое разделение application и infrastructure](#приоритет-1-жёсткое-разделение-application-и-infrastructure)
5. [Приоритет 2: Публичный API для extract-only режима](#приоритет-2-публичный-api-для-extract-only-режима)
6. [Приоритет 3: Усиление архитектурных тестов](#приоритет-3-усиление-архитектурных-тестов)
7. [Дополнительные задачи из v4](#дополнительные-задачи-из-v4)
8. [Метрики и тесты](#метрики-и-тесты)
9. [План выполнения](#план-выполнения)
10. [Ожидаемые результаты](#ожидаемые-результаты)

---

## Краткое резюме

Архитектура проекта находится в **среднем состоянии** (6.42/10): принципы заданы и частично соблюдаются, но есть заметные расхождения и точки роста.

**Ключевые проблемы:**

1. **Прямой импорт инфраструктуры в application** — `PipelineOrchestrator` импортирует `InMemoryProviderRegistry` через fallback, нарушая правило из ARCHITECTURE.md
2. **Обращение к приватным методам** — orchestrator использует `_get_extract_callable()` и `_normalize_extract_result()` из `PipelineBase`, ломая инкапсуляцию
3. **Недостаточные архитектурные проверки** — тесты проверяют только `impl` импорты, но не все инфраструктурные зависимости

```
┌─────────────────────────────────────────────────────────────┐
│                       v5 Roadmap                            │
├─────────────────────────────────────────────────────────────┤
│  [ПРИОРИТЕТ 1] DI-only для InMemoryProviderRegistry         │
│  [ПРИОРИТЕТ 2] Публичный API extract-only в PipelineBase    │
│  [ПРИОРИТЕТ 3] Усиление архитектурных тестов                │
├─────────────────────────────────────────────────────────────┤
│  [ИЗ v4] Ликвидация глобального состояния ProviderRegistry  │
│  [ИЗ v4] Вынос Pandera-зависимости из Domain                │
│  [ИЗ v4] Сокращение ignore_imports в .importlinter          │
└─────────────────────────────────────────────────────────────┘
```

---

## Текущая архитектурная оценка

| Категория | Описание | Вес | Оценка | Взвеш. балл |
|-----------|----------|:---:|:------:|:-----------:|
| Слоистая архитектура | Соответствие разделению domain/application/infrastructure/interfaces | 0.12 | 7 | 0.84 |
| Ports & Adapters / DDD | Наличие портов, адаптеров, фабрик, инверсия зависимостей | 0.10 | 6 | 0.60 |
| Границы модулей | Очевидность публичных API, отсутствие утечек абстракций | 0.10 | 6 | 0.60 |
| Качество доменной модели | Value Object'ы, модели выполнения пайплайна | 0.10 | 7 | 0.70 |
| Контракты и конфигурация | Единообразие портов, фабрик, конфигов | 0.08 | 6 | 0.48 |
| Обработка ошибок | Логирование, метрики, управляемые ошибки | 0.10 | 6 | 0.60 |
| Тестирование и QA | Архитектурные проверки и тестовые профили | 0.10 | 6 | 0.60 |
| Валидация данных | Pandera-схемы, нормализация | 0.10 | 7 | 0.70 |
| Документация | Архитектурные правила, индекс документации | 0.10 | 7 | 0.70 |
| Сопровождаемость | Простота расширения, отсутствие костылей | 0.10 | 6 | 0.60 |
| **Интегральный балл** | | **1.00** | | **6.42** |

**Интерпретация:** 5–7.9 = «среднее состояние» — архитектурные принципы заданы и частично соблюдаются, но есть заметные расхождения.

---

## Выявленные проблемы

### Проблема 1: Прямой импорт инфраструктуры в application

**Файл:** `src/bioetl/application/orchestrator.py:58-69`

```python
def _get_default_registry_factory() -> ProviderRegistryFactory:
    """Get the default provider registry factory.

    This function lazily imports from infrastructure to provide backward
    compatibility. New code should inject the factory explicitly.
    """
    from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
    return InMemoryProviderRegistry
```

**Использование в `__init__`:**
```python
self._provider_registry_factory = (
    provider_registry_factory or _get_default_registry_factory()  # fallback!
)
```

**Нарушение:** Application слой не должен импортировать инфраструктуру напрямую, даже через lazy import. Согласно ARCHITECTURE.md, все зависимости должны инъектироваться.

---

### Проблема 2: Обращение к приватным методам пайплайна

**Файл:** `src/bioetl/application/orchestrator.py:153-159`

```python
if effective_type == PipelineType.EXTRACT_ONLY:
    context = self._build_simple_context()
    extract_callable = pipeline._get_extract_callable()  # noqa: SLF001
    iterator = pipeline._normalize_extract_result(
        extract_callable()
    )  # noqa: SLF001
```

**Нарушение:** Orchestrator обращается к приватным методам `_get_extract_callable` и `_normalize_extract_result`, что ломает инкапсуляцию и усложняет замену реализаций.

---

### Проблема 3: Недостаточные архитектурные тесты

**Файл:** `tests/architecture/test_layer_dependencies.py:148-165`

```python
def test_application_avoids_infrastructure_implementations() -> None:
    for file_path in sorted(APPLICATION_ROOT.rglob("*.py")):
        for reference in _collect_imports(file_path):
            if not reference.module.startswith("bioetl.infrastructure"):
                continue
            if "impl" in reference.module.split("."):  # Проверяет только impl!
                violations.append(...)
```

**Проблема:** Тест проверяет только импорты с `impl` в пути, но пропускает прямые импорты типа `bioetl.infrastructure.provider_registry`.

---

## Приоритет 1: Жёсткое разделение application и infrastructure

### Цель
Убрать прямые импорты инфраструктуры из application, оставив только инъекцию фабрик через интерфейсы.

### Проблемные места

| Файл | Строка | Импорт |
|------|:------:|--------|
| `orchestrator.py` | 67 | `from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry` |

### План действий

#### Этап 1.1: Удаление fallback в orchestrator

**Изменить:** `src/bioetl/application/orchestrator.py`

```python
# БЫЛО:
def _get_default_registry_factory() -> ProviderRegistryFactory:
    from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
    return InMemoryProviderRegistry

class PipelineOrchestrator:
    def __init__(
        self,
        ...
        provider_registry_factory: ProviderRegistryFactory | None = None,
    ) -> None:
        self._provider_registry_factory = (
            provider_registry_factory or _get_default_registry_factory()
        )

# СТАНЕТ:
class PipelineOrchestrator:
    def __init__(
        self,
        ...
        provider_registry_factory: ProviderRegistryFactory,  # обязательный!
    ) -> None:
        self._provider_registry_factory = provider_registry_factory
```

#### Этап 1.2: Перенос фабрики в composition root

**Создать/обновить:** `src/bioetl/interfaces/factories/provider_registry.py`

```python
"""Provider registry factory for composition root."""
from __future__ import annotations

from bioetl.domain.provider_registry import ProviderRegistryFactory


def create_provider_registry_factory() -> ProviderRegistryFactory:
    """Create the default provider registry factory.

    This is the single place where infrastructure is imported for DI.
    """
    from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
    return InMemoryProviderRegistry
```

#### Этап 1.3: Обновление точек входа

**Обновить:** `src/bioetl/interfaces/composition_root.py`

```python
from bioetl.interfaces.factories.provider_registry import (
    create_provider_registry_factory,
)

class CompositionRoot:
    def create_orchestrator(
        self,
        pipeline_name: str,
        config: PipelineConfig,
    ) -> PipelineOrchestrator:
        return PipelineOrchestrator(
            pipeline_name,
            config,
            provider_registry_factory=create_provider_registry_factory(),
            # ... остальные зависимости
        )
```

#### Этап 1.4: Обновление тестов

Все тесты, создающие `PipelineOrchestrator` напрямую, должны передавать `provider_registry_factory`:

```python
# В тестах:
from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry

orchestrator = PipelineOrchestrator(
    "test_pipeline",
    config,
    provider_registry_factory=InMemoryProviderRegistry,
)
```

### Критерии готовности

- [ ] В `application/orchestrator.py` нет импортов `bioetl.infrastructure.*`
- [ ] Функция `_get_default_registry_factory()` удалена
- [ ] `provider_registry_factory` — обязательный параметр конструктора
- [ ] Все вызовы orchestrator проходят через явный DI
- [ ] Архитектурные тесты дополнены проверкой на инфраструктурные импорты

---

## Приоритет 2: Публичный API для extract-only режима

### Цель
Избавиться от обращения к `_get_extract_callable`/`_normalize_extract_result` снаружи, создав публичный метод для «extract-only» сценария.

### Проблемные места

| Файл | Строка | Вызов |
|------|:------:|-------|
| `orchestrator.py` | 156 | `pipeline._get_extract_callable()` |
| `orchestrator.py` | 157-159 | `pipeline._normalize_extract_result(...)` |

### План действий

#### Этап 2.1: Создание публичного метода в PipelineBase

**Изменить:** `src/bioetl/application/pipelines/base.py`

```python
class PipelineBase(ABC):
    # ... существующий код ...

    # === Public API ===

    def run_extract_only(self, **kwargs: Any) -> ExtractOnlyResult:
        """Execute only the extract stage and return statistics.

        This method provides a clean public API for extract-only mode,
        encapsulating the internal extraction logic.

        Args:
            **kwargs: Arguments passed to the extract stage.

        Returns:
            ExtractOnlyResult with row count and chunk count.
        """
        extract_callable = self._get_extract_callable()
        iterator = self._normalize_extract_result(extract_callable(**kwargs))

        total_rows = 0
        total_chunks = 0

        for chunk in iterator:
            if chunk is None:
                continue
            total_rows += len(chunk)
            total_chunks += 1

        return ExtractOnlyResult(
            total_rows=total_rows,
            total_chunks=max(total_chunks, 1),
        )
```

#### Этап 2.2: Создание модели результата

**Создать:** `src/bioetl/domain/models.py` (или дополнить)

```python
@dataclass(frozen=True)
class ExtractOnlyResult:
    """Result of extract-only pipeline execution."""

    total_rows: int
    total_chunks: int
```

#### Этап 2.3: Обновление orchestrator

**Изменить:** `src/bioetl/application/orchestrator.py`

```python
# БЫЛО:
if effective_type == PipelineType.EXTRACT_ONLY:
    context = self._build_simple_context()
    extract_callable = pipeline._get_extract_callable()  # noqa: SLF001
    iterator = pipeline._normalize_extract_result(
        extract_callable()
    )  # noqa: SLF001

    total_rows = 0
    total_chunks = 0
    for chunk in iterator:
        if chunk is None:
            continue
        total_rows += len(chunk)
        total_chunks += 1
    # ... построение RunResult

# СТАНЕТ:
if effective_type == PipelineType.EXTRACT_ONLY:
    context = self._build_simple_context()
    extract_result = pipeline.run_extract_only()  # Публичный API!

    stage = StageResult(
        stage_name=StageName.EXTRACT,
        success=True,
        records_processed=extract_result.total_rows,
        chunks_processed=extract_result.total_chunks,
        duration_sec=0.0,
        errors=[],
    )

    return RunResult(
        run_id=context.run_id,
        success=True,
        entity_name=self._config.entity_name,
        row_count=extract_result.total_rows,
        # ...
    )
```

### Критерии готовности

- [ ] Метод `run_extract_only()` добавлен в `PipelineBase`
- [ ] `ExtractOnlyResult` добавлен в `domain/models.py`
- [ ] `PipelineOrchestrator` использует публичный API
- [ ] Ни один модуль в `application/` не обращается к приватным методам пайплайна
- [ ] Удалены комментарии `noqa: SLF001`
- [ ] Новый метод покрыт тестами

---

## Приоритет 3: Усиление архитектурных тестов

### Цель
Закрепить правила ARCHITECTURE.md тестами: запрет любых инфраструктурных импортов в application.

### План действий

#### Этап 3.1: Расширение test_layer_dependencies.py

**Изменить:** `tests/architecture/test_layer_dependencies.py`

```python
# Добавить новый тест:

# Whitelist: разрешённые инфраструктурные импорты в application
# (только если они абсолютно необходимы и документированы)
APPLICATION_ALLOWED_INFRA_IMPORTS: set[str] = {
    # Пустой — никаких прямых импортов не разрешено
}


def test_application_has_no_infrastructure_imports() -> None:
    """Verify application layer has no direct infrastructure imports.

    This is stricter than test_application_avoids_infrastructure_implementations
    which only checks for 'impl' modules. This test catches ANY infrastructure
    import.
    """
    violations: list[str] = []

    for file_path in sorted(APPLICATION_ROOT.rglob("*.py")):
        for reference in _collect_imports(file_path):
            if not reference.module.startswith("bioetl.infrastructure"):
                continue

            # Проверяем whitelist
            if reference.module in APPLICATION_ALLOWED_INFRA_IMPORTS:
                continue

            violations.append(
                _format_violation(
                    file_path,
                    reference.lineno,
                    f"application must not import infrastructure "
                    f"(found {reference.module})",
                )
            )

    _assert_no_violations(violations)
```

#### Этап 3.2: Тест на приватные атрибуты

**Добавить в:** `tests/architecture/test_layer_dependencies.py`

```python
import re

PRIVATE_ATTR_PATTERN = re.compile(r"\._[a-z_]+\(")  # Вызовы приватных методов


def test_no_cross_module_private_access() -> None:
    """Verify no module accesses private attributes of other modules.

    This catches patterns like:
    - pipeline._get_extract_callable()
    - service._internal_method()
    """
    violations: list[str] = []

    for file_path in sorted(APPLICATION_ROOT.rglob("*.py")):
        content = file_path.read_text(encoding="utf-8")

        # Ищем паттерны вида object._private_method(
        for line_no, line in enumerate(content.splitlines(), 1):
            # Пропускаем строки внутри класса (self._method)
            if "self._" in line:
                continue
            if "cls._" in line:
                continue

            # Ищем внешние обращения к приватным методам
            matches = PRIVATE_ATTR_PATTERN.findall(line)
            for match in matches:
                # Исключаем self и cls
                if "self" not in line[:line.find(match)] and \
                   "cls" not in line[:line.find(match)]:
                    violations.append(
                        _format_violation(
                            file_path,
                            line_no,
                            f"cross-module private attribute access: {match}",
                        )
                    )

    _assert_no_violations(violations)
```

#### Этап 3.3: Интеграция с ruff

**Обновить:** `pyproject.toml` или `.ruff.toml`

```toml
[tool.ruff.lint]
select = [
    # ... существующие правила
    "SLF001",  # Private member accessed
]

# Убрать из per-file-ignores:
# [tool.ruff.lint.per-file-ignores]
# "src/bioetl/application/orchestrator.py" = ["SLF001"]  # УДАЛИТЬ!
```

### Критерии готовности

- [ ] Тест `test_application_has_no_infrastructure_imports` добавлен и проходит
- [ ] Тест `test_no_cross_module_private_access` добавлен и проходит
- [ ] ruff правило SLF001 включено без исключений для orchestrator
- [ ] CI блокирует регресс

---

## Дополнительные задачи из v4

Следующие задачи из REFACTORING_PLAN_v4.md остаются актуальными и должны быть выполнены после приоритетных задач:

### Задача v4-1: Ликвидация глобального состояния ProviderRegistry

**Статус:** Актуально
**Файл:** `src/bioetl/domain/provider_registry.py:78`

Удалить:
- `_PROVIDER_REGISTRY: ProviderRegistryABC | None = None`
- `set_provider_registry()`
- `get_provider_registry()`
- `default_provider_registry()`

### Задача v4-2: Вынос Pandera-зависимости из Domain

**Статус:** Актуально
**Файл:** `src/bioetl/domain/schemas/generator.py`

Перенести динамические импорты Pandera/YAML в infrastructure.

### Задача v4-4: Сокращение ignore_imports в .importlinter

**Статус:** Актуально
**Текущее количество:** 13 исключений
**Целевое количество:** ≤3

---

## Метрики и тесты

### Метрики качества

| Метрика | Текущее | Целевое | Проверка |
|---------|:-------:|:-------:|----------|
| Инфраструктурные импорты в application | >0 | 0 | `grep -rn "bioetl.infrastructure" src/bioetl/application/` |
| Обращения к приватным методам (cross-module) | >0 | 0 | `grep -rn "\._[a-z_]*(" src/bioetl/application/ \| grep -v "self\._\|cls\._"` |
| `noqa: SLF001` в orchestrator | 2 | 0 | `grep -c "noqa: SLF001" src/bioetl/application/orchestrator.py` |
| Архитектурные тесты | pass | pass | `pytest tests/architecture/ -v` |
| ignore_imports в .importlinter | 13 | ≤3 | Подсчёт строк |

### Команды проверки

```bash
# Проверка инфраструктурных импортов в application
grep -rn "from bioetl.infrastructure" src/bioetl/application/
grep -rn "import bioetl.infrastructure" src/bioetl/application/

# Проверка обращений к приватным методам
grep -rn "\._[a-z_]*(" src/bioetl/application/ | grep -v "self\._\|cls\._"

# Проверка noqa комментариев
grep -rn "noqa: SLF001" src/bioetl/application/

# Архитектурные тесты
pytest tests/architecture/ -v --tb=short

# Import linter
lint-imports

# Полная проверка
pytest tests/architecture/ tests/project_rules/ -v
```

---

## План выполнения

```
ПРИОРИТЕТ 1: Жёсткое разделение application и infrastructure
═══════════════════════════════════════════════════════════════

Этап 1.1: Удаление fallback в orchestrator                    [1 ч]
├── Удалить _get_default_registry_factory()
├── Сделать provider_registry_factory обязательным
└── Обновить сигнатуру __init__

Этап 1.2: Перенос фабрики в composition root                  [0.5 ч]
├── Создать interfaces/factories/provider_registry.py
└── Экспортировать create_provider_registry_factory()

Этап 1.3: Обновление точек входа                              [1 ч]
├── Обновить CompositionRoot.create_orchestrator()
├── Обновить CLI команды
└── Обновить REST endpoints

Этап 1.4: Обновление тестов                                   [1 ч]
├── Найти все тесты с PipelineOrchestrator
├── Добавить явную инъекцию provider_registry_factory
└── Проверить прохождение тестов
                                                              ─────────
                                                              Итого: 3.5 ч


ПРИОРИТЕТ 2: Публичный API для extract-only режима
═══════════════════════════════════════════════════════════════

Этап 2.1: Создание публичного метода в PipelineBase           [1 ч]
├── Добавить run_extract_only() в PipelineBase
└── Инкапсулировать логику _get_extract_callable/_normalize

Этап 2.2: Создание модели результата                          [0.5 ч]
├── Добавить ExtractOnlyResult в domain/models.py
└── Документировать поля

Этап 2.3: Обновление orchestrator                             [1 ч]
├── Заменить приватные вызовы на run_extract_only()
├── Удалить noqa: SLF001 комментарии
└── Проверить корректность RunResult

Этап 2.4: Покрытие тестами                                    [1 ч]
├── Unit-тест run_extract_only()
├── Integration-тест EXTRACT_ONLY режима
└── Проверить счётчики
                                                              ─────────
                                                              Итого: 3.5 ч


ПРИОРИТЕТ 3: Усиление архитектурных тестов
═══════════════════════════════════════════════════════════════

Этап 3.1: Тест на инфраструктурные импорты                    [1 ч]
├── Добавить test_application_has_no_infrastructure_imports
└── Проверить с whitelist

Этап 3.2: Тест на приватные атрибуты                          [1 ч]
├── Добавить test_no_cross_module_private_access
└── Исключить self/cls паттерны

Этап 3.3: Интеграция с ruff                                   [0.5 ч]
├── Включить SLF001 без исключений
└── Обновить pyproject.toml
                                                              ─────────
                                                              Итого: 2.5 ч


═══════════════════════════════════════════════════════════════
ОБЩЕЕ ВРЕМЯ ПРИОРИТЕТНЫХ ЗАДАЧ: ~9.5 ч
═══════════════════════════════════════════════════════════════


ДОПОЛНИТЕЛЬНЫЕ ЗАДАЧИ ИЗ v4 (после приоритетных)
═══════════════════════════════════════════════════════════════

Задача v4-1: Глобальное состояние ProviderRegistry            [2.5 ч]
Задача v4-2: Pandera в Domain                                 [2.5 ч]
Задача v4-4: Сокращение ignore_imports                        [4.5 ч]
                                                              ─────────
                                                              Итого: 9.5 ч


═══════════════════════════════════════════════════════════════
ПОЛНОЕ ВРЕМЯ (все задачи): ~19 ч
═══════════════════════════════════════════════════════════════
```

---

## Ожидаемые результаты

### Улучшение архитектурных оценок

| Категория | Текущая | После v5 | Изменение |
|-----------|:-------:|:--------:|:---------:|
| Слоистая архитектура | 7 | 8 | +1 |
| Ports & Adapters / DDD | 6 | 7.5 | +1.5 |
| Границы модулей | 6 | 7.5 | +1.5 |
| Тестирование и QA | 6 | 7 | +1 |
| Сопровождаемость | 6 | 7.5 | +1.5 |

### Прогноз интегрального балла

После реализации **приоритетных задач (1-3)**:

| Категория | Вес | До | После | Δ взвеш. |
|-----------|:---:|:--:|:-----:|:--------:|
| Слоистая архитектура | 0.12 | 7 | 8 | +0.12 |
| Ports & Adapters | 0.10 | 6 | 7.5 | +0.15 |
| Границы модулей | 0.10 | 6 | 7.5 | +0.15 |
| Тестирование и QA | 0.10 | 6 | 7 | +0.10 |
| Сопровождаемость | 0.10 | 6 | 7.5 | +0.15 |

**Суммарный прирост:** +0.67
**Прогноз интегрального балла:** 6.42 + 0.67 ≈ **7.1**

После реализации **всех задач (включая v4)**:

**Итоговый прогноз:** **7.5–7.8**

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|:-----------:|:-------:|-----------|
| Поломка существующих вызовов orchestrator | Высокая | Среднее | Deprecation warnings на 1-2 релиза |
| Ложные срабатывания архитектурных тестов | Средняя | Низкое | Whitelist для допустимых случаев |
| Несовместимость с internal CLI | Средняя | Среднее | Обновить CLI вместе с composition root |

### Стратегия миграции

1. **Фаза 1 (deprecation):** Добавить warning в `_get_default_registry_factory()`:
   ```python
   warnings.warn(
       "Using default registry factory is deprecated. "
       "Pass provider_registry_factory explicitly.",
       DeprecationWarning,
       stacklevel=3,
   )
   ```

2. **Фаза 2 (обновление):** Обновить все точки входа на явный DI

3. **Фаза 3 (удаление):** Удалить deprecated код, сделать параметр обязательным

---

## Ссылки

- [REFACTORING_PLAN_v4.md](./REFACTORING_PLAN_v4.md)
- [architecture.md](./architecture.md)
- [PipelineOrchestrator](../../src/bioetl/application/orchestrator.py)
- [PipelineBase](../../src/bioetl/application/pipelines/base.py)
- [test_layer_dependencies.py](../../tests/architecture/test_layer_dependencies.py)
- [Domain Provider Registry](../../src/bioetl/domain/provider_registry.py)
