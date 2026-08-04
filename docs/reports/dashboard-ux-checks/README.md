# Dashboard UX checks (gate directory)

> **Classification:** repo-only gate surface. Docs audit cycle 3 / #7433.

This directory holds **fresh** dashboard UX check reports required when
`grafana/dashboards/*.json` changes.

## Contract

- Integration guard: `tests/integration/test_dashboard_ux_report_freshness.py`
- Expected report name: `<YYYY-MM-DD>.md` for host UTC today or yesterday
- Change notes: `docs/03-guides/dashboards/dashboard-v2-updates.md`

## Historical reports

Dated residual reports from 2026-07-28 were archived to
`docs/99-archive/reports/dashboard-ux-checks/` (#7433).
