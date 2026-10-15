# DSA-06 closeout evidence (#6988)

- Date: 2026-08-06T13:25Z
- Decision: **close #6988** — freshness-aware fleet matrix shipped and locked by tests

## Acceptance mapping

| Acceptance | Evidence |
| --- | --- |
| Fleet verdict distinguishable from telemetry blind spot | Monitor Fleet Severity + Monitor Telemetry Freshness; UNKNOWN/null fail-closed (not healthy green) |
| Matrix sort critical → degraded → unknown/stale → healthy | Monitor Fleet Severity sortBy Severity desc; panel description documents order |
| Top causes paired with freshness taxonomy | Inspect Top Provider Causes + Telemetry Freshness presence gate |
| Selected-provider detail conditional | Selected Provider Details row collapsed; first-screen contract (#6572) |
| Empty selector does not dominate | Selected-provider detail behind collapsed row; range/debug collapsed |
| Provider dashboard integration tests green | test_provider_telemetry_freshness_fails_closed_when_status_is_missing; test_provider_critical_table_keeps_severity_only_scope |

## Files

- grafana/dashboards/bioetl-provider-health-v2.json
- docs/03-guides/dashboards/panels/bioetl-provider-health-v2-panels.md
- tests/integration/test_grafana_dashboard_metric_semantics.py
- tests/integration/test_grafana_dashboard_first_screen_contract.py

## Out of scope (unchanged)

- Native node graph topology (DSA-10)
- Inventing dependency edges without data contract
- New high-cardinality labels
