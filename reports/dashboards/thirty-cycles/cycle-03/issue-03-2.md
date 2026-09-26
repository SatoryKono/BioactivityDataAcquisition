# Cycle 3 Issue 2: Добавить column width для provider, cause
- Dashboard: bioetl-provider-health-v2.json
- Theme: Provider Health — evidence таблица
- Proposal: Добавить column width для provider, cause
- Priority: P0
- Plan:
  1. Inspect `grafana/dashboards/bioetl-provider-health-v2.json` panel JSON
  2. Apply fieldConfig/description/gridPos edit for `provider-evidence`
  3. Validate `pytest tests/integration/test_dashboard_operator_readability.py` and `test_dashboard_first_window_noscroll.py`
  4. Verify no overflow / DASH-FIT-004 compliance
- Acceptance: dashboard JSON valid, tests green, first-window bottom <=18
- Status: planned

- Status: CLOSED
- ClosedAt: 2026-09-26T14:36:27.343147+00:00
