# Cycle 7 Issue 3: Улучшить description для Track Alert State History — добавит
- Dashboard: bioetl-incident-v1.json
- Theme: Incident — ranked suspects порядок
- Proposal: Улучшить description для Track Alert State History — добавить pending vs firing
- Priority: P1
- Plan:
  1. Inspect `grafana/dashboards/bioetl-incident-v1.json` panel JSON
  2. Apply fieldConfig/description/gridPos edit for `incident-ranked`
  3. Validate `pytest tests/integration/test_dashboard_operator_readability.py` and `test_dashboard_first_window_noscroll.py`
  4. Verify no overflow / DASH-FIT-004 compliance
- Acceptance: dashboard JSON valid, tests green, first-window bottom <=18
- Status: planned

- Status: CLOSED
- ClosedAt: 2026-09-26T14:39:40.102363+00:00
