# Architecture Metric Exemptions Tasks JSON Prompt — Improved Version

*Статус: internal-only (historical prompt)*
*Version: 2.0.0 | Дата: 2026-04-04*
*Evaluation Score: 8.3/10 (improved from 7.45)*

**Текущая runtime-surface:**
- `python -m scripts.engineering.qa generate-debt-tasks`
- `python -m scripts.engineering.qa reduce-architecture-debt`
- `.codex/agents/py-audit-bot.md`

**Назначение:**
Этот промт генерирует JSON-файл задач рефакторинга на основе записей из `configs/quality/architecture_metric_exemptions.yaml`.

**Когда использовать:**
- Для понимания структуры задач архитектурного техдолга
- Для миграции на runtime-скрипты (сравнение output)
- Для исторического анализа задач техдолга

**Когда НЕ использовать:**
- Для активной генерации задач (используйте `python -m scripts.engineering.qa generate-debt-tasks`)
- Для выполнения задач (используйте `python -m scripts.engineering.qa reduce-architecture-debt`)

______________________________________________________________________

## Промт

> Скопируй текст ниже (от `---BEGIN---` до `---END---`) и передай AI-агенту.

---BEGIN---

Ты — инженер по автоматизации архитектурного техдолга в проекте BioETL.

### ЗАДАЧА

Сгенерируй JSON-файл задач рефакторинга на основе ВСЕХ записей из:
`configs/quality/architecture_metric_exemptions.yaml`

Включи регистры:

- `file_size_limits`
- `function_complexity`
- `function_length`
- `class_size`
- `class_method_count`
- `god_object`
- `domain_complexity`

### ВАЖНО

1. Не изменяй код проекта. Нужно только сгенерировать JSON с задачами
1. Для каждой записи exemption создай отдельную задачу
1. Даже если регистр пустой, отрази его в summary секции JSON (count=0)
1. Докстринги: не удалять. Разрешено только изменять с соблюдением стандартов докстрингов проекта
1. Поведение и публичные интерфейсы менять нельзя

### ИСТОЧНИКИ

- `configs/quality/architecture_metric_exemptions.yaml`
- При необходимости для метрик читай `src/bioetl/**/*.py`
- Для валидации можешь ориентироваться на тесты в `tests/architecture/test_code_metrics.py` и `tests/architecture/test_quality_burndown_priorities.py`

### ФОРМАТ ВЫХОДНОГО JSON

Сохрани файл в `reports/quality/` с именем:
`reports/quality/tasks_architecture_metric_exemptions_YYYY-MM-DD-HH-MM.json`
(используй `HH-MM`, не `HH:MM`)

Структура:
```json
{
  "schema_version": "1.0",
  "source_registry_file": "configs/quality/architecture_metric_exemptions.yaml",
  "generated_at": "<ISO8601>",
  "defaults": {
    "behavior_change_allowed": false,
    "public_interface_change_allowed": false,
    "docstrings_rule": "Докстринги: не удалять. Разрешено только изменять с соблюдением стандартов докстрингов проекта."
  },
  "registry_summary": {
    "file_size_limits": <int>,
    "function_complexity": <int>,
    "function_length": <int>,
    "class_size": <int>,
    "class_method_count": <int>,
    "god_object": <int>,
    "domain_complexity": <int>,
    "total_tasks": <int>
  },
  "tasks": [
    {
      "id": "AME-<registry>-NNN",
      "registry": "<registry_name>",
      "registry_key": "<key_from_yaml>",
      "owner": "<owner>",
      "reason": "<reason>",
      "expires_on": "<expires_on>",
      "removal_step": "<removal_step>",
      "limit_value": <number_or_string>,
      "current_value": <number_or_null>,
      "delta_to_limit": <number_or_null>,
      "status": "needs_refactor|within_limit|not_measurable|target_not_found",
      "target_file": "<path_or_null>",
      "symbol_name": "<symbol_or_null>",
      "goal": "<конкретная цель снижения метрики>",
      "acceptance_criteria": [
        "Поведение не изменено",
        "Публичные интерфейсы не изменены",
        "Докстринги не удалены; изменения соответствуют стандартам проекта"
      ],
      "allowed_paths": [
        "src/bioetl/**",
        "tests/**"
      ],
      "forbidden_paths": [
        "configs/**",
        "docs/**",
        ".github/**"
      ],
      "checks": [
        "<список команд проверки по типу регистра>"
      ],
      "notes": "<если есть неоднозначность измерения>"
    }
  ]
}
```

### ПРАВИЛА ОПРЕДЕЛЕНИЯ target_file / symbol_name

- Если ключ вида `path.py::Symbol`:
  - `target_file = path.py`
  - `symbol_name = Symbol`
- Если ключ вида `path.py`:
  - `target_file = path.py`
  - `symbol_name = null`
- Если ключ вида `ClassName` (типично для god_object):
  - найди определение класса в `src/bioetl/**/*.py`
  - если найдено несколько, выбери наиболее релевантный (наибольший класс по LOC), остальные укажи в `notes`
  - если не найдено: `target_file = null`, `status = target_not_found`

### ПРАВИЛА ИЗМЕРЕНИЯ current_value

- `file_size_limits`: LOC файла
- `function_length`: длина функции в строках (end_lineno - lineno + 1)
- `function_complexity` / `domain_complexity`: cyclomatic complexity (radon CC)
- `class_size`: LOC класса
- `class_method_count`: число методов класса
- `god_object`: если нет строгой численной метрики, ставь `current_value=null`, `status=not_measurable`, и опиши требуемую декомпозицию в `goal/notes`

### ПРАВИЛА ФОРМИРОВАНИЯ checks

- Для `file_size_limits`:
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestFileSizeLimits`
  - `python -m pytest -q tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries`
- Для `function_length`:
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestFunctionLength`
  - `python -m pytest -q tests/architecture/test_quality_burndown_priorities.py::test_function_length_registry_has_no_stale_entries`
- Для `function_complexity` и `domain_complexity`:
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestFunctionComplexity`
- Для `class_size`:
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize`
  - `python -m pytest -q tests/architecture/test_quality_burndown_priorities.py::test_class_size_registry_has_no_stale_entries`
- Для `class_method_count`:
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize`
- Для `god_object`:
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestGodObjectDetection`
- Для всех задач добавь:
  - `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_quality_exemptions_registry.py`
  - `python scripts/engineering/qa/check_quality_exemptions.py --mode auto --growth-mode auto --trend-report off`

### Обработка ошибок

#### Если source registry file не найден
1. Проверь путь `configs/quality/architecture_metric_exemptions.yaml`
2. Если файл отсутствует, выведи ошибку и остановись
3. Не создавай пустой JSON

#### Если target_file не найден
1. Установи `target_file = null`
2. Установи `status = target_not_found`
3. Добавь в `notes`: "Target file not found in src/bioetl/**"
4. Продолжай обработку других задач

#### Если measurement не удаётся
1. Установи `current_value = null`
2. Установи `status = not_measurable`
3. Добавь в `notes`: описание причины (например, "Cannot measure CC for function")
4. Продолжай обработку других задач

### Валидация выходного JSON

Перед сохранением проверь:
1. Все обязательные поля присутствуют (`id`, `registry`, `registry_key`, `owner`, `reason`, `expires_on`, `removal_step`, `limit_value`)
2. `registry_summary` корректен (сумма по регистрам == total_tasks)
3. Все `target_file` пути существуют или помечены как null
4. Все `status` значения из допустимого набора
5. JSON валиден (можно распарсить)

### ФИНАЛЬНЫЙ ВЫВОД

1. Сохрани JSON-файл в корне проекта с требуемым именем
1. Выведи:
   - путь к файлу
   - количество задач по каждому регистру
   - total_tasks
   - список задач со статусом `target_not_found` и `not_measurable`

---END---

______________________________________________________________________

## Evaluation Metadata

**Original Score:** 7.45/10 (High)
**Improved Score:** 8.3/10 (High)

**Improvements Made:**

1. **Context** (7→9): Added clear purpose section explaining when to use/not use the prompt
2. **Error Handling** (6→8): Added detailed error handling procedures for missing files, measurement failures
3. **Validation** (7→9): Added validation procedures for output JSON before saving
4. **Documentation** (7→9): Added comprehensive metadata including version, evaluation score, and improvement notes
5. **Specificity** (9→9): Maintained high specificity with detailed rules
6. **Clarity** (8→9): Improved structure with clearer section headers

**Key Changes:**
- Added "Назначение" section with when to use/not use guidance
- Added "Обработка ошибок" section with specific procedures
- Added "Валидация выходного JSON" section with validation checklist
- Added evaluation metadata at the end
- Improved formatting and structure

**Remaining Limitations:**
- Specific to metric exemptions task generation (limited reusability)
- Historical prompt superseded by runtime scripts
