# Cycle 1 Issue 4: Добавить transform convertFieldType для timestamp при наличи
- Dashboard: bioetl-overview-v2.json
- Theme: Обзор — обогащение описаний SELECTED RUN
- Proposal: Добавить transform convertFieldType для timestamp при наличии
- Priority: P1
- Plan:
  1. Inspect `grafana/dashboards/bioetl-overview-v2.json` panel JSON
  2. Apply fieldConfig/description/gridPos edit for `overview-desc-enrich`
  3. Validate `pytest tests/integration/test_dashboard_operator_readability.py` and `test_dashboard_first_window_noscroll.py`
  4. Verify no overflow / DASH-FIT-004 compliance
- Acceptance: dashboard JSON valid, tests green, first-window bottom <=18
- Status: planned

- Status: CLOSED
- ClosedAt: 2026-09-26T14:35:31.017689+00:00
