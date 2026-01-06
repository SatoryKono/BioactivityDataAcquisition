# Подробный План Рефакторинга (2025-12-29)

*Версия: 1.0 | Оценка: 2.5 дня | Автор: Claude*

> **Верификация выполнена** согласно CLAUDE.md §0 и RULES.md §7 (REQ-ARCH-040)

---

## Обзор Задач

| # | Задача | Оценка | Приоритет | Статус |
|---|--------|--------|-----------|--------|
| 1 | Обновить RULES.md секцией §6.1 Determinism | S (0.5 дня) | 🔵 Желательно | ⏳ Требуется |
| 2 | Унификация логирования (4 файла с `logging.getLogger`) | S (1 день) | 🟡 Средний | ⏳ Требуется |
| 3 | Тесты Observer (O2-O4) | S (1 день) | 🟢 Желательно | ✅ УЖЕ РЕАЛИЗОВАНО |

---

## Задача 1: Обновить RULES.md секцией §6.1 Determinism

### Верификация

- **Файл**: `docs/RULES.md:667-684` (17 строк)
- **Текущее состояние**: §6.1 существует, но содержит минимальную информацию
- **Проверено**: Нет в "ЛОЖНЫЕ УТВЕРЖДЕНИЯ" ✅
- **Дата верификации**: 2025-12-29

### Текущее Состояние

Секция §6.1 (`RULES.md:671-684`) содержит базовые правила:
- 4 MUST-требования
- Ссылки на 2 архитектурных теста
- Нет детализации по jitter, timestamp source, ordering

### Требуемые Изменения

| № | Изменение | Строки | Описание |
|---|-----------|--------|----------|
| 1 | Расширить §6.1 | 671-684 | Добавить детали из ADR-014 |
| 2 | Обновить §4.1 | ~395 | Добавить требование детерминистичного джиттера |
| 3 | Обновить §2.1 | ~103-118 | Упомянуть режимы записи Enum |

#### 1.1. Расширение §6.1 Determinism

**Целевой код** (заменить строки 671-684):

```markdown
## 6.1 Детерминизм и Воспроизводимость

**Детерминизм** — гарантия того, что при одинаковых входных данных пайплайн всегда
произведет идентичные выходные данные и побочные эффекты.

### MUST (Обязательные требования)

| # | Требование | Проверка |
|---|------------|----------|
| 1 | Storage writers **MUST NOT** использовать модуль `random` | `test_no_random_in_writers.py` |
| 2 | Timestamps **MUST** передаваться из application слоя | `test_no_datetime_now_in_infrastructure.py` |
| 3 | Retry jitter **MUST** быть детерминистичным при `deterministic=True` | `test_http_client.py::test_deterministic_jitter_*` |
| 4 | `PipelineContext.started_at` — единственный источник времени для batch | Unit тесты context |
| 5 | Запись в Delta Lake **MUST** происходить после сортировки по Primary Keys | `test_gold_writer.py` |

### Детерминистичный Jitter (ADR-014)

При `RetryConfig(deterministic=True)` jitter вычисляется через MD5-hash:

```python
hash_input = f"{attempt}:{url}:{seed}"
digest = hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()
jitter_factor = int(digest[:8], 16) / 0xFFFFFFFF
```

**Преимущества**:
- Кросс-процессная стабильность (в отличие от `hash()`)
- Воспроизводимость для debugging
- Возможность использовать seed для тестов

### Единый Источник Времени

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  PipelineContext.create() → started_at = datetime.now(UTC)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ передаётся вниз
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
   BronzeWriter           Quarantine          RecordProcessor
   ingestion_ts=          ingestion_ts=       ingestion_ts=
   context.started_at     context.started_at  context.started_at
```

**Запрещено**: Создание timestamps в infrastructure слое.

### Архитектурные Тесты

| Тест | Цель | Путь |
|------|------|------|
| `test_no_random_in_writers` | Блокирует `random` в storage writers | `tests/architecture/` |
| `test_no_datetime_now_in_infrastructure` | Блокирует `datetime.now()` в infra | `tests/architecture/` |
| `test_no_structlog_in_application_interfaces` | Блокирует прямой `structlog` | `tests/architecture/` |
```

#### 1.2. Обновление §4.1 Retry Logic

**Добавить в секцию §3.1.3** (после строки 273):

```markdown
- **Deterministic Mode**: При `RetryConfig(deterministic=True)` jitter **MUST** вычисляться
  через MD5-hash вместо random для воспроизводимости. См. [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md).
```

### Критерии Приёмки

- [ ] §6.1 расширен деталями из ADR-014
- [ ] Добавлены таблицы требований и архитектурных тестов
- [ ] Добавлена диаграмма единого источника времени
- [ ] Упоминание `deterministic=True` в §3.1.3
- [ ] `make lint` проходит (markdown валиден)

### Риски

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Несоответствие ADR-014 | Низкая | Сверить с ADR перед коммитом |
| Дублирование информации | Низкая | Ссылки на ADR вместо копирования |

### План Выполнения

```
Шаг 1: Прочитать текущие RULES.md:667-684 и ADR-014
Шаг 2: Подготовить расширенный текст §6.1
Шаг 3: Добавить упоминание deterministic в §3.1.3
Шаг 4: Проверить make lint
Шаг 5: Коммит и push
```

**Оценка**: 0.5 дня (4 часа)

---

## Задача 2: Унификация логирования (4 файла с `logging.getLogger`)

### Верификация

- **Файлы**: 4 файла в `infrastructure` слое
- **Текущее состояние**: Используют `logging.getLogger(__name__)` напрямую
- **Проверено**: Допустимо согласно ADR-019, но не консистентно ✅
- **Дата верификации**: 2025-12-29

### Найденные Файлы

| # | Файл | Строка | LOC | Использований |
|---|------|--------|-----|---------------|
| 1 | `infrastructure/export/csv_exporter.py` | 25 | 319 | 6 вызовов logger |
| 2 | `infrastructure/observability/server.py` | 12 | 144 | 8 вызовов logger |
| 3 | `infrastructure/observability/lineage.py` | 49 | 478 | 9 вызовов logger |
| 4 | `infrastructure/observability/anomaly/monitor.py` | 18 | 118 | 1 вызов logger |

### Архитектурный Контекст

Согласно ADR-019 (`ADR-019-observability-port-enforcement.md:73-79`):

| Layer | Logging | Status |
|-------|---------|--------|
| domain | ❌ No logging | ✅ Корректно |
| application | ✅ LoggerPort | ✅ Корректно |
| composition | ✅ Creates adapters | ✅ Корректно |
| **infrastructure** | ✅ structlog/logging allowed | ⚠️ Допустимо, но не унифицировано |
| interfaces | ✅ LoggerPort | ✅ Корректно |

**Вывод**: Использование `logging` в infrastructure **допустимо**, но для консистентности и тестируемости рекомендуется инжекция `LoggerPort`.

### Требуемые Изменения

#### 2.1. CsvExporter (`csv_exporter.py`)

**Текущий код** (строка 25):
```python
logger = logging.getLogger(__name__)
```

**Целевой код**:
```python
from bioetl.domain.ports import LoggerPort

class CsvExporter:
    def __init__(
        self,
        base_path: str,
        logger: LoggerPort,  # ← Добавить
        delimiter: str = ",",
        ...
    ) -> None:
        self.base_path = Path(base_path)
        self._logger = logger  # ← Использовать
        ...
```

**Изменения вызовов** (6 мест):
- Строка 84: `logger.warning(...)` → `self._logger.warning(...)`
- Строка 174: `logger.warning(...)` → `self._logger.warning(...)`
- Строка 189: `logger.debug(...)` → `self._logger.debug(...)`
- Строка 200: `logger.warning(...)` → `self._logger.warning(...)`
- Строка 234: `logger.warning(...)` → `self._logger.warning(...)`

**Обновление фабрики**: `composition/factories/` — добавить инжекцию logger

#### 2.2. MetricsServer (`server.py`)

**Текущий код** (строка 12):
```python
logger = logging.getLogger(__name__)
```

**Решение**: Сохранить `logging` для этого файла.

**Обоснование**:
- `server.py` — утилита для запуска Prometheus HTTP server
- Используется как singleton с глобальным состоянием (`_SERVER_STARTED`)
- Вызывается до инициализации DI-контейнера
- Инжекция `LoggerPort` усложнит API без пользы

**Добавить комментарий**:
```python
# NOTE: Using stdlib logging intentionally.
# This module runs before DI container is initialized.
# See ADR-019 for infrastructure layer logging policy.
logger = logging.getLogger(__name__)
```

#### 2.3. LineageTracker (`lineage.py`)

**Текущий код** (строка 49):
```python
logger = logging.getLogger(__name__)
```

**Целевой код**:
```python
from bioetl.domain.ports import LoggerPort

class LineageTracker:
    def __init__(
        self,
        delta_path: str | Path,
        pipeline_name: str,
        logger: LoggerPort,  # ← Добавить
    ) -> None:
        self.delta_path = Path(delta_path)
        self.pipeline_name = pipeline_name
        self._logger = logger  # ← Использовать
        ...
```

**Изменения вызовов** (9 мест):
- Строки 272, 274: `logger.debug/error(...)` → `self._logger.debug/error(...)`
- Строки 297, 300: аналогично
- Строки 338, 381, 413: аналогично
- Строки 472-477: аналогично

#### 2.4. DataQualityMonitor (`monitor.py`)

**Текущий код** (строка 18):
```python
logger = logging.getLogger(__name__)
```

**Целевой код**:
```python
from bioetl.domain.ports import LoggerPort

class DataQualityMonitor:
    def __init__(
        self,
        baseline_window: int = 7,
        z_score_threshold: float = 2.5,
        logger: LoggerPort | None = None,  # ← Опциональный
    ) -> None:
        self._logger = logger
        ...

    def update_baseline_from_metrics(...) -> None:
        ...
        if critical_anomalies and self._logger:
            self._logger.warning(
                f"Skipping baseline update due to {len(critical_anomalies)} critical anomalies"
            )
```

### Обновление Тестов

Для каждого изменённого класса:

1. **Unit тесты**: Обновить fixtures для передачи `logger_mock`
2. **Integration тесты**: Убедиться, что logger инжектируется из composition

**Пример теста**:
```python
def test_csv_exporter_with_injected_logger(logger_mock, tmp_path):
    exporter = CsvExporter(
        base_path=str(tmp_path),
        logger=logger_mock,  # ← Инжектируем
    )
    # ... test logic
    logger_mock.warning.assert_called_once()  # ← Проверяем
```

### Критерии Приёмки

- [ ] `CsvExporter` принимает `LoggerPort` в конструкторе
- [ ] `LineageTracker` принимает `LoggerPort` в конструкторе
- [ ] `DataQualityMonitor` принимает опциональный `LoggerPort`
- [ ] `server.py` сохраняет `logging` с комментарием-обоснованием
- [ ] Удалён `import logging` из 3 файлов
- [ ] Фабрики в `composition/` обновлены для инжекции logger
- [ ] Unit тесты обновлены и проходят
- [ ] `make lint && make test` проходят

### Риски

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Breaking change в API классов | Средняя | Сделать logger опциональным с fallback на NoOp |
| Пропущенные вызовы logger | Низкая | grep по файлам перед коммитом |
| Циклические импорты | Низкая | Использовать TYPE_CHECKING |

### План Выполнения

```
Шаг 1: Обновить CsvExporter (+ тесты)
Шаг 2: Обновить LineageTracker (+ тесты)
Шаг 3: Обновить DataQualityMonitor (+ тесты)
Шаг 4: Добавить комментарий в server.py
Шаг 5: Обновить фабрики в composition/
Шаг 6: make lint && make test
Шаг 7: Коммит и push
```

**Оценка**: 1 день (8 часов)

---

## Задача 3: Тесты Observer (O2-O4) — ✅ УЖЕ РЕАЛИЗОВАНО

### Верификация

- **Файл**: `tests/unit/application/observability/test_observer.py` (635 строк)
- **Статус**: ✅ Полностью реализовано
- **Дата верификации**: 2025-12-29

### Текущее Состояние

Согласно `docs/refactoring-plan.md:764-804`:

| Задача | Статус | Доказательство |
|--------|--------|----------------|
| O2: TracingContext в PipelineExecutor | ✅ РЕАЛИЗОВАНО | `executor.py:167-189,421-457` |
| O3: Graceful shutdown для tracer | ✅ РЕАЛИЗОВАНО | `observer.py:149-160` |
| O4: Тесты observer | ✅ РЕАЛИЗОВАНО | `test_observer.py` — 30+ тестов |

### Существующие Тесты Observer

| Тест | Строки | Проверяет |
|------|--------|-----------|
| `test_pipeline_observer_success` | 62-88 | Успешное выполнение |
| `test_pipeline_observer_failure` | 90-109 | Обработка ошибок |
| `test_pipeline_observer_shutdown` | 112-132 | Graceful shutdown |
| `test_observer_records_duration` | 138-168 | O4: Histogram duration |
| `test_observer_tracks_errors` | 170-195 | O4: Error counter |
| `test_observer_graceful_shutdown` | 198-222 | O4: Span flush |
| `test_observer_handles_close_error` | 224-246 | O3: Close error handling |
| `TestLifecyclePhase` | 252-271 | Enum values |
| `TestObserverEmitEvent` | 274-339 | Event emission |
| `TestObserverEmitPhase` | 342-415 | Phase events |
| `TestObserverHealthCheckEvents` | 418-467 | Health check events |
| `TestObserverDQEvents` | 470-522 | DQ anomaly events |
| `TestObserverVacuumEvents` | 525-572 | VACUUM events |
| `TestObserverSmokeTest` | 578-635 | Full lifecycle |

### Заключение

**Задача 3 не требует работы.** Все тесты O2-O4 уже реализованы и проходят.

Рекомендуется обновить `docs/refactoring-plan.md` — пометить критерии приёмки Фазы 4 как завершённые:

```diff
### Критерии приёмки Фазы 4
- [x] Tracing spans покрывают ключевые операции
- [x] Observer тесты проходят
- [x] Graceful shutdown работает
- [ ] Sampling настраивается для production (1/100)
```

---

## Сводка Изменений

### Файлы для Изменения

| Файл | Задача | Тип Изменения |
|------|--------|---------------|
| `docs/RULES.md` | 1 | Расширение §6.1 |
| `infrastructure/export/csv_exporter.py` | 2 | DI для logger |
| `infrastructure/observability/lineage.py` | 2 | DI для logger |
| `infrastructure/observability/anomaly/monitor.py` | 2 | DI для logger |
| `infrastructure/observability/server.py` | 2 | Добавить комментарий |
| `composition/factories/*.py` | 2 | Инжекция logger |
| `tests/unit/infrastructure/**` | 2 | Обновить fixtures |
| `docs/refactoring-plan.md` | 3 | Обновить статус O2-O4 |

### Зависимости

```
Задача 1 (RULES.md) ←── независима
Задача 2 (Logging)  ←── независима
Задача 3 (Observer) ←── ✅ завершена
```

### Общая Оценка

| Задача | Оценка | Реальная Работа |
|--------|--------|-----------------|
| 1. RULES.md | 0.5 дня | 0.5 дня |
| 2. Logging | 1 день | 1 день |
| 3. Observer | 1 день | 0 (уже сделано) |
| **Итого** | 2.5 дня | **1.5 дня** |

---

## Чек-лист Перед Началом

- [ ] `make lint && make test` проходят
- [ ] Git branch создан: `claude/refactoring-plan-fURYp`
- [ ] Прочитаны `docs/RULES.md` и `CLAUDE.md`
- [ ] Понятны критерии приёмки каждой задачи

---

*Строй надёжно. Верифицируй перед изменением. Документируй с доказательствами.*
