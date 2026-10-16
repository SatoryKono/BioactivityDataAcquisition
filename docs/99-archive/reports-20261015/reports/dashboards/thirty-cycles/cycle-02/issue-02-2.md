# Cycle 2 Issue 2: Уточнить description для Review Selected Run Status — добави
- Dashboard: bioetl-runtime.json
- Theme: Pipeline Diagnostics — thresholds и noValue
- Proposal: Уточнить description для Review Selected Run Status — добавить N/A пояснение
- Priority: P0
- Plan:
  1. Inspect `grafana/dashboards/bioetl-runtime.json` panel JSON
  2. Apply fieldConfig/description/gridPos edit for `runtime-thresholds`
  3. Validate `pytest tests/integration/test_dashboard_operator_readability.py` and `test_dashboard_first_window_noscroll.py`
  4. Verify no overflow / DASH-FIT-004 compliance
- Acceptance: dashboard JSON valid, tests green, first-window bottom <=18
- Status: planned

- Status: CLOSED
- ClosedAt: 2026-09-26T14:36:03.141500+00:00
