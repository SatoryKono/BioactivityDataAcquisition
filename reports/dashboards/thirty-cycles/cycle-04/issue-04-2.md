# Cycle 4 Issue 2: Улучшить описание Inspect Run Identity — добавить payload_ha
- Dashboard: bioetl-dq-v2.json
- Theme: Data Quality — домены и identity
- Proposal: Улучшить описание Inspect Run Identity — добавить payload_hash пояснение
- Priority: P0
- Plan:
  1. Inspect `grafana/dashboards/bioetl-dq-v2.json` panel JSON
  2. Apply fieldConfig/description/gridPos edit for `dq-domains`
  3. Validate `pytest tests/integration/test_dashboard_operator_readability.py` and `test_dashboard_first_window_noscroll.py`
  4. Verify no overflow / DASH-FIT-004 compliance
- Acceptance: dashboard JSON valid, tests green, first-window bottom <=18
- Status: planned

- Status: CLOSED
- ClosedAt: 2026-09-26T14:36:46.057094+00:00
