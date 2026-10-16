# Cycle 6 Issue 1: Добавить background colorMode для Review Exact Replay Readin
- Dashboard: bioetl-control-plane-v1.json
- Theme: Trust — replay readiness KPI
- Proposal: Добавить background colorMode для Review Exact Replay Readiness stat
- Priority: P0
- Plan:
  1. Inspect `grafana/dashboards/bioetl-control-plane-v1.json` panel JSON
  2. Apply fieldConfig/description/gridPos edit for `trust-kpi`
  3. Validate `pytest tests/integration/test_dashboard_operator_readability.py` and `test_dashboard_first_window_noscroll.py`
  4. Verify no overflow / DASH-FIT-004 compliance
- Acceptance: dashboard JSON valid, tests green, first-window bottom <=18
- Status: planned

- Status: CLOSED
- ClosedAt: 2026-09-26T14:37:35.827232+00:00
