# LF1-24 Incident status matrix

Issue: #12820. UID: `bioetl-incident-v1`.

- Source SHA: `48dc0257ed980decaf0d8bf4c209c7e39309a4c4` (`origin/main`).
- Observation UTC: `2026-11-09T08:35:23Z`.
- Local Ops HTTP: `http://127.0.0.1:8000`.
- Deploy SHA, Grafana and Prometheus: `NOT_VERIFIABLE`. `docker` is not installed. Prometheus queries were not executed. No dashboard injection was saved.
- Panels 9481 and 9604 are not on this UID. They remain on `bioetl-overview-v2` and are recorded in LF1-22.

## Status panels

Stat, gauge, state-timeline and the selected-run status table. `null` is the special-null mapping text.

| Panel | Title | Datasource | noValue | null |
| --- | --- | --- | --- | --- |
| 9401 | Monitor Scope Status | prometheus | `UNKNOWN` | `UNKNOWN` |
| 2006 | Track Alert State History | prometheus | `GAP` | none |
| 2101 | Review Selected Run Status | Ops HTTP | `UNKNOWN` | none |
| 18940 | Monitor Pipeline Status | prometheus | `UNKNOWN` | `UNKNOWN` |
| 9102 | Monitor Coverage | prometheus | `UNKNOWN` | `UNKNOWN` |
| 9463 | Review Total Run Duration | dashboard | `Not recorded` | none |
| 237 | Monitor Worst Stage Lag | prometheus | `UNKNOWN` | `UNKNOWN` |
| 16 | Monitor Active Blocker Count | prometheus | `UNKNOWN` | `UNKNOWN` |
| 205 | Monitor Failed Runs | prometheus | `UNKNOWN` | `UNKNOWN` |
| 230 | Monitor Pipeline Alerts | prometheus | `UNKNOWN` | `UNKNOWN` |
| 9996 | Track Failed Workflow Runs | prometheus | `0` | `UNKNOWN` |
| 236 | Monitor No-Records Runs | prometheus | `UNKNOWN` | `UNKNOWN` |
| 9997 | Track Failed Workflow Steps | prometheus | `0` | `UNKNOWN` |
| 21 | Monitor Memory Pressure | prometheus | `UNKNOWN` | `UNKNOWN` |
| 891 | Monitor Replay | prometheus | `UNKNOWN` | `UNKNOWN` |
| 892 | Track Checkpoint | prometheus | `UNKNOWN` | `UNKNOWN` |
| 893 | Monitor Ledger | prometheus | `UNKNOWN` | `UNKNOWN` |
| 907 | Monitor Telemetry | prometheus | `UNKNOWN` | `UNKNOWN` |
| 4 | Inspect DQ Alert Conditions | prometheus | `UNKNOWN` | `UNKNOWN` |
| 5 | Inspect Control Plane Alerts | prometheus | `UNKNOWN` | `UNKNOWN` |
| 6 | Inspect Provider Alerts | prometheus | `UNKNOWN` | `UNKNOWN` |
| 259 | Inspect Global Provider Alert Conditions | prometheus | `UNKNOWN` | `UNKNOWN` |
| 7 | Inspect Entities Stale Over 24h | prometheus | `UNKNOWN` | `UNKNOWN` |
| 8804 | Track Global Read Failures | prometheus | `NO OBSERVATIONS` | `NO OBSERVATIONS` |
| 136 | Monitor Global Read Failures (30m) | prometheus | `NO OBSERVATIONS` | `NO OBSERVATIONS` |
| 122 | Track Missing Lineage | prometheus | `NO OBSERVATIONS` | `NO OBSERVATIONS` |
| 137 | Track Lineage Failures | prometheus | `NO OBSERVATIONS` | `NO OBSERVATIONS` |
| 2 | Track Ledger Failures | prometheus | `UNKNOWN` | `UNKNOWN` |
| 130 | Track Replay Blockers | prometheus | `UNKNOWN` | `UNKNOWN` |
| 1 | Track Manifest Failures | prometheus | `UNKNOWN` | `UNKNOWN` |
| 3 | Track Incompatibilities | prometheus | `NO OBSERVATIONS` | `NO OBSERVATIONS` |
| 104 | Track Unreconstructable | prometheus | `NO OBSERVATIONS` | `NO OBSERVATIONS` |
| 120 | Track Replay Drift | prometheus | `NO OBSERVATIONS` | `NO OBSERVATIONS` |
| 132 | Monitor Manifest (30m) | prometheus | `UNKNOWN` | `UNKNOWN` |
| 101 | Track Load Failures | prometheus | `NO OBSERVATIONS` | `NO OBSERVATIONS` |
| 133 | Monitor Ledger (30m) | prometheus | `UNKNOWN` | `UNKNOWN` |
| 102 | Track Save Failures | prometheus | `NO OBSERVATIONS` | `NO OBSERVATIONS` |
| 9491 | Inspect Telemetry Coverage | prometheus | `UNKNOWN` | none; `0` maps to `PRESENT`, `1` maps to `MISSING` |
| 103 | Track Global Admin Failures | prometheus | `NO OBSERVATIONS` | `NO OBSERVATIONS` |
| 121 | Track Peak Replay Lag | prometheus | `UNKNOWN` | `UNKNOWN` |
| 220 | Monitor Runtime Error Rate | prometheus | `UNKNOWN` | `UNKNOWN` |

Numeric `0` maps to `OK` only on panels whose contract is a measured severity of zero (`9401`, `18940`, `21`, `891` and the same family). Their null mapping and `noValue` stay `UNKNOWN`, so an empty series is not that measured zero. Panels 9996 and 9997 keep the shipped workflow-band contract: `noValue` `0` displays `0 · valid empty range` in gray, and the null mapping remains `UNKNOWN`. That contract is already described for the workflow band. It was not changed, because no rendered query-error was observed and the Prometheus range was not executable here. None of these expressions use `or vector(0)`.

## HTTP panel 2101

Panel 2101 reads `/ops/observability/selected-run-status`. The same local calls as LF1-22 apply: HTTP 200 `НЕТ ЗАПУСКОВ` for an empty catalog, HTTP 200 `UNKNOWN` / `run_not_found` for an absent UUID, HTTP 400 for a missing `pipeline`. Those 200 responses are not request failures. Rendered table color is `NOT_VERIFIABLE`.

## Decision

No generator change. Empty Prometheus results were not observed as green `OK` in Grafana, because Grafana and Prometheus are absent. The static null mappings do not use `OK`.

## Checklist

- Each status panel has a static mapping row. Live success, empty series, missing evidence and request-failure colors are `NOT_VERIFIABLE` for Prometheus panels.
- Shipped null text is not `OK`. No injection was added.
- Evidence is this report plus the receipt and checksums. Deploy SHA is `NOT_VERIFIABLE`.
