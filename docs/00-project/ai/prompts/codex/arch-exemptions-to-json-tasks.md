# Codex Prompt: Generate Architecture Exemptions Task JSON

Source: `docs/00-project/ai/prompts/architecture_metric_exemptions_tasks_json_prompt.md`
Purpose: convert architecture metric exemptions into a structured Codex-friendly task file.

## Prompt

You are Codex acting as an automation engineer for BioETL architectural debt management.

Generate one JSON task file from every entry in `configs/quality/architecture_metric_exemptions.yaml`.

### Goal

Create a machine-readable backlog of refactoring tasks, one task per exemption entry.

### Hard constraints

- Do not edit project code.
- Only generate the JSON task file.
- Reflect every supported registry, even if empty.
- Do not change behavior or public interfaces.
- Do not delete docstrings.

### Registries

- `file_size_limits`
- `function_complexity`
- `function_length`
- `class_size`
- `class_method_count`
- `god_object`
- `domain_complexity`

### Inputs

Primary:

- `configs/quality/architecture_metric_exemptions.yaml`

Optional for measurement and validation:

- `src/bioetl/**/*.py`
- `tests/architecture/test_code_metrics.py`
- `tests/architecture/test_quality_burndown_priorities.py`

### Output file

Save the result in the repository root as:

`tasks_architecture_metric_exemptions_YYYY-MM-DD-HH-MM.json`

### Output schema

```json
{
  "schema_version": "1.0",
  "source_registry_file": "configs/quality/architecture_metric_exemptions.yaml",
  "generated_at": "<ISO8601>",
  "defaults": {
    "behavior_change_allowed": false,
    "public_interface_change_allowed": false,
    "docstrings_rule": "Do not delete docstrings. Any future edits must follow project standards."
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

Each task object must include:

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

### Status values

Use exactly one of:

- `needs_refactor`
- `within_limit`
- `not_measurable`
- `target_not_found`

### Mapping rules

#### `target_file` and `symbol_name`

- If key is `path.py::Symbol`:
  - `target_file = path.py`
  - `symbol_name = Symbol`
- If key is `path.py`:
  - `target_file = path.py`
  - `symbol_name = null`
- If key is only `ClassName`:
  - search `src/bioetl/**/*.py`
  - choose the most relevant definition
  - if several are plausible, choose the largest by LOC and explain alternatives in `notes`
  - if none are found, set `target_file = null` and `status = target_not_found`

#### `current_value`

- `file_size_limits`: file LOC
- `function_length`: function length by lines
- `function_complexity` and `domain_complexity`: cyclomatic complexity
- `class_size`: class LOC
- `class_method_count`: method count
- `god_object`: set `current_value = null` and `status = not_measurable` if no stable numeric metric exists

#### `checks`

Include registry-specific commands plus the shared registry checks.

Registry-specific checks:

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

Shared checks for every task:

- `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_quality_exemptions_registry.py`
- `python scripts/qa/check_quality_exemptions.py --mode auto --growth-mode auto --trend-report off`

### Quality rules

- Every exemption becomes exactly one task.
- `registry_summary` must include zero-count registries.
- `total_tasks` must equal the actual number of tasks.
- If evidence is missing, say so in `notes`; do not invent measurements.

### Final response

After saving the JSON file, report:

1. output path
2. task counts by registry
3. `total_tasks`
4. tasks with `target_not_found`
5. tasks with `not_measurable`
