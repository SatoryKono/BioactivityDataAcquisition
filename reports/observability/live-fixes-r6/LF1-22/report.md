# LF1-22 Overview status matrix

Issue: #12818. UID: `bioetl-overview-v2`.

- Source SHA: `48dc0257ed980decaf0d8bf4c209c7e39309a4c4` (`origin/main`).
- Observation UTC: `2026-11-09T08:35:23Z` through `2026-11-09T08:36:29Z`.
- Local Ops HTTP: `http://127.0.0.1:8000` (health server from this checkout; `src/` and `grafana/` match that SHA).
- Deploy SHA, Grafana and Prometheus: `NOT_VERIFIABLE`. `docker` is not installed, so the monitoring compose stack was not started. No panel text or color was read from a rendered dashboard. No temporary dashboard injection was saved.

## Status panels

Taken from the shipped dashboard JSON. Panels 9481 and 9604 are on this UID. Panel 9603 is the status table that 9604 reduces.

| Panel | Title | Source | noValue | Null mapping | Success mapping |
| --- | --- | --- | --- | --- | --- |
| 9604 | Review Overall Verdict | dashboard frame from 9002 | `UNKNOWN` | `UNKNOWN` / gray | `OK` / green only for the value `OK` |
| 9603 | Review Selected Run Status | dashboard frame from 9002 | `UNKNOWN` | none on defaults | column mappings follow the saved verdict |
| 9481 | Review Provider Check | dashboard frame from 9002, field `check_result_display` | `UNKNOWN` | `UNKNOWN` / gray | `OK` / green only for the value `OK` |
| 9482 | Review Contract Exclusions | dashboard frame from 9002 | `UNKNOWN` | status text is not defaulted to OK | regex colors `OK` / `WARN` / `CRIT` / `ERROR` |

Donor query of panel 9002: `GET /ops/observability/selected-run-status`. The value mapping of 9604 and 9481 includes `QUERY ERROR` as red and `НЕТ ЗАПУСКОВ` as gray. The first threshold color is gray, not green.

## Local HTTP matrix

These are semantic HTTP responses. They are not Grafana frame renders.

| Case | Request | HTTP | Body | Expected panel token | Render |
| --- | --- | --- | --- | --- | --- |
| valid empty catalog | `pipeline=chembl_assay&run_id=-&run_type=incremental` | 200 | `verdict=НЕТ ЗАПУСКОВ`, `reason=no_runs_in_scope`, `execution_state=UNKNOWN` | `НЕТ ЗАПУСКОВ`, not `OK` | `NOT_VERIFIABLE` |
| not found | `run_id=00000000-0000-0000-0000-000000000000` | 200 | `verdict=UNKNOWN`, `reason=run_not_found` | `UNKNOWN`, not `OK` | `NOT_VERIFIABLE` |
| saved historical UUID | `pipeline=chembl_activity&run_id=8ed593ce-3b75-56e0-a337-192953048582` | 200 | `verdict=UNKNOWN`, `reason=run_not_found` | `UNKNOWN` | `NOT_VERIFIABLE` |
| missing parameter | no `pipeline` | 400 | `Missing required query parameter: pipeline` | transport failure, not a 200 verdict | `NOT_VERIFIABLE` |
| unknown path | `/ops/observability/selected-run-status-missing` | 404 | `Not Found` | not a semantic 200 | `NOT_VERIFIABLE` |
| closed port | `127.0.0.1:9` | none | connection refused | request failure, not `OK` | `NOT_VERIFIABLE` |
| saved success | a mounted report with verdict `OK` | `NOT_RUN` | `index_state=tree_missing` at `reports/run-reports` | no saved success row exists | `NOT_VERIFIABLE` |

HTTP 200 with `НЕТ ЗАПУСКОВ` or `UNKNOWN` is not an HTTP failure. HTTP 400, HTTP 404 and connection refused are request failures and were not labeled `OK`.

## Decision

No generator change. The shipped mappings do not treat null, `UNKNOWN`, `QUERY ERROR` or `НЕТ ЗАПУСКОВ` as `OK`. A live color was not observed, so this is not a rendered PASS. No injection was added to the provisioned JSON.

## Checklist

- Status-panel matrix: partial. Static contract and local HTTP cases are recorded. Saved-success and rendered color are `NOT_RUN` / `NOT_VERIFIABLE`.
- Errors are not mapped to success in the shipped JSON. Temporary injection: none.
- This report, `machine_readable_receipt.json` and `checksums.txt` are the evidence. Deploy SHA remains `NOT_VERIFIABLE`.
