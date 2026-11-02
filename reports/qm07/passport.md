# Паспорт QM-07 / issue #12388

**Цель:** Доказать cold imports, корректность root seams и изоляцию установленного runtime wheel.

**Статус:** source cold imports, root seams и installed-wheel smoke закрыты harness'ом `tests/architecture/test_qm07_cold_imports.py`.

**Результаты:**
1. **Source CANDIDATE**
   - Все 30 модулей и facade `scripts.engineering.quality` импортируются из временного cwd с `-I` и явным `sys.path`; origin каждого модуля сверяется с путём в checkout.
   - Root/path seams (`architecture_debt_reduction`, `architecture_debt_task_generation`, scorecard, exemptions) сходятся к repository root текущего checkout; path/error контракты `build_module_path_key` / `resolve_registry_path` проверяются отдельно.
   - `debt_governance_gate_evaluators` не отдаёт `None` bindings (`callable`); `load_debt_scorecard` / `evaluate_debt_scorecard` и `build_architecture_quality_scorecard` вызываются успешно без записи артефактов через CLI `main()`.
2. **Installed runtime wheel**
   - Session fixture собирает wheel текущего checkout (`uv build --wheel`) и ставит его во временный venv.
   - Smoke без `PYTHONPATH`/checkout path загружает `bioetl` + `PipelineRunner` из `site-packages`; import hook блокирует `scripts.*`.

Известные source blockers quality→scripts по-прежнему зафиксированы в `tests/architecture/qm_07/test_qm07_cold_imports.py` (отдельный inventory, не отменяет wheel smoke для runtime package).
