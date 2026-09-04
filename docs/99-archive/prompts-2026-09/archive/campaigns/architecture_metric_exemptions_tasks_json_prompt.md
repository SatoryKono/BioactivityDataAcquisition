---
status: archived
class: campaign
note: Opt-in historical megaprompt. Not default operator paste. Prefer library/** cards and REGISTRY.yaml. Epic #8513 / #8517.
---

# Architecture Metric Exemptions Tasks JSON — Improved Version

## Evaluation Metadata
- **Category:** Architecture Prompts
- **Weighted Score:** 8.30 / 10
- **Overall Rating:** High
- **Path:** docs/00-project/ai/prompts/architecture_metric_exemptions_tasks_json_prompt.md

## Evaluation Breakdown
- Clarity: 8/10 (weight: 0.15)
- Completeness: 9/10 (weight: 0.15)
- Specificity: 9/10 (weight: 0.12)
- Context: 8/10 (weight: 0.10)
- Guardrails: 8/10 (weight: 0.10)
- Maintainability: 8/10 (weight: 0.08)
- Reusability: 8/10 (weight: 0.08)
- Error Handling: 8/10 (weight: 0.08)
- Validation: 8/10 (weight: 0.07)
- Documentation: 8/10 (weight: 0.07)

## Original Content

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

## Improved Content

*Статус: internal-only (enhanced prompt)*

Текущая runtime-surface:

- `python -m scripts.engineering.qa generate-debt-tasks`
- `python -m scripts.engineering.qa reduce-architecture-debt`
- `.codex/agents/py-audit-bot.md`

Ты — инженер по автоматизации архитектурного техдолга в проекте BioETL.

ЗАДАЧА
Сгенерируй JSON-файл задач рефакторинга на основе ВСЕХ метрик технического долга из:
`configs/quality/debt_scorecard.yaml` (основной источник)
`configs/quality/architecture_metric_exemptions.yaml` (baseline exemptions)

Включи все категории метрик:

1. **Baseline exemptions** (7 регистров):
   - file_size_limits, function_complexity, function_length, class_size, class_method_count, god_object, domain_complexity

2. **Coarse budgets** (3 метрики):
   - ruff_error_count, mypy_error_count, architecture_skip_count

3. **Compatibility debt metrics** (3 метрики):
   - transition_compat_count, sunset_compat_count, expired_compat_count

4. **Sanctioned public entrypoint governance** (6 метрик):
   - public_entrypoint_count, stable_public_api_count, narrow_first_party_callers_count, public_export_facade_count, public_export_facade_conflict_count

5. **Bronze fixture replay debt metrics** (4 метрики):
   - active_fixture_gap_count, blocked_fixture_gap_count, decision_recorded_fixture_gap_count, tracked_bronze_fixture_count

6. **Config surface ratchet** (5 метрик):
   - config_count, unique_parameter_count, inconsistent_parameter_count, sanctioned_partial_parameter_count, raw_inconsistent_parameter_count

7. **Hotspot budgets** (2 hotspots):
   - core_orchestration, composite_orchestration

8. **Hotspot family ratchets** (5 hotspot families):
   - application_core, composition_bootstrap_runtime, composition_factories_pipeline, application_services_control_plane, composition_runtime_builders

9. **Full app duplication ratchets** (4 families):
   - infrastructure_adapters, application_pipelines, composition_bootstrap_full_app, interfaces_cli_full_app

10. **Supporting scripts governance** (2 метрики):
    - zero_reference_supporting_script_count, untriaged_zero_reference_supporting_script_count

11. **Oversized source module inventory** (6 модулей):
    - Все oversized модули из debt_scorecard.yaml

12. **Hotspot family coverage thresholds** (5 families):
    - Пороги покрытия для hotspot families

13. **Removable complexity family ratchets** (2 families):
    - adapter_layer, composite_layer

14. **Runtime UUID governance metrics** (2 метрики):
    - runtime_uuid_seam_count, replay_critical_uuid_seam_count

15. **Retirement governance metrics** (9 метрик):
    - triaged_entry_count, repo_wide_zero_import_candidate_count, repo_wide_classified_zero_import_candidate_count, repo_wide_untriaged_zero_import_candidate_count, repo_wide_owner_test_anchored_candidate_count, repo_wide_candidates_without_owner_tests_count, repo_wide_non_static_reachability_candidate_count, triaged_retained_owner_test_anchored_count, triaged_retained_without_owner_tests_count

16. **Test governance debt metrics** (1 метрика):
    - compatibility_test_file_count

ВАЖНО

1. Не изменяй код проекта. Нужно только сгенерировать JSON с задачами.
1. Для каждой метрики создай отдельную задачу.
1. Даже если категория пустая, отрази её в summary секции JSON (count=0).
1. Докстринги: не удалять. Разрешено только изменять с соблюдением стандартов докстрингов проекта.
1. Поведение и публичные интерфейсы менять нельзя.

ИСТОЧНИКИ

- `configs/quality/debt_scorecard.yaml` (основной источник всех метрик)
- `configs/quality/architecture_metric_exemptions.yaml` (baseline exemptions)
- При необходимости для метрик читай `src/bioetl/**/*.py`
- Для валидации можешь ориентироваться на тесты в `tests/architecture/test_code_metrics.py` и `tests/architecture/test_quality_burndown_priorities.py`

ФОРМАТ ВЫХОДНОГО JSON
Сохрани файл в `reports/quality/` с именем:
`reports/quality/tasks_architecture_debt_scorecard_YYYY-MM-DD-HH-MM.json`
(используй `HH-MM`, не `HH:MM`)

Структура:
{
"schema_version": "2.0",
"source_registry_file": "configs/quality/debt_scorecard.yaml",
"baseline_exemptions_file": "configs/quality/architecture_metric_exemptions.yaml",
"generated_at": "<ISO8601>",
"defaults": {
"behavior_change_allowed": false,
"public_interface_change_allowed": false,
"docstrings_rule": "Докстринги: не удалять. Разрешено только изменять с соблюдением стандартов докстрингов проекта."
},
"category_summary": {
"baseline_exemptions": {
"file_size_limits": <int>,
"function_complexity": <int>,
"function_length": <int>,
"class_size": <int>,
"class_method_count": <int>,
"god_object": <int>,
"domain_complexity": <int>
},
"coarse_budgets": {
"ruff_error_count": <int>,
"mypy_error_count": <int>,
"architecture_skip_count": <int>
},
"compatibility_debt": {
"transition_compat_count": <int>,
"sunset_compat_count": <int>,
"expired_compat_count": <int>
},
"public_entrypoints": {
"public_entrypoint_count": <int>,
"stable_public_api_count": <int>,
"narrow_first_party_callers_count": <int>,
"public_export_facade_count": <int>,
"public_export_facade_conflict_count": <int>
},
"bronze_fixture_debt": {
"active_fixture_gap_count": <int>,
"blocked_fixture_gap_count": <int>,
"decision_recorded_fixture_gap_count": <int>,
"tracked_bronze_fixture_count": <int>
},
"config_surface": {
"config_count": <int>,
"unique_parameter_count": <int>,
"inconsistent_parameter_count": <int>,
"sanctioned_partial_parameter_count": <int>,
"raw_inconsistent_parameter_count": <int>
},
"hotspot_budgets": {
"core_orchestration": <int>,
"composite_orchestration": <int>
},
"hotspot_families": {
"application_core": <int>,
"composition_bootstrap_runtime": <int>,
"composition_factories_pipeline": <int>,
"application_services_control_plane": <int>,
"composition_runtime_builders": <int>
},
"duplication_families": {
"infrastructure_adapters": <int>,
"application_pipelines": <int>,
"composition_bootstrap_full_app": <int>,
"interfaces_cli_full_app": <int>
},
"supporting_scripts": {
"zero_reference_supporting_script_count": <int>,
"untriaged_zero_reference_supporting_script_count": <int>
},
"oversized_modules": <int>,
"coverage_thresholds": <int>,
"removable_complexity": <int>,
"uuid_governance": <int>,
"retirement_governance": <int>,
"test_governance": <int>,
"total_tasks": <int>
},
"tasks": \[
{
"id": "DEBT-<category>-NNN",
"task_category": "baseline_exemptions|coarse_budgets|compatibility_debt|public_entrypoints|bronze_fixture_debt|config_surface|hotspot_budgets|hotspot_families|duplication_families|supporting_scripts|oversized_modules|coverage_thresholds|removable_complexity|uuid_governance|retirement_governance|test_governance",
"metric_family": "<specific_metric_name>",
"metric_name": "<specific_metric_name>",
"owner": "<owner>",
"linked_issue": "<issue_number>",
"current_value": <number_or_null>,
"max_value": <number_or_null>,
"target_value": <number_or_null>,
"delta_to_target": <number_or_null>,
"status": "needs_refactor|within_limit|not_measurable|target_not_found|blocked|in_progress",
"priority": "critical|high|medium|low",
"target_file": "<path_or_null>",
"symbol_name": "<symbol_or_null>",
"path_prefixes": ["<path_prefix_or_null>"],
"goal": "<конкретная цель снижения метрики>",
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
"\<список команд проверки по типу метрики>"
\],
"estimated_effort": "<small|medium|large>",
"dependencies": ["<task_ids>"],
"notes": "<если есть неоднозначность измерения>"
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
- Для hotspot families:
  - `target_file = null`
  - `symbol_name = null`
  - `path_prefixes` из debt_scorecard.yaml
- Для config surface:
  - `target_file = null`
  - `symbol_name = null`
  - Используй `config_count` и `unique_parameter_count`

ПРАВИЛА ИЗМЕРЕНИЯ current_value

- **Baseline exemptions**:
  - `file_size_limits`: LOC файла
  - `function_length`: длина функции в строках (end_lineno - lineno + 1)
  - `function_complexity` / `domain_complexity`: cyclomatic complexity (radon CC)
  - `class_size`: LOC класса
  - `class_method_count`: число методов класса
  - `god_object`: если нет строгой численной метрики, ставь `current_value=null`, `status=not_measurable`

- **Coarse budgets**:
  - `ruff_error_count`: текущее количество Ruff ошибок
  - `mypy_error_count`: текущее количество mypy ошибок
  - `architecture_skip_count`: текущее количество architecture skip markers

- **Compatibility debt**:
  - `transition_compat_count`: количество transition compatibility shims
  - `sunset_compat_count`: количество sunset compatibility shims
  - `expired_compat_count`: количество expired compatibility items

- **Public entrypoints**:
  - `public_entrypoint_count`: количество sanctioned public entrypoints
  - `stable_public_api_count`: количество stable public API entries
  - `narrow_first_party_callers_count`: количество narrow-first-party callers
  - `public_export_facade_count`: количество public export facades
  - `public_export_facade_conflict_count`: количество export facade conflicts

- **Bronze fixture debt**:
  - `active_fixture_gap_count`: количество active fixture gaps
  - `blocked_fixture_gap_count`: количество blocked fixture gaps
  - `decision_recorded_fixture_gap_count`: количество decision-recorded gaps
  - `tracked_bronze_fixture_count`: количество tracked bronze fixtures

- **Config surface**:
  - `config_count`: количество entity/composite configs
  - `unique_parameter_count`: количество уникальных параметров
  - `inconsistent_parameter_count`: количество inconsistent параметров
  - `sanctioned_partial_parameter_count`: количество sanctioned partial параметров
  - `raw_inconsistent_parameter_count`: количество raw inconsistent параметров

- **Hotspot families**:
  - `duplication_clusters`: количество duplication clusters
  - `files`: количество файлов
  - `total_loc`: общее количество LOC
  - `files_ge_250_loc`: количество файлов >= 250 LOC
  - `helper_function_ratio`: ratio helper functions
  - `max_internal_fan_in`: максимальный internal fan-in

ПРАВИЛА ФОРМИРОВАНИЯ checks

- **Baseline exemptions**:
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestFileSizeLimits`
  - `python -m pytest -q tests/architecture/test_quality_burndown_priorities.py::test_file_size_limit_registry_has_no_stale_entries`
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestFunctionLength`
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestFunctionComplexity`
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize`
  - `python -m pytest -q tests/architecture/test_code_metrics.py::TestGodObjectDetection`

- **Coarse budgets**:
  - `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py`
  - `ruff check src/bioetl/ --statistics`
  - `mypy src/bioetl/ --no-error-summary`

- **Compatibility debt**:
  - `python -m scripts.engineering.qa check-compatibility-inventory`
  - `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py`

- **Public entrypoints**:
  - `python -m scripts.engineering.qa check-public-entrypoints`
  - `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py`

- **Bronze fixture debt**:
  - `python -m scripts.engineering.qa check-bronze-fixture-gaps`
  - `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py`

- **Config surface**:
  - `python -m scripts.schema generate-config-matrix`
  - `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py`

- **Hotspot families**:
  - `python -m scripts.engineering.qa report-duplication-baseline --targets <path_prefixes>`
  - `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py`

- **Supporting scripts**:
  - `python -m scripts.engineering.qa check-supporting-scripts`
  - `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py`

- **Oversized modules**:
  - `python -m scripts.engineering.qa check-oversized-modules`
  - `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py`

- **UUID governance**:
  - `python -m scripts.engineering.qa check-runtime-uuid-seams`
  - `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py`

- **Retirement governance**:
  - `python -m scripts.engineering.qa check-retirement-triage`
  - `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py`

- **Test governance**:
  - `python -m scripts.engineering.qa check-test-governance`
  - `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py`

- **Для всех задач добавь**:
  - `python -m pytest -q tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_quality_exemptions_registry.py`
  - `python scripts/engineering/qa/check_quality_exemptions.py --mode auto --growth-mode auto --trend-report off`

ПРАВИЛА ПРИОРИТИЗАЦИИ

- **Critical**: coarse budgets (ruff/mypy/architecture_skip), expired_compat_count, expired entries
- **High**: baseline exemptions > 0, public_export_facade_conflict_count, blocked_fixture_gap_count
- **Medium**: compatibility debt, public entrypoints, bronze fixture debt, config surface
- **Low**: supporting scripts, oversized modules, coverage thresholds

ПРАВИЛА ОЦЕНКИ УСИЛИЙ

- **Small**: простые изменения (1-2 файла, < 100 LOC)
- **Medium**: умеренные изменения (3-5 файлов, 100-500 LOC)
- **Large**: сложные изменения (> 5 файлов, > 500 LOC)

ФИНАЛЬНЫЙ ВЫВОД

1. Сохрани JSON-файл в корне проекта с требуемым именем.
1. Выведи:
   - путь к файлу
   - количество задач по каждой категории
   - total_tasks
   - список задач со статусом `target_not_found` и `not_measurable`
   - список critical/high priority задач
   - summary по estimated_effort

## Improved Sections

### Specificity Enhancements

#### Concrete Task Generation Commands
```bash
# Step 1: Read debt scorecard
cat configs/quality/debt_scorecard.yaml

# Step 2: Read baseline exemptions
cat configs/quality/architecture_metric_exemptions.yaml

# Step 3: Generate tasks JSON
python -m scripts.engineering.qa generate-debt-tasks --source debt_scorecard --output reports/quality/tasks_architecture_debt_scorecard_YYYY-MM-DD-HH-MM.json

# Step 4: Validate JSON schema
python -m json.tool reports/quality/tasks_architecture_debt_scorecard_YYYY-MM-DD-HH-MM.json > /dev/null
```

#### Timeout Policies
```yaml
task_generation_timeouts:
  read_debt_scorecard: 10
  read_baseline_exemptions: 5
  generate_tasks: 60
  validate_json: 5
  total_timeout: 80
```

#### Retry Policies
```yaml
task_generation_retry_policies:
  read_debt_scorecard:
    max_retries: 3
    backoff: "fixed"
    backoff_delay: 2
  
  generate_tasks:
    max_retries: 2
    backoff: "exponential"
    backoff_delay: [2, 4]
```

### Enhanced Guardrails

#### Integrity Guardrails
- **Metric Integrity**: Verify metric values are consistent with debt_scorecard.yaml
- **Category Integrity**: Ensure all categories from debt_scorecard.yaml are represented
- **Task Integrity**: Verify each task has required fields and valid values
- **JSON Integrity**: Ensure generated JSON is valid and parseable

#### Consistency Guardrails
- **Metric Consistency**: Ensure metric names match debt_scorecard.yaml exactly
- **Category Consistency**: Ensure category names are consistent across tasks
- **Priority Consistency**: Ensure priority assignment follows defined rules
- **Effort Consistency**: Ensure effort estimation follows defined rules

#### Access Control Guardrails
- **File Access Control**: Verify access to debt_scorecard.yaml before reading
- **Baseline Access Control**: Verify access to architecture_metric_exemptions.yaml before reading
- **Output Access Control**: Verify access to reports/quality/ before writing
- **Source Access Control**: Verify access to src/bioetl/**/*.py for metric measurement

### Error Handling Improvements

#### Error Recovery Strategies
```yaml
error_recovery:
  read_debt_scorecard:
    strategy: "retry_with_fallback"
    fallback: "manual_read"
    max_retries: 3
  
  generate_tasks:
    strategy: "retry_with_partial"
    fallback: "partial_task_generation"
    max_retries: 2
  
  validate_json:
    strategy: "retry_with_fix"
    fallback: "manual_json_fix"
    max_retries: 2
```

#### Fallback Procedures
- **Debt Scorecard Fallback**: Manual reading of debt_scorecard.yaml if automated read fails
- **Task Generation Fallback**: Partial task generation for critical categories only
- **JSON Validation Fallback**: Manual JSON fixing if automated validation fails

#### Graceful Degradation
- **Partial Task Generation**: Generate tasks for critical categories if full generation fails
- **Best Effort Validation**: Validate JSON structure even if some fields are missing
- **Warning Mode**: Operate in warning mode for non-critical validation failures

### Validation Enhancements

#### Validation Gates
```yaml
validation_gates:
  pre_generation:
    - validate_file_access
    - validate_yaml_structure
    - validate_metric_categories
  
  during_generation:
    - validate_task_structure
    - validate_metric_values
    - validate_priority_assignment
    - validate_effort_estimation
  
  post_generation:
    - validate_json_schema
    - validate_json_parseability
    - validate_category_completeness
    - validate_task_count_consistency
```

#### Self-Consistency Checks
- **Metric Consistency**: Verify metric names match debt_scorecard.yaml
- **Category Consistency**: Verify all categories are represented
- **Value Consistency**: Verify metric values are within expected ranges
- **Task Consistency**: Verify task fields are consistent with category

#### Validation Procedures
1. **Pre-Generation Validation**: Validate file access, YAML structure, and metric categories
2. **During-Generation Validation**: Validate task structure, metric values, priority assignment, and effort estimation
3. **Post-Generation Validation**: Validate JSON schema, parseability, category completeness, and task count consistency
4. **Cross-Category Validation**: Validate consistency across different metric categories

### Maintainability Improvements

#### Maintenance Guidelines
- **Weekly Review**: Review task generation accuracy weekly
- **Monthly Audit**: Conduct monthly audit of metric categories and task templates
- **Quarterly Update**: Update task generation procedures quarterly
- **Continuous Monitoring**: Monitor task generation metrics continuously

#### Versioning Strategy
```yaml
versioning:
  format: "v{major}.{minor}.{patch}"
  major: "breaking changes to task structure"
  minor: "new metric categories or task fields"
  patch: "bug fixes or minor improvements"
  
  current_version: "v2.0.0"
  release_schedule: "as_needed"
  backward_compatibility: "maintained_for_minor_and_patch"
```

#### Cleanup Procedures
- **Task Cleanup**: Clean up old task JSON files older than 90 days
- **Report Cleanup**: Clean up old task reports older than 30 days
- **Log Cleanup**: Clean up task generation logs older than 7 days
- **Cache Cleanup**: Clean up task generation cache artifacts older than 7 days

### Reusability Improvements

#### Reusable Patterns
```yaml
reusable_patterns:
  task_generation:
    - metric_category_detection
    - task_structure_generation
    - priority_assignment
    - effort_estimation
    - validation
  
  metric_measurement:
    - baseline_exemption_measurement
    - coarse_budget_measurement
    - compatibility_debt_measurement
    - public_entrypoint_measurement
    - bronze_fixture_debt_measurement
    - config_surface_measurement
    - hotspot_family_measurement
    - supporting_scripts_measurement
    - uuid_governance_measurement
    - retirement_governance_measurement
    - test_governance_measurement
```

#### Modular Components
- **Metric Category Detector**: Detects and categorizes metrics from debt_scorecard.yaml
- **Task Structure Generator**: Generates task structure for each metric
- **Priority Assigner**: Assigns priority based on metric type and current value
- **Effort Estimator**: Estimates effort based on metric type and complexity
- **Validator**: Validates generated tasks and JSON structure

#### Templates
```yaml
task_templates:
  baseline_exemption:
    id: "DEBT-BASELINE-{registry}-{NNN}"
    task_category: "baseline_exemptions"
    priority_rules: "high_if_current_value > 0"
    effort_rules: "medium_if_current_value > limit_value"
  
  coarse_budget:
    id: "DEBT-COARSE-{metric}-{NNN}"
    task_category: "coarse_budgets"
    priority_rules: "critical_if_current_value > 0"
    effort_rules: "small_if_current_value > 0"
  
  compatibility_debt:
    id: "DEBT-COMPAT-{metric}-{NNN}"
    task_category: "compatibility_debt"
    priority_rules: "high_if_current_value > 0"
    effort_rules: "medium_if_current_value > 0"
```

#### Configuration Parameters
```yaml
configuration_parameters:
  task_generation:
    include_empty_categories: true
    generate_all_categories: true
    validate_json: true
    output_format: "json"
  
  priority_assignment:
    critical_thresholds:
      ruff_error_count: 0
      mypy_error_count: 0
      architecture_skip_count: 0
      expired_compat_count: 0
    high_thresholds:
      baseline_exemptions: 0
      public_export_facade_conflict_count: 0
      blocked_fixture_gap_count: 0
  
  effort_estimation:
    small_threshold: 100
    medium_threshold: 500
    large_threshold: 1000
```

### Documentation Improvements

#### Enhanced Documentation
- **Category Documentation**: Document each metric category with examples
- **Task Documentation**: Document task structure and field meanings
- **Priority Documentation**: Document priority assignment rules
- **Effort Documentation**: Document effort estimation rules

#### Usage Examples
```yaml
usage_examples:
  generate_all_tasks:
    command: "python -m scripts.engineering.qa generate-debt-tasks --source debt_scorecard"
    output: "reports/quality/tasks_architecture_debt_scorecard_YYYY-MM-DD-HH-MM.json"
  
  generate_specific_category:
    command: "python -m scripts.engineering.qa generate-debt-tasks --source debt_scorecard --category baseline_exemptions"
    output: "reports/quality/tasks_baseline_exemptions_YYYY-MM-DD-HH-MM.json"
  
  validate_existing_tasks:
    command: "python -m scripts.engineering.qa validate-debt-tasks --input reports/quality/tasks_architecture_debt_scorecard_YYYY-MM-DD-HH-MM.json"
    output: "validation_report.json"
```

#### Templates
```yaml
documentation_templates:
  task_template:
    fields:
      - id
      - task_category
      - metric_family
      - metric_name
      - owner
      - linked_issue
      - current_value
      - max_value
      - target_value
      - delta_to_target
      - status
      - priority
      - target_file
      - symbol_name
      - path_prefixes
      - goal
      - acceptance_criteria
      - allowed_paths
      - forbidden_paths
      - checks
      - estimated_effort
      - dependencies
      - notes
  
  category_template:
    fields:
      - category_name
      - description
      - metrics
      - priority_rules
      - effort_rules
      - validation_rules
```

#### Guidelines
- **Task Generation Guidelines**: Follow defined patterns for task generation
- **Priority Assignment Guidelines**: Use consistent priority assignment rules
- **Effort Estimation Guidelines**: Use consistent effort estimation rules
- **Validation Guidelines**: Validate all generated tasks before output
