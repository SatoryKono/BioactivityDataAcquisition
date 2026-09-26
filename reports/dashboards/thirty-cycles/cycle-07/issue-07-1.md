# Cycle 7 Issue 1: Перенести Inspect Ranked Suspects выше Monitor Global Alerts
- Dashboard: bioetl-incident-v1.json
- Theme: Incident — ranked suspects порядок
- Proposal: Перенести Inspect Ranked Suspects выше Monitor Global Alerts для правильного triage
- Priority: P0
- Plan:
  1. Inspect `grafana/dashboards/bioetl-incident-v1.json` panel JSON
  2. Apply fieldConfig/description/gridPos edit for `incident-ranked`
  3. Validate `pytest tests/integration/test_dashboard_operator_readability.py` and `test_dashboard_first_window_noscroll.py`
  4. Verify no overflow / DASH-FIT-004 compliance
- Acceptance: dashboard JSON valid, tests green, first-window bottom <=18
- Status: planned

- Status: CLOSED
- ClosedAt: 2026-09-26T14:39:40.092276+00:00
