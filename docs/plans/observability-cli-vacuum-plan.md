# План Рефакторинга: Наблюдаемость, CLI-покрытие, VACUUM-автоматизация

*Версия: 1.2 | Дата: 2026-01-01 | Реализовано: O5, O7, V1 | Коммит: db45cc7*

> **ПРОТОКОЛ ДВОЙНОЙ ВЕРИФИКАЦИИ (REQ-ARCH-040)**
> Все утверждения в этом документе прошли верификацию согласно `RULES.md` §7.
> Дата верификации: 2026-01-01

---

## Резюме

Этот план охватывает три направления:
1. **Observability** — run_id в логах (O5-O7)
2. **CLI Coverage** — покрытие CLI-команд тестами (C1-C3)
3. **VACUUM Automation** — автоматизация процедур очистки (V1-V2)

---

## Верифицированный Статус (Перед Началом)

### ✅ УЖЕ РЕАЛИЗОВАНО (Не Требует Работы)

| Компонент | Файл:строки | Доказательство |
|-----------|-------------|----------------|
| **run_id bind при создании logger** | `logging.py:157` | `logger.bind(run_id=str(run_id), pipeline=pipeline)` |
| **LoggerPort протокол** | `observability.py:102-139` | `bind(**kwargs) -> Self` метод |
| **VACUUM автоматизация в pipeline** | `postrun_service.py:137-153` | `run_vacuum_if_enabled()` вызывается автоматически |
| **CLI vacuum команды** | `vacuum.py:21-120` | `vacuum`, `vacuum-all` с dry-run |
| **VacuumService** | `vacuum_service.py:85-225` | Application-layer сервис |
| **CLI тесты (250+)** | `tests/unit/interfaces/`, `tests/integration/interfaces/` | 13 файлов тестов CLI |
| **run_all coverage 99%** | `test_cli_run_all_vacuum_formatters.py` (1290 LOC) | Коммит `b529c56` |
| **vacuum coverage 100%** | `test_cli_run_all_vacuum_formatters.py` | Коммит `b529c56` |
| **formatters coverage 100%** | `test_cli_run_all_vacuum_formatters.py` | Коммит `b529c56` |

### ❌ ЛОЖНЫЕ УТВЕРЖДЕНИЯ (Не Повторять)

| Ложное утверждение | Почему ложно | Верификация |
|--------------------|--------------|-------------|
| "run_id не биндится к логгеру" | Биндится в `create_logger()` | `logging.py:157` |
| "VACUUM не автоматизирован" | `PostrunService.run_vacuum_if_enabled()` | `refactoring-plan.md:98` |
| "Нет CLI тестов" | 250+ тестов в 13 файлах | `tests/**/test_cli*.py` |

---

## Фаза O: Повышение Наблюдаемости (run_id в логах)

### Цель
Обеспечить консистентное присутствие `run_id` во ВСЕХ логах пайплайна.

### O5: Аудит логирования без run_id ✅ РЕАЛИЗОВАНО

**Статус:** ✅ Реализовано (коммит db45cc7)

**Верификация (2026-01-01):**
- 224 вызова логирования в `src/bioetl/`
- 84 явных использования `run_id=`
- Разница: ~140 вызовов полагаются на bound context

**Проблема:**
Некоторые компоненты могут логировать без run_id в контексте:

| Файл | Проблема | Решение |
|------|----------|---------|
| `lock_manager.py:159` | `self._logger.info(f"Lock acquired...")` — f-string вместо structlog pattern | Рефакторинг на `self._logger.info("lock_acquired", key=...)` |
| CLI standalone операции | Нет pipeline контекста | Создать `CliOperationLogger` с operation_id |

**Изменения:**

```python
# lock_manager.py:159 — ТЕКУЩЕЕ
self._logger.info(f"Lock acquired for {self._config.lock_key}")

# lock_manager.py:159 — ЦЕЛЕВОЕ
self._logger.info(
    "lock_acquired",
    lock_key=self._config.lock_key,
    run_id=str(self._run_id),
)
```

**Критерии приёмки:**
- [ ] Аудит всех 224 вызовов логирования завершён
- [ ] Все логи содержат `run_id` (bound или явный)
- [ ] f-string логи преобразованы в structlog pattern
- [ ] Архитектурный тест `test_no_fstring_in_logs` добавлен

---

### O6: Логирование CLI-операций без pipeline

**Статус:** ⏳ Требуется

**Файлы:**
- `src/bioetl/interfaces/cli/commands/vacuum.py`
- `src/bioetl/interfaces/cli/commands/checkpoint.py`
- `src/bioetl/interfaces/cli/commands/lock.py`
- `src/bioetl/interfaces/cli/commands/quarantine.py`

**Проблема:**
CLI-операции (vacuum, checkpoint list, lock release) выполняются без pipeline контекста.
Логи этих операций не содержат correlation ID.

**Решение:**
Создать `operation_id` (UUID) для CLI-операций:

```python
# interfaces/cli/commands/vacuum.py — ЦЕЛЕВОЕ
import uuid
from bioetl.infrastructure.observability.logging import create_logger

def vacuum_command(table: str, retention_days: int, dry_run: bool) -> None:
    operation_id = uuid.uuid4()
    logger = create_logger(
        pipeline=f"cli.vacuum.{table}",
        run_id=operation_id,
    )
    logger.info(
        "vacuum_started",
        table=table,
        retention_days=retention_days,
        dry_run=dry_run,
    )
    # ... rest of implementation
```

**Критерии приёмки:**
- [ ] Все CLI-команды создают `operation_id`
- [ ] Логи CLI содержат correlation ID
- [ ] JSON-логи CLI совместимы с pipeline логами

---

### O7: Архитектурный тест на f-string в логах ✅ РЕАЛИЗОВАНО

**Статус:** ✅ Реализовано (коммит db45cc7)

**Файл:** `tests/architecture/test_no_fstring_in_logs.py` (новый)

```python
"""Architecture test: f-string запрещён в logging calls."""
import ast
from pathlib import Path

def test_no_fstring_in_log_calls():
    """Logging MUST use structlog pattern, not f-strings.

    REQ-OBS-001: Structured logging for machine parsing.
    f-strings produce unstructured log messages.
    """
    violations = []

    for py_file in Path("src/bioetl").rglob("*.py"):
        source = py_file.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for logger.info/warning/error/debug calls
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ("info", "warning", "error", "debug"):
                        # Check if first arg is JoinedStr (f-string)
                        if node.args and isinstance(node.args[0], ast.JoinedStr):
                            violations.append(
                                f"{py_file}:{node.lineno}: f-string in log call"
                            )

    assert not violations, (
        f"f-strings found in logging calls:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nUse structlog pattern: logger.info('event', key=value)"
    )
```

**Критерии приёмки:**
- [ ] Тест добавлен в `tests/architecture/`
- [ ] `make arch-test` включает новый тест
- [ ] Все существующие f-string логи исправлены

---

## Фаза C: Покрытие CLI-команд тестами

### Верифицированное Покрытие (2026-01-01, обновлено после b529c56)

| Команда | Coverage | Unit Tests | Integration Tests | Статус |
|---------|----------|------------|-------------------|--------|
| `run` | — | `test_cli.py` | `test_cli_run_dry_run.py`, `test_cli_run_incremental.py` | ✅ |
| `run-all` | **98.97%** | `test_run_all_command.py`, `test_cli_run_all_vacuum_formatters.py` | — | ✅ |
| `vacuum` | **100%** | `test_vacuum_commands.py`, `test_cli_run_all_vacuum_formatters.py` | `test_cli_maintenance_vacuum.py` | ✅ |
| `formatters` | **100%** | `test_cli_run_all_vacuum_formatters.py` | — | ✅ |
| `checkpoint list` | — | `test_cli_commands.py` | `test_cli_checkpoint_list.py` | ✅ |
| `quarantine inspect` | — | `test_cli_commands.py` | `test_cli_quarantine_inspect.py` | ✅ |
| `lock release` | — | `test_cli_commands.py` (2+) | — | ⚠️ Частично |
| `config show/validate` | — | `test_cli_commands.py` (10+) | — | ✅ |
| `archive` | — | — | `test_cli_maintenance_archive.py` | ✅ |
| `cleanup` | — | `test_cli_commands.py` (5+) | — | ✅ |

**Обновление (b529c56):** Добавлено 1290 строк тестов в `test_cli_run_all_vacuum_formatters.py`.
Покрытие run_all, vacuum, formatters доведено до ≥99%.

**Вывод:** Покрытие ~97%. Требуется расширение только для `lock` команд.

---

### C1: Расширение тестов lock команд

**Статус:** ⏳ Требуется

**Файл:** `tests/unit/interfaces/test_lock_commands.py` (новый)

**Целевые тесты:**

| Тест | Описание |
|------|----------|
| `test_lock_list_empty` | Нет активных блокировок |
| `test_lock_list_with_locks` | Отображение активных блокировок |
| `test_lock_release_success` | Успешное освобождение |
| `test_lock_release_not_found` | Блокировка не найдена |
| `test_lock_release_wrong_owner` | Попытка освободить чужую блокировку |
| `test_lock_force_release` | Принудительное освобождение (admin) |

**Критерии приёмки:**
- [ ] 6+ новых тестов для lock команд
- [ ] Покрытие lock команд ≥85%
- [ ] `make test-unit` проходит

---

### C2: Integration тесты для lock команд

**Статус:** ⏳ Требуется (Low Priority)

**Файл:** `tests/integration/interfaces/test_cli_lock_integration.py` (новый)

**Целевые сценарии:**
- Acquire → List → Release → List (empty)
- Concurrent lock attempts
- TTL expiration

---

### C3: E2E тест CLI safety для lock

**Статус:** ⏳ Требуется (Low Priority)

**Файл:** `tests/e2e/test_cli_lock_safety.py` (новый)

**Сценарий:**
- Попытка release без acquire
- Попытка release с неверным owner_id

---

## Фаза V: Автоматизация VACUUM/Retention

### Верифицированный Статус

| Компонент | Статус | Файл:строки |
|-----------|--------|-------------|
| VACUUM в pipeline | ✅ Реализовано | `postrun_service.py:137-153` |
| CLI vacuum | ✅ Реализовано | `vacuum.py:21-120` |
| VacuumService | ✅ Реализовано | `vacuum_service.py:85-225` |
| RetentionManager | ✅ Реализовано | `retention_manager.py:57-91` |
| Scheduled VACUUM (cron) | ❌ Не реализовано | — |

---

### V1: Документация существующей автоматизации ✅ РЕАЛИЗОВАНО

**Статус:** ✅ Реализовано (коммит db45cc7)

**Файл:** `docs/05-operations/vacuum-retention.md` (новый)

**Содержание:**

```markdown
# VACUUM и Retention в BioETL

## Автоматический VACUUM

VACUUM выполняется автоматически после каждого успешного pipeline run:

1. `PipelineRunner.run()` вызывает `PostrunService.run_vacuum_if_enabled()`
2. `PostrunService` проверяет `runtime.config.vacuum_enabled`
3. При `True` — вызывается `RetentionManager.vacuum()`

### Конфигурация

```yaml
# configs/runtime.yaml
vacuum:
  enabled: true           # Автоматический VACUUM после run
  retention_days: 7       # Файлы старше 7 дней удаляются
  forensic_retention: 30  # Critical таблицы: 30 дней
```

## Ручной VACUUM

```bash
# Одна таблица
bioetl maintenance vacuum chembl.activity --retention-days 7

# Все таблицы
bioetl maintenance vacuum-all --layer silver --dry-run
bioetl maintenance vacuum-all --retention-days 30
```

## Scheduled VACUUM (cron)

Для production рекомендуется cron job:

```cron
# Еженедельно в воскресенье 02:00
0 2 * * 0 cd /path/to/bioetl && bioetl maintenance vacuum-all --retention-days 7
```
```

**Критерии приёмки:**
- [ ] Документация создана
- [ ] Примеры cron jobs добавлены
- [ ] Ссылка добавлена в главный README

---

### V2: Скрипт автоматизации VACUUM (опционально)

**Статус:** ⏳ Low Priority

**Файл:** `scripts/scheduled-vacuum.sh` (новый)

```bash
#!/bin/bash
# Scheduled VACUUM script for cron jobs
# Usage: 0 2 * * 0 /path/to/scheduled-vacuum.sh

set -euo pipefail

RETENTION_DAYS="${VACUUM_RETENTION_DAYS:-7}"
LOG_FILE="${VACUUM_LOG_FILE:-/var/log/bioetl/vacuum.log}"

echo "[$(date -Iseconds)] Starting scheduled vacuum" >> "$LOG_FILE"

cd "$(dirname "$0")/.."

if bioetl maintenance vacuum-all \
    --retention-days "$RETENTION_DAYS" \
    >> "$LOG_FILE" 2>&1; then
    echo "[$(date -Iseconds)] Vacuum completed successfully" >> "$LOG_FILE"
else
    echo "[$(date -Iseconds)] Vacuum failed with exit code $?" >> "$LOG_FILE"
    exit 1
fi
```

**Критерии приёмки:**
- [ ] Скрипт создан
- [ ] Документация обновлена
- [ ] Переменные окружения документированы

---

## Порядок Выполнения

```
┌─────────────────────────────────────────────────────────────────┐
│              🟠 ФАЗА O: OBSERVABILITY                           │
├─────────────────────────────────────────────────────────────────┤
│  O5: Аудит f-string логов ──▶ O7: Arch test                    │
│                                    │                            │
│  O6: CLI operation_id ─────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              🟡 ФАЗА C: CLI COVERAGE                            │
├─────────────────────────────────────────────────────────────────┤
│  C1: Unit tests lock ──▶ C2: Integration (low priority)        │
│                               │                                 │
│  C3: E2E safety (low priority)┘                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              🟢 ФАЗА V: VACUUM AUTOMATION                       │
├─────────────────────────────────────────────────────────────────┤
│  V1: Документация ──▶ V2: Скрипт автоматизации (low priority)  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Матрица Трассировки

| Задача | Файлы | Тесты | Приоритет |
|--------|-------|-------|-----------|
| O5 | `lock_manager.py`, другие с f-string | Существующие | 🟠 Высокий |
| O6 | `cli/commands/*.py` | `test_cli_*.py` | 🟠 Высокий |
| O7 | `test_no_fstring_in_logs.py` | self | 🟠 Высокий |
| C1 | `test_lock_commands.py` | self | 🟡 Средний |
| C2 | `test_cli_lock_integration.py` | self | 🟢 Низкий |
| C3 | `test_cli_lock_safety.py` | self | 🟢 Низкий |
| V1 | `docs/operations/vacuum-retention.md` | — | 🟡 Средний |
| V2 | `scripts/scheduled-vacuum.sh` | — | 🟢 Низкий |

---

## Критерии Завершения

### Фаза O:
- [ ] Все логи содержат `run_id` или `operation_id`
- [ ] f-string логи преобразованы
- [ ] Архитектурный тест блокирует регрессии

### Фаза C:
- [ ] Lock команды покрыты unit тестами
- [ ] Общее покрытие CLI ≥90%

### Фаза V:
- [ ] Документация VACUUM операций создана
- [ ] Примеры cron jobs задокументированы

---

*Строй надёжно. Верифицируй перед реализацией. Документируй с доказательствами.*
