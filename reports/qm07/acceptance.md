| Пункт | Результат | Evidence |
| --- | --- | --- |
| Все 30 cold imports и facade проходят отдельно, origins совпадают с manifest | PASS | `tests/architecture/test_qm07_cold_imports.py::test_source_cold_import_from_outside_cwd` |
| Пять root seams и все заявленные path/error контракты проверены из другого cwd | PASS | `tests/architecture/test_qm07_cold_imports.py::test_root_seams_from_outside_cwd` |
| Изолированно установленный wheel исполняет реальные runtime-smoke без scripts; негативный smoke harness проверен | PASS | `tests/architecture/test_qm07_cold_imports.py::test_wheel_runtime_smoke_without_scripts` and `test_wheel_harness_catches_script_imports` |
| None bindings не скрываются, два побочных output генератора учтены | PASS | `tests/architecture/test_qm07_cold_imports.py::test_debt_governance_gate_evaluators_from_outside_cwd` |
