*Статус: internal-only (historical prompt)*

Текущая runtime-surface:

- `python -m scripts.engineering.qa generate-debt-tasks`
- `python -m scripts.engineering.qa reduce-architecture-debt`
- `.codex/agents/py-audit-bot.md`

Ты — инженер по автоматизации архитектурного техдолга в проекте BioETL.

ЗАДАЧА
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

ВАЖНО

1. Не изменяй код проекта. Нужно только сгенерировать JSON с задачами.
1. Для каждой записи exemption создай отдельную задачу.
1. Даже если регистр пустой, отрази его в summary секции JSON (count=0).
1. Докстринги: не удалять. Разрешено только изменять с соблюдением стандартов докстрингов проекта.
1. Поведение и публичные интерфейсы менять нельзя.

ИСТОЧНИКИ

- `configs/quality/architecture_metric_exemptions.yaml`
- При необходимости для метрик читай `src/bioetl/**/*.py`
- Для валидации можешь ориентироваться на тесты в `tests/architecture/test_code_metrics.py` и `tests/architecture/test_quality_burndown_priorities.py`

ФОРМАТ ВЫХОДНОГО JSON
Сохрани файл в `reports/quality/` с именем:
`reports/quality/tasks_architecture_metric_exemptions_YYYY-MM-DD-HH-MM.json`
(используй `HH-MM`, не `HH:MM`)

Структура:
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
"tasks": \[
{
"id": "AME-<registry>-NNN",
"registry": "\<registry_name>",
"registry_key": "\<key_from_yaml>",
"owner": "<owner>",
"reason": "<reason>",
"expires_on": "\<expires_on>",
"removal_step": "\<removal_step>",
"limit_value": \<number_or_string>,
"current_value": \<number_or_null>,
"delta_to_limit": \<number_or_null>,
"status": "needs_refactor|within_limit|not_measurable|target_not_found",
"target_file": "\<path_or_null>",
"symbol_name": "\<symbol_or_null>",
"goal": "\<конкретная цель снижения метрики>",
"acceptance_criteria": \[
"Поведение не изменено",
"Публичные интерфейсы не изменены",
"Докстринги не удалены; изменения соответствуют стандартам проекта"
\],
"allowed_paths": \[
"src/bioetl/**",
"tests/**"
\],
"forbidden_paths": \[
"configs/**",
"docs/**",
".github/\*\*"
\],
"checks": \[
"\<список команд проверки по типу регистра>"
\],
"notes": "\<если есть неоднозначность измерения>"
}
\]
}

ПРАВИЛА ОПРЕДЕЛЕНИЯ target_file / symbol_name

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

ПРАВИЛА ИЗМЕРЕНИЯ current_value

- `file_size_limits`: LOC файла
- `function_length`: длина функции в строках (end_lineno - lineno + 1)
- `function_complexity` / `domain_complexity`: cyclomatic complexity (radon CC)
- `class_size`: LOC класса
- `class_method_count`: число методов класса
- `god_object`: если нет строгой численной метрики, ставь `current_value=null`, `status=not_measurable`, и опиши требуемую декомпозицию в `goal/notes`

ПРАВИЛА ФОРМИРОВАНИЯ checks

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

ФИНАЛЬНЫЙ ВЫВОД

1. Сохрани JSON-файл в корне проекта с требуемым именем.
1. Выведи:
   - путь к файлу
   - количество задач по каждому регистру
   - total_tasks
   - список задач со статусом `target_not_found` и `not_measurable`.
