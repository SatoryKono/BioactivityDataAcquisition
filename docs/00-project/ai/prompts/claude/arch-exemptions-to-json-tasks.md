# Generate Architecture Exemptions Task JSON

<role>
Automation engineer: конвертируй все записи из `configs/quality/architecture_metric_exemptions.yaml` в structured JSON task file.
</role>

<constraints>
- НЕ редактируй код проекта
- Генерируй ТОЛЬКО JSON task file
- Отрази ВСЕ registries, даже пустые
- Не меняй behavior/public interfaces, не удаляй docstrings
</constraints>

<registries>
`file_size_limits`, `function_complexity`, `function_length`, `class_size`, `class_method_count`, `god_object`, `domain_complexity`
</registries>

<inputs>
- Primary: `configs/quality/architecture_metric_exemptions.yaml`
- Optional: `src/bioetl/**/*.py`, `tests/architecture/test_code_metrics.py`, `tests/architecture/test_quality_burndown_priorities.py`
</inputs>

<output_file>
`tasks_architecture_metric_exemptions_YYYY-MM-DD-HH-MM.json` (в корне репозитория, `HH-MM` не `HH:MM`)
</output_file>

<schema>
```json
{
  "schema_version": "1.0",
  "source_registry_file": "configs/quality/architecture_metric_exemptions.yaml",
  "generated_at": "<ISO8601>",
  "defaults": {
    "behavior_change_allowed": false,
    "public_interface_change_allowed": false,
    "docstrings_rule": "Do not delete docstrings."
  },
  "registry_summary": { "<each_registry>": 0, "total_tasks": 0 },
  "tasks": [/* ... */]
}
```

Каждый task: `id`, `registry`, `registry_key`, `owner`, `reason`, `expires_on`, `removal_step`, `limit_value`, `current_value`, `delta_to_limit`, `status`, `target_file`, `symbol_name`, `goal`, `acceptance_criteria`, `allowed_paths`, `forbidden_paths`, `checks`, `notes`.
</schema>

<mapping_rules>
**target_file / symbol_name:**
- `path.py::Symbol` → target_file=path.py, symbol_name=Symbol
- `path.py` → target_file=path.py, symbol_name=null
- `ClassName` only → search `src/bioetl/**/*.py`, выбери largest by LOC, alternatives в notes; если нет → target_file=null, status=target_not_found

**current_value:**
- file_size_limits → LOC файла
- function_length → lines функции
- function/domain_complexity → cyclomatic complexity
- class_size → LOC класса
- class_method_count → кол-во методов
- god_object → null + status=not_measurable

**status:** `needs_refactor` | `within_limit` | `not_measurable` | `target_not_found`

**goal:** Конкретная, implementation-oriented цель снижения метрики без behavior change.

**checks:** Registry-specific тесты + shared:
```
python -m pytest -q tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_quality_exemptions_registry.py
python scripts/qa/check_quality_exemptions.py --mode auto --growth-mode auto --trend-report off
```
</mapping_rules>

<output_format>
После сохранения JSON:
1. Output path
2. Task counts by registry
3. total_tasks
4. Tasks с target_not_found
5. Tasks с not_measurable
</output_format>
