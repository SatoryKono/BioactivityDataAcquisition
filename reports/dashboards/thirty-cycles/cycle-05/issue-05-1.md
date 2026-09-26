# Cycle 5 Issue 1: Добавить pagination и limit=10 в Inspect Recent Runs
- Dashboard: bioetl-run-explorer-v1.json
- Theme: Run Explorer — таблица 10 строк
- Proposal: Добавить pagination и limit=10 в Inspect Recent Runs
- Priority: P0
- Plan:
  1. Inspect `grafana/dashboards/bioetl-run-explorer-v1.json` panel JSON
  2. Apply fieldConfig/description/gridPos edit for `run-explorer-table`
  3. Validate `pytest tests/integration/test_dashboard_operator_readability.py` and `test_dashboard_first_window_noscroll.py`
  4. Verify no overflow / DASH-FIT-004 compliance
- Acceptance: dashboard JSON valid, tests green, first-window bottom <=18
- Status: planned

- Status: CLOSED
- ClosedAt: 2026-09-26T14:37:08.855965+00:00
