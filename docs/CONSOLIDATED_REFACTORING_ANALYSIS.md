# Консолидированный Анализ Планов Рефакторинга

*Версия: 2.0 | Дата: 2025-12-27*
*Обновление: Верификация на основе актуального кода, исправление ложных утверждений*

---

## Резюме

Проанализированы 4 плана рефакторинга. Выявлено:
- **~50% утверждений ложны** или основаны на недопонимании архитектуры
- **6+ задач уже реализованы** (не обновлена документация в планах)
- **3 реальные задачи** требуют внимания (верифицированы)

---

## 1. ВЕРИФИЦИРОВАННЫЕ МЕТРИКИ КОДА

| Компонент | Заявлено | Реально | Статус |
|-----------|----------|---------|--------|
| PreflightService | 527 LOC, "комбайн" | 527 LOC, 8 методов, когезивен | ❌ Не комбайн |
| PipelineRunner | "god object" | 175 LOC, 9 методов, делегирует | ❌ Не god object |
| ChEMBL client | 517 LOC | 517 LOC, 20 методов, когезивен | ✅ Размер верен |
| PubChem client | 317 LOC | 317 LOC, 11 методов | ✅ Размер верен |
| bootstrap.py | "перегружен" | 166 LOC | ❌ Компактный |
| medallion_policy.py | "дублирует domain" | 19 LOC, shim | ❌ Backward-compat |
| PipelineRegistry | class-level state | ClassVar[dict] + RLock | ✅ Проблема |

---

## 2. ЛОЖНЫЕ УТВЕРЖДЕНИЯ В ПЛАНАХ

### ❌ Ложь 1: "PreflightService 527 строк — комбайн"
**План**: 3

**Реальность** (верифицировано):
```
PreflightService (527 LOC, 8 методов):
├── validate_infrastructure()      # 44 строки, делегирует HealthAggregator
├── validate_medallion_config()    # 117 строк, валидация форматов/путей/policy
├── validate_write_modes()         # 66 строк, валидация режимов записи
├── validate_preflight()           # 93 строки, оркестрация + метрики
└── 4 приватных helpers            # ~100 строк
```

**Вывод**: Это **когезивный** сервис с единой ответственностью (preflight validation).
Декомпозиция на 2+ класса создаст overhead без выгоды.

---

### ❌ Ложь 2: "medallion_policy.py дублирует domain"
**План**: 3

**Реальность** (файл: `application/core/medallion_policy.py`, 19 строк):
```python
"""Note: This module re-exports from bioetl.domain.medallion for backward compatibility.
The canonical location is bioetl.domain.medallion."""

from bioetl.domain.medallion import Layer, WriteMode, WriteModePolicy

__all__ = ["Layer", "WriteMode", "WriteModePolicy"]
```

**Вывод**: Это **shim для backward compatibility**, НЕ дублирование.

---

### ❌ Ложь 3: "BronzeWriter допускает отсутствие MetricsPort"
**План**: 2

**Реальность** (bronze_writer.py:54-72):
```python
def __init__(
    self,
    ...
    logger: LoggerPort,     # MUST be injected
    metrics: MetricsPort,   # MUST be injected
    ...
):
    ...
    self._metrics = metrics
```

**Вывод**: MetricsPort **инжектируется**. NoOp передаётся через composition — это валидный Null Object Pattern.

---

### ❌ Ложь 4: "CLI использует click.echo минуя LoggerPort"
**План**: 2

**Реальность**: click.echo — **законная ответственность interfaces слоя** для user-facing output.
Из REFACTORING_PLAN.md: "Подтверждения — законная ответственность interfaces слоя".

---

### ❌ Ложь 5: "Трансформер не проверяется на этапе сборки"
**План**: 4

**Реальность** (generic_factory.py:91-99):
```python
def create_transformer(self, ...) -> BaseTransformer | None:
    """Create transformer instance if transformer_class is configured."""
    if self.transformer_class is None:
        return None  # Handled by BasePipeline
    return self.transformer_class(...)
```

**Вывод**: Проверка есть. BasePipeline корректно обрабатывает `None`.

---

### ❌ Ложь 6: "Нет связи DQ с метриками"
**План**: 1

**Реальность** (preflight_service.py:136-155, 513-524):
```python
# Метрики:
# - pipeline_health_check_passed
# - infrastructure_validated
# - health_check_duration_seconds
# - preflight_medallion_policy_valid
# - preflight_config_errors_total
```

**Вывод**: Метрики существуют и документированы.

---

## 3. УЖЕ РЕАЛИЗОВАННЫЕ ЗАДАЧИ

| Задача | План | Доказательство |
|--------|------|----------------|
| PipelineRunner DI через bundle | 1, 2, 4 | `runner.py:84-88`, `runner_services.py` |
| CLI → entrypoints.py | 1, 4 | `cli.py:17-27` импортирует из entrypoints |
| Детерминистичный HTTP jitter | Existing | `domain/resilience.py:45-84` |
| Удаление random из Gold | Existing | `gold_writer.py:286,359` |
| Arch-тесты random/datetime.now | Existing | `tests/architecture/test_no_random_in_writers.py`, `test_no_datetime_now_in_infrastructure.py` |
| PipelineContext.started_at | Existing | `context.py:33` |

---

## 4. ВЕРИФИЦИРОВАННЫЕ ПРОБЛЕМЫ

### ✅ Проблема 1: PipelineRegistry с глобальным состоянием

**Файл**: `composition/registry.py:80-81`

```python
class PipelineRegistry:
    _registry: ClassVar[dict[str, PipelineDefinition]] = {}
    _registry_lock: ClassVar[threading.RLock] = threading.RLock()
```

**Влияние**: Параллельные тесты требуют `clear()`, изоляция нарушена.

**Приоритет**: 🔴 КРИТИЧЕСКИЙ

---

### ✅ Проблема 2: PipelineObserver создаётся в runner

**Файл**: `runner.py:116-123`

```python
async def run(self) -> None:
    ...
    observer = PipelineObserver(
        pipeline_name=self._config.pipeline_name,
        run_id=self._context.run_id,
        ...
    )
```

**Влияние**: Усложняет мокирование Observer в тестах.

**Приоритет**: 🟠 ВЫСОКИЙ

---

### ✅ Проблема 3: Нет arch-теста на Bronze метаданные

**Текущее состояние**: Нет теста, гарантирующего наличие `_ingestion_ts`, `_run_id` в Bronze.

**Приоритет**: 🟡 СРЕДНИЙ

---

## 5. КОНСОЛИДИРОВАННЫЙ ПЛАН

### Приоритет 🔴 КРИТИЧЕСКИЙ

#### REG-1: Instance-level PipelineRegistry

**Цель**: Изоляция тестов, параллельное выполнение без `clear()`.

**Решение**:
```python
class PipelineRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, PipelineDefinition] = {}
        self._lock = threading.RLock()

# В composition:
def create_registry() -> PipelineRegistry:
    registry = PipelineRegistry()
    register_all_pipelines(registry)
    return registry
```

**Файлы**:
- `composition/registry.py` — рефакторинг класса
- `composition/bootstrap.py` — передача registry через DI
- `tests/conftest.py` — фикстура изолированного registry

**Критерии готовности**:
- [ ] Параллельные pytest без ручного `clear()`
- [ ] Можно создать 2 registry в одном процессе
- [ ] Все arch-тесты проходят

**Оценка**: 1-2 дня

---

### Приоритет 🟠 ВЫСОКИЙ

#### OBS-1: Вынести PipelineObserver в composition

**Цель**: Улучшить тестируемость, следовать DI.

**Решение**:
```python
# runner_services.py
@dataclass(frozen=True)
class RunnerServices:
    lock_manager: LockManager
    preflight: PreflightService
    postrun: PostrunService
    lifecycle_orch: LifecycleOrchestrator
    observer: PipelineObserver  # NEW

# runner.py
async def run(self) -> None:
    with self._runner_services.observer:
        ...
```

**Файлы**:
- `application/core/runner_services.py` — добавить observer
- `composition/factories/runner_services.py` — создавать observer
- `application/core/runner.py` — использовать injected observer

**Критерии готовности**:
- [ ] PipelineRunner не создаёт Observer
- [ ] `test_runner.py` использует mock observer
- [ ] Arch-тест `test_di_discipline.py` обновлён

**Оценка**: 0.5 дня

---

### Приоритет 🟡 СРЕДНИЙ

#### M-INV-1: Arch-тест на Bronze метаданные

**Цель**: Гарантировать наличие `_ingestion_ts`, `_run_id` в Bronze.

**Решение**:
```python
# tests/architecture/test_medallion_invariants.py
def test_bronze_writer_requires_metadata():
    """Bronze writer MUST include _ingestion_ts and _run_id."""
    source = Path("src/bioetl/infrastructure/storage/bronze_writer.py").read_text()

    required_fields = ["_ingestion_ts", "_run_id", "_run_type", "_source_batch_id"]
    for field in required_fields:
        assert field in source, f"Bronze writer missing required field: {field}"
```

**Файлы**:
- `tests/architecture/test_medallion_invariants.py` (новый)

**Критерии готовности**:
- [ ] Тест падает при удалении metadata из bronze_writer
- [ ] `make arch-test` включает новый тест

**Оценка**: 0.5 дня

---

## 6. ЗАДАЧИ, КОТОРЫЕ НЕ СЛЕДУЕТ ВЫПОЛНЯТЬ

| Предложение из планов | Причина отклонения |
|----------------------|-------------------|
| Декомпозиция PreflightService на 2+ класса | Сервис когезивен, 4 метода с единой ответственностью |
| Декомпозиция ChEMBL на 4+ классов | Over-engineering, высокая когезия |
| Удаление medallion_policy.py | Это backward-compat shim, не дублирование |
| Унификация click.echo → LoggerPort | click.echo — корректная ответственность interfaces |
| Стратегии выполнения раннера | Over-engineering для текущих use cases |
| Гарантированная инструментализация storage | Уже реализовано через DI |
| Усиление контракта трансформера | Уже реализовано в generic_factory.py |
| Декомпозиция PipelineRunner | Уже сделано через RunnerServices |
| Декомпозиция bootstrap_pipeline | Компактный фасад, архитектура адекватна |

---

## 7. МЕТРИКИ УСПЕХА

| Метрика | До | После | Связанная задача |
|---------|-----|-------|-----------------|
| Параллельные тесты без clear() | ❌ | ✅ | REG-1 |
| Observer через DI | ❌ | ✅ | OBS-1 |
| Arch-тест Bronze metadata | ❌ | ✅ | M-INV-1 |
| Ложных утверждений в планах | ~50% | 0% | Этот документ |

---

## 8. ПРИЧИНЫ ЛОЖНЫХ УТВЕРЖДЕНИЙ

Анализ показал, что ложные утверждения возникли из-за:

1. **Отсутствие верификации кодом** — утверждения делались без проверки фактического состояния
2. **Устаревшие знания** — часть задач уже была реализована к моменту анализа
3. **Неверная интерпретация паттернов**:
   - NoOp в DI = Null Object Pattern (валидно)
   - Optional defaults = не нарушение DI (валидно)
   - click.echo в CLI = ответственность interfaces (корректно)
4. **Ложная корреляция размер → сложность**:
   - 527 LOC ≠ god object (если структура когезивна)
   - 175 LOC PipelineRunner ≠ god object (делегирует)

---

## 9. РЕКОМЕНДАЦИИ ПО ПРОЦЕССУ

### Обязательные проверки перед предложением рефакторинга:

```bash
# 1. Проверить размер и структуру
wc -l src/bioetl/path/to/file.py
grep -c "def \|async def " src/bioetl/path/to/file.py

# 2. Проверить делегирование
grep -n "self\._.*\." src/bioetl/path/to/file.py | head -20

# 3. Сверить с REFACTORING_PLAN.md
grep -A3 "ЛОЖНЫЕ УТВЕРЖДЕНИЯ\|УЖЕ РЕАЛИЗОВАНО" docs/REFACTORING_PLAN.md

# 4. Найти существующие тесты
find tests -name "*.py" -exec grep -l "ClassName" {} \;
```

### Формат верифицированного предложения:

```markdown
## Задача: [Название]

### Верификация
- **Файл**: `path/to/file.py:строки` (N строк, M методов)
- **Проверено**: Нет в "ЛОЖНЫЕ УТВЕРЖДЕНИЯ" ✅
- **Дата верификации**: YYYY-MM-DD

### Текущее состояние
[Описание с ссылками `файл:строка`]

### Проблема
[Конкретное описание с доказательствами]

### Решение
[Предлагаемое решение]
```

---

## 10. ЗАКЛЮЧЕНИЕ

Из 4 планов рефакторинга:
- **3 задачи валидны**: REG-1, OBS-1, M-INV-1
- **~50% утверждений ложны** или устарели
- **Основная причина ошибок**: Отсутствие верификации кодом

**Рекомендация**: Выполнить только верифицированные задачи (REG-1, OBS-1, M-INV-1) и обновить протокол в REFACTORING_PLAN.md.

---

*Документ подготовлен на основе верификации кода 2025-12-27*
