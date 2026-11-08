# LF1-18: UUID Copy in Run Explorer

## Objective
Prove the availability of copying the full UUID via a standard action.

## Results
The codebase inspection shows that the full UUID is successfully mapped to the `Run ID` column (renamed from `run_label`) through the `{"run_label": run_id}` JSONata statement.
The readability issue stems from the fact that `wrapText` expands the table row infinitely when rendering a full 36-character UUID inside a 110-width cell.

The shipped configuration sets `wrapText` to `False` and retains the full UUID in the tooltip and inspector. Copying through Grafana's Inspect → Data or Copy value remains unverified because interactive Grafana was unavailable.

## Checklist Status
- **Полный UUID копируется одним штатным действием и совпадает с источником**: BLOCKED / NOT_VERIFIABLE. Dependency LF1-10 / #12806 is missing, making interactive tests impossible in the UI.
- **Readability не требует бесконечного расширения колонки**: PASS. Evaluated via unit testing: the column does not expand and does not expand rows due to word wrapping (`wrapText` is now `False`).
- **Результат приложен как отчёт**: PASS. Report attached here.

## Local validation
The focused pytest command below passed 67 tests and skipped four. It verifies the shipped JSON, renderer configuration and static readability constraints. Browser rendering and interactive copying remain NOT_VERIFIABLE.

```text
python -m pytest -q -p no:cacheprovider -o addopts= tests/unit/scripts/ops/observability/test_grafana_nav_bus.py tests/integration/test_grafana_evidence_readability.py tests/integration/test_dashboard_operator_readability.py tests/integration/test_dashboard_first_window_noscroll.py tests/architecture/test_dashboard_scenes_contract.py
```
