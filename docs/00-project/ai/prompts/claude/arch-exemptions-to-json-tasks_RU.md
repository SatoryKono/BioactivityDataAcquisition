# Русский промт: генерация JSON-задач из архитектурных exemption-записей

Источник: `docs/00-project/ai/prompts/claude2/arch-exemptions-to-json-tasks.md`
Назначение: преобразовать architecture metric exemptions в структурированный backlog задач.

## Промт

Ты — Claude Code, выполняющий роль инженера по автоматизации архитектурного долга в BioETL.

Сгенерируй один JSON-файл задач на основе всех записей из `configs/quality/architecture_metric_exemptions.yaml`.

### Цель

Создать machine-readable backlog задач рефакторинга: одна exemption-запись = одна задача.

### Жёсткие ограничения

- Код проекта не менять.
- Нужен только JSON-файл задач.
- Все поддерживаемые registry должны присутствовать, даже если они пустые.
- Публичные интерфейсы и поведение менять нельзя.
- Docstrings удалять нельзя.

### Реестры

- `file_size_limits`
- `function_complexity`
- `function_length`
- `class_size`
- `class_method_count`
- `god_object`
- `domain_complexity`

### Входные данные

Основной источник:

- `configs/quality/architecture_metric_exemptions.yaml`

Дополнительно для измерения и проверки:

- `src/bioetl/**/*.py`
- `tests/architecture/test_code_metrics.py`
- `tests/architecture/test_quality_burndown_priorities.py`

### Выходной файл

Сохрани результат в корне репозитория под именем:

`tasks_architecture_metric_exemptions_YYYY-MM-DD-HH-MM.json`

### Схема выходного JSON

```json
{
  "schema_version": "1.0",
  "source_registry_file": "configs/quality/architecture_metric_exemptions.yaml",
  "generated_at": "<ISO8601>",
  "defaults": {
    "behavior_change_allowed": false,
    "public_interface_change_allowed": false,
    "docstrings_rule": "Docstrings удалять нельзя. Любые будущие правки должны следовать стандартам проекта."
  },
  "registry_summary": {
    "file_size_limits": 0,
    "function_complexity": 0,
    "function_length": 0,
    "class_size": 0,
    "class_method_count": 0,
    "god_object": 0,
    "domain_complexity": 0,
    "total_tasks": 0
  },
  "tasks": []
}
```

Каждый task object обязан содержать:

- `id`
- `registry`
- `registry_key`
- `owner`
- `reason`
- `expires_on`
- `removal_step`
- `limit_value`
- `current_value`
- `delta_to_limit`
- `status`
- `target_file`
- `symbol_name`
- `goal`
- `acceptance_criteria`
- `allowed_paths`
- `forbidden_paths`
- `checks`
- `notes`

### Допустимые `status`

Используй только:

- `needs_refactor`
- `within_limit`
- `not_measurable`
- `target_not_found`

### Правила маппинга

#### `target_file` и `symbol_name`

- Если ключ выглядит как `path.py::Symbol`:
  - `target_file = path.py`
  - `symbol_name = Symbol`
- Если ключ выглядит как `path.py`:
  - `target_file = path.py`
  - `symbol_name = null`
- Если ключ — только `ClassName`:
  - ищи по `src/bioetl/**/*.py`
  - выбери наиболее релевантное определение
  - если вариантов несколько, выбери наибольший по LOC и остальные объясни в `notes`
  - если не найдено, установи `target_file = null` и `status = target_not_found`

#### `current_value`

- `file_size_limits`: LOC файла
- `function_length`: длина функции в строках
- `function_complexity` и `domain_complexity`: cyclomatic complexity
- `class_size`: LOC класса
- `class_method_count`: число методов
- `god_object`: если нет устойчивой численной метрики, ставь `current_value = null` и `status = not_measurable`

#### `checks`

Добавляй registry-specific commands и общие shared checks.

Registry-specific:

- `file_size_limits`
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestFileSizeLimits`
  - `python -m pytest -q tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries`
- `function_length`
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestFunctionLength`
  - `python -m pytest -q tests/architecture/test_quality_burndown_priorities.py::test_function_length_registry_has_no_stale_entries`
- `function_complexity`
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestFunctionComplexity`
- `domain_complexity`
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestFunctionComplexity`
- `class_size`
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize`
  - `python -m pytest -q tests/architecture/test_quality_burndown_priorities.py::test_class_size_registry_has_no_stale_entries`
- `class_method_count`
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize`
- `god_object`
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestGodObjectDetection`

Shared checks для каждой задачи:

- `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_quality_exemptions_registry.py`
- `python scripts/qa/check_quality_exemptions.py --mode auto --growth-mode auto --trend-report off`

### Правила качества

- Каждая exemption-запись должна стать ровно одной задачей.
- `registry_summary` обязан содержать zero-count registry.
- `total_tasks` должен точно совпадать с числом задач.
- Если evidence недостаточно, так и напиши в `notes`, не выдумывай измерения.

### Финальный ответ

После сохранения JSON-файла выведи:

1. путь к файлу
2. количество задач по реестрам
3. `total_tasks`
4. задачи со статусом `target_not_found`
5. задачи со статусом `not_measurable`
