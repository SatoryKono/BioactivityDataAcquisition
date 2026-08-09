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
"tasks": [
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
"<список команд проверки по типу метрики>"
],
"estimated_effort": "<small|medium|large>",
"dependencies": ["<task_ids>"],
"notes": "<если есть неоднозначность измерения>"
}
]
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
