# Cycle 4 Issue 1: Добавить thresholds для DQ доменов (OK/WARN/CRIT)
- Dashboard: bioetl-dq-v2.json
- Theme: Data Quality — домены и identity
- Proposal: Добавить thresholds для DQ доменов (OK/WARN/CRIT)
- Priority: P0
- Plan:
  1. Inspect `grafana/dashboards/bioetl-dq-v2.json` panel JSON
  2. Apply fieldConfig/description/gridPos edit for `dq-domains`
  3. Validate `pytest tests/integration/test_dashboard_operator_readability.py` and `test_dashboard_first_window_noscroll.py`
  4. Verify no overflow / DASH-FIT-004 compliance
- Acceptance: dashboard JSON valid, tests green, first-window bottom <=18
- Status: planned

- Status: CLOSED
- ClosedAt: 2026-09-26T14:36:46.051908+00:00
