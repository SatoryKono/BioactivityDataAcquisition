| Пункт | Результат | Evidence |
| --- | --- | --- |
| Все 30 cold imports и facade проходят отдельно, origins совпадают с manifest | PASS | `tests/architecture/test_qm07_cold_imports.py::test_source_cold_import_from_outside_cwd` |
| Пять root seams и заявленные path/error контракты проверены из другого cwd | PASS | `tests/architecture/test_qm07_cold_imports.py::test_root_seams_from_outside_cwd`, `test_root_seams_custom_roots_and_errors` |
| Изолированно установленный wheel исполняет runtime-smoke без scripts; негативный harness | PASS | session fixture `wheel_venv_python` (`uv build` + temp venv install); `test_wheel_runtime_smoke_without_scripts`, `test_wheel_harness_catches_script_imports` |
| None bindings не скрываются; scorecard/debt evaluators вызываются без записи отчётов через `main()` | PASS | `test_debt_governance_gate_evaluators_from_outside_cwd`, `test_debt_scorecard_functional_bounded`, `test_report_architecture_quality_scorecard_functional` |
