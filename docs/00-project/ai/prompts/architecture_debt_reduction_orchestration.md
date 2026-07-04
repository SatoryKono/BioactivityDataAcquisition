*Статус: internal-only (historical prompt)*

Текущая runtime-surface:

- `python -m scripts.engineering.qa generate-debt-tasks`
- `python -m scripts.engineering.qa reduce-architecture-debt`
- `.codex/agents/py-architecture-debt-bot.md`
- `configs/` изменения выполняются только через `py-config-bot`

# Architecture Debt Reduction — Orchestration Prompt

*Версия: 2.0.0 | Дата: 2026-03-08*

## Назначение

автоматическое устранение architecture debt
на основе задач из `reports/quality/tasks_architecture_metric_exemptions_*.json`.

______________________________________________________________________

## 1. Инициализация

### 1.1 Загрузка задач

1. Найди все файлы `reports/quality/tasks_architecture_metric_exemptions_*.json`.
1. При наличии нескольких файлов — используй файл с **наиболее поздней датой** в имени.
1. Прочитай JSON и извлеки массив `tasks[]`.

### 1.2 Фильтрация и классификация задач

Разбей задачи на **категории действий** по `registry` и `status`:

| Категория           | Условие                                                                                                                           | Действие                                                                                                     |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **STALE_EXEMPTION** | `status == "within_limit"` И `current_value` значительно ниже layer default limit (файл/класс уже не нарушает базовый лимит слоя) | Удалить exemption из YAML, обновить debt_scorecard baseline                                                  |
| **REDUCE_TO_LIMIT** | `status == "over_limit"` ИЛИ `delta_to_limit >= 0`                                                                                | Рефакторинг: уменьшить LOC/CC до допустимого порога                                                          |
| **GOD_OBJECT**      | `registry == "god_object"`                                                                                                        | Увеличить delegation patterns (≥3 уникальных `self._component.method()`)                                     |
| **COMPLEXITY**      | `registry in ["function_complexity", "domain_complexity"]`                                                                        | Снизить CC через ранние выходы, extract method, strategy dispatch                                            |
| **NEAR_LIMIT**      | `status == "within_limit"` И `delta_to_limit` в диапазоне [-5, 0]                                                                 | Приоритетная задача: небольшой рост LOC сделает exemption stale. Уменьшить значение, затем удалить exemption |
| **SAFE_MARGIN**     | `status == "within_limit"` И `delta_to_limit < -15`                                                                               | Низкий приоритет. Exemption жива, значение далеко от лимита. Можно отложить                                  |

### 1.3 Определение layer default limits

Для проверки STALE_EXEMPTION используй **базовые лимиты слоёв** (без exemptions):

```yaml
file_size_limits:  # LOC per file
  domain: 305
  application: 500
  composition: 350
  infrastructure: 650
  interfaces: 400

class_size: 300        # LOC per class (all layers)
function_complexity:
  domain: 5            # max CC
  application: 10
  infrastructure: 15
god_object:
  min_delegation: 3    # min unique self._component.method() patterns for classes >300 LOC
```

**STALE_EXEMPTION** = файл/класс уже ниже базового лимита слоя (не `limit_value` из exemption, а дефолтного лимита архитектурного теста).

### 1.4 Приоритизация

Порядок обработки задач:

1. **STALE_EXEMPTION** (быстрый выигрыш: просто удалить запись)
1. **GOD_OBJECT** (архитектурный дефект)
1. **COMPLEXITY** (domain purity)
1. **NEAR_LIMIT** (превентивный рефакторинг)
1. **REDUCE_TO_LIMIT** (активные нарушения)
1. **SAFE_MARGIN** (можно отложить)

______________________________________________________________________

## 2. Выбор агента по типу задачи

### 2.1 Таблица агентов

| Категория задачи                 | Агент-исполнитель        | `subagent_type` | `model` | Пояснение                                                                                    |
| -------------------------------- | ------------------------ | --------------- | ------- | -------------------------------------------------------------------------------------------- |
| **STALE_EXEMPTION**              | Оркестратор (ты сам)     | —               | —       | Простое удаление записи из YAML. Не требует агента.                                          |
| **GOD_OBJECT**                   | Production code напрямую | —               | —       | Добавить delegation patterns. Малые изменения — пиши сам. Большие — используй `py-debug-bot` |
| **COMPLEXITY**                   | Production code напрямую | —               | —       | Extract method, simplify branching. Малые изменения.                                         |
| **REDUCE_TO_LIMIT** (file_size)  | Production code напрямую | —               | —       | Декомпозиция файла: extract module, move helpers                                             |
| **REDUCE_TO_LIMIT** (class_size) | Production code напрямую | —               | —       | Extract mixin, extract strategy                                                              |
| **NEAR_LIMIT**                   | Production code напрямую | —               | —       | Trim LOC через удаление пустых строк, объединение imports                                    |

> **Правило**: Production-код пишет оркестратор напрямую (без субагента).
> Субагенты используются для **тестирования**, **документации** и **аудита**.

### 2.2 Агенты сопровождения (после каждой задачи)

| Роль                         | `subagent_type`          | `model`  | Когда запускать                                                          |
| ---------------------------- | ------------------------ | -------- | ------------------------------------------------------------------------ |
| **Тестирование**             | `py-test-bot`            | `sonnet` | После каждого исполнителя. Проверяет, что изменения не сломали тесты.    |
| **Doc-sync**                 | `py-doc-bot`             | `haiku`  | После каждого исполнителя. Синхронизирует docstrings/docs с изменениями. |
| **Финальный аудит (arch)**   | `py-audit-bot`           | `opus`   | После завершения ВСЕХ задач. Полная проверка архитектуры.                |
| **Финальный аудит (review)** | `py-review-orchestrator` | `opus`   | После завершения ВСЕХ задач. Code review изменений.                      |

### 2.3 Шаблоны промтов для субагентов

#### py-test-bot (тестирование после исправления)

```
task_id={task.id}-TEST, phase=final

Проверь изменения в файле `{task.target_file}`.
Изменения: {краткое описание что сделано}.

НЕ удаляй docstrings. Запусти:
1. `uv run pytest {specific_test_files} -v --tb=short`
2. `uv run pytest tests/architecture/test_code_metrics.py::{relevant_test_class} -v --tb=short`
3. `uv run mypy {task.target_file} --strict`

Все отчёты и артефакты сохраняй ТОЛЬКО в reports/exemptions_refactoring/.
НЕ создавай файлы в корне проекта.

Отчитайся по результатам.
```

**Выбор `{specific_test_files}`:**

| Слой target_file                      | Тестовый путь                                           |
| ------------------------------------- | ------------------------------------------------------- |
| `infrastructure/storage/`             | `tests/unit/infrastructure/storage/ -k "{module_name}"` |
| `infrastructure/adapters/chembl/`     | `tests/unit/infrastructure/adapters/chembl/`            |
| `infrastructure/adapters/http/`       | `tests/unit/infrastructure/adapters/http/`              |
| `infrastructure/adapters/common/`     | `tests/unit/infrastructure/adapters/common/`            |
| `infrastructure/adapters/decorators/` | `tests/unit/infrastructure/adapters/`                   |
| `application/composite/`              | `tests/unit/application/composite/`                     |
| `application/core/`                   | `tests/unit/application/core/`                          |
| `domain/`                             | `tests/unit/domain/`                                    |
| `composition/`                        | `tests/unit/composition/`                               |
| `interfaces/`                         | `tests/unit/interfaces/`                                |

**Выбор `{relevant_test_class}`:**

| Registry                                    | Test class               |
| ------------------------------------------- | ------------------------ |
| `file_size_limits`                          | `TestFileSizeLimits`     |
| `class_size`                                | `TestClassSize`          |
| `function_complexity` / `domain_complexity` | `TestFunctionComplexity` |
| `function_length`                           | `TestFunctionLength`     |
| `god_object`                                | `TestGodObjectDetection` |

#### py-doc-bot (синхронизация документации)

```
task_id={task.id}-DOC, mode=doc-sync

Синхронизируй документацию с изменениями в `{task.target_file}`.
Изменения: {краткое описание что сделано}.

НЕ удаляй docstrings. Проверь:
1. Docstrings в изменённых файлах актуальны
2. Документация в docs/ не требует обновления (обычно изменения внутренние)
3. Диаграммы не нуждаются в изменении

Все отчёты и артефакты сохраняй ТОЛЬКО в reports/exemptions_refactoring/.
НЕ создавай файлы в корне проекта.

Отчитайся кратко.
```

#### py-audit-bot (финальный аудит)

```
task_id=AME-FINAL-AUDIT, phase=final

Финальный аудит после architecture debt reduction ({N} задач).

Изменённые файлы:
{список файлов}

Проверь:
1. `uv run pytest tests/architecture/ -v --tb=short` — все архитектурные тесты
2. `uv run mypy {список файлов через пробел} --strict` — type checking
3. `uv run pytest tests/unit/ -v --tb=short -q` — unit tests
4. Проверь что debt_scorecard.yaml baseline корректен (сумма by_registry == total_exemptions)
5. Проверь что architecture_metric_exemptions.yaml валиден (обязательные поля: value, owner, reason, expires_on, removal_step)

Все отчёты и артефакты сохраняй ТОЛЬКО в reports/exemptions_refactoring/.
НЕ создавай файлы в корне проекта.

Выдай финальный отчёт.
```

#### py-review-orchestrator (code review)

```
task_id=AME-FINAL-REVIEW, scope=src/bioetl/

Code review изменений architecture debt reduction.
Фокус: корректность рефакторинга, сохранение поведения, отсутствие регрессий.

Изменённые файлы:
{список файлов}

Все отчёты и артефакты сохраняй ТОЛЬКО в reports/exemptions_refactoring/.
НЕ создавай файлы в корне проекта.
```

______________________________________________________________________

## 3. Execution Workflow

### 3.1 Общая схема

```
┌─────────────────────────────────────────────────────────┐
│ 1. ИНИЦИАЛИЗАЦИЯ                                        │
│    Загрузить JSON → Классифицировать → Приоритизировать  │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│ 2. STALE EXEMPTIONS (batch)                             │
│    Удалить stale записи из YAML + обновить scorecard    │
│    → py-test-bot (1 агент на весь batch)                │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│ 3. ДЛЯ КАЖДОЙ ЗАДАЧИ (параллельно где возможно):       │
│    ┌───────────────┐                                    │
│    │ Исполнитель   │ (оркестратор пишет код напрямую)   │
│    └───────┬───────┘                                    │
│            ▼                                            │
│    ┌───────────────┐  ┌───────────────┐                 │
│    │ py-test-bot   │  │ py-doc-bot    │  (параллельно)  │
│    │ (sonnet)      │  │ (haiku)       │                 │
│    └───────┬───────┘  └───────┬───────┘                 │
│            ▼                  ▼                          │
│    ┌─────────────────────────────────┐                  │
│    │ Если FAIL → py-debug-bot (opus) │                  │
│    │ → повторный py-test-bot         │                  │
│    └─────────────────────────────────┘                  │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│ 4. ФИНАЛИЗАЦИЯ                                          │
│    Обновить debt_scorecard.yaml (baseline counts)       │
│    → py-audit-bot (opus)        — архитектурный аудит   │
│    → py-review-orchestrator (opus) — code review        │
│    (запускать параллельно)                               │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│ 5. КОНСОЛИДАЦИЯ                                         │
│    Собрать отчёты всех агентов → Вывести сводку         │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Правила параллелизации

- **Задачи в разных файлах** — можно запускать параллельно (до 4 одновременно)
- **Задачи в одном файле** (file_size + class_size для одного .py) — выполнять последовательно
- **test + doc-sync** после исполнителя — запускать параллельно (`run_in_background: true`)
- **Два финальных аудит-агента** — запускать параллельно
- **Debug-цикл** — строго последовательно: debug → test → (повтор если FAIL)

### 3.3 Правила обновления configs

После ЛЮБЫХ изменений в exemptions:

1. **architecture_metric_exemptions.yaml** — удалить/обновить записи
1. **debt_scorecard.yaml** — пересчитать:
   - `baseline.total_exemptions` = сумма всех `by_registry.*`
   - `baseline.by_registry.{registry}` = количество записей в соответствующем registry

**Правило подсчёта:**

```
total = file_size_limits + function_complexity + function_length
      + class_size + class_method_count + god_object + domain_complexity
```

Пустые реестры (`{ }`) = 0.

### 3.4 Правила безопасности при рефакторинге

Каждый агент-исполнитель **MUST** соблюдать:

1. **Поведение не изменено** — все существующие тесты проходят
1. **Публичные интерфейсы не изменены** — signatures, return types, __all__ exports
1. **Docstrings не удалены** — разрешено только редактирование для актуализации
1. **Import boundaries** — соблюдать матрицу ARCH-001
1. **mypy --strict** — после изменений файл проходит strict type checking

### 3.5 Стратегии рефакторинга по типу задачи

#### file_size_limits (уменьшение LOC файла)

| Приём                                      | Когда                        | Экономия LOC |
| ------------------------------------------ | ---------------------------- | ------------ |
| Удалить избыточные пустые строки           | Всегда                       | 5-15         |
| Сжать многострочные imports                | >10 imports из одного модуля | 3-8          |
| Extract helper module                      | >50 LOC выделяемой логики    | 50-150       |
| Extract dataclass в отдельный файл         | >30 LOC dataclass            | 30-50        |
| Инлайнить тривиальные однострочные helpers | 1-3 строки обёртка           | 3-10         |

#### class_size (уменьшение LOC класса)

| Приём                            | Когда                                   | Экономия LOC |
| -------------------------------- | --------------------------------------- | ------------ |
| Extract Mixin                    | Группа методов с общей ответственностью | 50-150       |
| Extract Strategy/Policy          | Ветвление по типу/режиму                | 30-80        |
| Extract Value Object             | Группа связанных полей                  | 20-40        |
| Делегирование в injected service | Самостоятельная ответственность         | 30-100       |

#### function_complexity (снижение CC)

| Приём                                 | Когда                   | Снижение CC       |
| ------------------------------------- | ----------------------- | ----------------- |
| Early return / guard clause           | Вложенные if/else       | -1 per guard      |
| Extract method                        | Блок >5 строк в ветке   | -1 per extraction |
| Strategy dispatch (dict mapping)      | switch/case по значению | -N+1              |
| Replace conditional with polymorphism | Ветвление по типу       | -N+1              |

#### god_object (увеличение delegation)

| Приём                              | Когда                          | Добавляет delegations |
| ---------------------------------- | ------------------------------ | --------------------- |
| Private alias (`self._x = self.x`) | Dataclass с публичными полями  | +N per field          |
| Property delegation (`@property`)  | Mixin обращается к parent attr | +1 per property       |
| Inline metrics/logging calls       | Нет прямых `self._metrics.*`   | +1 per call           |
| Extract to injected component      | Крупная самостоятельная логика | +3-10                 |

______________________________________________________________________

## 4. Формат отчёта консолидации

После завершения всех агентов выведи:

```markdown
## Architecture Debt Reduction — Consolidated Report

**Дата**: YYYY-MM-DD
**Источник задач**: {имя JSON файла}
**Задач обработано**: N из M

### Сводка по категориям

| Категория | Задач | Выполнено | Пропущено | Причина пропуска |
|-----------|:-----:|:---------:|:---------:|------------------|
| STALE_EXEMPTION | N | N | 0 | — |
| GOD_OBJECT | N | N | 0 | — |
| COMPLEXITY | N | N | 0 | — |
| NEAR_LIMIT | N | N | 0 | — |
| REDUCE_TO_LIMIT | N | N | 0 | — |
| SAFE_MARGIN | N | 0 | N | Отложено (низкий приоритет) |

### Результаты по задачам

| ID | Registry | Target | Действие | Результат | Test | Doc |
|----|----------|--------|----------|-----------|:----:|:---:|
| AME-xxx | type | file::Symbol | Описание | PASS/FAIL | PASS | DONE |

### Debt Scorecard Delta

| Метрика | Было | Стало | Δ |
|---------|:----:|:-----:|:-:|
| total_exemptions | N | M | -K |
| file_size_limits | N | M | -K |
| god_object | N | M | -K |
| ... | | | |

### Аудит

| Агент | Статус | Score | Критические замечания |
|-------|:------:|:-----:|----------------------|
| py-audit-bot | PASS/FAIL | X/10 | ... |
| py-review-orchestrator | PASS/FAIL | — | ... |

### Рекомендации

1. {Задачи для следующей итерации}
2. {Потенциальные улучшения}
```

______________________________________________________________________

## 5. Обработка ошибок

### 5.1 Агент-тестировщик вернул FAIL

1. Запусти `py-debug-bot` с описанием падения:
   ```
   task_id={task.id}-DEBUG, phase=post_refactor
   failing_test_report="{вывод из py-test-bot}"
   target_file="{task.target_file}"
   ```
1. После фикса — повторный `py-test-bot`
1. Максимум 2 debug-итерации. При 3-м FAIL — откатить изменения, пометить задачу SKIP

### 5.2 Конфликт между агентами

Если два агента модифицируют один файл (например, configs/quality/):

- Не запускать параллельно
- Второй агент запускать только после завершения первого
- **configs/** модификации — только оркестратор (ты сам), НЕ делегировать субагентам

### 5.3 Stale exemption vs Live exemption

Перед удалением exemption **ВСЕГДА** проверь актуальное значение:

```bash
# Для file_size_limits
wc -l < {target_file}

# Для class_size
python -c "import ast; t=ast.parse(open('{file}').read()); [print(f'{n.name}: {n.end_lineno-n.lineno+1}') for n in ast.walk(t) if isinstance(n, ast.ClassDef) and n.name=='{symbol}']"

# Для function_complexity
python -c "from radon.complexity import cc_visit; [print(f'{b.name}: CC={b.complexity}') for b in cc_visit(open('{file}').read()) if b.name=='{symbol}']"
```

Удалять exemption ТОЛЬКО если `current_value <= layer_default_limit`.

______________________________________________________________________

## 6. Управление отчётами

### 6.1 Директория отчётов

Все отчёты агентов **MUST** сохраняться в `reports/exemptions_refactoring/`.

```
reports/
└── exemptions_refactoring/
    ├── {YYYY-MM-DD}_consolidated_report.md    ← итоговый отчёт оркестратора
    ├── {task.id}_test_report.md                ← отчёт py-test-bot
    ├── {task.id}_doc_sync_report.md            ← отчёт py-doc-bot
    ├── {task.id}_debug_report.md               ← отчёт py-debug-bot (если был)
    ├── final_audit_report.md                   ← отчёт py-audit-bot
    └── final_review_report.md                  ← отчёт py-review-orchestrator
```

### 6.2 Правила размещения файлов

- **ЗАПРЕЩЕНО** создавать файлы в корне проекта (за исключением уже существующих)
- **ЗАПРЕЩЕНО** создавать отчёты, логи и промежуточные файлы вне `reports/exemptions_refactoring/`
- При первом запуске — создать директорию `reports/exemptions_refactoring/` если она не существует
- Имена файлов отчётов **MUST** содержать `task.id` или дату для уникальности
- Промежуточные JSON/YAML артефакты (если нужны) — тоже в `reports/exemptions_refactoring/`

### 6.3 Инструкции для субагентов

В промт каждого субагента **MUST** добавлять:

```
Все отчёты и артефакты сохраняй ТОЛЬКО в reports/exemptions_refactoring/.
НЕ создавай файлы в корне проекта.
```

______________________________________________________________________

## 7. Ограничения

- **НЕ менять публичные интерфейсы** (`__all__`, function signatures, return types)
- **НЕ менять поведение** (семантика должна остаться идентичной)
- **НЕ удалять docstrings** (можно редактировать для актуальности)
- **НЕ добавлять новые зависимости** (pip packages)
- **НЕ трогать** `.github/`, `Makefile`, `pyproject.toml` без явного указания
- **НЕ создавать файлы в корне проекта** — отчёты и артефакты только в `reports/exemptions_refactoring/`
- **configs/** — модифицирует только оркестратор, не субагенты
