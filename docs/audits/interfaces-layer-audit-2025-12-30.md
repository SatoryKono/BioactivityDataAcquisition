# Архитектурный Аудит Слоя `interfaces`

**Дата:** 2025-12-30
**Проект:** BioETL
**Ветка:** `claude/ddd-architecture-analysis-lIcLO`
**Автор:** Senior Software Architect (DDD & Clean Architecture)

---

## Краткое резюме аудита

- **Слой interfaces структурирован корректно** — 1478 LOC, разделён на CLI (`cli/`) и Orchestration (`orchestration/`), следует паттерну "тонкий контроллер".
- **Выявлено дублирование DTO** — классы `RunOptions`, `RunResult`, `RunStatus` дублируются между `composition/entrypoints.py` и `application/services/pipeline_runner_service.py`.
- **Обнаружены нарушения границ слоёв** — прямой импорт `infrastructure` в `interfaces` (`observability.py`, `config.py`).
- **Локальные Protocol-определения** — `_ShutdownSignalLike` и `_ShutdownServiceLike` в `signals.py` дублируют функциональность `domain/ports/shutdown.py`.
- **`BatchRunResult` живёт в неправильном месте** — DTO уровня приложения определён в CLI-команде (`run_all.py`).
- **Deprecated-команда `run_chembl_all`** — явно помечена как deprecated, готова к удалению.
- **Общая оценка: слой interfaces в хорошем состоянии**, требуется minor рефакторинг для выравнивания с принципами DDD.

---

## Карта слоя interfaces

### Структура пакетов

```
src/bioetl/interfaces/          # 1478 LOC total
├── __init__.py                 # 1 LOC (пустой модуль)
├── observability.py            # 48 LOC (фасад для metrics server)
├── cli/                        # CLI пакет
│   ├── __init__.py             # 44 LOC (re-export для backward compat)
│   ├── __main__.py             # 7 LOC (entry point)
│   ├── main.py                 # 48 LOC (CLI группа и main())
│   ├── exit_codes.py           # 125 LOC (ExitCode enum + маппинг)
│   ├── formatters.py           # 149 LOC (presentation-only)
│   └── commands/               # Команды CLI
│       ├── __init__.py         # 8 LOC
│       ├── run.py              # 208 LOC (основная команда)
│       ├── run_all.py          # 412 LOC (batch execution)
│       ├── run_helpers.py      # 128 LOC (helpers для run)
│       ├── checkpoint.py       # 36 LOC
│       ├── quarantine.py       # 41 LOC
│       ├── lock.py             # 95 LOC
│       ├── config.py           # 158 LOC
│       ├── maintenance.py      # 27 LOC (группа команд)
│       ├── vacuum.py           # 120 LOC
│       ├── archive.py          # 49 LOC
│       └── cleanup.py          # 58 LOC
└── orchestration/              # Signal handling
    ├── __init__.py             # 16 LOC
    └── signals.py              # 89 LOC
```

### Ответственность модулей

| Модуль | Ответственность | Зависимости внутрь | Зависимости наружу |
|--------|-----------------|--------------------|--------------------|
| `observability.py` | Фасад для запуска metrics server | — | `infrastructure.observability.server` (нарушение!) |
| `cli/main.py` | Entry point, регистрация команд | `composition.factories` | `click` |
| `cli/exit_codes.py` | Exit codes enum, exception mapping | — | — |
| `cli/formatters.py` | Presentation-only форматирование | `application.core.cleanup_service` (TYPE_CHECKING) | `click` |
| `cli/commands/run.py` | Pipeline execution command | `application.services`, `composition.entrypoints` | `click`, `asyncio` |
| `cli/commands/run_all.py` | Batch pipeline execution | `application.services`, `composition.entrypoints` | `click`, `asyncio` |
| `cli/commands/config.py` | Config inspection | `composition.registry` | `infrastructure.config` (нарушение!) |
| `orchestration/signals.py` | OS signal → ShutdownService | `domain.ports.LoggerPort` | `signal`, `asyncio` |

---

## Найденные проблемы

### 1. Дублирующие и пересекающиеся интерфейсы и модели

#### 1.1 Дублирование RunOptions, RunResult, RunStatus

**Локации:**
- `composition/entrypoints.py:102-228` — определяет `RunOptions`, `RunStatus`, `RunResult`
- `application/services/pipeline_runner_service.py:34-143` — определяет **идентичные** классы

**Анализ:**
- Классы практически идентичны (одинаковые поля, docstrings)
- `RunStatus` в `pipeline_runner_service.py` имеет дополнительное значение `DRY_RUN`
- `RunResult` в `pipeline_runner_service.py` имеет дополнительное поле `error_type` и свойство `is_success`

**Влияние:**
- Confusion при импорте — непонятно, какой класс использовать
- CLI импортирует из `application.services`, entrypoints дублирует определения
- Нарушает принцип DRY

**Рекомендация:**
```
[ВЫСОКИЙ ПРИОРИТЕТ]
Удалить дублирование. Канонические определения — в application/services.
composition/entrypoints.py должен реэкспортировать из application.services.
```

#### 1.2 Локальные Protocol-дубликаты в signals.py

**Локация:** `interfaces/orchestration/signals.py:23-34`

```python
@runtime_checkable
class _ShutdownSignalLike(Protocol):
    def request(self) -> None: ...

@runtime_checkable
class _ShutdownServiceLike(Protocol):
    async def initiate_shutdown(self, reason: str) -> None: ...
```

**Анализ:**
- `_ShutdownServiceLike` дублирует `domain.ports.ShutdownPort`
- `_ShutdownSignalLike` — legacy для обратной совместимости

**Рекомендация:**
```
[СРЕДНИЙ ПРИОРИТЕТ]
1. Заменить _ShutdownServiceLike на импорт ShutdownPort из domain.ports
2. После удаления setup_shutdown_handlers() удалить _ShutdownSignalLike
```

#### 1.3 BatchRunResult в неправильном месте

**Локация:** `interfaces/cli/commands/run_all.py:33-56`

**Анализ:**
- `BatchRunResult` — это DTO уровня application, не presentation
- Содержит бизнес-логику (`all_succeeded` property)
- Используется только в `run_all.py`, но экспортируется в `__all__`

**Рекомендация:**
```
[НИЗКИЙ ПРИОРИТЕТ]
Если понадобится batch-execution из других интерфейсов (REST API):
- Перенести BatchRunResult в application/services
- Создать BatchPipelineService
```

---

### 2. Неиспользуемые или избыточные абстракции

#### 2.1 Deprecated команда run_chembl_all

**Локация:** `interfaces/cli/commands/run_all.py:335-404`

**Анализ:**
- Явно помечена `[DEPRECATED]`
- Делегирует в `run_all` с `source="chembl"`
- Занимает 70 LOC

**Рекомендация:**
```
[СРЕДНИЙ ПРИОРИТЕТ]
Удалить после следующего major-релиза.
Добавить в CHANGELOG note о breaking change.
```

#### 2.2 setup_shutdown_handlers (deprecated)

**Локация:** `interfaces/orchestration/signals.py:61-88`

**Анализ:**
- Docstring: "Deprecated: Use register_signal_handlers() with ShutdownService instead"
- Используется для backward-compat с legacy `ShutdownSignal`

**Рекомендация:**
```
[СРЕДНИЙ ПРИОРИТЕТ]
Удалить после миграции всех callsites на register_signal_handlers().
```

#### 2.3 Re-export _private функций в cli/__init__.py

**Локация:** `interfaces/cli/__init__.py:26-31`

```python
from bioetl.interfaces.cli.commands.run import (
    _get_runner_logger,
    _handle_destructive_run_confirmation,
    _preview_cleanup,
)
```

**Анализ:**
- Экспорт `_private` функций (с underscore) противоречит Python conventions
- Комментарий: "for backward compatibility with tests"
- Tests должны использовать публичный API

**Рекомендация:**
```
[НИЗКИЙ ПРИОРИТЕТ]
Рефакторить тесты, чтобы использовать публичный API.
Удалить re-export _private функций.
```

---

### 3. Нарушения принципов DDD и границ слоёв

#### 3.1 Прямой импорт infrastructure в interfaces

**Нарушение 1 — observability.py:8-13:**
```python
from bioetl.infrastructure.observability.server import (
    MetricsServerError,
)
from bioetl.infrastructure.observability.server import (
    start_metrics_server as _start_server,
)
```

**Нарушение 2 — config.py:14:**
```python
from bioetl.infrastructure.config import get_settings, load_pipeline_config
```

**Анализ:**
По матрице импортов из CLAUDE.md:

| Из ↓ / В → | infrastructure |
|------------|----------------|
| **interfaces** | ✅ |

Матрица разрешает импорт `infrastructure` в `interfaces`! Это **НЕ нарушение** по правилам проекта.

**Однако**, с точки зрения чистой архитектуры DDD:
- `interfaces` должен зависеть от абстракций (`domain.ports`), не от `infrastructure`
- Для observability лучше использовать порт `MetricsPort` и инжектировать реализацию

**Рекомендация:**
```
[НИЗКИЙ ПРИОРИТЕТ / КОСМЕТИЧЕСКИЙ]
Текущая реализация соответствует правилам проекта.
Для более чистой архитектуры можно:
1. Создать MetricsServerPort в domain/ports
2. Реализацию оставить в infrastructure
3. Инжектировать через composition/bootstrap
```

#### 3.2 composition/registry импортируется напрямую

**Локации:**
- `cli/commands/run_helpers.py:23`
- `cli/commands/run_all.py:24`
- `cli/commands/config.py:13`

**Анализ:**
- `composition.registry.get_default_registry()` используется для валидации pipelines
- Это корректно — `interfaces` может зависеть от `composition`
- Альтернатива: использовать `PipelineRunnerService.list_pipelines()`

**Рекомендация:**
```
[НЕТ ДЕЙСТВИЯ]
Текущий подход корректен. Переход на service добавит overhead.
```

#### 3.3 Бизнес-логика в CLI (ложное срабатывание)

При первичном анализе могло показаться, что `handle_destructive_run_confirmation()` содержит бизнес-логику.

**Верификация (`run_helpers.py:98-127`):**
- Функция обрабатывает **UI confirmation** — это законная ответственность `interfaces`
- Логика: if rebuild/backfill → show warning → get user confirmation
- Это **presentation concern**, не business logic

**Вывод:** НЕ является нарушением. Подтверждения и UI-flow — ответственность interfaces слоя.

---

## Рекомендации по рефакторингу

### Высокий приоритет

| # | Задача | Файлы | Сложность | Статус |
|---|--------|-------|-----------|--------|
| H1 | Устранить дублирование `RunOptions`/`RunResult`/`RunStatus` | `composition/entrypoints.py` | Низкая | ✅ Выполнено |

**Детали H1:**
```python
# composition/entrypoints.py — заменить определения на реэкспорт:
from bioetl.application.services import RunOptions, RunResult, RunStatus

# Удалить строки 102-228 (определения классов)
```

### Средний приоритет

| # | Задача | Файлы | Сложность | Статус |
|---|--------|-------|-----------|--------|
| M1 | Удалить deprecated `run_chembl_all` | `run_all.py`, `main.py` | Низкая | ✅ Выполнено |
| M2 | Удалить deprecated `setup_shutdown_handlers` | `signals.py` | Низкая | ✅ Выполнено |
| M3 | Использовать `ShutdownPort` вместо локального Protocol | `signals.py` | Низкая | ✅ Выполнено |

**Детали M3:**
```python
# signals.py — заменить:
from bioetl.domain.ports import ShutdownPort

# Удалить _ShutdownServiceLike, использовать ShutdownPort
```

### Низкий приоритет / Косметические

| # | Задача | Файлы | Сложность | Статус |
|---|--------|-------|-----------|--------|
| L1 | Рефакторить тесты для использования публичного API | `tests/unit/interfaces/` | Средняя | ✅ Выполнено |
| L2 | Удалить re-export `_private` функций | `cli/__init__.py` | Низкая | ✅ Выполнено |
| L3 | Перенести `BatchRunResult` в application (опционально) | `run_all.py` | Средняя | ⏳ Отложено |

---

## Целевая структура слоя interfaces

После применения рекомендаций:

```
src/bioetl/interfaces/
├── __init__.py                 # Пустой или минимальный export
├── observability.py            # Фасад (OK, разрешено по правилам)
├── cli/
│   ├── __init__.py             # Только публичный API: cli, main
│   ├── __main__.py
│   ├── main.py
│   ├── exit_codes.py
│   ├── formatters.py
│   └── commands/
│       ├── run.py
│       ├── run_all.py          # БЕЗ run_chembl_all
│       ├── run_helpers.py
│       ├── checkpoint.py
│       ├── quarantine.py
│       ├── lock.py
│       ├── config.py
│       ├── maintenance.py
│       ├── vacuum.py
│       ├── archive.py
│       └── cleanup.py
└── orchestration/
    ├── __init__.py             # Только register_signal_handlers
    └── signals.py              # БЕЗ setup_shutdown_handlers
```

---

## Допущения и ограничения

### Допущения

1. **Матрица импортов из CLAUDE.md актуальна** — interfaces может импортировать infrastructure
2. **Deprecated функции готовы к удалению** — нет внешних зависимостей вне проекта
3. **Тесты могут быть рефакторены** — нет жёстких требований на backward compat для test internals

### Чувствительные выводы

- Рекомендация H1 (устранение дублирования) может потребовать изменения импортов в зависимых модулях
- Удаление deprecated команд (M1, M2) — breaking change, требует version bump

### Дополнительные артефакты для улучшения аудита

- Диаграмма зависимостей между слоями (PlantUML)
- ADR по решению о допустимости `interfaces → infrastructure`
- Changelog с историей deprecated функций

---

## Итоговая оценка

| Критерий | Оценка | Комментарий |
|----------|--------|-------------|
| **Структура** | 4/5 | Хорошее разделение, но есть дублирование DTO |
| **Границы слоёв** | 4/5 | Соответствует правилам проекта, minor violations по DDD |
| **Чистота кода** | 4/5 | Deprecated код должен быть удалён |
| **Именование** | 5/5 | Ubiquitous language соблюдается |
| **Тестируемость** | 4/5 | Re-export _private функций — tech debt |

**Общая оценка: 4.2/5** — слой interfaces в хорошем состоянии, требуется minor рефакторинг.

---

*Строй надёжно. Документируй честно. Спрашивай смело.*
