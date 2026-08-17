# Six-board panel audit registry — 2026-08-17

Scope: non-row panels on Overview, Runtime, Provider Health, DQ, Incident,
Run Explorer. Selectors: `chembl_assay` / `backfill` / `chembl_baseline` /
`64927f44-df86-533f-bcaa-1554d5105473` / `now-12h..now`.

Classification after OBS-FILL-01/03:

- `filled` — query returned series/rows in the 2026-08-17 fill pass
- `missing_required_telemetry` — empty because the scrape trust-anchor /
  current-* recordings were absent (must not look like 0 events)
- `semantic_empty` — empty is valid only when parent trust/coverage is
  OK/PRESENT (no active events)
- `static` — text / nav / instruction, no query

| Board | id | Title (abbrev) | Class |
| --- | ---: | --- | --- |
| Overview | — | 3 text/nav surfaces | static |
| Overview | — | First Action, Domain Status Tracks, Active Alerts, exact-run HTTP | filled (15) |
| Overview | — | Global Provider Status, Failed Runs, Recent Terminal Runs, Silver Rejects | missing_required_telemetry |
| Runtime | — | 6 text/instruction surfaces | static |
| Runtime | — | Selected-run identity/accounting, Failed Runs, Records by Stage, Errors, No-Records, Coverage, Status | filled (8) |
| Runtime | — | stage backlog/flow/lag/duration, error rate, workflow failures, memory, shutdown | missing_required_telemetry (22) |
| Provider | — | 3 text/nav surfaces | static |
| Provider | — | exact-run identity/accounting HTTP | filled (2) |
| Provider | — | fleet/selected health, circuit breaker, retries, latency, rate-limit, network | missing_required_telemetry (26) |
| Provider | Non-OK / Top Causes | empty tables | semantic_empty only after Telemetry Presence=PRESENT |
| DQ | — | 5 text/nav surfaces | static |
| DQ | — | exact-run identity + processed records + 2 score panels | filled (4) |
| DQ | — | current reasons, quarantine, freshness, rejects, anomalies, duration | missing_required_telemetry (23) |
| DQ | current reasons noValue | “No active reason rows. Valid only when Current DQ Status is OK” | semantic_empty (contract) |
| Incident | — | 4 text/nav surfaces | static |
| Incident | — | Status series + 2 active-alert series | filled (3) |
| Incident | Ranked Suspects + 3 domain details | empty | semantic_empty only after Status is not UNKNOWN |
| Run Explorer | — | 5 text/nav surfaces | static |
| Run Explorer | — | 11 HTTP exact-run / recent-runs panels | filled (11) |

Totals: 148 surfaces = 43 filled + 79 empty + 26 static. The 79 empties split
into missing required current telemetry (majority) vs semantic-empty event
tables that stay empty after the trust anchor is restored.

Re-score command after container recreate from this SHA:

```
python scripts/ops/observability/grafana/audit_live_grafana_panels.py \
  --pipeline chembl_assay --workflow chembl_baseline --run-type backfill \
  --range-hours 12
```
